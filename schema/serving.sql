-- The contract between the pipeline and everything that reads the database.
--
-- Every build applies this file to its database (serving/build=<id>/fiscal.duckdb)
-- after loading the model tables, so the measures below are calculated the same
-- way everywhere: on every page of the site and in every API answer.
--
-- It only creates views: saved queries over the model tables. It stores no data.
--
-- Tables loaded by the pipeline (see the model transformers for their columns):
--     jurisdictions, functions, spending, municipal_transfers, context, sources,
--     build_info (one row: build ID, build time, base year, years covered)
--
-- Views created here:
--     context_by_year               CPI, population and GDP side by side
--     spending_measures             spending in every measure
--     municipal_transfers_measures  the municipal bucket in every measure
--
-- The measures:
--     amount                  dollars, as spent that year ("nominal")
--     amount_real             in base-year dollars: adjusted for inflation using
--                             the jurisdiction's own consumer price index
--     amount_per_person       amount / population
--     amount_real_per_person  amount_real / population
--     percent_of_gdp          amount / GDP x 100
--
-- The base year is the newest fiscal year with spending (2024 means 2024-25),
-- so real dollars read as "in today's dollars".
--
-- Each spending row appears twice, once per context basis:
--     fiscal    population, prices and GDP for the fiscal year (April to March)
--     calendar  the same for the calendar year the fiscal year starts in
--
-- Federal and Canada-combined figures use Canada's context ("ca"). So does
-- "all provinces combined", which is "ca" in the province-wide view.


-- CPI, population and GDP side by side, one row per jurisdiction, basis and year.
--
--     gdp_method    exact, blended or partial (see the context dataset): lets the
--                   site add a footnote when share of GDP uses a partial figure
--     base_year     the newest fiscal year with spending
--     price_factor  CPI in the base year / CPI in this year: multiplying an
--                   amount by it gives the amount in base-year dollars
CREATE OR REPLACE VIEW context_by_year AS
WITH side_by_side AS (
    SELECT
        jurisdiction,
        basis,
        year,
        any_value(value) FILTER (WHERE series = 'cpi') AS cpi,
        any_value(value) FILTER (WHERE series = 'population') AS population,
        any_value(value) FILTER (WHERE series = 'gdp') AS gdp,
        any_value(method) FILTER (WHERE series = 'gdp') AS gdp_method
    FROM context
    GROUP BY jurisdiction, basis, year
),
base AS (
    SELECT max(fiscal_year) AS base_year FROM spending
)
SELECT
    this_year.jurisdiction,
    this_year.basis,
    this_year.year,
    this_year.cpi,
    this_year.population,
    this_year.gdp,
    this_year.gdp_method,
    base.base_year,
    base_year_prices.cpi / this_year.cpi AS price_factor
FROM side_by_side AS this_year
CROSS JOIN base
LEFT JOIN side_by_side AS base_year_prices
    ON base_year_prices.jurisdiction = this_year.jurisdiction
   AND base_year_prices.basis = this_year.basis
   AND base_year_prices.year = base.base_year;


-- Spending in every measure: each spending row twice, once per context basis.
CREATE OR REPLACE VIEW spending_measures AS
SELECT
    s.view,
    s.jurisdiction,
    s.function_id,
    s.fiscal_year,
    bases.basis AS context_basis,
    s.amount,
    s.amount * c.price_factor AS amount_real,
    s.amount / c.population AS amount_per_person,
    s.amount * c.price_factor / c.population AS amount_real_per_person,
    s.amount / c.gdp * 100 AS percent_of_gdp,
    (SELECT max(fiscal_year) FROM spending) AS base_year,
    c.gdp_method,
    s.revision_status,
    s.release,
    s.source_id,
    s.vector
FROM spending AS s
CROSS JOIN (VALUES ('fiscal'), ('calendar')) AS bases(basis)
LEFT JOIN context_by_year AS c
    ON c.jurisdiction = s.jurisdiction
   AND c.basis = bases.basis
   AND c.year = s.fiscal_year;


-- The municipal bucket in every measure. Shown beside the provincial-government
-- view, never added to it.
CREATE OR REPLACE VIEW municipal_transfers_measures AS
SELECT
    m.jurisdiction,
    m.fiscal_year,
    bases.basis AS context_basis,
    m.amount,
    m.amount * c.price_factor AS amount_real,
    m.amount / c.population AS amount_per_person,
    m.amount * c.price_factor / c.population AS amount_real_per_person,
    m.amount / c.gdp * 100 AS percent_of_gdp,
    (SELECT max(fiscal_year) FROM spending) AS base_year,
    c.gdp_method,
    m.revision_status,
    m.release,
    m.source_id,
    m.vector
FROM municipal_transfers AS m
CROSS JOIN (VALUES ('fiscal'), ('calendar')) AS bases(basis)
LEFT JOIN context_by_year AS c
    ON c.jurisdiction = m.jurisdiction
   AND c.basis = bases.basis
   AND c.year = m.fiscal_year;
