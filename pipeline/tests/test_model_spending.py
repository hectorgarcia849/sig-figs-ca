"""Tests for the reference lists (jurisdictions, functions) and spending datasets.

They build small made-up staged tables in an in-memory DuckDB database, shaped
like the real ones: every jurisdiction, all 10 functions, a few sub-functions
(including a merged "7015, 7016, 7018" group) and two fiscal years. Then they
run the transformers in order, the way the runner will.
"""

from datetime import date

import duckdb
import pytest

from public_spend_tracker_pipeline.common.settings import JURISDICTIONS
from public_spend_tracker_pipeline.transform.base import CheckResult, Transformer, sql_text
from public_spend_tracker_pipeline.transform.model_reference import Functions, Jurisdictions
from public_spend_tracker_pipeline.transform.model_spending import (
    MUNICIPAL_FLOWS,
    MUNICIPAL_GRANTS_CODE,
    MunicipalTransfers,
    Spending,
)

RELEASE = date(2025, 11, 27)
OLDER_RELEASE = date(2024, 11, 28)
YEARS = {"2023": "r", "2024": "p"}  # year as published -> revision flag

CANADA = "Canada"
PROVINCES = [place.statcan_name for place in JURISDICTIONS if place.code != "ca"]

# Each function has two sub-functions worth 30 and 70 (millions), adding up to 100.
FUNCTION_CODES = [str(code) for code in range(701, 711)]
MERGED_CODE = "7015, 7016, 7018"


def sub_function_codes(function_code: str) -> list[str]:
    first = MERGED_CODE if function_code == "701" else f"{function_code}1"
    return [first, f"{function_code}2"]


SUB_FUNCTION_VALUES = (30.0, 70.0)
FUNCTION_VALUE = sum(SUB_FUNCTION_VALUES)

STAGED_COLUMNS = (
    "ref_date", "geo_en", "geo_fr", "component_en", "function_code", "function_en",
    "function_fr", "value", "scalar_factor", "symbol", "vector", "release",
)  # fmt: skip


def cofog_rows(component, places, release=RELEASE, value_offset=0.0):
    """Rows of a made-up staged COFOG table for one component and some places."""
    rows = []
    for place in places:
        for year, flag in YEARS.items():
            for code in FUNCTION_CODES:
                values = [(code, FUNCTION_VALUE)]
                values += zip(sub_function_codes(code), SUB_FUNCTION_VALUES, strict=True)
                for each_code, value in values:
                    rows.append((
                        year, place, f"{place} (fr)", component, each_code,
                        f"Function {each_code}", f"Fonction {each_code}",
                        value + value_offset, "millions", flag, f"v-{place}-{each_code}", release,
                    ))  # fmt: skip
    return rows


def create_table(db, name, columns, rows):
    """Create a table from Python rows."""
    values = ", ".join("(" + ", ".join(sql_literal(value) for value in row) + ")" for row in rows)
    column_names = ", ".join(columns)
    db.sql(
        f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM (VALUES {values}) AS t({column_names})"
    )


def sql_literal(value):
    if value is None:
        return "NULL"
    if isinstance(value, date):
        return f"DATE '{value.isoformat()}'"
    if isinstance(value, str):
        return sql_text(value)
    if isinstance(value, float):
        return f"CAST({value} AS DOUBLE)"  # like the real staged value column
    return str(value)


def make_staged_tables(db, consolidated=None, by_component=None):
    """Create the three staged tables the spending datasets read."""
    if consolidated is None:
        consolidated = cofog_rows("Consolidated Canadian general government", [CANADA])
        consolidated += cofog_rows(
            "Consolidated provincial-territorial and local governments", [CANADA, *PROVINCES]
        )
    if by_component is None:
        by_component = cofog_rows("Federal government", [CANADA])
        by_component += cofog_rows("Provincial and territorial governments", PROVINCES)
    create_table(db, "cofog_consolidated", STAGED_COLUMNS, consolidated)
    create_table(db, "cofog_by_component", STAGED_COLUMNS, by_component)

    municipal = []
    for place in PROVINCES:
        municipal.append(("2007", place, MUNICIPAL_GRANTS_CODE, MUNICIPAL_FLOWS, None, None))
        municipal.append(("2023", place, MUNICIPAL_GRANTS_CODE, MUNICIPAL_FLOWS, 90.0, "r"))
        municipal.append(("2024", place, MUNICIPAL_GRANTS_CODE, MUNICIPAL_FLOWS, 95.0, "p"))
        municipal.append(("2024", place, MUNICIPAL_GRANTS_CODE, "Stocks", 999.0, "p"))
    create_table(
        db,
        "gfs_municipal",
        ("ref_date", "geo_en", "gfs_item_code", "display_value_en", "value", "symbol",
         "scalar_factor", "vector", "release"),
        [(*row, "millions", f"v-{row[1]}", date(2025, 11, 21)) for row in municipal],
    )  # fmt: skip


