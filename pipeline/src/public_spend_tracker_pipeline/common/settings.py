"""Fixed settings for the pipeline.

One place for every value the pipeline depends on: which Statistics Canada
tables we use and why, where data files are stored, and how we talk to
Statistics Canada's servers. No other module should contain a bare web
address, table number or time limit.
"""

import os
from dataclasses import dataclass
from pathlib import Path

# --- Where data lives -------------------------------------------------------

# Folder holding all downloaded and generated data. It is relative to the folder
# you run commands from (normally the repository root), so by default data goes
# in ./data. Set the PST_DATA_ROOT environment variable to use another folder.
DATA_ROOT = Path(os.environ.get("PST_DATA_ROOT", "data"))

# The repository's root folder, found from this file's place in it
# (pipeline/src/public_spend_tracker_pipeline/common/settings.py).
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]

# The SQL file defining the measure views in every build's database: the
# contract between the pipeline and the API and site.
SERVING_SQL_FILE = REPOSITORY_ROOT / "schema" / "serving.sql"

# Where "pst export" writes the JSON files the site is built from. Generated,
# so not kept in git.
WEB_DATA_FOLDER = REPOSITORY_ROOT / "web" / "data"


# --- Talking to Statistics Canada -------------------------------------------

# Statistics Canada's data API (the "Web Data Service"). Free, no key needed.
STATCAN_API_URL = "https://www150.statcan.gc.ca/t1/wds/rest"

# How long to wait for a server before giving up on a request.
HTTP_TIMEOUT_SECONDS = 60

# How many times to try a request before reporting a failure.
HTTP_MAX_ATTEMPTS = 3

# How long to wait before the second attempt. The wait doubles before each
# later attempt: with these settings, 5 seconds and then 10.
HTTP_RETRY_WAIT_SECONDS = 5

# How we identify ourselves to servers. Deliberately generic: no personal details.
USER_AGENT = "public_spend_tracker/0.1"

# The encryption key-exchange method used when connecting. Newer Python versions
# (with OpenSSL 3.5) offer an extra "post-quantum" method by default, which makes
# the first connection message larger. Statistics Canada's servers sometimes
# never answer that larger message, so about one connection in three hung until
# it timed out. Offering only X25519, the widely used standard method, made
# every test connection succeed.
TLS_KEY_EXCHANGE = "X25519"


# --- The Statistics Canada tables we use ------------------------------------

# Language codes Statistics Canada uses in its download links.
ENGLISH = "en"
FRENCH = "fr"


@dataclass(frozen=True)
class StatCanTable:
    """One Statistics Canada table we download, and why we need it.

    product_id  Statistics Canada's 8-digit table number. The table shown on
                their website as 10-10-0005-01 has product_id "10100005".
    name        Our short name for the table, used in logs and later in
                dataset names.
    purpose     Plain-English reason we use the table.
    languages   Which language versions to download. Spending tables need both,
                because they give us the official French names of functions
                and governments. Context tables (inflation, population, GDP)
                are numbers we label ourselves, so English is enough.
    dimensions  The table's own columns, in the order they appear: each one's
                name exactly as Statistics Canada publishes it in English, and
                the short name we use for it. Every table also has the standard
                columns all Statistics Canada tables share (date, place,
                value...), so only the columns in between are listed here.
                If Statistics Canada changes these, the build stops.
    """

    product_id: str
    name: str
    purpose: str
    languages: tuple[str, ...]
    dimensions: tuple[tuple[str, str], ...] = ()


