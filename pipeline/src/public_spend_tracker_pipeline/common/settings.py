"""Fixed settings for the pipeline.

One place for every value the pipeline depends on: which Statistics Canada
tables and other published files (Elections Canada, Natural Resources Canada)
we use and why, where data files are stored, and how we talk to their
servers. No other module should contain a bare web address, table number or
time limit.
"""

import os
from dataclasses import dataclass
from datetime import date
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

# The Cloud Storage bucket holding the permanent copy of the data folder (same
# folders as data/). "pst sync" copies between the two. Made by Terraform
# (infra/storage.tf). Set PST_DATA_BUCKET to use another bucket.
DATA_BUCKET = os.environ.get("PST_DATA_BUCKET", "gs://ca-pol-econ-data")

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

# The encryption key-exchange method used when connecting: we offer only one.
#
# Why only one: newer Python versions (with OpenSSL 3.5 and later) also offer a
# "post-quantum" method by default, which makes the first connection message
# larger. Statistics Canada's servers sometimes never answered that larger
# message, so about one connection in three hung until it timed out.
#
# Why P-256 ("prime256v1"): it is the method every web server supports. We first
# offered X25519, but in November 2026 Statistics Canada's servers stopped
# accepting it and every connection failed ("wrong curve").
TLS_KEY_EXCHANGE = "prime256v1"


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


# --- Other published files we use ------------------------------------------
#
# Files published at a fixed address, recognised as new when their contents
# change (see extract/published.py): Elections Canada's riding boundaries and
# results, and Natural Resources Canada's outline of Canada's land.

# Our names for their publishers, used in folder names and source IDs.
ELECTIONS_SOURCE = "elections"
NRCAN_SOURCE = "nrcan"

# Language code for a file that has both English and French in it.
ENGLISH_AND_FRENCH = f"{ENGLISH},{FRENCH}"

# The licences our sources are published under, as recorded in manifests.
OPEN_GOVERNMENT_LICENCE = "Open Government Licence - Canada"
OPEN_GOVERNMENT_LICENCE_URL = "https://open.canada.ca/en/open-government-licence-canada"
ELECTIONS_CANADA_TERMS = (
    "Elections Canada terms and conditions: non-commercial reproduction allowed with "
    "attribution; commercial redistribution needs written permission"
)
ELECTIONS_CANADA_TERMS_URL = (
    "https://www.elections.ca/content.aspx?section=pri&document=index&lang=e"
)


@dataclass(frozen=True)
class PublishedFile:
    """One file we download from a publisher's website, and why we need it.

    These publishers have no API that reports release dates, so a new release
    is recognised by a change in the file's contents (see extract/published.py).

    name             Our short name for the file, used in folder names, logs
                     and as the name of its staged dataset, if it has one.
    source           Our name for the publisher: ELECTIONS_SOURCE or NRCAN_SOURCE.
    publisher        The publisher's name, as the site shows it.
    purpose          Plain-English reason we use the file.
    title_en         The file's official title, in English and French, as
    title_fr         the listing page gives it.
    url              Where the file is downloaded from.
    listing_url      The page that lists the file and states its licence.
    listing_url_fr   The same page in French.
    licence          The licence it is published under (see the constants above).
    licence_url      Where that licence is written down.
    language         ENGLISH, FRENCH or ENGLISH_AND_FRENCH.
    """

    name: str
    source: str
    publisher: str
    purpose: str
    title_en: str
    title_fr: str
    url: str
    listing_url: str
    listing_url_fr: str
    licence: str
    licence_url: str
    language: str

    @property
    def source_id(self) -> str:
        """Our ID for the file as a source, e.g. "elections-ge45_results_by_candidate"."""
        return f"{self.source}-{self.name}"


# Official results of the 45th general election (28 April 2025).
#
# Licence note (November 2026): Elections Canada put the official results of
# the 42nd, 43rd and 44th general elections on open.canada.ca under the Open
# Government Licence, but the 45th's are so far only on elections.ca, under its
# own non-commercial terms. We use them on the assumption they will be posted
# under the Open Government Licence like the others; when they are, switch
# these entries to the open.canada.ca copy.
GE45_RESULTS_URL = "https://www.elections.ca/res/rep/off/ovrGE45/62/data_donnees"
GE45_RESULTS_PAGE = "https://www.elections.ca/res/rep/off/ovrGE45/home.html"
GE45_RESULTS_PAGE_FR = "https://www.elections.ca/res/rep/off/ovrGE45/accueil.html"
GE45_TITLE_EN = "45th General Election: Official Voting Results"
GE45_TITLE_FR = "45e élection générale : Résultats officiels du scrutin"

