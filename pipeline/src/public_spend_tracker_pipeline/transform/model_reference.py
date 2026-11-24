"""The two reference lists every other dataset points to: jurisdictions and functions.

jurisdictions  The 14 places we cover (Canada, 10 provinces, 3 territories),
               with official English and French names.
functions      The COFOG tree: 10 functions and their sub-functions, with
               official English and French names.

Both take their names from Statistics Canada's consolidated spending table, so
the labels on the site are the official ones in both languages.
"""

from __future__ import annotations

import duckdb

from public_spend_tracker_pipeline.common.paths import MODEL
from public_spend_tracker_pipeline.common.settings import JURISDICTIONS
from public_spend_tracker_pipeline.transform.base import (
    CheckResult,
    Layout,
    Transformer,
    expect_no_rows,
    no_duplicate_keys,
    no_missing_values,
    sql_text,
)
from public_spend_tracker_pipeline.transform.statcan_sql import latest_release

# Where the official names come from.
NAMES_DATASET = "cofog_consolidated"

# COFOG has exactly 10 functions (codes 701 to 710).
FUNCTION_COUNT = 10

# A function's code has 3 digits ("701"); a sub-function's has 4 ("7011").
FUNCTION_CODE_LENGTH = 3

# Some sub-functions are merged groups with several codes, published as
# "7015, 7016, 7018". In our IDs the codes are joined with dashes instead,
# "7015-7016-7018", which reads well and is safe in web addresses.
PUBLISHED_CODE_SEPARATOR = ", "
ID_CODE_SEPARATOR = "-"


class Jurisdictions(Transformer):
    """The places we cover, from settings.JURISDICTIONS, with official names in both languages."""

    name = "jurisdictions"
    description = "Canada, the 10 provinces and the 3 territories, with English and French names"
    stage = MODEL
    inputs = (NAMES_DATASET,)
    layout = Layout(
        keys=("code",),
        tracked=("name_en", "name_fr", "kind", "sort_order", "statcan_name", "cpi_place"),
    )

    def transform(self, db: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyRelation:
        """Our list of places, with each one's names looked up in Statistics Canada's data.

        A place whose name is not found gets empty names, which the checks catch.
        """
        return db.sql(f"""
            WITH ours AS ({_jurisdictions_as_sql()}),
            official_names AS (
                SELECT DISTINCT geo_en, geo_fr
                FROM {NAMES_DATASET}
                WHERE release = {latest_release(NAMES_DATASET)}
            )
            SELECT
                ours.code,
                official_names.geo_en AS name_en,
                official_names.geo_fr AS name_fr,
                ours.kind,
                ours.sort_order,
                ours.statcan_name,
                ours.cpi_place
            FROM ours
            LEFT JOIN official_names ON official_names.geo_en = ours.statcan_name
            ORDER BY ours.sort_order
        """)

    def checks(self, db: duckdb.DuckDBPyConnection) -> list[CheckResult]:
        """Each code appears once, and every place was found with both names."""
        return [
            no_duplicate_keys(db, self.name, self.layout.keys),
            no_missing_values(db, self.name, ["name_en", "name_fr"]),
        ]


class Functions(Transformer):
    """The COFOG functions and sub-functions, with official names in both languages.

    Columns:
        function_id    "701" for a function, "7011" or "7015-7016-7018" for a sub-function
        level          1 for a function, 2 for a sub-function
        parent_id      the function a sub-function belongs to; empty for functions
        statcan_codes  the code exactly as Statistics Canada publishes it
        name_en, name_fr
        sort_order     each function followed by its sub-functions, in code order
    """

    name = "functions"
    description = "The 10 COFOG functions and their sub-functions, with English and French names"
    stage = MODEL
    inputs = (NAMES_DATASET,)
    layout = Layout(
        keys=("function_id",),
        tracked=("level", "parent_id", "statcan_codes", "name_en", "name_fr", "sort_order"),
    )

    def transform(self, db: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyRelation:
        """One row per COFOG code in Statistics Canada's consolidated table."""
        is_function = f"length(function_code) = {FUNCTION_CODE_LENGTH}"
        return db.sql(f"""
            WITH codes AS (
                SELECT DISTINCT function_code, function_en, function_fr
                FROM {NAMES_DATASET}
                WHERE release = {latest_release(NAMES_DATASET)}
            )
            SELECT
                replace(function_code, {sql_text(PUBLISHED_CODE_SEPARATOR)},
                        {sql_text(ID_CODE_SEPARATOR)}) AS function_id,
                CASE WHEN {is_function} THEN 1 ELSE 2 END AS level,
                CASE WHEN {is_function} THEN NULL
                     ELSE left(function_code, {FUNCTION_CODE_LENGTH}) END AS parent_id,
                function_code AS statcan_codes,
                function_en AS name_en,
                function_fr AS name_fr,
                -- Code order puts each function just before its sub-functions:
                -- "701", "7011", "7012", ..., "702", "7021", ...
                row_number() OVER (ORDER BY function_code) AS sort_order
            FROM codes
            ORDER BY sort_order
        """)

    def checks(self, db: duckdb.DuckDBPyConnection) -> list[CheckResult]:
        """Unique IDs, both names, exactly 10 functions, and every sub-function has its parent."""
        return [
            no_duplicate_keys(db, self.name, self.layout.keys),
            no_missing_values(db, self.name, ["name_en", "name_fr"]),
            expect_no_rows(
                db,
                f"{self.name}: exactly {FUNCTION_COUNT} functions",
                f"""SELECT count(*) AS functions FROM {self.name} WHERE level = 1
                    HAVING count(*) <> {FUNCTION_COUNT}""",
            ),
            expect_no_rows(
                db,
                f"{self.name}: every sub-function belongs to a function",
                f"""SELECT function_id, parent_id FROM {self.name}
                    WHERE level = 2 AND parent_id NOT IN
                        (SELECT function_id FROM {self.name} WHERE level = 1)""",
            ),
        ]


def _jurisdictions_as_sql() -> str:
    """settings.JURISDICTIONS written as a SQL table, with a sort_order column."""
    rows = ",\n".join(
        f"({sql_text(place.code)}, {sql_text(place.kind)}, {position}, "
        f"{sql_text(place.statcan_name)}, {sql_text(place.cpi_place)})"
        for position, place in enumerate(JURISDICTIONS, start=1)
    )
    return f"SELECT * FROM (VALUES {rows}) AS ours(code, kind, sort_order, statcan_name, cpi_place)"
