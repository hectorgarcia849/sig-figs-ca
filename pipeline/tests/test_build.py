"""Tests for the build runner, using small made-up transformers instead of real data.

The made-up build has one staged dataset with two releases ("numbers") and two
model datasets: "totals" (the sum of the numbers in each release) and
"doubled" (each total times two), so "doubled" must run after "totals".
"""

import json
from datetime import date

import duckdb
import pytest

from public_spend_tracker_pipeline.build.run import BuildError, file_sha256, run_build
from public_spend_tracker_pipeline.build.serving import Serving
from public_spend_tracker_pipeline.common.logs import start_logging, stop_logging
from public_spend_tracker_pipeline.common.paths import (
    BUILD_MANIFEST_FILE_NAME,
    BUILD_WORK_FOLDER_PREFIX,
    DATABASE_FILE_NAME,
    MODEL,
    SERVING,
    STAGED,
)
from public_spend_tracker_pipeline.transform.base import (
    CheckResult,
    Transformer,
    expect_no_rows,
    has_rows,
)
from public_spend_tracker_pipeline.transform.staged_statcan import SourceChangedError

BUILD_ID = "20261115-153000"
OLDER = date(2024, 11, 28)
NEWER = date(2025, 11, 27)


class Numbers(Transformer):
    """A made-up staged dataset: three numbers per release."""

    name = "numbers"
    description = "Made-up numbers"
    stage = STAGED

    def __init__(self, release: date, offset: int = 0, changed: bool = False):
        self.release = release
        self.offset = offset
        self.changed = changed
        self.ran = False

    def transform(self, db):
        self.ran = True
        if self.changed:
            raise SourceChangedError("numbers release 2025-11-27: the columns changed")
        return db.sql(f"SELECT n + {self.offset} AS n FROM (VALUES (1), (2), (3)) AS t(n)")

    def checks(self, db):
        return [has_rows(db, self.name)]


class Totals(Transformer):
    name = "totals"
    description = "Sum of the numbers in each release"
    stage = MODEL
    inputs = ("numbers",)

    def transform(self, db):
        return db.sql("SELECT release, sum(n) AS total FROM numbers GROUP BY release")


class Doubled(Transformer):
    name = "doubled"
    description = "Each total times two"
    stage = MODEL
    inputs = ("totals",)

    def __init__(self, fail_check: bool = False):
        self.fail_check = fail_check

    def transform(self, db):
        return db.sql("SELECT release, total * 2 AS doubled FROM totals")

    def checks(self, db) -> list[CheckResult]:
        limit = 0 if self.fail_check else 1000
        return [
            expect_no_rows(
                db, "doubled: under the limit", f"SELECT * FROM doubled WHERE doubled > {limit}"
            )
        ]


def staged():
    return [Numbers(OLDER), Numbers(NEWER, offset=10)]


@pytest.fixture
def log_text(tmp_path):
    """Logging to a file for the test; returns a function that reads the file."""
    path = start_logging("build", BUILD_ID, tmp_path)
    yield lambda: path.read_text(encoding="utf-8")
    stop_logging()


def saved_items(data_root):
    """Everything a build left in the data folder, apart from logs."""
    return sorted(
        path.relative_to(data_root).as_posix()
        for path in data_root.rglob("*")
        if path.is_file() and path.parts[len(data_root.parts)] != "logs"
    )


def test_complete_build_saves_every_file(tmp_path, log_text):
    serving = run_build(staged(), [Doubled(), Totals()], build_id=BUILD_ID, data_root=tmp_path)

    assert serving == tmp_path / SERVING / f"build={BUILD_ID}"
    assert saved_items(tmp_path) == [
        f"model/dataset=doubled/build={BUILD_ID}/data.parquet",
        f"model/dataset=totals/build={BUILD_ID}/data.parquet",
        f"serving/build={BUILD_ID}/{BUILD_MANIFEST_FILE_NAME}",
        f"serving/build={BUILD_ID}/{DATABASE_FILE_NAME}",
        "staged/dataset=numbers/release=2024-11-28/data.parquet",
        "staged/dataset=numbers/release=2025-11-27/data.parquet",
    ]
    assert not list(tmp_path.glob(f"{BUILD_WORK_FOLDER_PREFIX}*"))  # work folder removed
    assert "finished" in log_text()


def test_model_runs_after_its_inputs_and_sees_every_release(tmp_path, log_text):
    serving = run_build(staged(), [Doubled(), Totals()], build_id=BUILD_ID, data_root=tmp_path)

    database = duckdb.connect(str(serving / DATABASE_FILE_NAME), read_only=True)
    rows = database.sql("SELECT release, doubled FROM doubled ORDER BY release").fetchall()
    assert rows == [(OLDER, 12), (NEWER, 72)]  # (1+2+3)*2 and (11+12+13)*2