# The riding boundaries, listed on open.canada.ca (English and French).
FEDERAL_ELECTORAL_DISTRICTS_DATASET = "18bf3ea7-1940-46ec-af52-9ba3f77ed708"

ELECTIONS_FILES: tuple[PublishedFile, ...] = (
    PublishedFile(
        source=ELECTIONS_SOURCE,
        publisher="Elections Canada",
        name="federal_electoral_districts",
        purpose="Boundaries of the 343 federal ridings (2023 Representation Order), for the map",
        title_en="Federal Electoral Districts - Canada 2023",
        title_fr="Circonscriptions fédérales - Canada 2023",
        url="https://www.elections.ca/res/cir/mapsCorner/edb/FederalElectoralDistricts_SHP.zip",
        listing_url=f"https://open.canada.ca/data/en/dataset/{FEDERAL_ELECTORAL_DISTRICTS_DATASET}",
        listing_url_fr=f"https://ouvert.canada.ca/data/fr/dataset/{FEDERAL_ELECTORAL_DISTRICTS_DATASET}",
        licence=OPEN_GOVERNMENT_LICENCE,
        licence_url=OPEN_GOVERNMENT_LICENCE_URL,
        language=ENGLISH_AND_FRENCH,
    ),
    PublishedFile(
        source=ELECTIONS_SOURCE,
        publisher="Elections Canada",
        name="ge45_results_by_district",
        purpose="2025 election: electors, ballots cast and turnout in each riding",
        title_en=f"{GE45_TITLE_EN} - Table 11: Voting results by electoral district",
        title_fr=f"{GE45_TITLE_FR} - Tableau 11 : Résultats du scrutin par circonscription",
        url=f"{GE45_RESULTS_URL}/table_tableau11.csv",
        listing_url=GE45_RESULTS_PAGE,
        listing_url_fr=GE45_RESULTS_PAGE_FR,
        licence=ELECTIONS_CANADA_TERMS,
        licence_url=ELECTIONS_CANADA_TERMS_URL,
        language=ENGLISH_AND_FRENCH,
    ),
    PublishedFile(
        source=ELECTIONS_SOURCE,
        publisher="Elections Canada",
        name="ge45_results_by_candidate",
        purpose="2025 election: votes for every candidate in each riding, and who was elected",
        title_en=(
            f"{GE45_TITLE_EN} - Table 12: List of candidates by electoral district "
            "and individual results"
        ),
        title_fr=(
            f"{GE45_TITLE_FR} - Tableau 12 : Liste des candidats par circonscription "
            "et résultats individuels"
        ),
        url=f"{GE45_RESULTS_URL}/table_tableau12.csv",
        listing_url=GE45_RESULTS_PAGE,
        listing_url_fr=GE45_RESULTS_PAGE_FR,
        licence=ELECTIONS_CANADA_TERMS,
        licence_url=ELECTIONS_CANADA_TERMS_URL,
        language=ENGLISH_AND_FRENCH,
    ),
)


# Canada's land, to cut the ridings' legal boundaries (which take in Hudson Bay,
# the Arctic waters and the sea) back to the shoreline for the site's map.
# The 1:1,000,000 scale keeps city shorelines (Vancouver, Halifax) recognisable.
ATLAS_1M_DATASET = "fec926ca-25ad-5c92-a9a7-6009c21d17b3"
LAND_OUTLINE_FILE = PublishedFile(
    name="land_outline",
    source=NRCAN_SOURCE,
    publisher="Natural Resources Canada",
    purpose="Canada's land and coastline, to cut the riding map back to the shore",
    title_en="Atlas of Canada National Scale Data 1:1,000,000 - Boundary Polygons",
    title_fr="Données de l'Atlas du Canada à l'échelle nationale de 1/1 000 000 - "
    "Limites (polygones)",
    url="https://ftp.geogratis.gc.ca/pub/nrcan_rncan/vector/framework_cadre/"
    "Atlas_of_Canada_1M/boundary/AC_1M_BoundaryPolygons.shp.zip",
    listing_url=f"https://open.canada.ca/data/en/dataset/{ATLAS_1M_DATASET}",
    listing_url_fr=f"https://ouvert.canada.ca/data/fr/dataset/{ATLAS_1M_DATASET}",
    licence=OPEN_GOVERNMENT_LICENCE,
    licence_url=OPEN_GOVERNMENT_LICENCE_URL,
    language=ENGLISH_AND_FRENCH,
)

# Every published file we download.
PUBLISHED_FILES: tuple[PublishedFile, ...] = (*ELECTIONS_FILES, LAND_OUTLINE_FILE)


