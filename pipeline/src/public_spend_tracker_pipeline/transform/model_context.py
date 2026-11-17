"""Context figures that make spending comparable: prices, population and the size of the economy.

One dataset, context, with one row per jurisdiction, series, basis and year:

    series   cpi         consumer price index, to show spending in real dollars
             population  to show spending per person
             gdp         to show spending as a share of the economy
    basis    fiscal      April to March, matching spending: 2024 means 2024-25
             calendar    January to December
    method   exact       calculated exactly from the published figures
             blended     estimated from two calendar years (provincial GDP)
             partial     the next calendar year is not published yet, so
                         year N is used alone; replaced automatically later

How each value is worked out:

    CPI         fiscal: average of the 12 months April to March
                calendar: average of the 12 months January to December
                (a year missing any month gets no value). The territories
                use their capital city's index, as Statistics Canada does
                not publish a territory-wide one.
    Population  the July 1 estimate of year N, for both bases.
    GDP, ca     from quarterly national GDP (current prices, not seasonally
                adjusted): the sum of the four quarters in the year.
    GDP, others provincial GDP is only published by calendar year, so the
                fiscal year is 75% of year N plus 25% of year N+1 (nine months
                fall in N and three in N+1). Calendar year is year N.

Years run from the first year we have spending for to the latest the data
allows. Real dollars, per person and share of GDP are calculated later, as
views in the database the API serves, not here.
"""

from __future__ import annotations

import duckdb

from public_spend_tracker_pipeline.common.paths import MODEL
from public_spend_tracker_pipeline.transform.base import (
    CheckResult,
    Transformer,
    expect_no_rows,
    no_duplicate_keys,
    no_missing_values,
    sql_table,
    sql_text,
)
from public_spend_tracker_pipeline.transform.statcan_sql import (
    full_value,
    latest_release,
    source_id,
)

# Series, bases and methods (see the top of this module).
CPI = "cpi"
POPULATION = "population"
GDP = "gdp"
SERIES = (CPI, POPULATION, GDP)

FISCAL = "fiscal"
CALENDAR = "calendar"
BASES = (FISCAL, CALENDAR)

EXACT = "exact"
BLENDED = "blended"
PARTIAL = "partial"

# Which Statistics Canada rows each series uses.
CPI_PRODUCT = "All-items"
GDP_ESTIMATE = "Gross domestic product at market prices"
GDP_PRICES = "Current prices"
GDP_SEASONAL_ADJUSTMENT = "Unadjusted"  # so the four quarters add up to the year
POPULATION_MONTH = 7  # the July 1 estimate

# Months and quarters in a full year.
MONTHS_IN_YEAR = 12
QUARTERS_IN_YEAR = 4

# The fiscal year starts in April, three months after the calendar year. Moving
# a date back three months gives the calendar year that matches its fiscal
# year's start: April 2024 -> January 2024 (2024-25); March 2025 -> December
# 2024 (still 2024-25).
FISCAL_YEAR_SQL = "year(period_start - INTERVAL 3 MONTH)"

# Share of a fiscal year falling in its first calendar year (April to December)
# and in the next one (January to March).
FIRST_YEAR_SHARE = 0.75
NEXT_YEAR_SHARE = 0.25

# Staged datasets read here.
CPI_DATASET = "cpi_monthly"
POPULATION_DATASET = "population_quarterly"
NATIONAL_GDP_DATASET = "gdp_national_quarterly"
PROVINCIAL_GDP_DATASET = "gdp_provincial_annual"

# Our code for Canada as a whole.
CANADA_CODE = "ca"

# The dataset's columns, in order.
COLUMNS = (
    "jurisdiction",
    "series",
    "basis",
    "year",
    "value",
    "unit",
    "method",
    "release",
    "source_id",
    "vector",
)


