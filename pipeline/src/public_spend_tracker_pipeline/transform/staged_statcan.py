"""Turn one downloaded Statistics Canada table into a clean staged dataset.

Every Statistics Canada table we download has the same shape: standard columns
(date, place, unit, series ID, value, flags) around a few columns of its own
(for spending: the public sector component and the COFOG function). So one
class, StagedStatCanTable, handles all of them, using the table's own columns
listed in settings.STATCAN_TABLES.

For one downloaded release, it:

    1. Unzips the table's CSV file for each language into a temporary folder.
    2. Checks the columns are exactly what we expect. If Statistics Canada has
       added, removed or renamed one, it stops with SourceChangedError rather
       than guess, because a shifted column would put wrong numbers in the
       wrong places.
    3. Reads the English and French files under our own short column names.
    4. Pairs each English row with its French labels, using the series ID and
       the date.
    5. Tidies the result: values become numbers, codes in labels such as
       "General public services [701]" move to their own column, and dates
       become real dates.

A staged dataset stays faithful to the source: every row is kept, values stay
in the published units (for example "millions"), and the preliminary/revised
and quality flags stay as Statistics Canada's own codes. Converting units,
mapping to fiscal years and picking out the rows we need all happen later, in
the model step, so a staged dataset can always be checked against the table on
Statistics Canada's website.

The columns of a staged dataset, using cofog_consolidated as the example:

    ref_date, period_start             "2024" as published, and 2024-01-01
    geo_en, geo_fr, dguid              the place, and Statistics Canada's ID for it
    component_en, _fr, _code           one set per table column of its own
    function_en, _fr, _code            "General public services", ..., "701"
    value, unit, scalar_factor         97511, "Dollars", "millions"
    symbol, status, terminated         "p" preliminary, "r" revised; quality flags
    decimals                           decimal places Statistics Canada shows
    vector, coordinate                 Statistics Canada's series ID and its position

English-only tables have no _fr columns.
"""

from __future__ import annotations

import csv
import json
import logging
import tempfile
import zipfile
from datetime import date
from pathlib import Path

import duckdb

from public_spend_tracker_pipeline.paths import MANIFEST_FILE_NAME, STAGED
from public_spend_tracker_pipeline.settings import ENGLISH, FRENCH, StatCanTable
from public_spend_tracker_pipeline.transform.base import (
    CheckResult,
    Transformer,
    has_rows,
    no_duplicate_keys,
    no_missing_values,
    sql_text,
)

log = logging.getLogger(__name__)

# The standard columns every Statistics Canada table has, as
# (name as published in English, our name). The table's own columns come
# between the leading and trailing ones.
LEADING_COLUMNS = (
    ("REF_DATE", "ref_date"),
    ("GEO", "geo"),
    ("DGUID", "dguid"),
)
TRAILING_COLUMNS = (
    ("UOM", "unit"),
    ("UOM_ID", "unit_id"),
    ("SCALAR_FACTOR", "scalar_factor"),
    ("SCALAR_ID", "scalar_id"),
    ("VECTOR", "vector"),
    ("COORDINATE", "coordinate"),
    ("VALUE", "value"),
    ("STATUS", "status"),
    ("SYMBOL", "symbol"),
    ("TERMINATED", "terminated"),
    ("DECIMALS", "decimals"),
)

# The character separating values in each language's CSV file.
CSV_DELIMITERS = {ENGLISH: ",", FRENCH: ";"}

# Statistics Canada writes some codes at the end of a label, in square
# brackets: "General public services [701]". These patterns find the code,
# and the label without it.
LABEL_CODE_PATTERN = r"\[([^\]]+)\]$"
LABEL_WITHOUT_CODE_PATTERN = r"\s*\[[^\]]+\]$"

# Dates are published as a year ("2024"), a month ("2024-04") or a day
# ("2024-07-01"). This turns each into the first day of its period.
PERIOD_START_SQL = """CAST(CASE length(e.ref_date)
        WHEN 4 THEN e.ref_date || '-01-01'
        WHEN 7 THEN e.ref_date || '-01'
        ELSE e.ref_date
    END AS DATE)"""


class SourceChangedError(Exception):
    """Statistics Canada changed the layout of a table, so we stop rather than guess."""