# Name of the staged dataset holding the riding boundaries' names and numbers.
RIDING_BOUNDARIES_DATASET = "federal_electoral_districts"

# How many ridings the 2023 Representation Order created. The build stops if
# the boundary file or a general election's results have a different number.
RIDING_COUNT = 343

# The first two digits of a riding's number are its province or territory's
# Standard Geographical Classification code (Statistics Canada's code for it):
# 35105 is in Ontario (35). This is each code's jurisdiction (see JURISDICTIONS).
JURISDICTION_BY_GEOGRAPHIC_CODE = {
    "10": "nl", "11": "pe", "12": "ns", "13": "nb", "24": "qc", "35": "on", "46": "mb",
    "47": "sk", "48": "ab", "59": "bc", "60": "yt", "61": "nt", "62": "nu",
}  # fmt: skip


@dataclass(frozen=True)
class Election:
    """One federal election whose official results we use.

    code               Our short ID, used in the data and page addresses.
    name_en, name_fr   Its name in English and French.
    voting_day         The day of the vote.
    general            True for a general election (every riding votes),
                       False for a by-election (a few ridings).
    districts_dataset  The staged datasets holding its results by riding
    candidates_dataset and by candidate (see ELECTIONS_FILES).
    """

    code: str
    name_en: str
    name_fr: str
    voting_day: date
    general: bool
    districts_dataset: str
    candidates_dataset: str


ELECTIONS: tuple[Election, ...] = (
    Election(
        code="ge45",
        name_en="45th general election",
        name_fr="45e élection générale",
        voting_day=date(2025, 4, 28),
        general=True,
        districts_dataset="ge45_results_by_district",
        candidates_dataset="ge45_results_by_candidate",
    ),
)


@dataclass(frozen=True)
class Party:
    """A party (or Independent, or No affiliation) a candidate can stand for.

    code      Our ID, used in the data and page addresses, e.g. "ndp".
    label     Exactly how Elections Canada's results write it, after the
              candidate's name: "Paul Connors Liberal/Libéral". English, then
              French. The part before "/" is the English name, the part after
              the French one.
    short_en  A short name for tight spaces such as legends, e.g. "NDP".
    short_fr  The same in French, e.g. "NPD".

    If a results file names a party not listed here, the build stops and says
    which, so a new party is added on purpose rather than guessed at.
    """

    code: str
    label: str
    short_en: str
    short_fr: str

    @property
    def name_en(self) -> str:
        return self.label.split("/")[0]

    @property
    def name_fr(self) -> str:
        return self.label.split("/")[1]


# Every label in the 2025 general election's results, largest parties first.
PARTIES: tuple[Party, ...] = (
    Party("liberal", "Liberal/Libéral", "Liberal", "Libéral"),
    Party("conservative", "Conservative/Conservateur", "Conservative", "Conservateur"),
    Party("bloc", "Bloc Québécois/Bloc Québécois", "Bloc", "Bloc"),
    Party("ndp", "NDP-New Democratic Party/NPD-Nouveau Parti démocratique", "NDP", "NPD"),
    Party("green", "Green Party/Parti Vert", "Green", "Vert"),
    Party("ppc", "People's Party - PPC/Parti populaire - PPC", "PPC", "PPC"),
    Party("christian_heritage", "Christian Heritage Party/Parti de l'Héritage Chrétien",
          "Christian Heritage", "Héritage chrétien"),
    Party("communist", "Communist/Communiste", "Communist", "Communiste"),
    Party("marxist_leninist", "Marxist-Leninist/Marxiste-Léniniste",
          "Marxist-Leninist", "Marxiste-léniniste"),
    Party("libertarian", "Libertarian/Libertarien", "Libertarian", "Libertarien"),
    Party("canadian_future", "Canadian Future Party/Parti Avenir Canadien",
          "Canadian Future", "Avenir canadien"),
    Party("centrist", "Centrist/Centriste", "Centrist", "Centriste"),
    Party("united", "United Party of Canada (UP)/Parti Uni du Canada (UP)", "United", "Uni"),
    Party("rhinoceros", "Parti Rhinocéros Party/Parti Rhinocéros Party",
          "Rhinoceros", "Rhinocéros"),
    Party("animal_protection", "Animal Protection Party/Parti Protection Animaux",
          "Animal Protection", "Protection animaux"),
    Party("marijuana", "Marijuana Party/Parti Marijuana", "Marijuana", "Marijuana"),
    Party("independent", "Independent/Indépendant(e)", "Independent", "Indépendant(e)"),
    Party("no_affiliation", "No Affiliation/Aucune appartenance",
          "No affiliation", "Aucune appartenance"),
)  # fmt: skip


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