STATCAN_TABLES: tuple[StatCanTable, ...] = (
    StatCanTable(
        product_id="10100005",
        name="cofog_consolidated",
        purpose="Canada combined and province-wide spending by function",
        languages=(ENGLISH, FRENCH),
        dimensions=(
            ("Public sector components", "component"),
            ("Canadian Classification of Functions of Government (CCOFOG)", "function"),
        ),
    ),
    StatCanTable(
        product_id="10100024",
        name="cofog_by_component",
        purpose="Federal and provincial-government-only spending by function",
        languages=(ENGLISH, FRENCH),
        dimensions=(
            ("Public sector components", "component"),
            ("Canadian Classification of Functions of Government (CCOFOG)", "function"),
        ),
    ),
    StatCanTable(
        product_id="10100020",
        name="gfs_municipal",
        purpose="Transfers received by municipalities (the municipal bucket)",
        languages=(ENGLISH, FRENCH),
        dimensions=(
            ("Public sector components", "component"),
            ("Display value", "display_value"),
            ("Statement of operations and balance sheet", "gfs_item"),
        ),
    ),
    StatCanTable(
        product_id="18100004",
        name="cpi_monthly",
        purpose="Consumer price index, to show spending in real dollars",
        languages=(ENGLISH,),
        dimensions=(("Products and product groups", "product"),),
    ),
    StatCanTable(
        product_id="17100009",
        name="population_quarterly",
        purpose="Population, to show spending per person",
        languages=(ENGLISH,),
    ),
    StatCanTable(
        product_id="36100104",
        name="gdp_national_quarterly",
        purpose="National GDP, to show spending as a share of the economy",
        languages=(ENGLISH,),
        dimensions=(
            ("Prices", "prices"),
            ("Seasonal adjustment", "seasonal_adjustment"),
            ("Estimates", "estimate"),
        ),
    ),
    StatCanTable(
        product_id="36100222",
        name="gdp_provincial_annual",
        purpose="Provincial and territorial GDP, to show spending as a share of the economy",
        languages=(ENGLISH,),
        dimensions=(
            ("Prices", "prices"),
            ("Estimates", "estimate"),
        ),
    ),
)


# --- The governments we cover -----------------------------------------------

# Kinds of jurisdiction.
COUNTRY = "country"
PROVINCE = "province"
TERRITORY = "territory"


@dataclass(frozen=True)
class Jurisdiction:
    """One place whose governments we cover.

    code          Our two-letter code, the same as the postal abbreviation and
                  the page address (/en/governments/on). "ca" is Canada as a
                  whole: the federal government, all governments combined, or
                  all provinces and territories combined, depending on the view.
    kind          COUNTRY, PROVINCE or TERRITORY.
    statcan_name  The place's English name in Statistics Canada's files. Places
                  are matched by name because Statistics Canada's place IDs
                  differ between tables (some use 2016 boundaries, some 2021).
    cpi_place     The place whose consumer price index we use. Provinces have
                  their own; the territories use their capital city.
    """

    code: str
    kind: str
    statcan_name: str
    cpi_place: str


# In Statistics Canada's usual order: east to west, then the territories.
JURISDICTIONS: tuple[Jurisdiction, ...] = (
    Jurisdiction("ca", COUNTRY, "Canada", "Canada"),
    Jurisdiction("nl", PROVINCE, "Newfoundland and Labrador", "Newfoundland and Labrador"),
    Jurisdiction("pe", PROVINCE, "Prince Edward Island", "Prince Edward Island"),
    Jurisdiction("ns", PROVINCE, "Nova Scotia", "Nova Scotia"),
    Jurisdiction("nb", PROVINCE, "New Brunswick", "New Brunswick"),
    Jurisdiction("qc", PROVINCE, "Quebec", "Quebec"),
    Jurisdiction("on", PROVINCE, "Ontario", "Ontario"),
    Jurisdiction("mb", PROVINCE, "Manitoba", "Manitoba"),
    Jurisdiction("sk", PROVINCE, "Saskatchewan", "Saskatchewan"),
    Jurisdiction("ab", PROVINCE, "Alberta", "Alberta"),
    Jurisdiction("bc", PROVINCE, "British Columbia", "British Columbia"),
    Jurisdiction("yt", TERRITORY, "Yukon", "Whitehorse, Yukon"),
    Jurisdiction("nt", TERRITORY, "Northwest Territories", "Yellowknife, Northwest Territories"),
    Jurisdiction("nu", TERRITORY, "Nunavut", "Iqaluit, Nunavut"),
)
