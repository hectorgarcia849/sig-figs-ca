"""Build the database: stage every download, build the model, check everything, then save.

Run it from the repository root with:

    uv run python -m public_spend_tracker_pipeline.build.run      (or: just build)

One build:

    1. Starts a log and takes an ID from the current time, e.g. 20261115-153000.
    2. Finds every complete download of every Statistics Canada table.
    3. Staged step: turns every downloaded release into a staged dataset and
       checks it. Results go to a temporary work folder for now.
    4. Model step: runs the model transformers in the order their inputs need.
       Each staged input is offered as one table holding every release, with
       a "release" column.
    5. Serving step: adds build_info and the measure views from
       schema/serving.sql (real dollars, per person, share of GDP), and
       checks the views.
    6. Only once every check has passed, saves:
           staged/...       moved from the work folder into place
           model/dataset=<name>/build=<id>/data.parquet   each model dataset
           serving/build=<id>/fiscal.duckdb                the database
           serving/build=<id>/build_manifest.json          how it was built
       The manifest is written last: a build is complete only once it exists.
    7. Logs a summary.

If anything goes wrong the build stops, the log says why (look for
SOURCE CHANGED or CHECK FAILED), and nothing but the log is saved.

A build never changes serving/current.json. It produces a candidate; approving
and releasing a build is a separate step.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from graphlib import CycleError, TopologicalSorter
from pathlib import Path

import duckdb

from public_spend_tracker_pipeline.build.serving import Serving
from public_spend_tracker_pipeline.common.logs import (
    CHECK_FAILED,
    SOURCE_CHANGED,
    start_logging,
    stop_logging,
)
from public_spend_tracker_pipeline.common.paths import (
    BUILD_MANIFEST_FILE_NAME,
    DATABASE_FILE_NAME,
    MANIFEST_FILE_NAME,
    build_work_folder,
    complete_releases,
    model_file,
    new_build_id,
    raw_release_folder,
    raw_table_folder,
    serving_build_folder,
    staged_file,
)
from public_spend_tracker_pipeline.common.settings import (
    DATA_ROOT,
    REPOSITORY_ROOT,
    STATCAN_TABLES,
    StatCanTable,
)
from public_spend_tracker_pipeline.extract.statcan import SOURCE_NAME
from public_spend_tracker_pipeline.transform.base import CheckResult, Transformer, sql_text
from public_spend_tracker_pipeline.transform.model_context import Context
from public_spend_tracker_pipeline.transform.model_reference import Functions, Jurisdictions
from public_spend_tracker_pipeline.transform.model_sources import Sources
from public_spend_tracker_pipeline.transform.model_spending import MunicipalTransfers, Spending
from public_spend_tracker_pipeline.transform.staged_statcan import (
    SourceChangedError,
    StagedStatCanTable,
)
from public_spend_tracker_pipeline.transform.statcan_sql import source_id

log = logging.getLogger(__name__)

# Files are fingerprinted in pieces of this size, so large files never need to
# fit in memory at once.
FINGERPRINT_CHUNK_BYTES = 1024 * 1024

# The name the database file is known by while the build writes to it, and
# DuckDB's name for the in-memory database the build works in.
DATABASE_ALIAS = "serving_database"
IN_MEMORY_DATABASE = "memory"


class BuildError(Exception):
    """The build stopped. The message says why; details are in the log."""


@dataclass
class DatasetRecord:
    """What the build manifest records about one dataset.

    file and sha256 are filled in once the dataset is saved. file is relative
    to the data folder, so it reads the same locally and in the cloud bucket.
    """

    name: str
    stage: str
    description: str
    inputs: tuple[str, ...]
    release: date | None
    rows: int
    checks: list[CheckResult]
    file: str = ""
    sha256: str = ""


@dataclass
class Build:
    """Where one build writes, and what it has produced so far."""

    build_id: str
    data_root: Path
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_clock: float = field(default_factory=time.monotonic)
    staged: list[DatasetRecord] = field(default_factory=list)
    model: list[DatasetRecord] = field(default_factory=list)
    serving_checks: list[CheckResult] = field(default_factory=list)

    @property
    def work_root(self) -> Path:
        """The temporary folder staged files go to until the build passes."""
        return build_work_folder(self.build_id, self.data_root)

    @property
    def serving_folder(self) -> Path:
        return serving_build_folder(self.build_id, self.data_root)


# --- What to build ----------------------------------------------------------


def find_releases(data_root: Path = DATA_ROOT) -> dict[StatCanTable, list[Path]]:
    """Every complete download of every table, oldest first. Stops if a table has none."""
    releases = {}
    for table in STATCAN_TABLES:
        table_folder = raw_table_folder(SOURCE_NAME, table.product_id, data_root)
        dates = complete_releases(table_folder)
        if not dates:
            raise BuildError(
                f"No complete download of table {table.product_id} {table.name} "
                f"in {table_folder}. Run extract first."
            )
        releases[table] = [
            raw_release_folder(SOURCE_NAME, table.product_id, release, data_root)
            for release in dates
        ]
    return releases


def latest_releases(releases: dict[StatCanTable, list[Path]]) -> list[tuple[StatCanTable, Path]]:
    """Each table with the folder of its newest release."""
    return [(table, folders[-1]) for table, folders in releases.items()]


def staged_transformers(releases: dict[StatCanTable, list[Path]]) -> list[Transformer]:
    """One staged transformer for every downloaded release of every table."""
    return [
        StagedStatCanTable(table, folder)
        for table, folders in releases.items()
        for folder in folders
    ]


def model_transformers(releases: dict[StatCanTable, list[Path]]) -> list[Transformer]:
    """The model transformers. The runner works out the order they run in."""
    return [
        Jurisdictions(),
        Functions(),
        Spending(),
        MunicipalTransfers(),
        Context(),
        Sources(latest_releases(releases)),
    ]


# --- Running a build --------------------------------------------------------


def run_build(
    staged: Sequence[Transformer],
    model: Sequence[Transformer],
    sources: Sequence[tuple[StatCanTable, Path]] = (),
    build_id: str | None = None,
    data_root: Path = DATA_ROOT,
    serving: Serving | None = None,
) -> Path:
    """Run a whole build and return its serving folder. Raises BuildError if it stops.

    staged   Staged transformers, one per source release.
    model    Model transformers, in any order.
    sources  The download releases used, recorded in the build manifest.
    serving  The measure views and build_info to add (main() passes Serving()).
             Leave empty to save only the model tables, as some tests do.
    """
    build = Build(build_id or new_build_id(), data_root)
    model_in_order = dependency_order(staged, model)
    log.info(f"Build {build.build_id}: {len(staged)} staged and {len(model)} model datasets")

    try:
        for transformer in staged:
            # A fresh database for each table keeps memory low: the big CPI
            # table is let go of as soon as it is saved.
            with duckdb.connect() as db:
                build.staged.append(_stage(db, transformer, build))

        with duckdb.connect() as db:
            _offer_staged_inputs(db, build)
            for transformer in model_in_order:
                build.model.append(_run_model(db, transformer))
            if serving is not None:
                build.serving_checks = _prepare_serving(db, serving, build)

            # Every check has passed: save everything.
            _save_staged(build)
            _save_model(db, build)
            database = _save_database(db, build, serving)
        _write_build_manifest(build, sources, database, serving)
    finally:
        shutil.rmtree(build.work_root, ignore_errors=True)

    _log_summary(build, database)
    return build.serving_folder


def dependency_order(
    staged: Sequence[Transformer], model: Sequence[Transformer]
) -> list[Transformer]:
    """The model transformers in an order where each runs after its inputs.

    Stops before anything runs if two datasets share a name, an input is not
    produced by any step, or datasets need each other in a loop.
    """
    staged_names = {transformer.name for transformer in staged}
    by_name: dict[str, Transformer] = {}
    for transformer in model:
        if transformer.name in by_name or transformer.name in staged_names:
            raise BuildError(f"Two datasets are named {transformer.name!r}")
        by_name[transformer.name] = transformer

    produced = staged_names | set(by_name)
    for transformer in model:
        missing = [name for name in transformer.inputs if name not in produced]
        if missing:
            raise BuildError(
                f"{transformer.name} needs {', '.join(missing)}, which no step produces"
            )

    needs = {
        transformer.name: {name for name in transformer.inputs if name in by_name}
        for transformer in model
    }
    try:
        order = list(TopologicalSorter(needs).static_order())
    except CycleError as error:
        raise BuildError(f"These datasets need each other in a loop: {error.args[1]}") from None
    return [by_name[name] for name in order]


def _stage(db: duckdb.DuckDBPyConnection, transformer: Transformer, build: Build) -> DatasetRecord:
    """Run one staged transformer, check it, and write it to the work folder."""
    if transformer.release is None:
        raise BuildError(f"Staged dataset {transformer.name} does not say which release it read")
    try:
        transformer.transform(db).create(transformer.name)
    except SourceChangedError as error:
        log.error(f"{SOURCE_CHANGED} {error}")
        raise BuildError(
            f"Statistics Canada changed {transformer.name} (see {SOURCE_CHANGED} in the log)"
        ) from None

    record = _check(db, transformer)
    path = staged_file(transformer.name, transformer.release, build.work_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_parquet(db, transformer.name, path)
    return record


def _run_model(db: duckdb.DuckDBPyConnection, transformer: Transformer) -> DatasetRecord:
    """Run one model transformer and check it. Its result stays in the database for later steps."""
    transformer.transform(db).create(transformer.name)
    return _check(db, transformer)


def _check(db: duckdb.DuckDBPyConnection, transformer: Transformer) -> DatasetRecord:
    """Run a dataset's checks. Logs each failure, then stops the build if any failed."""
    label = transformer.name
    if transformer.release is not None:
        label += f" release {transformer.release}"

    rows = db.sql(f"SELECT count(*) FROM {transformer.name}").fetchall()[0][0]
    results = transformer.checks(db)
    _stop_if_any_failed(results, label)

    log.info(f"{label}: {rows:,} rows, {len(results)} checks passed")
    return DatasetRecord(
        name=transformer.name,
        stage=transformer.stage,
        description=transformer.description,
        inputs=tuple(transformer.inputs),
        release=transformer.release,
        rows=rows,
        checks=results,
    )


