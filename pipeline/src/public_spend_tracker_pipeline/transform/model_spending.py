"""Spending by function of government, in each of the four views, plus the municipal bucket.

spending             One row per view, jurisdiction, function and fiscal year.
municipal_transfers  Money municipalities received from other governments,
                     shown with the "provincial government only" view.

The four views (every page says which one it shows):

    federal                The federal government. Functions and sub-functions.
    province_wide          Each province or territory with its municipalities,
                           hospitals, school boards, universities and colleges,
                           with transfers among them removed. The fair way to
                           compare provinces. "ca" is all of them combined.
    provincial_government  The provincial or territorial government alone.
                           Statistics Canada publishes the 10 functions only.
    canada                 All governments in Canada combined, with transfers
                           between them removed so each dollar counts once.

Only the newest Statistics Canada release is used. Every row records which
release it came from and the series it was read from (vector), so each figure
can be traced to its source.

Amounts are in dollars, written out in full. They cover operating spending:
Statistics Canada's figures leave out capital purchases (roads, buildings,
equipment) and depreciation.
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from public_spend_tracker_pipeline.paths import MODEL
from public_spend_tracker_pipeline.transform.base import (
    CheckResult,
    Transformer,
    expect_no_rows,
    no_duplicate_keys,
    no_missing_values,
    sql_table,
    sql_text,
)
from public_spend_tracker_pipeline.transform.model_reference import (
    FUNCTION_CODE_LENGTH,
    FUNCTION_COUNT,
    ID_CODE_SEPARATOR,
    PUBLISHED_CODE_SEPARATOR,
)
from public_spend_tracker_pipeline.transform.statcan_sql import (
    fiscal_year,
    full_value,
    latest_release,
    revision_status,
    source_id,
)

# The four views, by name.
FEDERAL = "federal"
PROVINCE_WIDE = "province_wide"
PROVINCIAL_GOVERNMENT = "provincial_government"
CANADA = "canada"

# Number of provinces and territories.
PROVINCES_AND_TERRITORIES = 13

# Each published figure is rounded to the nearest million dollars, so it can be
# off by up to half a million. When sub-functions are added up and compared
# with their function, each figure involved may be off by this much.
ROUNDING_DOLLARS = 500_000

# Where the municipal bucket comes from, in table 10-10-0020-01: the flows
# (not the balance sheet) of "Grants from general government units".
MUNICIPAL_GRANTS_CODE = "133, 134"
MUNICIPAL_FLOWS = "Transactions and other economic flows"


@dataclass(frozen=True)
class View:
    """Where one view's figures come from.

    name                    One of the four view names above.
    dataset                 The staged dataset holding its figures.
    component               Statistics Canada's "public sector component" for it.
    with_sub_functions      Whether to include sub-functions as well as functions.
    expected_jurisdictions  How many jurisdictions it should cover each year.
    """

    name: str
    dataset: str
    component: str
    with_sub_functions: bool
    expected_jurisdictions: int


VIEWS: tuple[View, ...] = (
    View(
        name=FEDERAL,
        dataset="cofog_by_component",
        component="Federal government",
        with_sub_functions=True,
        expected_jurisdictions=1,
    ),
    View(
        name=PROVINCE_WIDE,
        dataset="cofog_consolidated",
        component="Consolidated provincial-territorial and local governments",
        with_sub_functions=True,
        expected_jurisdictions=PROVINCES_AND_TERRITORIES + 1,  # plus "ca": all combined
    ),
    View(
        name=PROVINCIAL_GOVERNMENT,
        dataset="cofog_by_component",
        component="Provincial and territorial governments",
        with_sub_functions=False,
        expected_jurisdictions=PROVINCES_AND_TERRITORIES,
    ),
    View(
        name=CANADA,
        dataset="cofog_consolidated",
        component="Consolidated Canadian general government",
        with_sub_functions=True,
        expected_jurisdictions=1,
    ),
)


class Spending(Transformer):
    """Spending by function in each of the four views.

    Columns:
        view             federal, province_wide, provincial_government or canada
        jurisdiction     "ca", "on", ... (see the jurisdictions dataset)
        function_id      "701", "7011", ... (see the functions dataset)
        fiscal_year      start year: 2024 means 2024-25
        amount           dollars, written out in full
        revision_status  "preliminary", "revised", or empty if not flagged
        release          the Statistics Canada release the figure came from
        source_id        the source table, e.g. "statcan-10100005"
        vector           Statistics Canada's ID for the series
    """

    name = "spending"
    description = "Spending by COFOG function in the four views, in dollars"
    stage = MODEL
    inputs = ("cofog_consolidated", "cofog_by_component", "jurisdictions", "functions")

    def transform(self, db: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyRelation:
        """One query per view, stacked together."""
        return db.sql("\nUNION ALL\n".join(_view_sql(view) for view in VIEWS))

    def checks(self, db: duckdb.DuckDBPyConnection) -> list[CheckResult]:
        """Unique, complete, linked to the reference lists, and sub-functions add up."""
        return [
            no_duplicate_keys(
                db, self.name, ["view", "jurisdiction", "function_id", "fiscal_year"]
            ),
            no_missing_values(db, self.name, ["amount"]),
            expect_no_rows(
                db,
                f"{self.name}: every function_id is in functions",
                f"""SELECT DISTINCT function_id FROM {self.name}
                    WHERE function_id NOT IN (SELECT function_id FROM functions)""",
            ),
            expect_no_rows(
                db,
                f"{self.name}: every view covers all its jurisdictions every year",
                f"""SELECT s.view, s.fiscal_year, count(DISTINCT s.jurisdiction) AS found,
                           expected.jurisdictions AS expected
                    FROM {self.name} AS s
                    JOIN ({_expected_jurisdictions_sql()}) AS expected USING (view)
                    GROUP BY ALL
                    HAVING count(DISTINCT s.jurisdiction) <> expected.jurisdictions""",
            ),
            expect_no_rows(
                db,
                f"{self.name}: every view covers the same years",
                f"""SELECT view, count(DISTINCT fiscal_year) AS years FROM {self.name}
                    GROUP BY view
                    HAVING count(DISTINCT fiscal_year) <>
                        (SELECT count(DISTINCT fiscal_year) FROM {self.name})""",
            ),
            expect_no_rows(
                db,
                f"{self.name}: all {FUNCTION_COUNT} functions every year",
                f"""SELECT s.view, s.jurisdiction, s.fiscal_year, count(*) AS functions
                    FROM {self.name} AS s JOIN functions AS f USING (function_id)
                    WHERE f.level = 1
                    GROUP BY ALL
                    HAVING count(*) <> {FUNCTION_COUNT}""",
            ),
            expect_no_rows(
                db,
                f"{self.name}: sub-functions add up to their function, within rounding",
                f"""WITH sub_totals AS (
                        SELECT s.view, s.jurisdiction, s.fiscal_year,
                               f.parent_id AS function_id,
                               sum(s.amount) AS sub_function_total,
                               count(*) AS sub_functions
                        FROM {self.name} AS s JOIN functions AS f USING (function_id)
                        WHERE f.level = 2
                        GROUP BY ALL
                    )
                    SELECT t.view, t.jurisdiction, t.fiscal_year, t.function_id,
                           s.amount AS function_total, t.sub_function_total
                    FROM sub_totals AS t
                    JOIN {self.name} AS s
                        USING (view, jurisdiction, fiscal_year, function_id)
                    -- The function and each sub-function may each be off by the rounding.
                    WHERE abs(s.amount - t.sub_function_total)
                          > (t.sub_functions + 1) * {ROUNDING_DOLLARS}""",
            ),
        ]


class MunicipalTransfers(Transformer):
    """Money municipalities received from other governments, by province or territory.

    This is Statistics Canada's "grants from general government units" for
    municipalities. It includes some federal money and is not split by
    function, so it is kept apart from spending: it is shown next to the
    provincial-government view, never added to it.

    Covers the same years as spending. Columns: jurisdiction, fiscal_year,
    amount, revision_status, release, source_id, vector (as in spending).
    """

    name = "municipal_transfers"
    description = "Grants municipalities received from other governments, in dollars"
    stage = MODEL
    inputs = ("gfs_municipal", "jurisdictions", "spending")

    def transform(self, db: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyRelation:
        dataset = "gfs_municipal"
        return db.sql(f"""
            SELECT
                j.code AS jurisdiction,
                {fiscal_year("g")} AS fiscal_year,
                CAST(round({full_value("g")}) AS BIGINT) AS amount,
                {revision_status("g")} AS revision_status,
                g.release,
                {sql_text(source_id(dataset))} AS source_id,
                g.vector
            FROM {dataset} AS g
            JOIN jurisdictions AS j ON j.statcan_name = g.geo_en
            WHERE g.release = {latest_release(dataset)}
              AND g.gfs_item_code = {sql_text(MUNICIPAL_GRANTS_CODE)}
              AND g.display_value_en = {sql_text(MUNICIPAL_FLOWS)}
              AND {fiscal_year("g")} IN (SELECT DISTINCT fiscal_year FROM spending)
        """)

    def checks(self, db: duckdb.DuckDBPyConnection) -> list[CheckResult]:
        """Unique, no missing amounts, and every province and territory every year."""
        return [
            no_duplicate_keys(db, self.name, ["jurisdiction", "fiscal_year"]),
            no_missing_values(db, self.name, ["amount"]),
            expect_no_rows(
                db,
                f"{self.name}: every province and territory every year",
                f"""SELECT fiscal_year, count(*) AS jurisdictions FROM {self.name}
                    GROUP BY fiscal_year
                    HAVING count(*) <> {PROVINCES_AND_TERRITORIES}""",
            ),
        ]


def _view_sql(view: View) -> str:
    """The query for one view's rows."""
    function_id = (
        f"replace(c.function_code, {sql_text(PUBLISHED_CODE_SEPARATOR)}, "
        f"{sql_text(ID_CODE_SEPARATOR)})"
    )
    functions_only = (
        "" if view.with_sub_functions
        else f"AND length(c.function_code) = {FUNCTION_CODE_LENGTH}"
    )  # fmt: skip
    return f"""
        SELECT
            {sql_text(view.name)} AS view,
            j.code AS jurisdiction,
            {function_id} AS function_id,
            {fiscal_year("c")} AS fiscal_year,
            CAST(round({full_value("c")}) AS BIGINT) AS amount,
            {revision_status("c")} AS revision_status,
            c.release,
            {sql_text(source_id(view.dataset))} AS source_id,
            c.vector
        FROM {view.dataset} AS c
        JOIN jurisdictions AS j ON j.statcan_name = c.geo_en
        WHERE c.release = {latest_release(view.dataset)}
          AND c.component_en = {sql_text(view.component)}
          {functions_only}
    """


def _expected_jurisdictions_sql() -> str:
    """How many jurisdictions each view should cover, written as a SQL table."""
    return sql_table(
        ["view", "jurisdictions"],
        [(view.name, view.expected_jurisdictions) for view in VIEWS],
    )
