"""SQL pieces shared by the model transformers that read staged Statistics Canada data.

Each function returns a small piece of SQL to drop into a query, so the same
rule (which release to use, how to read a year, how to write a value in full)
is written once and reads the same everywhere.
"""

from public_spend_tracker_pipeline.common.settings import STATCAN_TABLES
from public_spend_tracker_pipeline.transform.base import sql_text

# What each of Statistics Canada's "scalar factors" means: the published value
# is in these units, so multiplying by this number writes it out in full.
SCALAR_FACTORS = {
    "units": 1,
    "thousands": 1_000,
    "millions": 1_000_000,
    "billions": 1_000_000_000,
}

# Statistics Canada's revision flags (the "symbol" column) and our names for them.
# Years without a flag have not been marked as preliminary or recently revised.
REVISION_FLAGS = {
    "p": "preliminary",
    "r": "revised",
}


def latest_release(dataset: str) -> str:
    """SQL for the newest release date in a staged dataset.

    Staged datasets hold every release we have downloaded; current figures
    come from the newest one. Use as: WHERE release = {latest_release("x")}
    """
    return f"(SELECT max(release) FROM {dataset})"


def full_value(alias: str) -> str:
    """SQL for a value written out in full, e.g. 97511 "millions" -> 97511000000.

    An unknown scalar factor gives NULL, which the missing-value checks catch.
    """
    cases = " ".join(
        f"WHEN {sql_text(name)} THEN {alias}.value * {factor}"
        for name, factor in SCALAR_FACTORS.items()
    )
    return f"CASE {alias}.scalar_factor {cases} END"


def revision_status(alias: str) -> str:
    """SQL for our name for a row's revision flag: "preliminary", "revised" or NULL."""
    cases = " ".join(
        f"WHEN {sql_text(flag)} THEN {sql_text(name)}" for flag, name in REVISION_FLAGS.items()
    )
    return f"CASE {alias}.symbol {cases} END"


def fiscal_year(alias: str) -> str:
    """SQL for the fiscal year a government-finance row belongs to, by its start year.

    Statistics Canada labels each year by "the end of fiscal year closest to
    December 31st". So "2024" is fiscal 2024-25 for governments whose year runs
    April to March, and calendar 2024 for municipalities. We store the start
    year: 2024 means 2024-25.
    """
    return f"CAST({alias}.ref_date AS INTEGER)"


def source_id(dataset: str) -> str:
    """Our ID for the Statistics Canada table behind a staged dataset, e.g. "statcan-10100005"."""
    for table in STATCAN_TABLES:
        if table.name == dataset:
            return f"statcan-{table.product_id}"
    raise KeyError(f"No Statistics Canada table is named {dataset!r} in settings.STATCAN_TABLES")