def _prepare_serving(
    db: duckdb.DuckDBPyConnection, serving: Serving, build: Build
) -> list[CheckResult]:
    """Add build_info and the measure views, then check the views."""
    serving.prepare(db, build.build_id, build.started_at)
    results = serving.checks(db)
    _stop_if_any_failed(results, "serving views")
    log.info(f"serving views: {len(results)} checks passed")
    return results


def _stop_if_any_failed(results: list[CheckResult], label: str) -> None:
    """Log each failed check, then stop the build if any failed."""
    failed = [result for result in results if not result.passed]
    for result in failed:
        log.error(f"{CHECK_FAILED} {result.name}: {result.detail}")
    if failed:
        raise BuildError(
            f"{len(failed)} of {len(results)} checks failed for {label} "
            f"(see {CHECK_FAILED} in the log)"
        )


def _offer_staged_inputs(db: duckdb.DuckDBPyConnection, build: Build) -> None:
    """Make each staged dataset available as one table holding every release.

    The release comes from the "release=..." folder in each file's path, as a
    "release" column.
    """
    files_by_dataset: dict[str, list[str]] = defaultdict(list)
    for record in build.staged:
        path = staged_file(record.name, record.release, build.work_root)
        files_by_dataset[record.name].append(sql_text(str(path)))

    for dataset, files in files_by_dataset.items():
        db.sql(f"""
            CREATE VIEW {dataset} AS
            SELECT * EXCLUDE (dataset)
            FROM read_parquet(
                [{", ".join(files)}],
                hive_partitioning = true,
                hive_types = {{'release': DATE}}
            )
        """)


