"""Turn downloaded Elections Canada files into clean staged datasets.

Two kinds of file, so two classes:

    StagedRidingBoundaries  The riding boundary file (a zipped shapefile). Only
                            its table of ridings is read here: number, English
                            name, French name. The shapes themselves are turned
                            into the site's map later, by the export.
    StagedResultsTable      An official results table (a CSV file): results by
                            riding, or by candidate. Which columns to expect
                            comes from RESULTS_COLUMNS.

Like the Statistics Canada staged datasets, these stay faithful to the source:
every row is kept and text stays as published (a candidate's name still has
their party on the end, as Elections Canada writes it). Numbers become numbers,
and the province, published as "English/French", is split in two. Matching
candidates to parties and ridings to provinces happens in the model step.

If Elections Canada changes a file's columns, the build stops with
SourceChangedError rather than guess.

staged_elections_transformer() picks the right class for each downloaded file.
"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb
import shapefile

from public_spend_tracker_pipeline.common.paths import MANIFEST_FILE_NAME, STAGED
from public_spend_tracker_pipeline.common.settings import (
    ELECTIONS,
    RIDING_BOUNDARIES_DATASET,
    ElectionsFile,
)
from public_spend_tracker_pipeline.transform.base import (
    CheckResult,
    Transformer,
    has_rows,
    no_duplicate_keys,
    no_missing_values,
    sql_table,
    sql_text,
)
from public_spend_tracker_pipeline.transform.staged_statcan import SourceChangedError

# Our ID for the source behind a staged Elections Canada dataset.
SOURCE_ID_PREFIX = "elections-"

# --- The riding boundary file -----------------------------------------------

# The boundary file's columns, as (name in the file, our name), in order.
BOUNDARY_FIELDS = (
    ("ED_CF_NUM", "district_number"),
    ("ED_NAMEE", "name_en"),
    ("CF_NOMF", "name_fr"),
)

# Shapefiles come as several files; the table of ridings is the one ending
# .dbf, and the one ending .cpg names its text encoding.
TABLE_FILE_ENDING = ".dbf"
ENCODING_FILE_ENDING = ".cpg"
EXPECTED_ENCODING = "UTF-8"

# --- The results tables -----------------------------------------------------

# Kinds of column in a results table.
TEXT = "text"
WHOLE_NUMBER = "whole number"
PERCENT = "percent"  # published with one decimal, e.g. 66.9 for 66.9%

# What DuckDB stores each kind as.
SQL_TYPES = {TEXT: "VARCHAR", WHOLE_NUMBER: "BIGINT", PERCENT: "DOUBLE"}

# Published as "Newfoundland and Labrador/Terre-Neuve-et-Labrador"; split in two.
PROVINCE_COLUMN = "province"

# The two kinds of results table.
RESULTS_BY_DISTRICT = "by district"
RESULTS_BY_CANDIDATE = "by candidate"


@dataclass(frozen=True)
class Column:
    """One column of a results table.

    published  Its name in the file, exactly (English/French).
    name       Our name for it.
    kind       TEXT, WHOLE_NUMBER or PERCENT.
    required   Whether every row must have it. The winner's majority is the
               only column left blank on most rows.
    """

    published: str
    name: str
    kind: str
    required: bool = True


# The columns shared by both tables, which start every row.
_RIDING_COLUMNS = (
    Column("Province", PROVINCE_COLUMN, TEXT),
    Column("Electoral District Name/Nom de circonscription", "district_name", TEXT),
    Column("Electoral District Number/Numéro de circonscription", "district_number", TEXT),
)

RESULTS_COLUMNS: dict[str, tuple[Column, ...]] = {
    # Table 11: one row per riding.
    RESULTS_BY_DISTRICT: (
        *_RIDING_COLUMNS,
        Column("Population", "population", WHOLE_NUMBER),
        Column("Electors/Électeurs", "electors", WHOLE_NUMBER),
        Column("Voting desks/Tables de vote", "voting_desks", WHOLE_NUMBER),
        Column("Valid Ballots/Bulletins valides", "valid_ballots", WHOLE_NUMBER),
        Column(
            "Percentage of Valid Ballots /Pourcentage des bulletins valides",
            "valid_ballots_pct", PERCENT,
        ),
        Column("Rejected Ballots/Bulletins rejetés", "rejected_ballots", WHOLE_NUMBER),
        Column(
            "Percentage of Rejected Ballots /Pourcentage des bulletins rejetés",
            "rejected_ballots_pct", PERCENT,
        ),
        Column("Total Ballots Cast/Total des bulletins déposés", "total_ballots", WHOLE_NUMBER),
        Column(
            "Percentage of Voter Turnout/Pourcentage de la participation électorale",
            "turnout_pct", PERCENT,
        ),
        Column("Elected Candidate/Candidat élu", "elected_candidate", TEXT),
    ),
    # Table 12: one row per candidate.
    RESULTS_BY_CANDIDATE: (
        *_RIDING_COLUMNS,
        Column("Candidate/Candidat", "candidate", TEXT),
        Column("Candidate Residence/Résidence du candidat", "residence", TEXT),
        Column("Candidate Occupation/Profession du candidat", "occupation", TEXT),
        Column("Votes Obtained/Votes obtenus", "votes", WHOLE_NUMBER),
        Column(
            "Percentage of Votes Obtained /Pourcentage des votes obtenus",
            "vote_share_pct", PERCENT,
        ),
        # Filled in for the winner only: their lead over the runner-up.
        Column("Majority/Majorité", "majority", WHOLE_NUMBER, required=False),
        Column("Majority Percentage/Pourcentage de majorité", "majority_pct", PERCENT,
               required=False),
    ),
}  # fmt: skip

# The columns that identify a row in each kind of table.
RESULTS_KEYS = {
    RESULTS_BY_DISTRICT: ("district_number",),
    RESULTS_BY_CANDIDATE: ("district_number", "candidate"),
}


def source_id(dataset: str) -> str:
    """Our ID for the Elections Canada file behind a staged dataset.

    For example "elections-ge45_results_by_candidate".
    """
    return SOURCE_ID_PREFIX + dataset


def staged_elections_transformer(source_file: ElectionsFile, release_folder: Path) -> Transformer:
    """The staged transformer for one downloaded release of an Elections Canada file."""
    if source_file.name == RIDING_BOUNDARIES_DATASET:
        return StagedRidingBoundaries(source_file, release_folder)
    for election in ELECTIONS:
        if source_file.name == election.districts_dataset:
            return StagedResultsTable(source_file, release_folder, RESULTS_BY_DISTRICT)
        if source_file.name == election.candidates_dataset:
            return StagedResultsTable(source_file, release_folder, RESULTS_BY_CANDIDATE)
    raise ValueError(
        f"No staged transformer for the Elections Canada file {source_file.name!r}: "
        "it is neither the riding boundaries nor results of an election in settings.ELECTIONS"
    )


class _StagedElectionsFile(Transformer):
    """What both kinds share: reading the release's manifest.

    source_file     The file, as listed in settings.ELECTIONS_FILES.
    release_folder  The folder holding the downloaded release. The runner finds
                    it and passes it in, so this class never builds a path.
    """

    stage = STAGED

    def __init__(self, source_file: ElectionsFile, release_folder: Path) -> None:
        self.source_file = source_file
        self.name = source_file.name
        self.description = source_file.purpose
        manifest = json.loads((release_folder / MANIFEST_FILE_NAME).read_text(encoding="utf-8"))
        self.release = date.fromisoformat(manifest["release"])
        self.downloaded_file = release_folder / manifest["files"][0]["name"]

    @property
    def label(self) -> str:
        """How this file and release are named in errors."""
        return f"Elections Canada {self.name} release {self.release}"


class StagedRidingBoundaries(_StagedElectionsFile):
    """The table of ridings inside the boundary file: number, English name, French name."""

    def transform(self, db: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyRelation:
        """Read the ridings from the shapefile's table, checking its columns first."""
        with zipfile.ZipFile(self.downloaded_file) as archive:
            table_file = self._only_file_ending(archive, TABLE_FILE_ENDING)
            self._check_encoding(archive)
            reader = shapefile.Reader(dbf=io.BytesIO(archive.read(table_file)), encoding="utf-8")
            found = [field.name for field in reader.fields[1:]]  # the first is internal
            expected = [published for published, _ in BOUNDARY_FIELDS]
            if found != expected:
                raise SourceChangedError(
                    f"{self.label}: the columns changed.\n"
                    f"  Expected: {expected}\n  Found:    {found}"
                )
            rows = [
                (str(record[0]), record[1], record[2])
                for record in reader.iterRecords(fields=expected)
            ]
        ours = [name for _, name in BOUNDARY_FIELDS]
        return db.sql(f"{sql_table(ours, rows)} ORDER BY district_number")

    def checks(self, db: duckdb.DuckDBPyConnection) -> list[CheckResult]:
        """Not empty, one row per riding, and every riding has both names."""
        return [
            has_rows(db, self.name),
            no_duplicate_keys(db, self.name, ["district_number"]),
            no_missing_values(db, self.name, ["district_number", "name_en", "name_fr"]),
        ]

    def _only_file_ending(self, archive: zipfile.ZipFile, ending: str) -> str:
        """The one file in the zip whose name ends this way; stops if there is not exactly one."""
        matches = [name for name in archive.namelist() if name.lower().endswith(ending)]
        if len(matches) != 1:
            raise SourceChangedError(
                f"{self.label}: expected one {ending} file in the zip, found "
                f"{len(matches)}. It holds: {', '.join(archive.namelist())}"
            )
        return matches[0]

    def _check_encoding(self, archive: zipfile.ZipFile) -> None:
        """Stop if the file says its text is in another encoding than UTF-8."""
        encoding_file = self._only_file_ending(archive, ENCODING_FILE_ENDING)
        encoding = archive.read(encoding_file).decode("ascii").strip()
        if encoding.upper() != EXPECTED_ENCODING:
            raise SourceChangedError(
                f"{self.label}: its text is now in {encoding}, not {EXPECTED_ENCODING}"
            )


