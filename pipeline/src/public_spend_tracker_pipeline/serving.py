"""The serving layer: the measure views and build information in every build's database.

schema/serving.sql (at the repository root) defines the views that calculate
the measures: real dollars, per person, share of GDP. It is the contract
between the pipeline and everything that reads the database. This module:

    1. adds build_info, a one-row table the API and site read ("data as of ...")
    2. applies schema/serving.sql, creating the views
    3. checks the views, before anything is saved

The build then saves build_info with the model tables and applies the same
SQL inside the saved database file, so the views travel with the data.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import duckdb

from public_spend_tracker_pipeline.settings import SERVING_SQL_FILE
from public_spend_tracker_pipeline.transform.base import (
    CheckResult,
    expect_no_rows,
    has_rows,
    no_missing_values,
    sql_text,
)

# The one-row table describing the build.
BUILD_INFO = "build_info"

# The views holding measures, and their measure columns.
MEASURE_VIEWS = ("spending_measures", "municipal_transfers_measures")
MEASURE_COLUMNS = ("amount_real", "amount_per_person", "amount_real_per_person", "percent_of_gdp")

# Real and nominal dollars must match in the base year to within this much
# (they should be identical; this only allows for how computers store decimals).
SAME_DOLLARS_TOLERANCE = 0.01


class Serving:
    """Prepares and checks the serving layer of a build's database.

    sql_file  The SQL file with the view definitions. Normally schema/serving.sql.
    """

    # Tables this adds, which the build saves alongside the model tables.
    tables = (BUILD_INFO,)

    def __init__(self, sql_file: Path = SERVING_SQL_FILE) -> None:
        self.sql_file = sql_file
        self.sql = sql_file.read_text(encoding="utf-8")

    def prepare(self, db: duckdb.DuckDBPyConnection, build_id: str, built_at: datetime) -> None:
        """Add build_info and create the views, in the build's working database."""
        _add_build_info(db, build_id, built_at)
        self.create_views(db)

    def create_views(self, db: duckdb.DuckDBPyConnection) -> None:
        """Run the SQL file, creating (or replacing) every view."""
        db.sql(self.sql)

    def checks(self, db: duckdb.DuckDBPyConnection) -> list[CheckResult]:
        """Every measure is filled in, anchored to the base year, and in a sensible range."""
        results = [has_rows(db, BUILD_INFO)]
        for view in MEASURE_VIEWS:
            results += [
                has_rows(db, view),
                no_missing_values(db, view, MEASURE_COLUMNS),
                expect_no_rows(
                    db,
                    f"{view}: real dollars equal nominal dollars in the base year",
                    f"""SELECT * FROM {view}
                        WHERE fiscal_year = base_year
                          AND abs(amount_real - amount) > {SAME_DOLLARS_TOLERANCE}""",
                ),
                expect_no_rows(
                    db,
                    f"{view}: share of GDP between 0 and 100%",
                    f"SELECT * FROM {view} WHERE percent_of_gdp NOT BETWEEN 0 AND 100",
                ),
                expect_no_rows(
                    db,
                    f"{view}: per-person amounts have the same sign as amounts",
                    f"SELECT * FROM {view} WHERE sign(amount_per_person) <> sign(amount)",
                ),
            ]
        return results


def _add_build_info(db: duckdb.DuckDBPyConnection, build_id: str, built_at: datetime) -> None:
    """Create build_info: the build ID, when it was built (UTC), and the years covered.

    base_year is the newest fiscal year with spending: real dollars are in its dollars.
    """
    built_at_utc = built_at.replace(tzinfo=None).isoformat(sep=" ", timespec="seconds")
    db.sql(f"""
        CREATE OR REPLACE TABLE {BUILD_INFO} AS
        SELECT
            {sql_text(build_id)} AS build_id,
            TIMESTAMP {sql_text(built_at_utc)} AS built_at,
            max(fiscal_year) AS base_year,
            min(fiscal_year) AS first_fiscal_year,
            max(fiscal_year) AS latest_fiscal_year
        FROM spending
    """)