# --- Saving -----------------------------------------------------------------


def _save_staged(build: Build) -> None:
    """Move the staged files from the work folder into place."""
    for record in build.staged:
        work_path = staged_file(record.name, record.release, build.work_root)
        final_path = staged_file(record.name, record.release, build.data_root)
        final_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(work_path, final_path)
        _record_file(record, final_path, build.data_root)


def _save_model(db: duckdb.DuckDBPyConnection, build: Build) -> None:
    """Write each model dataset to its Parquet file."""
    for record in build.model:
        path = model_file(record.name, build.build_id, build.data_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_parquet(db, record.name, path)
        _record_file(record, path, build.data_root)


def _save_database(db: duckdb.DuckDBPyConnection, build: Build, serving: Serving | None) -> Path:
    """Write the database file the API will serve: the tables, then the views inside it."""
    path = build.serving_folder / DATABASE_FILE_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    tables = [record.name for record in build.model]
    if serving is not None:
        tables += serving.tables

    db.sql(f"ATTACH {sql_text(str(path))} AS {DATABASE_ALIAS}")
    for table in tables:
        db.sql(f"CREATE TABLE {DATABASE_ALIAS}.{table} AS SELECT * FROM {table}")
    if serving is not None:
        # Switch to the file so the views are created inside it, then switch back.
        db.sql(f"USE {DATABASE_ALIAS}")
        serving.create_views(db)
        db.sql(f"USE {IN_MEMORY_DATABASE}")
    db.sql(f"DETACH {DATABASE_ALIAS}")
    return path


def _write_parquet(db: duckdb.DuckDBPyConnection, table: str, path: Path) -> None:
    db.sql(f"COPY {table} TO {sql_text(str(path))} (FORMAT parquet)")


def _record_file(record: DatasetRecord, path: Path, data_root: Path) -> None:
    """Note where a dataset was saved, and its fingerprint."""
    record.file = path.relative_to(data_root).as_posix()
    record.sha256 = file_sha256(path)


def file_sha256(path: Path) -> str:
    """A fingerprint of a file's contents: it changes if even one byte changes."""
    fingerprint = hashlib.sha256()
    with open(path, "rb") as file:
        while chunk := file.read(FINGERPRINT_CHUNK_BYTES):
            fingerprint.update(chunk)
    return fingerprint.hexdigest()


# --- The build manifest -----------------------------------------------------


def _write_build_manifest(
    build: Build,
    sources: Sequence[tuple[StatCanTable, Path]],
    database: Path,
    serving: Serving | None,
) -> None:
    """Record how this build was made. Written last: its presence marks a complete build."""
    finished_at = datetime.now(UTC)
    manifest = {
        "build_id": build.build_id,
        "started_at": build.started_at.isoformat(timespec="seconds"),
        "finished_at": finished_at.isoformat(timespec="seconds"),
        "duration_seconds": round(time.monotonic() - build.started_clock, 1),
        "code": _code_version(),
        "versions": {"python": platform.python_version(), "duckdb": duckdb.__version__},
        "sources": [_source_entry(table, folder) for table, folder in sources],
        "datasets": [_dataset_entry(record) for record in build.staged + build.model],
        "database": {
            "file": database.relative_to(build.data_root).as_posix(),
            "sha256": file_sha256(database),
        },
        "serving": _serving_entry(build, serving),
    }
    text = json.dumps(manifest, indent=2, ensure_ascii=False)
    (build.serving_folder / BUILD_MANIFEST_FILE_NAME).write_text(text + "\n", encoding="utf-8")


def _serving_entry(build: Build, serving: Serving | None) -> dict | None:
    """The serving SQL used (its fingerprint shows which version) and its checks."""
    if serving is None:
        return None
    sql_file = serving.sql_file.resolve()
    if sql_file.is_relative_to(REPOSITORY_ROOT):
        sql_file = sql_file.relative_to(REPOSITORY_ROOT)
    return {
        "sql_file": sql_file.as_posix(),
        "sha256": file_sha256(serving.sql_file),
        "checks": [
            {"name": check.name, "passed": check.passed, "detail": check.detail}
            for check in build.serving_checks
        ],
    }


def _source_entry(table: StatCanTable, release_folder: Path) -> dict:
    """One source table in the build manifest, from its download manifest."""
    download = json.loads((release_folder / MANIFEST_FILE_NAME).read_text(encoding="utf-8"))
    return {
        "source_id": source_id(table.name),
        "table_name": table.name,
        "release": download["release_time"][:10],
        "fetched_at": download["fetched_at"],
        "files": [
            {"name": file["name"], "language": file["language"], "sha256": file["sha256"]}
            for file in download["files"]
        ],
    }


def _dataset_entry(record: DatasetRecord) -> dict:
    """One dataset in the build manifest."""
    return {
        "name": record.name,
        "stage": record.stage,
        "description": record.description,
        "release": record.release.isoformat() if record.release else None,
        "inputs": list(record.inputs),
        "rows": record.rows,
        "file": record.file,
        "sha256": record.sha256,
        "checks": [
            {"name": check.name, "passed": check.passed, "detail": check.detail}
            for check in record.checks
        ],
    }


def _code_version() -> dict:
    """The git commit the code came from, and whether it had uncommitted changes."""
    here = Path(__file__).parent

    def git(*arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments], cwd=here, capture_output=True, text=True, check=True
        ).stdout.strip()

    try:
        return {
            "git_commit": git("rev-parse", "HEAD"),
            "uncommitted_changes": bool(git("status", "--porcelain")),
        }
    except (OSError, subprocess.CalledProcessError):
        return {"git_commit": None, "uncommitted_changes": None}