def run(db, transformers: list[Transformer]) -> dict[str, list[CheckResult]]:
    """Run transformers in order the way the runner will; return each one's check results."""
    results = {}
    for transformer in transformers:
        transformer.transform(db).create(transformer.name)
        results[transformer.name] = transformer.checks(db)
    return results


def failed(results: list[CheckResult]) -> list[str]:
    return [result.name for result in results if not result.passed]


ALL_TRANSFORMERS = [Jurisdictions, Functions, Spending, MunicipalTransfers]


@pytest.fixture
def db() -> duckdb.DuckDBPyConnection:
    return duckdb.connect()


@pytest.fixture
def built(db):
    """A database where every round-1 model dataset was built from good data."""
    make_staged_tables(db)
    results = run(db, [make() for make in ALL_TRANSFORMERS])
    for name, checks in results.items():
        assert failed(checks) == [], name
    return db


# --- Jurisdictions and functions --------------------------------------------


def test_jurisdictions_have_codes_names_and_order(built):
    rows = built.sql("SELECT code, name_en, name_fr, kind FROM jurisdictions").fetchall()
    assert len(rows) == len(JURISDICTIONS) == 14
    assert rows[0] == ("ca", "Canada", "Canada (fr)", "country")
    assert rows[-1] == ("nu", "Nunavut", "Nunavut (fr)", "territory")


def test_jurisdiction_missing_from_the_data_fails_its_check(db):
    make_staged_tables(db)
    db.sql("DELETE FROM cofog_consolidated WHERE geo_en = 'Nunavut'")
    results = run(db, [Jurisdictions()])
    assert failed(results["jurisdictions"]) == ["jurisdictions: no missing name_en, name_fr"]


def test_functions_tree(built):
    rows = built.sql("""
        SELECT function_id, level, parent_id, statcan_codes FROM functions
        WHERE function_id LIKE '701%' ORDER BY sort_order
    """).fetchall()
    assert rows == [
        ("701", 1, None, "701"),
        ("7012", 2, "701", "7012"),
        ("7015-7016-7018", 2, "701", MERGED_CODE),
    ]


# --- Spending ---------------------------------------------------------------


def test_spending_amounts_are_in_dollars_with_flags_and_sources(built):
    row = built.sql("""
        SELECT amount, revision_status, release, source_id
        FROM spending
        WHERE view = 'province_wide' AND jurisdiction = 'qc'
          AND function_id = '701' AND fiscal_year = 2024
    """).fetchall()
    assert row == [(100_000_000, "preliminary", RELEASE, "statcan-10100005")]


def test_each_view_covers_what_it_should(built):
    rows = built.sql("""
        SELECT view, count(DISTINCT jurisdiction), count(DISTINCT function_id)
        FROM spending GROUP BY view ORDER BY view
    """).fetchall()
    assert rows == [
        ("canada", 1, 30),
        ("federal", 1, 30),
        ("province_wide", 14, 30),
        ("provincial_government", 13, 10),  # functions only
    ]


def test_only_the_latest_release_is_used(db):
    make_staged_tables(db)
    older = cofog_rows("Federal government", [CANADA], OLDER_RELEASE, value_offset=1000)
    create_table(db, "older", STAGED_COLUMNS, older)
    db.sql("INSERT INTO cofog_by_component SELECT * FROM older")

    run(db, [Jurisdictions(), Functions(), Spending()])
    releases = db.sql("SELECT DISTINCT release FROM spending WHERE view = 'federal'").fetchall()
    assert releases == [(RELEASE,)]