class StagedResultsTable(_StagedElectionsFile):
    """One official results table: results by riding, or by candidate.

    kind  RESULTS_BY_DISTRICT or RESULTS_BY_CANDIDATE.
    """

    def __init__(self, source_file: ElectionsFile, release_folder: Path, kind: str) -> None:
        super().__init__(source_file, release_folder)
        self.kind = kind
        self.columns = RESULTS_COLUMNS[kind]

    def transform(self, db: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyRelation:
        """Check the columns, read everything as text, then type and tidy it."""
        self._check_columns()
        loaded = f"loaded_{self.name}"
        names = ", ".join(sql_text(column.name) for column in self.columns)
        db.sql(f"""
            CREATE TEMP TABLE {loaded} AS
            SELECT * FROM read_csv(
                {sql_text(str(self.downloaded_file))},
                header = true, all_varchar = true, names = [{names}]
            )
        """)
        return db.sql(f"SELECT {', '.join(self._tidy(column) for column in self.columns)} "
                      f"FROM {loaded} ORDER BY {', '.join(RESULTS_KEYS[self.kind])}")  # fmt: skip

    def checks(self, db: duckdb.DuckDBPyConnection) -> list[CheckResult]:
        """Not empty, no repeated rows, and every required column filled in.

        A number that could not be read counts as missing, so a stray
        character in a vote count stops the build instead of becoming nothing.
        """
        required = [
            name
            for column in self.columns
            if column.required
            for name in self._tidied_names(column)
        ]
        return [
            has_rows(db, self.name),
            no_duplicate_keys(db, self.name, RESULTS_KEYS[self.kind]),
            no_missing_values(db, self.name, required),
        ]

    def _check_columns(self) -> None:
        """Stop if the file's columns are not exactly what we expect."""
        # "utf-8-sig" skips the invisible marker at the start of the file.
        with open(self.downloaded_file, encoding="utf-8-sig", newline="") as file:
            header = next(csv.reader(file))
        expected = [column.published for column in self.columns]
        if header != expected:
            raise SourceChangedError(
                f"{self.label}: the columns changed.\n  Expected: {expected}\n  Found:    {header}"
            )

    @staticmethod
    def _tidied_names(column: Column) -> list[str]:
        """The staged column names one published column becomes."""
        if column.name == PROVINCE_COLUMN:
            return [f"{PROVINCE_COLUMN}_en", f"{PROVINCE_COLUMN}_fr"]
        return [column.name]

    @staticmethod
    def _tidy(column: Column) -> str:
        """SQL turning one published column into its staged column(s).

        Text is trimmed. Numbers are read with TRY_CAST, so one that cannot be
        read becomes NULL and the missing-value check stops the build. The
        province "English/French" is split; a name the same in both languages
        ("Nunavut") is published once and used for both.
        """
        value = f"trim({column.name})"
        if column.name == PROVINCE_COLUMN:
            return (
                f"split_part({value}, '/', 1) AS {PROVINCE_COLUMN}_en, "
                f"CASE WHEN contains({value}, '/') THEN split_part({value}, '/', 2) "
                f"ELSE {value} END AS {PROVINCE_COLUMN}_fr"
            )
        if column.kind == TEXT:
            return f"{value} AS {column.name}"
        return f"TRY_CAST(nullif({value}, '') AS {SQL_TYPES[column.kind]}) AS {column.name}"