def _log_summary(build: Build, database: Path) -> None:
    seconds = time.monotonic() - build.started_clock
    checks = sum(len(record.checks) for record in build.staged + build.model)
    checks += len(build.serving_checks)
    staged_datasets = len({record.name for record in build.staged})
    log.info(
        f"Build {build.build_id} finished in {seconds:.1f} s: {staged_datasets} staged and "
        f"{len(build.model)} model datasets, {checks} checks passed"
    )
    log.info(f"Database: {database}")


# --- Command ----------------------------------------------------------------


def build_everything(data_root: Path = DATA_ROOT) -> int:
    """Build from everything downloaded in a data folder. Returns 0 if it finished, 1 if not."""
    build_id = new_build_id()
    log_path = start_logging("build", build_id, data_root)
    try:
        releases = find_releases(data_root)
        run_build(
            staged_transformers(releases),
            model_transformers(releases),
            latest_releases(releases),
            build_id,
            data_root=data_root,
            serving=Serving(),
        )
    except BuildError as error:
        log.error(f"Build {build_id} stopped: {error}")
        log.error(f"Nothing was saved. Log: {log_path}")
        return 1
    except Exception:
        log.exception(f"Build {build_id} stopped by an unexpected error")
        log.error(f"Nothing was saved. Log: {log_path}")
        return 1
    finally:
        stop_logging()
    return 0


def main() -> int:
    """Build from the default data folder (see settings.DATA_ROOT)."""
    return build_everything(DATA_ROOT)


if __name__ == "__main__":
    sys.exit(main())
