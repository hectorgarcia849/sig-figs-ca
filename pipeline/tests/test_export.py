"""Tests for the site export.

Each test makes tiny builds in a temporary data folder: a real DuckDB database
with made-up model tables and the real serving views, for Canada ("ca") and
Quebec ("qc") over fiscal years 2023-24 and 2024-25.
"""

import json
from datetime import UTC, date, datetime

import duckdb
import pytest

from public_spend_tracker_pipeline.approve import approve
from public_spend_tracker_pipeline.export import (
    ExportError,
    build_to_export,
    export_site,
    run_export,
)
from public_spend_tracker_pipeline.paths import (
    BUILD_MANIFEST_FILE_NAME,
    DATABASE_FILE_NAME,
    serving_build_folder,
)
from public_spend_tracker_pipeline.serving import Serving
from public_spend_tracker_pipeline.transform.base import sql_table

OLDER = "20261115-070145"
NEWER = "20261116-152117"
UNFINISHED = "20261116-170000"
RELEASE = date(2025, 11, 27)

EXPORTED_FILES = [
    "functions.json",
    "jurisdictions.json",
    "meta.json",
    "municipal_transfers.json",
    "spending.json",
]


def create(db, name, columns, rows):
    db.sql(f"CREATE TABLE {name} AS {sql_table(columns, rows)}")


def make_build(data_root, build_id, complete=True):
    """A build folder with a small database; complete builds also get a manifest."""
    folder = serving_build_folder(build_id, data_root)
    folder.mkdir(parents=True)
    db = duckdb.connect(str(folder / DATABASE_FILE_NAME))

    create(db, "jurisdictions", ["code", "name_en", "name_fr", "kind", "sort_order"], [
        ("ca", "Canada", "Canada", "country", 1),
        ("qc", "Quebec", "Québec", "province", 2),
    ])  # fmt: skip
    create(db, "functions",
        ["function_id", "level", "parent_id", "name_en", "name_fr", "sort_order"],
        [("701", 1, None, "General public services", "Services publics généraux", 1)],
    )  # fmt: skip
    create(db, "spending",
        ["view", "jurisdiction", "function_id", "fiscal_year", "amount",
         "transfers_to_governments", "revision_status", "release", "source_id", "vector"],
        [("federal", "ca", "701", 2023, 1000, 400, "revised", RELEASE, "statcan-10100024", "v1"),
         ("federal", "ca", "701", 2024, 1000, 400, "preliminary", RELEASE, "statcan-10100024",
          "v1")],
    )  # fmt: skip
    create(db, "municipal_transfers",
        ["jurisdiction", "fiscal_year", "amount", "revision_status", "release", "source_id",
         "vector"],
        [("qc", 2024, 300, "preliminary", RELEASE, "statcan-10100020", "v2")],
    )  # fmt: skip
    context = []
    for basis in ("fiscal", "calendar"):
        for code in ("ca", "qc"):
            context += [
                (code, basis, 2023, "cpi", 99.0, "exact"),
                (code, basis, 2024, "cpi", 110.0, "exact"),
            ]
            context += [(code, basis, year, "population", 3.0, "exact") for year in (2023, 2024)]
            context += [(code, basis, year, "gdp", 7000.0, "exact") for year in (2023, 2024)]
    create(db, "context", ["jurisdiction", "basis", "year", "series", "value", "method"], context)
    create(db, "sources",
        ["source_id", "publisher", "table_number", "title_en", "title_fr", "release",
         "url_en", "url_fr", "doi", "licence", "licence_url", "sha256_en"],
        [("statcan-10100024", "Statistics Canada", "10-10-0024-01", "Functions", "Fonctions",
          RELEASE, "https://example.ca/en", "https://example.ca/fr", "https://doi.org/x",
          "Open Government Licence - Canada", "https://example.ca/licence", "abc")],
    )  # fmt: skip

    Serving().prepare(db, build_id, datetime(2026, 11, 16, 15, 21, 17, tzinfo=UTC))
    db.close()
    if complete:
        (folder / BUILD_MANIFEST_FILE_NAME).write_text("{}", encoding="utf-8")


def read(folder, file_name):
    return json.loads((folder / file_name).read_text(encoding="utf-8"))


@pytest.fixture
def data_root(tmp_path):
    root = tmp_path / "data"
    make_build(root, OLDER)
    make_build(root, NEWER)
    make_build(root, UNFINISHED, complete=False)
    return root


