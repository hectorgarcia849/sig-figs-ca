"""The sources every figure links to.

One dataset, sources, with one row per Statistics Canada table used in the
build: its official titles, the release we used, links to the table on
Statistics Canada's website, its permanent citation link (DOI), and
fingerprints of the exact files we downloaded.

It is read from the download manifests rather than from other datasets, so
like the staged transformers it is handed the release folders by the runner.

Its main check enforces the promise that every figure links to its source:
every source and release used in spending, municipal_transfers and context
must appear here. Those datasets are listed as inputs so this runs last.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import date
from pathlib import Path

import duckdb

from public_spend_tracker_pipeline.common.paths import MANIFEST_FILE_NAME, MODEL
from public_spend_tracker_pipeline.common.settings import ENGLISH, FRENCH, StatCanTable
from public_spend_tracker_pipeline.transform.base import (
    CheckResult,
    Transformer,
    expect_no_rows,
    no_duplicate_keys,
    no_missing_values,
    sql_table,
    sql_text,
)
from public_spend_tracker_pipeline.transform.statcan_sql import source_id

PUBLISHER = "Statistics Canada"
LICENCE = "Open Government Licence – Canada"
LICENCE_URL = "https://open.canada.ca/en/open-government-licence-canada"

# Statistics Canada shows each table in "views"; 01 is the table's default view.
# Table 10100005 is written 10-10-0005-01 and its pages use pid=1010000501.
DEFAULT_VIEW = "01"
TABLE_PAGE_URL = "https://www150.statcan.gc.ca/t1/tbl1/{language}/tv.action?pid={pid}"
DOI_URL = "https://doi.org/10.25318/{pid}-eng"

# The datasets whose figures must each have a source.
DATASETS_WITH_FIGURES = ("spending", "municipal_transfers", "context")

COLUMNS = (
    "source_id",
    "publisher",
    "table_number",
    "title_en",
    "title_fr",
    "release",
    "fetched_at",
    "url_en",
    "url_fr",
    "doi",
    "sha256_en",
    "sha256_fr",
    "licence",
    "licence_url",
)


class Sources(Transformer):
    """One row per Statistics Canada table used, from its download manifest.

    fetched_at is when we downloaded the table, in UTC.

    releases  Each table with the folder of the release used. The runner
              passes the same releases the staged datasets were built from.
    """

    name = "sources"
    description = "The Statistics Canada tables behind every figure, with links and fingerprints"
    stage = MODEL
    inputs = DATASETS_WITH_FIGURES

    def __init__(self, releases: Sequence[tuple[StatCanTable, Path]]) -> None:
        self.releases = releases

    def transform(self, db: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyRelation:
        """Read each manifest and write one row per table."""
        rows = [_source_row(table, folder) for table, folder in self.releases]
        return db.sql(f"""
            -- Download time, stored as UTC without a time zone so any tool can read it.
            SELECT * REPLACE (
                CAST(fetched_at AS TIMESTAMPTZ) AT TIME ZONE 'UTC' AS fetched_at
            )
            FROM ({sql_table(COLUMNS, rows)})
            ORDER BY source_id
        """)

    def checks(self, db: duckdb.DuckDBPyConnection) -> list[CheckResult]:
        """Unique, filled in, and every figure in the build has its source here."""
        used = "\nUNION\n".join(
            f"SELECT DISTINCT {sql_text(dataset)} AS dataset, source_id, release FROM {dataset}"
            for dataset in DATASETS_WITH_FIGURES
        )
        return [
            no_duplicate_keys(db, self.name, ["source_id"]),
            no_missing_values(db, self.name, ["title_en", "title_fr", "url_en", "sha256_en"]),
            expect_no_rows(
                db,
                f"{self.name}: every figure's source and release is listed",
                f"""SELECT * FROM ({used}) AS used
                    WHERE NOT EXISTS (
                        SELECT 1 FROM {self.name} AS s
                        WHERE s.source_id = used.source_id AND s.release = used.release
                    )""",
            ),
        ]


def _source_row(table: StatCanTable, release_folder: Path) -> tuple:
    """One row of the sources dataset, from a release's manifest."""
    manifest = json.loads((release_folder / MANIFEST_FILE_NAME).read_text(encoding="utf-8"))
    fingerprints = {file["language"]: file["sha256"] for file in manifest["files"]}
    pid = table.product_id + DEFAULT_VIEW
    return (
        source_id(table.name),
        PUBLISHER,
        table_number(table.product_id),
        manifest["title_en"],
        manifest["title_fr"],
        date.fromisoformat(manifest["release_time"][:10]),
        manifest["fetched_at"],
        TABLE_PAGE_URL.format(language=ENGLISH, pid=pid),
        TABLE_PAGE_URL.format(language=FRENCH, pid=pid),
        DOI_URL.format(pid=pid),
        fingerprints.get(ENGLISH),
        fingerprints.get(FRENCH),
        LICENCE,
        LICENCE_URL,
    )


def table_number(product_id: str) -> str:
    """Statistics Canada's written table number: "10100005" -> "10-10-0005-01"."""
    return f"{product_id[0:2]}-{product_id[2:4]}-{product_id[4:8]}-{DEFAULT_VIEW}"