class Context(Transformer):
    """CPI, population and GDP for every jurisdiction, by fiscal and calendar year.

    Columns: jurisdiction, series, basis, year, value, unit, method, release,
    source_id, vector.
    """

    name = "context"
    description = "Consumer prices, population and GDP, by fiscal and calendar year"
    stage = MODEL
    inputs = (
        CPI_DATASET,
        POPULATION_DATASET,
        NATIONAL_GDP_DATASET,
        PROVINCIAL_GDP_DATASET,
        "jurisdictions",
        "spending",
    )

    def transform(self, db: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyRelation:
        """Each series' rows, stacked, from the first spending year onward."""
        # "BY NAME" stacks the queries by matching column names, not positions.
        series = "\nUNION ALL BY NAME\n".join(
            f"({query})"
            for query in (_cpi_sql(), _population_sql(), _national_gdp_sql(), _provincial_gdp_sql())
        )
        return db.sql(f"""
            SELECT {", ".join(COLUMNS)} FROM ({series})
            WHERE year >= (SELECT min(fiscal_year) FROM spending)
            ORDER BY jurisdiction, series, basis, year
        """)

    def checks(self, db: duckdb.DuckDBPyConnection) -> list[CheckResult]:
        """Unique, filled in, and present for every jurisdiction and every spending year."""
        needed = sql_table(
            ["series", "basis"], [(series, basis) for series in SERIES for basis in BASES]
        )
        return [
            no_duplicate_keys(db, self.name, ["jurisdiction", "series", "basis", "year"]),
            no_missing_values(db, self.name, ["value", "unit", "method"]),
            expect_no_rows(
                db,
                f"{self.name}: every jurisdiction has every series for every spending year",
                f"""SELECT j.code AS jurisdiction, n.series, n.basis, y.fiscal_year AS year
                    FROM jurisdictions AS j
                    CROSS JOIN ({needed}) AS n
                    CROSS JOIN (SELECT DISTINCT fiscal_year FROM spending) AS y
                    EXCEPT
                    SELECT jurisdiction, series, basis, year FROM {self.name}""",
            ),
        ]


# --- One query per series ---------------------------------------------------
# Each returns the columns: jurisdiction, series, basis, year, value, unit,
# method, release, source_id, vector.


def _cpi_sql() -> str:
    """Average CPI over each fiscal and calendar year that has all 12 months."""
    months = f"""
        SELECT j.code AS jurisdiction, c.period_start, c.value, c.unit, c.release, c.vector
        FROM {CPI_DATASET} AS c
        JOIN jurisdictions AS j ON c.geo_en = j.cpi_place
        WHERE c.release = {latest_release(CPI_DATASET)}
          AND c.product_en = {sql_text(CPI_PRODUCT)}
    """
    return "\nUNION ALL\n".join(
        f"""
        SELECT
            jurisdiction,
            {sql_text(CPI)} AS series,
            {sql_text(basis)} AS basis,
            {year} AS year,
            avg(value) AS value,
            'index (' || any_value(unit) || ')' AS unit,
            {sql_text(EXACT)} AS method,
            any_value(release) AS release,
            {sql_text(source_id(CPI_DATASET))} AS source_id,
            any_value(vector) AS vector
        FROM ({months})
        GROUP BY jurisdiction, {year}
        HAVING count(value) = {MONTHS_IN_YEAR}
        """
        for basis, year in ((FISCAL, FISCAL_YEAR_SQL), (CALENDAR, "year(period_start)"))
    )


def _population_sql() -> str:
    """The July 1 population estimate, used for both the fiscal and calendar year."""
    return "\nUNION ALL\n".join(
        f"""
        SELECT
            j.code AS jurisdiction,
            {sql_text(POPULATION)} AS series,
            {sql_text(basis)} AS basis,
            year(p.period_start) AS year,
            {full_value("p")} AS value,
            lower(p.unit) AS unit,
            {sql_text(EXACT)} AS method,
            p.release,
            {sql_text(source_id(POPULATION_DATASET))} AS source_id,
            p.vector
        FROM {POPULATION_DATASET} AS p
        JOIN jurisdictions AS j ON p.geo_en = j.statcan_name
        WHERE p.release = {latest_release(POPULATION_DATASET)}
          AND month(p.period_start) = {POPULATION_MONTH}
        """
        for basis in BASES
    )


def _national_gdp_sql() -> str:
    """Canada's GDP: the sum of the four quarters in each fiscal and calendar year."""
    quarters = f"""
        SELECT g.period_start, {full_value("g")} AS value, g.unit, g.release, g.vector
        FROM {NATIONAL_GDP_DATASET} AS g
        WHERE g.release = {latest_release(NATIONAL_GDP_DATASET)}
          AND g.geo_en = 'Canada'
          AND g.estimate_en = {sql_text(GDP_ESTIMATE)}
          AND g.prices_en = {sql_text(GDP_PRICES)}
          AND g.seasonal_adjustment_en = {sql_text(GDP_SEASONAL_ADJUSTMENT)}
    """
    return "\nUNION ALL\n".join(
        f"""
        SELECT
            {sql_text(CANADA_CODE)} AS jurisdiction,
            {sql_text(GDP)} AS series,
            {sql_text(basis)} AS basis,
            {year} AS year,
            sum(value) AS value,
            lower(any_value(unit)) AS unit,
            {sql_text(EXACT)} AS method,
            any_value(release) AS release,
            {sql_text(source_id(NATIONAL_GDP_DATASET))} AS source_id,
            any_value(vector) AS vector
        FROM ({quarters})
        GROUP BY {year}
        HAVING count(value) = {QUARTERS_IN_YEAR}
        """
        for basis, year in ((FISCAL, FISCAL_YEAR_SQL), (CALENDAR, "year(period_start)"))
    )


def _provincial_gdp_sql() -> str:
    """Provinces' and territories' GDP: calendar year as published, fiscal year blended.

    The fiscal year is 75% of year N plus 25% of year N+1. When year N+1 is not
    published yet, year N is used alone and marked "partial".
    """
    years = f"""
        SELECT j.code AS jurisdiction, year(g.period_start) AS year,
               {full_value("g")} AS value, g.unit, g.release, g.vector
        FROM {PROVINCIAL_GDP_DATASET} AS g
        JOIN jurisdictions AS j ON g.geo_en = j.statcan_name
        WHERE g.release = {latest_release(PROVINCIAL_GDP_DATASET)}
          AND j.code <> {sql_text(CANADA_CODE)}
          AND g.estimate_en = {sql_text(GDP_ESTIMATE)}
          AND g.prices_en = {sql_text(GDP_PRICES)}
          AND g.value IS NOT NULL
    """
    common = f"""
        {sql_text(GDP)} AS series,
        lower(this_year.unit) AS unit,
        this_year.release,
        {sql_text(source_id(PROVINCIAL_GDP_DATASET))} AS source_id,
        this_year.vector
    """
    return f"""
        SELECT
            this_year.jurisdiction,
            {sql_text(CALENDAR)} AS basis,
            this_year.year,
            this_year.value,
            {sql_text(EXACT)} AS method,
            {common}
        FROM ({years}) AS this_year

        UNION ALL BY NAME

        SELECT
            this_year.jurisdiction,
            {sql_text(FISCAL)} AS basis,
            this_year.year,
            CASE WHEN next_year.value IS NULL THEN this_year.value
                 ELSE {FIRST_YEAR_SHARE} * this_year.value + {NEXT_YEAR_SHARE} * next_year.value
            END AS value,
            CASE WHEN next_year.value IS NULL THEN {sql_text(PARTIAL)}
                 ELSE {sql_text(BLENDED)} END AS method,
            {common}
        FROM ({years}) AS this_year
        LEFT JOIN ({years}) AS next_year
            ON next_year.jurisdiction = this_year.jurisdiction
           AND next_year.year = this_year.year + 1
    """
