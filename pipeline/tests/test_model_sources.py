"""Tests for the sources dataset, built from made-up download manifests."""

import json
from datetime import date, datetime

import duckdb
import pytest

from public_spend_tracker_pipeline.common.paths import MANIFEST_FILE_NAME
from public_spend_tracker_pipeline.common.settings import (
    ELECTIONS_FILES,
    ENGLISH,
    FRENCH,
    StatCanTable,
)
from public_spend_tracker_pipeline.transform.base import sql_table
from public_spend_tracker_pipeline.transform.model_sources import Sources, table_number

SPENDING_TABLE = StatCanTable("10100005", "cofog_consolidated", "test", (ENGLISH, FRENCH))
CPI_TABLE = StatCanTable("18100004", "cpi_monthly", "test", (ENGLISH,))


def write_manifest(folder, table, release_time, fetched_at):
    """A made-up manifest, as the extractor writes it."""
    folder.mkdir(parents=True)
    files = [
        {"name": f"{table.product_id}-{language}.zip", "language": language,
         "sha256": f"{language}-fingerprint"}
        for language in table.languages
    ]  # fmt: skip
    manifest = {
        "title_en": f"Table {table.product_id}",
        "title_fr": f"Tableau {table.product_id}",
        "release_time": release_time,
        "fetched_at": fetched_at,
        "files": files,
    }
    (folder / MANIFEST_FILE_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    return folder


def make_figures(db, extra_rows=(), elections_rows=()):
    """Made-up tables with source_id and release columns, as the checks read them.

    The election datasets are empty unless elections_rows are given.
    """
    used = [("statcan-10100005", date(2025, 11, 27))]
    for name in ("spending", "municipal_transfers"):
        db.sql(f"CREATE TABLE {name} AS {sql_table(['source_id', 'release'], used)}")
    context = [("statcan-18100004", date(2026, 10, 19)), *extra_rows]
    db.sql(f"CREATE TABLE context AS {sql_table(['source_id', 'release'], context)}")
    for name in ("ridings", "election_districts", "election_candidates"):
        db.sql(f"CREATE TABLE {name} (source_id VARCHAR, release DATE)")
        if elections_rows:
            db.sql(f"INSERT INTO {name} {sql_table(['source_id', 'release'], elections_rows)}")


@pytest.fixture
def releases(tmp_path):
    return [
        (SPENDING_TABLE, write_manifest(tmp_path / "a", SPENDING_TABLE,
                                        "2025-11-27T08:30", "2026-11-14T21:45:49+00:00")),
        (CPI_TABLE, write_manifest(tmp_path / "b", CPI_TABLE,
                                   "2026-10-19T08:30", "2026-11-14T21:40:21+00:00")),
    ]  # fmt: skip


def run(db, releases):
    sources = Sources(releases)
    sources.transform(db).create(sources.name)
    return sources.checks(db)


def test_table_number():
    assert table_number("10100005") == "10-10-0005-01"


def test_source_rows_have_links_and_fingerprints(releases):
    db = duckdb.connect()
    make_figures(db)
    results = run(db, releases)
    assert all(result.passed for result in results), results

    row = db.sql("""
        SELECT source_id, table_number, title_fr, release, fetched_at,
               url_en, url_fr, doi, sha256_en, sha256_fr
        FROM sources WHERE source_id = 'statcan-10100005'
    """).fetchall()[0]
    assert row == (
        "statcan-10100005",
        "10-10-0005-01",
        "Tableau 10100005",
        date(2025, 11, 27),
        datetime(2026, 11, 14, 21, 45, 49),  # UTC
        "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1010000501",
        "https://www150.statcan.gc.ca/t1/tbl1/fr/tv.action?pid=1010000501",
        "https://doi.org/10.25318/1010000501-eng",
        "en-fingerprint",
        "fr-fingerprint",
    )


def test_english_only_table_has_no_french_fingerprint(releases):
    db = duckdb.connect()
    make_figures(db)
    run(db, releases)
    fingerprints = db.sql(
        "SELECT sha256_en, sha256_fr FROM sources WHERE source_id = 'statcan-18100004'"
    ).fetchall()
    assert fingerprints == [("en-fingerprint", None)]


@pytest.mark.parametrize(
    "unlisted",
    [
        ("statcan-99999999", date(2026, 10, 19)),  # a table we never downloaded
        ("statcan-18100004", date(2025, 1, 1)),  # a release we did not use
    ],
)
def test_figure_without_a_listed_source_fails_the_check(releases, unlisted):
    db = duckdb.connect()
    make_figures(db, extra_rows=[unlisted])
    results = run(db, releases)
    failed = [result for result in results if not result.passed]
    assert [result.name for result in failed] == [
        "sources: every figure's source and release is listed"
    ]
    assert unlisted[0] in failed[0].detail


def test_elections_canada_file_has_its_licence_and_no_table_number(tmp_path, releases):
    results_file = next(f for f in ELECTIONS_FILES if f.name == "ge45_results_by_candidate")
    folder = tmp_path / "elections"
    folder.mkdir()
    manifest = {
        "release": "2026-11-24",
        "fetched_at": "2026-11-24T04:49:47+00:00",
        "licence": "Elections Canada terms",
        "licence_url": "https://www.elections.ca/terms",
        "files": [{"name": "table_tableau12.csv", "language": "en,fr", "sha256": "abc"}],
    }
    (folder / MANIFEST_FILE_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    db = duckdb.connect()
    make_figures(db, elections_rows=[("elections-ge45_results_by_candidate", date(2026, 11, 24))])

    sources = Sources(releases, [(results_file, folder)])
    sources.transform(db).create(sources.name)

    assert all(result.passed for result in sources.checks(db))
    row = db.sql("""
        SELECT publisher, table_number, doi, sha256_en, sha256_fr, licence, url_fr
        FROM sources WHERE source_id = 'elections-ge45_results_by_candidate'
    """).fetchall()
    assert row == [("Elections Canada", None, None, "abc", "abc", "Elections Canada terms",
                    "https://www.elections.ca/res/rep/off/ovrGE45/accueil.html")]  # fmt: skip
