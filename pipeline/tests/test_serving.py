"""Tests for the measure views in schema/serving.sql and their checks.

They build tiny made-up model tables for Canada ("ca") and Ontario ("on") over
fiscal years 2023-24 and 2024-25, apply the real serving SQL, and check the
measures by hand-worked examples.
"""

from datetime import UTC, date, datetime

import duckdb
import pytest

from public_spend_tracker_pipeline.serving import Serving
from public_spend_tracker_pipeline.transform.base import sql_table

RELEASE = date(2025, 11, 27)
BUILT_AT = datetime(2026, 11, 15, 15, 30, tzinfo=UTC)

SPENDING = [
    # view, jurisdiction, function_id, fiscal_year, amount, transfers_to_governments
    ("federal", "ca", "701", 2023, 1000, 600),
    ("federal", "ca", "701", 2024, 2000, 1500),
    ("federal", "ca", "7011", 2024, 300, None),  # a sub-function: transfers not known
    ("province_wide", "on", "701", 2024, 500, 0),  # consolidated: no transfers left
]

# CPI by jurisdiction, basis and year: Ontario's prices rose faster than Canada's.
CPI = {
    ("ca", "fiscal", 2023): 100.0,
    ("ca", "fiscal", 2024): 110.0,
    ("ca", "calendar", 2023): 98.0,
    ("ca", "calendar", 2024): 108.0,
    ("on", "fiscal", 2023): 100.0,
    ("on", "fiscal", 2024): 125.0,
    ("on", "calendar", 2023): 99.0,
    ("on", "calendar", 2024): 120.0,
}
POPULATION = {"ca": 10.0, "on": 4.0}
GDP = {
    # jurisdiction, basis, year -> (value, method)
    ("ca", "fiscal", 2023): (10_000.0, "exact"),
    ("ca", "fiscal", 2024): (20_000.0, "exact"),
    ("ca", "calendar", 2023): (9_000.0, "exact"),
    ("ca", "calendar", 2024): (19_000.0, "exact"),
    ("on", "fiscal", 2023): (4_000.0, "blended"),
    ("on", "fiscal", 2024): (5_000.0, "partial"),
    ("on", "calendar", 2023): (3_500.0, "exact"),
    ("on", "calendar", 2024): (4_500.0, "exact"),
}


def make_model_tables(db):
    spending = [(*row, "preliminary", RELEASE, "statcan-10100024", "v1") for row in SPENDING]
    db.sql(f"""CREATE TABLE spending AS {sql_table(
        ["view", "jurisdiction", "function_id", "fiscal_year", "amount",
         "transfers_to_governments", "revision_status", "release", "source_id", "vector"],
        spending)}""")  # fmt: skip

    transfers = [("on", 2024, 300, "preliminary", RELEASE, "statcan-10100020", "v2")]
    db.sql(f"""CREATE TABLE municipal_transfers AS {sql_table(
        ["jurisdiction", "fiscal_year", "amount", "revision_status", "release",
         "source_id", "vector"], transfers)}""")  # fmt: skip

    context = [(*key, "cpi", value, "exact") for key, value in CPI.items()]
    context += [
        (code, basis, year, "population", POPULATION[code], "exact") for code, basis, year in CPI
    ]
    context += [(*key, "gdp", value, method) for key, (value, method) in GDP.items()]
    db.sql(f"""CREATE TABLE context AS {sql_table(
        ["jurisdiction", "basis", "year", "series", "value", "method"], context)}""")  # fmt: skip


@pytest.fixture
def db():
    connection = duckdb.connect()
    make_model_tables(connection)
    Serving().prepare(connection, "20261115-153000", BUILT_AT)
    return connection


def measures(db, view, jurisdiction, year, basis, transfers="included"):
    """The measures for function 701 in one view, jurisdiction, year, basis and transfers choice."""
    return db.sql(f"""
        SELECT amount, amount_real, amount_per_person, amount_real_per_person,
               percent_of_gdp, base_year, gdp_method
        FROM spending_measures
        WHERE view = '{view}' AND jurisdiction = '{jurisdiction}' AND function_id = '701'
          AND fiscal_year = {year} AND context_basis = '{basis}'
          AND transfers = '{transfers}'
    """).fetchall()[0]


