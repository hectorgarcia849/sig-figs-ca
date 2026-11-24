"""Tests for the context dataset (CPI, population, GDP by fiscal and calendar year).

They build small made-up staged tables for three places, Canada, Ontario and
Yukon, covering spending years 2023-24 and 2024-25, then run the transformer
the way the runner will.
"""

from datetime import date
from statistics import mean

import duckdb
import pytest

from public_spend_tracker_pipeline.transform.base import CheckResult, sql_table
from public_spend_tracker_pipeline.transform.model_context import (
    CPI_PRODUCT,
    GDP_ESTIMATE,
    GDP_PRICES,
    GDP_SEASONAL_ADJUSTMENT,
    Context,
    _exact_sum,
)

RELEASE = date(2026, 10, 19)
SPENDING_YEARS = (2023, 2024)
PLACES = [
    # code, Statistics Canada name, CPI place
    ("ca", "Canada", "Canada"),
    ("on", "Ontario", "Ontario"),
    ("yt", "Yukon", "Whitehorse, Yukon"),
]


def months(first: date, last: date) -> list[date]:
    """The first day of every month from first to last."""
    result, current = [], first
    while current <= last:
        result.append(current)
        current = date(current.year + current.month // 12, current.month % 12 + 1, 1)
    return result


MONTHS = months(date(2023, 1, 1), date(2025, 3, 1))
QUARTERS = [month for month in MONTHS if month.month in (1, 4, 7, 10)]


# Made-up starting index for each CPI place; it then rises by 1 each month.
CPI_START = {"Canada": 100.0, "Ontario": 200.0, "Whitehorse, Yukon": 300.0}


def cpi_value(place: str, month: date) -> float:
    """A made-up index that is different for every place and month."""
    return CPI_START[place] + MONTHS.index(month)


def create(db, name, columns, rows):
    db.sql(f"CREATE OR REPLACE TABLE {name} AS {sql_table(columns, rows)}")


def make_tables(db):
    """Create the made-up staged and model tables that context reads."""
    create(
        db,
        "jurisdictions",
        ["code", "statcan_name", "cpi_place"],
        PLACES,
    )
    create(db, "spending", ["fiscal_year"], [(year,) for year in SPENDING_YEARS])

    cpi_rows = [
        (cpi_place, CPI_PRODUCT, month, cpi_value(cpi_place, month))
        for _, _, cpi_place in PLACES
        for month in MONTHS
    ]
    # A Yukon-wide index does not exist in reality; this one must be ignored.
    cpi_rows += [("Yukon", CPI_PRODUCT, month, 999.0) for month in MONTHS]
    create(
        db,
        "cpi_monthly",
        ["geo_en", "product_en", "period_start", "value", "unit", "release", "vector"],
        [(*row, "2002=100", RELEASE, f"v-cpi-{row[0]}") for row in cpi_rows],
    )

    population_rows = [
        (name, quarter, 1000.0 * (1 + PLACES.index((code, name, cpi)))
         + (5.0 if quarter.month == 7 else 0.0) + quarter.year)
        for code, name, cpi in PLACES
        for quarter in QUARTERS
    ]  # fmt: skip
    create(
        db,
        "population_quarterly",
        ["geo_en", "period_start", "value", "unit", "scalar_factor", "release", "vector"],
        [(*row, "Persons", "units", RELEASE, f"v-pop-{row[0]}") for row in population_rows],
    )

    national = [
        ("Canada", GDP_ESTIMATE, GDP_PRICES, GDP_SEASONAL_ADJUSTMENT, quarter,
         float(QUARTERS.index(quarter) + 1))
        for quarter in QUARTERS
    ]  # fmt: skip
    # Seasonally adjusted figures must be ignored.
    national += [
        ("Canada", GDP_ESTIMATE, GDP_PRICES, "Seasonally adjusted at annual rates", q, 999.0)
        for q in QUARTERS
    ]
    create(
        db,
        "gdp_national_quarterly",
        ["geo_en", "estimate_en", "prices_en", "seasonal_adjustment_en", "period_start", "value",
         "unit", "scalar_factor", "release", "vector"],
        [(*row, "Dollars", "millions", RELEASE, "v-gdp-ca") for row in national],
    )  # fmt: skip

    provincial = [
        ("Ontario", date(2023, 1, 1), 1000.0),
        ("Ontario", date(2024, 1, 1), 1100.0),
        ("Ontario", date(2025, 1, 1), 1200.0),
        ("Yukon", date(2023, 1, 1), 10.0),
        ("Yukon", date(2024, 1, 1), 20.0),  # 2025 not published yet
        ("Canada", date(2024, 1, 1), 999.0),  # Canada comes from the quarterly table
    ]
    create(
        db,
        "gdp_provincial_annual",
        ["geo_en", "period_start", "value", "estimate_en", "prices_en", "unit", "scalar_factor",
         "release", "vector"],
        [(*row, GDP_ESTIMATE, GDP_PRICES, "Dollars", "millions", RELEASE, f"v-gdp-{row[0]}")
         for row in provincial],
    )  # fmt: skip


def run(db) -> list[CheckResult]:
    context = Context()
    context.transform(db).create(context.name)
    return context.checks(db)


def value(db, jurisdiction, series, basis, year):
    rows = db.sql(f"""
        SELECT value, method FROM context
        WHERE jurisdiction = '{jurisdiction}' AND series = '{series}'
          AND basis = '{basis}' AND year = {year}
    """).fetchall()
    return rows[0] if rows else None


@pytest.fixture
def db():
    connection = duckdb.connect()
    make_tables(connection)
    return connection


@pytest.fixture
def built(db):
    results = run(db)
    assert all(result.passed for result in results), results
    return db


def test_cpi_fiscal_year_is_the_april_to_march_average(built):
    fiscal_2023 = [m for m in MONTHS if date(2023, 4, 1) <= m <= date(2024, 3, 1)]
    expected = mean(cpi_value("Ontario", m) for m in fiscal_2023)
    assert value(built, "on", "cpi", "fiscal", 2023) == (pytest.approx(expected), "exact")


def test_cpi_calendar_year_is_the_january_to_december_average(built):
    calendar_2024 = [m for m in MONTHS if m.year == 2024]
    expected = mean(cpi_value("Ontario", m) for m in calendar_2024)
    assert value(built, "on", "cpi", "calendar", 2024) == (pytest.approx(expected), "exact")


def test_territories_use_their_capital_city_cpi(built):
    calendar_2024 = [m for m in MONTHS if m.year == 2024]
    expected = mean(cpi_value("Whitehorse, Yukon", m) for m in calendar_2024)
    assert value(built, "yt", "cpi", "calendar", 2024)[0] == pytest.approx(expected)


def test_year_missing_a_month_has_no_cpi_and_fails_the_check(db):
    db.sql("DELETE FROM cpi_monthly WHERE geo_en = 'Ontario' AND period_start = '2024-02-01'")
    results = run(db)
    assert value(db, "on", "cpi", "fiscal", 2023) is None
    assert value(db, "on", "cpi", "calendar", 2024) is None
    failed = [result for result in results if not result.passed]
    assert [result.name for result in failed] == [
        "context: every jurisdiction has every series for every spending year"
    ]
    assert "('on', 'cpi', 'fiscal', 2023)" in failed[0].detail


def test_population_uses_the_july_1_estimate_for_both_bases(built):
    july_2024 = 2000.0 + 5.0 + 2024  # Ontario's made-up July value
    assert value(built, "on", "population", "fiscal", 2024) == (july_2024, "exact")
    assert value(built, "on", "population", "calendar", 2024) == (july_2024, "exact")


def test_national_gdp_adds_up_the_fiscal_and_calendar_quarters(built):
    def quarter_value(year, month):
        return QUARTERS.index(date(year, month, 1)) + 1

    fiscal_2024 = sum(quarter_value(*q) for q in [(2024, 4), (2024, 7), (2024, 10), (2025, 1)])
    calendar_2024 = sum(quarter_value(2024, month) for month in (1, 4, 7, 10))
    assert value(built, "ca", "gdp", "fiscal", 2024) == (fiscal_2024 * 1e6, "exact")
    assert value(built, "ca", "gdp", "calendar", 2024) == (calendar_2024 * 1e6, "exact")


def test_provincial_gdp_fiscal_year_is_blended(built):
    expected = (0.75 * 1100 + 0.25 * 1200) * 1e6
    assert value(built, "on", "gdp", "fiscal", 2024) == (pytest.approx(expected), "blended")
    assert value(built, "on", "gdp", "calendar", 2024) == (1100e6, "exact")


def test_provincial_gdp_without_next_year_is_partial(built):
    assert value(built, "yt", "gdp", "fiscal", 2024) == (20e6, "partial")
    assert value(built, "yt", "gdp", "fiscal", 2023) == (pytest.approx(12.5e6), "blended")


def test_months_and_quarters_are_added_up_exactly():
    # Ten 0.1s add up to 0.9999999999999999 in ordinary floating point; exactly, to 1.
    db = duckdb.connect()
    db.sql("CREATE TABLE t AS SELECT 0.1::DOUBLE AS v FROM range(10)")
    assert db.sql(f"SELECT {_exact_sum('v')} FROM t").fetchall()[0][0] == 1.0
    assert db.sql("SELECT sum(v) FROM t").fetchall()[0][0] != 1.0
