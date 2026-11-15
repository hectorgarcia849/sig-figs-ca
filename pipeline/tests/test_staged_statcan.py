"""Tests for staging Statistics Canada tables.

Each test writes a tiny made-up release (English and French zips plus a
manifest, laid out like a real download) into a temporary folder, then runs the
transformer on an in-memory DuckDB database the way the runner will.
"""

import csv
import io
import json
import zipfile
from datetime import date
from pathlib import Path

import duckdb
import pytest

from public_spend_tracker_pipeline.paths import MANIFEST_FILE_NAME
from public_spend_tracker_pipeline.settings import ENGLISH, FRENCH, StatCanTable
from public_spend_tracker_pipeline.transform.base import CheckResult
from public_spend_tracker_pipeline.transform.staged_statcan import (
    SourceChangedError,
    StagedStatCanTable,
)

SPENDING_TABLE = StatCanTable(
    product_id="10100005",
    name="cofog_consolidated",
    purpose="test spending table",
    languages=(ENGLISH, FRENCH),
    dimensions=(
        ("Public sector components", "component"),
        ("Canadian Classification of Functions of Government (CCOFOG)", "function"),
    ),
)

PRICES_TABLE = StatCanTable(
    product_id="18100004",
    name="cpi_monthly",
    purpose="test English-only table",
    languages=(ENGLISH,),
    dimensions=(("Products and product groups", "product"),),
)

ENGLISH_HEADER = [
    "REF_DATE", "GEO", "DGUID",
    "Public sector components",
    "Canadian Classification of Functions of Government (CCOFOG)",
    "UOM", "UOM_ID", "SCALAR_FACTOR", "SCALAR_ID", "VECTOR", "COORDINATE",
    "VALUE", "STATUS", "SYMBOL", "TERMINATED", "DECIMALS",
]  # fmt: skip
FRENCH_HEADER = [
    "PÉRIODE DE RÉFÉRENCE", "GÉO", "DGUID",
    "Composantes du secteur public",
    "Classification canadienne des fonctions des administrations publiques (CCFAP)",
    "UNITÉ DE MESURE", "IDENTIFICATEUR D'UNITÉ DE MESURE", "FACTEUR SCALAIRE",
    "IDENTIFICATEUR SCALAIRE", "VECTEUR", "COORDONNÉES", "VALEUR", "STATUS",
    "SYMBOLE", "TERMINÉ", "DÉCIMALES",
]  # fmt: skip


def spending_row(ref_date, geo, function, value, vector, symbol=""):
    """One row of the made-up spending table, with the standard columns filled in."""
    component = "Consolidated provincial-territorial and local governments"
    return [ref_date, geo, "2016A000224", component, function, "Dollars", "81",
            "millions", "6", vector, "1.1", value, "", symbol, "", "0"]  # fmt: skip


ENGLISH_ROWS = [
    spending_row("2024", "Quebec", "General public services [701]", "33040", "v1", symbol="p"),
    spending_row("2023", "Quebec", "General public services [701]", "31000", "v1", symbol="r"),
    spending_row("2024", "Quebec", "Defence [702]", "", "v2"),
]
FRENCH_ROWS = [
    spending_row("2024", "Québec", "Services généraux des administrations publiques [701]",
                 "33040", "v1", symbol="p"),
    spending_row("2023", "Québec", "Services généraux des administrations publiques [701]",
                 "31000", "v1", symbol="r"),
    spending_row("2024", "Québec", "Défense [702]", "", "v2"),
]  # fmt: skip