def test_every_check_passes_on_good_data(db):
    results = Serving().checks(db)
    assert [result.name for result in results if not result.passed] == []


def test_build_info(db):
    rows = db.sql("SELECT * FROM build_info").fetchall()
    assert rows == [("20261115-153000", datetime(2026, 11, 15, 15, 30), 2024, 2023, 2024)]


def test_real_equals_nominal_in_the_base_year(db):
    amount, real, *_ = measures(db, "federal", "ca", 2024, "fiscal")
    assert real == amount == 2000


def test_earlier_years_scale_by_the_cpi_ratio(db):
    amount, real, per_person, real_per_person, percent, base_year, method = measures(
        db, "federal", "ca", 2023, "fiscal"
    )
    assert real == pytest.approx(1000 * 110 / 100)  # in 2024-25 dollars
    assert per_person == pytest.approx(1000 / 10)
    assert real_per_person == pytest.approx(1100 / 10)
    assert percent == pytest.approx(1000 / 10_000 * 100)
    assert (base_year, method) == (2024, "exact")


def test_calendar_basis_uses_calendar_context(db):
    _, real, _, _, percent, _, _ = measures(db, "federal", "ca", 2023, "calendar")
    assert real == pytest.approx(1000 * 108 / 98)
    assert percent == pytest.approx(1000 / 9_000 * 100)


def test_each_jurisdiction_uses_its_own_context(db):
    _, _, per_person, _, percent, _, method = measures(db, "province_wide", "on", 2024, "fiscal")
    assert per_person == pytest.approx(500 / 4)
    assert percent == pytest.approx(500 / 5_000 * 100)
    assert method == "partial"  # passed through, so the site can add a footnote


def test_excluding_transfers_takes_them_out_of_every_measure(db):
    amount, real, per_person, real_per_person, percent, *_ = measures(
        db, "federal", "ca", 2023, "fiscal", transfers="excluded"
    )
    assert amount == 1000 - 600
    assert real == pytest.approx(400 * 110 / 100)
    assert per_person == pytest.approx(400 / 10)
    assert real_per_person == pytest.approx(440 / 10)
    assert percent == pytest.approx(400 / 10_000 * 100)


def test_only_rows_with_a_known_transfer_figure_can_exclude_it(db):
    rows = db.sql("""
        SELECT view, function_id, transfers, amount, transfers_to_governments
        FROM spending_measures
        WHERE fiscal_year = 2024 AND context_basis = 'fiscal'
        ORDER BY view, function_id, transfers
    """).fetchall()
    assert rows == [
        ("federal", "701", "excluded", 500, 1500),
        ("federal", "701", "included", 2000, 1500),
        ("federal", "7011", "included", 300, None),  # no "excluded" row
        ("province_wide", "701", "excluded", 500, 0),  # the same either way
        ("province_wide", "701", "included", 500, 0),
    ]


def test_municipal_transfers_get_the_same_measures(db):
    rows = db.sql("""
        SELECT context_basis, amount_real, amount_per_person, percent_of_gdp
        FROM municipal_transfers_measures ORDER BY context_basis
    """).fetchall()
    assert rows == [
        ("calendar", pytest.approx(300.0), pytest.approx(75.0), pytest.approx(300 / 4_500 * 100)),
        ("fiscal", pytest.approx(300.0), pytest.approx(75.0), pytest.approx(300 / 5_000 * 100)),
    ]


def test_missing_population_fails_the_check(db):
    db.sql("DELETE FROM context WHERE jurisdiction = 'on' AND series = 'population'")
    failed = [result.name for result in Serving().checks(db) if not result.passed]
    assert failed == [
        "spending_measures: no missing amount_real, amount_per_person, amount_real_per_person, "
        "percent_of_gdp",
        "municipal_transfers_measures: no missing amount_real, amount_per_person, "
        "amount_real_per_person, percent_of_gdp",
    ]


def test_share_of_gdp_over_100_percent_fails_the_check(db):
    # A unit mistake, e.g. GDP left in millions, would push shares far over 100%.
    db.sql("UPDATE context SET value = value / 1000 WHERE series = 'gdp'")
    failed = [result.name for result in Serving().checks(db) if not result.passed]
    assert "spending_measures: share of GDP between 0 and 100%" in failed
