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

Transfers to other governments: the federal amounts include money the federal
government hands to provinces, territories and municipalities to spend (the
Canada Health Transfer, equalization and so on). transfers_to_governments
records how much, so the site can show spending with or without it. No table
publishes it by function, so it is worked out by subtraction, for each
function and year:

    federal amount - (Canada combined - all provinces and territories combined)

The subtraction is exact for the 10 functions, but below that it gives
negative figures for services Ottawa barely provides (fire protection, street
lighting), so it is left out for sub-functions. The subtraction also nets out
money flowing the other way, such as provinces paying for RCMP policing.

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

# The jurisdiction code for Canada, and for "all provinces and territories
# combined" in the province-wide view.
ALL_OF_CANADA = "ca"

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
    consolidated            Whether transfers among its parts are already removed,
                            so there are no transfers left to take out.
    """

    name: str
    dataset: str
    component: str
    with_sub_functions: bool
    expected_jurisdictions: int
    consolidated: bool


VIEWS: tuple[View, ...] = (
    View(
        name=FEDERAL,
        dataset="cofog_by_component",
        component="Federal government",
        with_sub_functions=True,
        expected_jurisdictions=1,
        consolidated=False,
    ),
    View(
        name=PROVINCE_WIDE,
        dataset="cofog_consolidated",
        component="Consolidated provincial-territorial and local governments",
        with_sub_functions=True,
        expected_jurisdictions=PROVINCES_AND_TERRITORIES + 1,  # plus "ca": all combined
        consolidated=True,
    ),
    View(
        name=PROVINCIAL_GOVERNMENT,
        dataset="cofog_by_component",
        component="Provincial and territorial governments",
        with_sub_functions=False,
        expected_jurisdictions=PROVINCES_AND_TERRITORIES,
        consolidated=False,
    ),
    View(
        name=CANADA,
        dataset="cofog_consolidated",
        component="Consolidated Canadian general government",
        with_sub_functions=True,
        expected_jurisdictions=1,
        consolidated=True,
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
        transfers_to_governments
                         the part of amount handed to other governments to spend:
                         worked out for federal functions; 0 for the consolidated
                         views (canada, province_wide); empty where not known
                         (federal sub-functions, provincial_government)
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
        """One query per view, stacked together, then transfers to other governments added."""
        all_views = "\nUNION ALL\n".join(_view_sql(view) for view in VIEWS)
        consolidated = ", ".join(sql_text(view.name) for view in VIEWS if view.consolidated)
        return db.sql(f"""
            WITH spending AS ({all_views}),
            federal_transfers AS (
                SELECT
                    federal.view,
                    federal.jurisdiction,
                    federal.function_id,
                    federal.fiscal_year,
                    federal.amount - (canada.amount - provinces.amount)
                        AS transfers_to_governments
                FROM {_federal_beside_consolidated("spending")}
            )
            SELECT
                s.view,
                s.jurisdiction,
                s.function_id,
                s.fiscal_year,
                s.amount,
                CASE
                    WHEN s.view IN ({consolidated}) THEN 0
                    ELSE t.transfers_to_governments
                END AS transfers_to_governments,
                s.revision_status,
                s.release,
                s.source_id,
                s.vector
            FROM spending AS s
            LEFT JOIN federal_transfers AS t
                USING (view, jurisdiction, function_id, fiscal_year)
        """)

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
            expect_no_rows(
                db,
                f"{self.name}: federal transfers to other governments are between 0 and the amount",
                f"""SELECT s.function_id, s.fiscal_year, s.amount, s.transfers_to_governments
                    FROM {self.name} AS s JOIN functions AS f USING (function_id)
                    WHERE s.view = {sql_text(FEDERAL)} AND f.level = 1
                      AND (s.transfers_to_governments IS NULL
                           OR s.transfers_to_governments NOT BETWEEN 0 AND s.amount)""",
            ),
            expect_no_rows(
                db,
                f"{self.name}: the rows behind federal transfers share a release and status",
                f"""SELECT federal.function_id, federal.fiscal_year,
                           federal.release, canada.release AS canada_release,
                           provinces.release AS provinces_release,
                           federal.revision_status,
                           canada.revision_status AS canada_status,
                           provinces.revision_status AS provinces_status
                    FROM {_federal_beside_consolidated(self.name)}
                      AND ((canada.release, canada.revision_status)
                               IS DISTINCT FROM (federal.release, federal.revision_status)
                           OR (provinces.release, provinces.revision_status)
                               IS DISTINCT FROM (federal.release, federal.revision_status))""",
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


def _federal_beside_consolidated(table: str) -> str:
    """Each federal function row beside the matching Canada-combined and all-provinces rows.

    These are the three rows behind each transfers_to_governments figure. Use
    after FROM; add further conditions with AND. The aliases are federal,
    canada and provinces.
    """

    def same_function_and_year(alias: str) -> str:
        return (
            f"{alias}.function_id = federal.function_id"
            f" AND {alias}.fiscal_year = federal.fiscal_year"
        )

    return f"""
        {table} AS federal
        JOIN functions AS f USING (function_id)
        JOIN {table} AS canada
            ON canada.view = {sql_text(CANADA)}
           AND canada.jurisdiction = {sql_text(ALL_OF_CANADA)}
           AND {same_function_and_year("canada")}
        JOIN {table} AS provinces
            ON provinces.view = {sql_text(PROVINCE_WIDE)}
           AND provinces.jurisdiction = {sql_text(ALL_OF_CANADA)}
           AND {same_function_and_year("provinces")}
        WHERE federal.view = {sql_text(FEDERAL)} AND f.level = 1
    """


def _expected_jurisdictions_sql() -> str:
    """How many jurisdictions each view should cover, written as a SQL table."""
    return sql_table(
        ["view", "jurisdictions"],
        [(view.name, view.expected_jurisdictions) for view in VIEWS],
    )
