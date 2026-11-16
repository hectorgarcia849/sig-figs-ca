"""Export the site's data: copy one build's figures into JSON files the site is built from.

Run it from the repository root with:

    uv run pst export                  the approved build (see approve.py), into web/data/
    uv run pst export --build <id>     a particular build, e.g. to try one before approving it

It writes five files:

    meta.json                 the build, the years covered, and every source
    jurisdictions.json        codes, with English and French names
    functions.json            the COFOG tree, with English and French names
    spending.json             the spending_measures view, fiscal basis
    municipal_transfers.json  the municipal_transfers_measures view, fiscal basis

Nothing is calculated here. The measures come from the views in
schema/serving.sql, so the site shows exactly what the database holds, only
rounded to drop meaningless digits. The site reads these files while it is
being built, and each page takes only the rows it needs.

The files are written to a temporary folder first, which then replaces the
previous export whole, so the site never sees a mix of two builds.
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import duckdb

from public_spend_tracker_pipeline.approve import approved_build, is_complete
from public_spend_tracker_pipeline.logs import start_logging, stop_logging
from public_spend_tracker_pipeline.paths import (
    BUILD_MANIFEST_FILE_NAME,
    DATABASE_FILE_NAME,
    new_build_id,
    serving_build_folder,
)
from public_spend_tracker_pipeline.settings import DATA_ROOT, WEB_DATA_FOLDER
from public_spend_tracker_pipeline.transform.base import sql_text

log = logging.getLogger(__name__)

# Population, prices and GDP are for the fiscal year (April to March). The
# calendar-year basis can be added later.
CONTEXT_BASIS = "fiscal"

# Decimal places kept. Real dollars are rounded to the whole dollar, like
# amounts. The database keeps full precision.
PER_PERSON_DECIMALS = 2
PERCENT_DECIMALS = 4

# View columns left out: the same on every row, or recorded once in meta.json.
LEFT_OUT_COLUMNS = ("context_basis", "base_year")

# Sources columns the site needs (checksums and download times stay in the database).
SOURCE_COLUMNS = (
    "source_id", "publisher", "table_number", "title_en", "title_fr", "release",
    "url_en", "url_fr", "doi", "licence", "licence_url",
)  # fmt: skip

META_FILE_NAME = "meta.json"

# While an export runs, its files go to a temporary folder next to the
# destination, named with this start. The replaced export is briefly renamed
# with the second start before it is removed.
EXPORT_WORK_FOLDER_PREFIX = ".exporting-"
REPLACED_EXPORT_FOLDER_PREFIX = ".replaced-"


class ExportError(Exception):
    """The export could not be made, for example because there is no complete build."""


@dataclass(frozen=True)
class ExportFile:
    """One JSON file of the export: its name and the query giving its rows."""

    file_name: str
    query: str


def _measures_query(view: str, keys: str) -> str:
    """Rows of a measures view for the chosen basis, rounded, in a fixed order."""
    return f"""
        SELECT * EXCLUDE ({", ".join(LEFT_OUT_COLUMNS)})
            REPLACE (
                CAST(round(amount_real) AS BIGINT) AS amount_real,
                round(amount_per_person, {PER_PERSON_DECIMALS}) AS amount_per_person,
                round(amount_real_per_person, {PER_PERSON_DECIMALS}) AS amount_real_per_person,
                round(percent_of_gdp, {PERCENT_DECIMALS}) AS percent_of_gdp
            )
        FROM {view}
        WHERE context_basis = {sql_text(CONTEXT_BASIS)}
        ORDER BY {keys}
    """


# Every file except meta.json, which is put together separately.
EXPORT_FILES: tuple[ExportFile, ...] = (
    ExportFile(
        "jurisdictions.json",
        "SELECT code, name_en, name_fr, kind, sort_order FROM jurisdictions ORDER BY sort_order",
    ),
    ExportFile(
        "functions.json",
        """SELECT function_id, level, parent_id, name_en, name_fr, sort_order
           FROM functions ORDER BY sort_order""",
    ),
    ExportFile(
        "spending.json",
        _measures_query(
            "spending_measures", "view, jurisdiction, function_id, fiscal_year, transfers"
        ),
    ),
    ExportFile(
        "municipal_transfers.json",
        _measures_query("municipal_transfers_measures", "jurisdiction, fiscal_year"),
    ),
)


# --- Choosing the build -----------------------------------------------------


def build_to_export(data_root: Path = DATA_ROOT) -> str:
    """The approved build: the one the site should show."""
    build_id = approved_build(data_root)
    if build_id is None:
        raise ExportError(
            "No build is approved yet. Run: uv run pst approve "
            "(or export a particular build with --build)"
        )
    return build_id


# --- Exporting --------------------------------------------------------------


def run_export(
    build_id: str, destination: Path = WEB_DATA_FOLDER, data_root: Path = DATA_ROOT
) -> dict[str, int]:
    """Export one build into the destination folder, replacing what was there.

    Returns how many rows went into each file.
    """
    if not is_complete(build_id, data_root):
        raise ExportError(
            f"Build {build_id} is not complete (it has no {BUILD_MANIFEST_FILE_NAME})"
        )

    work = destination.parent / f"{EXPORT_WORK_FOLDER_PREFIX}{destination.name}"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    try:
        database = serving_build_folder(build_id, data_root) / DATABASE_FILE_NAME
        db = duckdb.connect(str(database), read_only=True)
        try:
            _check_build_id(db, build_id)
            rows = {export.file_name: _write_rows(db, export, work) for export in EXPORT_FILES}
            rows[META_FILE_NAME] = _write_meta(db, work / META_FILE_NAME)
        finally:
            db.close()
        _swap_in(work, destination)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    log.info(f"Exported build {build_id} to {destination}")
    for file_name, count in rows.items():
        log.info(f"  {file_name:<26} {count:>7,} rows")
    return rows


def _check_build_id(db: duckdb.DuckDBPyConnection, build_id: str) -> None:
    """Stop if the database says it belongs to another build (a misplaced file)."""
    found = db.sql("SELECT build_id FROM build_info").fetchall()
    if found != [(build_id,)]:
        raise ExportError(f"The database in build {build_id}'s folder says it is from {found}")


def _write_rows(db: duckdb.DuckDBPyConnection, export: ExportFile, folder: Path) -> int:
    """Write a query's rows as a JSON list of objects. Returns how many rows."""
    path = folder / export.file_name
    db.sql(f"COPY ({export.query}) TO {sql_text(str(path))} (FORMAT json, ARRAY true)")
    return db.sql(f"SELECT count(*) FROM ({export.query})").fetchall()[0][0]