@pytest.fixture
def out(tmp_path):
    return tmp_path / "web" / "data"


# --- Choosing the build -----------------------------------------------------


def test_the_approved_build_is_exported_not_the_newest(data_root):
    approve(OLDER, data_root)
    assert build_to_export(data_root) == OLDER


def test_no_approved_build_gives_a_clear_error(data_root):
    with pytest.raises(ExportError, match="No build is approved yet"):
        build_to_export(data_root)


def test_an_unfinished_build_is_refused(data_root, out):
    with pytest.raises(ExportError, match="not complete"):
        run_export(UNFINISHED, out, data_root)
    assert not out.exists()


# --- What is written --------------------------------------------------------


def test_every_file_is_written(data_root, out):
    rows = run_export(OLDER, out, data_root)
    assert sorted(path.name for path in out.iterdir()) == EXPORTED_FILES
    assert rows["spending.json"] == 4  # 2 years x included and excluded, fiscal basis only
    assert read(out, "meta.json")["build_id"] == OLDER


def test_meta_has_the_build_years_and_sources(data_root, out):
    run_export(NEWER, out, data_root)
    meta = read(out, "meta.json")
    assert {key: meta[key] for key in ("build_id", "built_at", "base_year")} == {
        "build_id": NEWER,
        "built_at": "2026-11-16T15:21:17",
        "base_year": 2024,
    }
    assert (meta["first_fiscal_year"], meta["latest_fiscal_year"]) == (2023, 2024)
    [source] = meta["sources"]
    assert source["release"] == "2025-11-27"
    assert source["url_fr"] == "https://example.ca/fr"
    assert "sha256_en" not in source


def test_spending_rows_are_fiscal_and_rounded(data_root, out):
    run_export(NEWER, out, data_root)
    rows = read(out, "spending.json")
    assert rows[0] == {
        "view": "federal",
        "jurisdiction": "ca",
        "function_id": "701",
        "fiscal_year": 2023,
        "transfers": "excluded",
        "amount": 600,
        "amount_real": 667,  # 600 x 110 / 99 = 666.67, to the whole dollar
        "amount_per_person": 200.0,
        "amount_real_per_person": 222.22,  # to the cent
        "percent_of_gdp": 8.5714,  # 600 / 7000 x 100, to 4 decimals
        "transfers_to_governments": 400,
        "gdp_method": "exact",
        "revision_status": "revised",
        "release": "2025-11-27",
        "source_id": "statcan-10100024",
        "vector": "v1",
    }


def test_municipal_transfers_are_exported(data_root, out):
    run_export(NEWER, out, data_root)
    [row] = read(out, "municipal_transfers.json")
    assert (row["jurisdiction"], row["amount"], row["amount_per_person"]) == ("qc", 300, 100.0)


def test_french_text_is_kept_as_written(data_root, out):
    run_export(NEWER, out, data_root)
    assert "Québec" in (out / "jurisdictions.json").read_text(encoding="utf-8")
    assert "généraux" in (out / "functions.json").read_text(encoding="utf-8")


def test_an_old_export_is_replaced_whole(data_root, out):
    out.mkdir(parents=True)
    (out / "left_over.json").write_text("[]", encoding="utf-8")

    run_export(NEWER, out, data_root)

    assert sorted(path.name for path in out.iterdir()) == EXPORTED_FILES
    assert sorted(path.name for path in out.parent.iterdir()) == ["data"]  # no work folders


def test_a_failed_export_leaves_the_old_one_alone(data_root, out):
    run_export(OLDER, out, data_root)
    with pytest.raises(ExportError):
        run_export(UNFINISHED, out, data_root)
    assert read(out, "meta.json")["build_id"] == OLDER


# --- The command ------------------------------------------------------------


def test_export_site_uses_the_approved_build(data_root, out):
    approve(OLDER, data_root)
    assert export_site(data_root, destination=out) == 0
    assert read(out, "meta.json")["build_id"] == OLDER


def test_export_site_can_export_a_build_that_is_not_approved(data_root, out):
    assert export_site(data_root, NEWER, out) == 0
    assert read(out, "meta.json")["build_id"] == NEWER


def test_export_site_returns_1_when_no_build_is_approved(data_root, out):
    assert export_site(data_root, destination=out) == 1
    assert not out.exists()