def test_sub_functions_that_do_not_add_up_fail_their_check(db):
    make_staged_tables(db)
    db.sql("""
        UPDATE cofog_by_component SET value = value + 5
        WHERE component_en = 'Federal government' AND function_code = '7022'
          AND ref_date = '2024'
    """)
    results = run(db, [Jurisdictions(), Functions(), Spending()])
    assert failed(results["spending"]) == [
        "spending: sub-functions add up to their function, within rounding"
    ]


def test_rounding_gaps_are_allowed(db):
    make_staged_tables(db)
    # Off by $1M across two sub-functions and a function: within rounding.
    db.sql("""
        UPDATE cofog_by_component SET value = value + 1
        WHERE component_en = 'Federal government' AND function_code = '7022'
    """)
    results = run(db, [Jurisdictions(), Functions(), Spending()])
    assert failed(results["spending"]) == []


def test_missing_jurisdiction_fails_the_coverage_check(db):
    make_staged_tables(db)
    db.sql("""
        DELETE FROM cofog_by_component
        WHERE component_en = 'Provincial and territorial governments' AND geo_en = 'Yukon'
    """)
    results = run(db, [Jurisdictions(), Functions(), Spending()])
    assert failed(results["spending"]) == [
        "spending: every view covers all its jurisdictions every year"
    ]


# --- Transfers to other governments -----------------------------------------


def test_federal_transfers_are_worked_out_for_functions_only(db):
    make_staged_tables(db)
    # Canada combined health becomes 160 (millions) while all provinces stay at
    # 100, so of its 100 the federal government spent 60 itself and transferred 40.
    db.sql("""
        UPDATE cofog_consolidated SET value = value * 1.6
        WHERE component_en = 'Consolidated Canadian general government'
          AND function_code LIKE '707%'
    """)
    results = run(db, [Jurisdictions(), Functions(), Spending()])
    assert failed(results["spending"]) == []
    rows = db.sql("""
        SELECT function_id, amount, transfers_to_governments FROM spending
        WHERE view = 'federal' AND fiscal_year = 2024 AND function_id LIKE '707%'
        ORDER BY function_id
    """).fetchall()
    assert rows == [
        ("707", 100_000_000, 40_000_000),
        ("7071", 30_000_000, None),  # sub-functions: not worked out
        ("7072", 70_000_000, None),
    ]


def test_consolidated_views_have_no_transfers_left_and_others_are_unknown(built):
    rows = built.sql("""
        SELECT view,
               count(*) FILTER (WHERE transfers_to_governments = 0) AS zero,
               count(*) FILTER (WHERE transfers_to_governments IS NULL) AS unknown,
               count(*) AS rows
        FROM spending WHERE view <> 'federal' GROUP BY view ORDER BY view
    """).fetchall()
    assert rows == [
        ("canada", 60, 0, 60),
        ("province_wide", 840, 0, 840),
        ("provincial_government", 0, 260, 260),
    ]


def test_transfers_larger_than_the_amount_fail_their_check(db):
    make_staged_tables(db)
    # Canada combined below all provinces combined: federal transfers would be
    # 100 - (50 - 100) = 150, more than the federal amount of 100.
    db.sql("""
        UPDATE cofog_consolidated SET value = value * 0.5
        WHERE component_en = 'Consolidated Canadian general government'
          AND function_code LIKE '703%'
    """)
    results = run(db, [Jurisdictions(), Functions(), Spending()])
    assert failed(results["spending"]) == [
        "spending: federal transfers to other governments are between 0 and the amount"
    ]


def test_rows_behind_transfers_with_different_statuses_fail_their_check(db):
    make_staged_tables(db)
    db.sql("""
        UPDATE cofog_consolidated SET symbol = 'r'
        WHERE component_en = 'Consolidated Canadian general government' AND ref_date = '2024'
    """)
    results = run(db, [Jurisdictions(), Functions(), Spending()])
    assert failed(results["spending"]) == [
        "spending: the rows behind federal transfers share a release and status"
    ]


# --- Municipal transfers ----------------------------------------------------


def test_municipal_transfers_use_flows_for_spending_years_only(built):
    rows = built.sql("""
        SELECT fiscal_year, amount, revision_status FROM municipal_transfers
        WHERE jurisdiction = 'on' ORDER BY fiscal_year
    """).fetchall()
    # 2007 has no spending (and no value); the "Stocks" row is ignored.
    assert rows == [(2023, 90_000_000, "revised"), (2024, 95_000_000, "preliminary")]