def _write_meta(db: duckdb.DuckDBPyConnection, path: Path) -> int:
    """Write meta.json: build_info's fields plus the list of sources. Returns 1 (one object)."""
    meta = _rows_as_dicts(db, "SELECT * FROM build_info")[0]
    meta["sources"] = _rows_as_dicts(
        db, f"SELECT {', '.join(SOURCE_COLUMNS)} FROM sources ORDER BY source_id"
    )
    path.write_text(json.dumps(meta, default=_json_value, ensure_ascii=False), encoding="utf-8")
    return 1


def _rows_as_dicts(db: duckdb.DuckDBPyConnection, query: str) -> list[dict]:
    relation = db.sql(query)
    return [dict(zip(relation.columns, row, strict=True)) for row in relation.fetchall()]


def _json_value(value: object) -> str:
    """Dates and times as ISO text, e.g. "2025-11-27" or "2026-11-16T15:21:17"."""
    if isinstance(value, date | datetime):
        return value.isoformat()
    raise TypeError(f"Cannot write {value!r} as JSON")


def _swap_in(work: Path, destination: Path) -> None:
    """Put the finished work folder in the destination's place, removing the old export."""
    replaced = destination.parent / f"{REPLACED_EXPORT_FOLDER_PREFIX}{destination.name}"
    shutil.rmtree(replaced, ignore_errors=True)
    if destination.exists():
        destination.rename(replaced)
    work.rename(destination)
    shutil.rmtree(replaced, ignore_errors=True)


# --- Command ----------------------------------------------------------------


def export_site(
    data_root: Path = DATA_ROOT,
    build_id: str | None = None,
    destination: Path = WEB_DATA_FOLDER,
) -> int:
    """Export a build (the approved one by default). Returns 0 if it worked, 1 if not."""
    log_path = start_logging("export", new_build_id(), data_root)
    try:
        run_export(build_id or build_to_export(data_root), destination, data_root)
    except ExportError as error:
        log.error(f"Export stopped: {error}")
        return 1
    except Exception:
        log.exception("Export stopped by an unexpected error")
        log.error(f"Log: {log_path}")
        return 1
    finally:
        stop_logging()
    return 0