def write_zip(path: Path, csv_name: str, header: list[str], rows: list[list[str]], delimiter: str):
    """Write a zip holding one CSV, quoted and marked as UTF-8 the way Statistics Canada does."""
    text = io.StringIO()
    writer = csv.writer(text, delimiter=delimiter, quoting=csv.QUOTE_ALL, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(csv_name, "﻿" + text.getvalue())


def make_release(
    folder: Path,
    table: StatCanTable,
    english_header: list[str],
    english_rows: list[list[str]],
    french_rows: list[list[str]] | None = None,
) -> Path:
    """Write a made-up downloaded release of a table and return its folder."""
    folder.mkdir(parents=True)
    files = []
    csv_name = f"{table.product_id}.csv"
    english_zip = f"{table.product_id}-eng.zip"
    write_zip(folder / english_zip, csv_name, english_header, english_rows, ",")
    files.append({"name": english_zip, "language": ENGLISH})
    if french_rows is not None:
        french_zip = f"{table.product_id}-fra.zip"
        write_zip(folder / french_zip, csv_name, FRENCH_HEADER, french_rows, ";")
        files.append({"name": french_zip, "language": FRENCH})
    manifest = {"release_time": "2025-11-27T08:30", "files": files}
    (folder / MANIFEST_FILE_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    return folder


def run(transformer: StagedStatCanTable, db: duckdb.DuckDBPyConnection) -> list[CheckResult]:
    """Do what the runner will do: save the result under the dataset's name, then check it."""
    transformer.transform(db).create(transformer.name)
    return transformer.checks(db)


@pytest.fixture
def db() -> duckdb.DuckDBPyConnection:
    return duckdb.connect()


@pytest.fixture
def spending(tmp_path) -> StagedStatCanTable:
    """The transformer for a normal bilingual spending release."""
    folder = make_release(
        tmp_path / "release", SPENDING_TABLE, ENGLISH_HEADER, ENGLISH_ROWS, FRENCH_ROWS
    )
    return StagedStatCanTable(SPENDING_TABLE, folder)


def test_release_date_comes_from_the_manifest(spending):
    assert spending.release == date(2025, 11, 27)


def test_stages_values_codes_and_french_labels(spending, db):
    results = run(spending, db)
    assert all(result.passed for result in results), results

    row = db.sql("""
        SELECT ref_date, period_start, geo_en, geo_fr, function_en, function_fr,
               function_code, value, unit, scalar_factor, symbol, vector
        FROM cofog_consolidated WHERE ref_date = '2024' AND vector = 'v1'
    """).fetchall()[0]
    assert row == (
        "2024", date(2024, 1, 1), "Quebec", "Québec",
        "General public services", "Services généraux des administrations publiques",
        "701", 33040.0, "Dollars", "millions", "p", "v1",
    )  # fmt: skip


def test_blank_value_stays_empty(spending, db):
    run(spending, db)
    value = db.sql("SELECT value FROM cofog_consolidated WHERE vector = 'v2'").fetchall()
    assert value == [(None,)]


def test_parses_all_three_date_forms(tmp_path, db):
    rows = [
        spending_row("2024", "Quebec", "Defence [702]", "1", "v1"),
        spending_row("2024-04", "Quebec", "Defence [702]", "1", "v1"),
        spending_row("2024-07-01", "Quebec", "Defence [702]", "1", "v1"),
    ]
    english_only = StatCanTable("10100005", "dates", "test", (ENGLISH,), SPENDING_TABLE.dimensions)
    folder = make_release(tmp_path / "release", english_only, ENGLISH_HEADER, rows)
    run(StagedStatCanTable(english_only, folder), db)

    starts = db.sql("SELECT period_start FROM dates ORDER BY period_start").fetchall()
    assert starts == [(date(2024, 1, 1),), (date(2024, 4, 1),), (date(2024, 7, 1),)]


def test_renamed_column_stops_with_a_clear_message(tmp_path, db):
    renamed = ["Public sector" if name == "Public sector components" else name
               for name in ENGLISH_HEADER]  # fmt: skip
    folder = make_release(tmp_path / "release", SPENDING_TABLE, renamed, ENGLISH_ROWS, FRENCH_ROWS)

    with pytest.raises(SourceChangedError, match="10100005 cofog_consolidated.*columns changed"):
        StagedStatCanTable(SPENDING_TABLE, folder).transform(db)


def test_duplicate_series_and_date_fails_its_check(tmp_path, db):
    english = [*ENGLISH_ROWS, ENGLISH_ROWS[0]]
    french = [*FRENCH_ROWS, FRENCH_ROWS[0]]
    folder = make_release(tmp_path / "release", SPENDING_TABLE, ENGLISH_HEADER, english, french)
    results = run(StagedStatCanTable(SPENDING_TABLE, folder), db)

    failed = [result for result in results if not result.passed]
    assert [result.name for result in failed] == [
        "cofog_consolidated: no duplicate vector, ref_date"
    ]


def test_missing_french_row_fails_its_check(tmp_path, db):
    folder = make_release(
        tmp_path / "release", SPENDING_TABLE, ENGLISH_HEADER, ENGLISH_ROWS, FRENCH_ROWS[:2]
    )
    results = run(StagedStatCanTable(SPENDING_TABLE, folder), db)

    failed = [result for result in results if not result.passed]
    assert len(failed) == 1
    assert failed[0].name == "cofog_consolidated: no missing geo_fr, component_fr, function_fr"


def test_english_only_table_has_no_french_columns(tmp_path, db):
    header = ["REF_DATE", "GEO", "DGUID", "Products and product groups", *ENGLISH_HEADER[5:]]
    row = ["2024-09", "Canada", "2016A000011124", "All-items", "2002=100", "17",
           "units", "0", "v41690973", "2.2", "161.1", "", "", "", "1"]  # fmt: skip
    folder = make_release(tmp_path / "release", PRICES_TABLE, header, [row])
    results = run(StagedStatCanTable(PRICES_TABLE, folder), db)

    assert all(result.passed for result in results), results
    columns = [name for name, *_ in db.sql("DESCRIBE cpi_monthly").fetchall()]
    assert "product_en" in columns
    assert not any(name.endswith("_fr") for name in columns)
    assert db.sql("SELECT value FROM cpi_monthly").fetchall() == [(161.1,)]