def test_manifest_records_datasets_checks_and_fingerprints(tmp_path, log_text):
    serving = run_build(staged(), [Totals(), Doubled()], build_id=BUILD_ID, data_root=tmp_path)
    manifest = json.loads((serving / BUILD_MANIFEST_FILE_NAME).read_text(encoding="utf-8"))

    assert manifest["build_id"] == BUILD_ID
    assert set(manifest["code"]) == {"git_commit", "uncommitted_changes"}
    datasets = {(d["name"], d["release"]): d for d in manifest["datasets"]}
    assert set(datasets) == {
        ("numbers", "2024-11-28"),
        ("numbers", "2025-11-27"),
        ("totals", None),
        ("doubled", None),
    }
    doubled = datasets[("doubled", None)]
    assert doubled["rows"] == 2
    assert doubled["inputs"] == ["totals"]
    assert doubled["checks"] == [
        {"name": "doubled: under the limit", "passed": True, "detail": "no bad rows"}
    ]
    assert doubled["sha256"] == file_sha256(tmp_path / doubled["file"])
    assert manifest["database"]["sha256"] == file_sha256(tmp_path / manifest["database"]["file"])


def test_failed_check_stops_the_build_and_saves_nothing(tmp_path, log_text):
    with pytest.raises(BuildError, match="1 of 1 checks failed for doubled"):
        run_build(staged(), [Totals(), Doubled(fail_check=True)], BUILD_ID, data_root=tmp_path)

    assert saved_items(tmp_path) == []
    assert "CHECK FAILED doubled: under the limit: 2 bad rows" in log_text()


def test_source_change_is_logged_and_stops_the_build(tmp_path, log_text):
    changed = [Numbers(OLDER), Numbers(NEWER, changed=True)]
    with pytest.raises(BuildError, match="Statistics Canada changed numbers"):
        run_build(changed, [Totals()], build_id=BUILD_ID, data_root=tmp_path)

    assert saved_items(tmp_path) == []
    assert "SOURCE CHANGED numbers release 2025-11-27: the columns changed" in log_text()


def test_missing_input_is_reported_before_anything_runs(tmp_path, log_text):
    class NeedsSomethingElse(Totals):
        name = "needs_something_else"
        inputs = ("numbers", "prices")

    numbers = staged()
    with pytest.raises(BuildError, match="needs_something_else needs prices"):
        run_build(numbers, [NeedsSomethingElse()], build_id=BUILD_ID, data_root=tmp_path)
    assert not any(transformer.ran for transformer in numbers)


def test_datasets_needing_each_other_in_a_loop_are_reported(tmp_path, log_text):
    class First(Totals):
        name = "first"
        inputs = ("second",)

    class Second(Totals):
        name = "second"
        inputs = ("first",)

    with pytest.raises(BuildError, match="loop"):
        run_build(staged(), [First(), Second()], build_id=BUILD_ID, data_root=tmp_path)


# --- The serving step -------------------------------------------------------


class TinyServing(Serving):
    """A stand-in serving layer: one view over "doubled", and one check on it."""

    tables = ()

    def __init__(self, sql_file, fail_check=False):
        super().__init__(sql_file)
        self.fail_check = fail_check

    def prepare(self, db, build_id, built_at):
        self.create_views(db)

    def checks(self, db):
        limit = 0 if self.fail_check else 1000
        return [
            expect_no_rows(
                db,
                "doubled_view: under the limit",
                f"SELECT * FROM doubled_view WHERE doubled > {limit}",
            )
        ]


@pytest.fixture
def tiny_sql(tmp_path):
    path = tmp_path / "tiny_serving.sql"
    path.write_text("CREATE OR REPLACE VIEW doubled_view AS SELECT * FROM doubled;\n")
    return path


def test_serving_views_are_saved_inside_the_database(tmp_path, log_text, tiny_sql):
    data_root = tmp_path / "data"
    serving = run_build(
        staged(), [Totals(), Doubled()], build_id=BUILD_ID, data_root=data_root,
        serving=TinyServing(tiny_sql),
    )  # fmt: skip

    database = duckdb.connect(str(serving / DATABASE_FILE_NAME), read_only=True)
    assert database.sql("SELECT count(*) FROM doubled_view").fetchall() == [(2,)]
    manifest = json.loads((serving / BUILD_MANIFEST_FILE_NAME).read_text(encoding="utf-8"))
    assert manifest["serving"]["sha256"] == file_sha256(tiny_sql)
    assert manifest["serving"]["checks"][0]["passed"] is True


def test_failed_serving_check_stops_the_build_and_saves_nothing(tmp_path, log_text, tiny_sql):
    data_root = tmp_path / "data"
    with pytest.raises(BuildError, match="checks failed for serving views"):
        run_build(
            staged(), [Totals(), Doubled()], build_id=BUILD_ID, data_root=data_root,
            serving=TinyServing(tiny_sql, fail_check=True),
        )  # fmt: skip
    assert saved_items(data_root) == []
    assert "CHECK FAILED doubled_view: under the limit" in log_text()