class StagedStatCanTable(Transformer):
    """Produces the staged dataset for one release of one Statistics Canada table.

    table           The table, as listed in settings.STATCAN_TABLES.
    release_folder  The folder holding the downloaded release. The runner finds
                    it and passes it in, so this class never builds a path.
    """

    stage = STAGED

    def __init__(self, table: StatCanTable, release_folder: Path) -> None:
        self.table = table
        self.release_folder = release_folder
        self.name = table.name
        self.description = table.purpose

        manifest_text = (release_folder / MANIFEST_FILE_NAME).read_text(encoding="utf-8")
        manifest = json.loads(manifest_text)
        self.release = date.fromisoformat(manifest["release_time"][:10])
        self.zip_files = {
            file["language"]: release_folder / file["name"] for file in manifest["files"]
        }

    @property
    def is_bilingual(self) -> bool:
        """Whether we downloaded the French version too."""
        return FRENCH in self.table.languages

    @property
    def label(self) -> str:
        """How this table and release are named in logs and errors."""
        return f"{self.table.product_id} {self.table.name} release {self.release}"

    # --- Building the dataset -----------------------------------------------

    def transform(self, db: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyRelation:
        """Unzip, check and read each language, then pair and tidy the rows."""
        with tempfile.TemporaryDirectory() as temp_folder:
            for language in self.table.languages:
                csv_file = self._unzip_csv(language, Path(temp_folder))
                self._check_columns(csv_file, language)
                self._read_csv(db, csv_file, language)
        # The CSV files are deleted now, but their contents are in DuckDB.

        row_count = db.sql(f"SELECT count(*) FROM {self._loaded_table(ENGLISH)}").fetchall()[0][0]
        log.info(f"{self.label}: read {row_count:,} rows")
        return db.sql(self._tidy_sql())

    def _unzip_csv(self, language: str, into: Path) -> Path:
        """Take the table's CSV file out of the downloaded zip for one language."""
        csv_name = f"{self.table.product_id}.csv"
        with zipfile.ZipFile(self.zip_files[language]) as archive:
            if csv_name not in archive.namelist():
                raise SourceChangedError(
                    f"{self.label}: the {language} zip has no {csv_name}. "
                    f"It holds: {', '.join(archive.namelist())}"
                )
            return Path(archive.extract(csv_name, into / language))

    def _check_columns(self, csv_file: Path, language: str) -> None:
        """Stop if the file's columns are not what we expect.

        The English column names must match exactly. French names are
        translated, so for French only the number of columns is checked; its
        rows are then matched to English ones by series ID and date.
        """
        # "utf-8-sig" skips the invisible marker Statistics Canada puts at the
        # start of the file.
        with open(csv_file, encoding="utf-8-sig", newline="") as file:
            header = next(csv.reader(file, delimiter=CSV_DELIMITERS[language]))

        expected = self._published_column_names()
        if language == ENGLISH and header != expected:
            raise SourceChangedError(
                f"{self.label}: the columns changed.\n  Expected: {expected}\n  Found:    {header}"
            )
        if len(header) != len(expected):
            raise SourceChangedError(
                f"{self.label}: the {language} file has {len(header)} columns, "
                f"expected {len(expected)}.\n  Found: {header}"
            )

    def _read_csv(self, db: duckdb.DuckDBPyConnection, csv_file: Path, language: str) -> None:
        """Load one CSV file into a temporary DuckDB table, under our column names.

        Everything is read as text, so nothing is guessed wrong; values are
        converted on purpose in _tidy_sql.
        """
        db.sql(f"""
            CREATE OR REPLACE TEMP TABLE {self._loaded_table(language)} AS
            SELECT * FROM read_csv(
                {sql_text(str(csv_file))},
                header = true,
                names = {self._our_column_names()},
                all_varchar = true,
                delim = {sql_text(CSV_DELIMITERS[language])}
            )
        """)

    def _tidy_sql(self) -> str:
        """The query that pairs English rows with French labels and tidies the values."""
        bilingual = self.is_bilingual
        columns = [
            "e.ref_date",
            f"{PERIOD_START_SQL} AS period_start",
            "e.geo AS geo_en",
        ]
        if bilingual:
            columns.append("f.geo AS geo_fr")
        columns.append("e.dguid")

        for _, ours in self.table.dimensions:
            columns.append(f"{_label_without_code('e.' + ours)} AS {ours}_en")
            if bilingual:
                columns.append(f"{_label_without_code('f.' + ours)} AS {ours}_fr")
            columns.append(f"{_label_code('e.' + ours)} AS {ours}_code")

        columns += [
            "CAST(e.value AS DOUBLE) AS value",
            "e.unit",
            "e.scalar_factor",
            "e.symbol",
            "e.status",
            "e.terminated",
            "CAST(e.decimals AS INTEGER) AS decimals",
            "e.vector",
            "e.coordinate",
        ]

        source = f"{self._loaded_table(ENGLISH)} AS e"
        if bilingual:
            source += (
                f"\nLEFT JOIN {self._loaded_table(FRENCH)} AS f"
                "\n    ON f.vector = e.vector AND f.ref_date = e.ref_date"
            )
        return "SELECT\n    " + ",\n    ".join(columns) + f"\nFROM {source}"

    # --- Checks -------------------------------------------------------------

    def checks(self, db: duckdb.DuckDBPyConnection) -> list[CheckResult]:
        """The dataset has rows, each series has one value per date, French labels are present."""
        results = [
            has_rows(db, self.name),
            no_duplicate_keys(db, self.name, ["vector", "ref_date"]),
        ]
        if self.is_bilingual:
            french_columns = ["geo_fr"] + [f"{ours}_fr" for _, ours in self.table.dimensions]
            results.append(no_missing_values(db, self.name, french_columns))
        return results

    # --- Column names -------------------------------------------------------

    def _all_columns(self) -> tuple[tuple[str, str], ...]:
        """Every column in file order, as (name as published in English, our name)."""
        return LEADING_COLUMNS + self.table.dimensions + TRAILING_COLUMNS

    def _published_column_names(self) -> list[str]:
        return [published for published, _ in self._all_columns()]

    def _our_column_names(self) -> list[str]:
        return [ours for _, ours in self._all_columns()]

    def _loaded_table(self, language: str) -> str:
        """Name of the temporary table holding one language's file as read."""
        return f"loaded_{self.name}_{language}"


# --- Small SQL helpers --------------------------------------------------------


def _label_without_code(column: str) -> str:
    """SQL for a label without its bracketed code: "General public services"."""
    return f"regexp_replace({column}, '{LABEL_WITHOUT_CODE_PATTERN}', '')"


def _label_code(column: str) -> str:
    """SQL for just the bracketed code in a label: "701", or empty (NULL) if none."""
    return f"NULLIF(regexp_extract({column}, '{LABEL_CODE_PATTERN}', 1), '')"
