"""What every transformer looks like, and the checks they share.

A transformer produces one dataset. It declares:

    name         the dataset it produces, e.g. "governments"
    description  one plain-English line, shown in logs and the build record
    stage        paths.STAGED or paths.MODEL: tells the runner where to save it
    inputs       the datasets it reads, e.g. ("cofog_consolidated",)
    layout       model datasets only: what each column is (see Layout), so
                 two builds can be compared table by table (release/compare.py)

and has two methods:

    transform(db)  builds the dataset and returns it (required)
    checks(db)     proves the dataset is right (optional)

A transformer never deals with file paths. The runner (build/run.py) does that:

    1. Makes each input available in DuckDB as a table with the same name,
       so transform() can simply say "FROM cofog_consolidated". A staged
       input holds every release, with a "release" column.
    2. Calls transform() and saves the result as a table named after the
       dataset.
    3. Calls checks(), which query that table.
    4. Writes the Parquet file only if every check passed.

A check is a query that finds bad rows. It passes when it finds none, and when
it fails it says how many there were and shows the first few, so the problem
is visible straight away.

Example:

    class Governments(Transformer):
        name = "governments"
        description = "Every government we cover, with English and French names"
        stage = MODEL
        inputs = ("cofog_consolidated",)
        layout = Layout(keys=("code",), tracked=("name_en", "name_fr"))

        def transform(self, db):
            return db.sql('''
                SELECT DISTINCT geo_code AS code, geo_en AS name_en, geo_fr AS name_fr
                FROM cofog_consolidated
            ''')

        def checks(self, db):
            return [
                no_duplicate_keys(db, self.name, self.layout.keys),
                no_missing_values(db, self.name, ["name_en", "name_fr"]),
            ]
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date

import duckdb

# How many bad rows a failed check shows as examples.
MAX_EXAMPLE_ROWS = 3

# How a number column is compared between two builds (see Layout.values).
WHOLE = "whole"  # whole numbers, e.g. dollars: any difference is a real change
DECIMAL = "decimal"  # numbers with decimals, e.g. a price index: tiny rounding differences are not


@dataclass(frozen=True)
class CheckResult:
    """The outcome of one check.

    name    What was checked, e.g. "governments: no duplicate code".
    passed  True if the check found nothing wrong.
    detail  "no bad rows", or how many bad rows were found and the first few.
    """

    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class Layout:
    """What each column of a model dataset is, so two builds can be compared.

    Every column belongs to exactly one of the first four groups (a check in
    every build makes sure of it), so a new column cannot slip past a review.

    keys     the columns that identify a row, e.g. ("jurisdiction", "fiscal_year")
    values   the numbers, each compared as WHOLE (any difference is a real
             change) or DECIMAL (differences too small to be real are ignored),
             e.g. {"amount": WHOLE}
    tracked  other columns whose changes are worth reviewing, e.g.
             ("revision_status",)
    ignored  columns not compared, because they change with every download
             without the figures changing, e.g. ("release", "fetched_at").
             The sources dataset records each release, so nothing is lost.
    labels   key columns to show with a readable name: {"jurisdiction":
             "jurisdictions"} shows the name_en of the matching row of the
             jurisdictions dataset next to each jurisdiction code.
    """

    keys: tuple[str, ...]
    values: Mapping[str, str] = field(default_factory=dict)
    tracked: tuple[str, ...] = ()
    ignored: tuple[str, ...] = ()
    labels: Mapping[str, str] = field(default_factory=dict)

    @property
    def columns(self) -> tuple[str, ...]:
        """Every column named, in the order: keys, values, tracked, ignored."""
        return (*self.keys, *self.values, *self.tracked, *self.ignored)


class Transformer(ABC):
    """One step that produces one dataset. See the top of this module for how it is run.

    Subclasses set name, description and stage, and inputs if they read any
    datasets. They can be set on the class, or in __init__ when one class
    produces several datasets (for example, one per Statistics Canada table).
    """

    name: str
    description: str
    stage: str
    inputs: tuple[str, ...] = ()
    # Staged transformers set this to the source release they read; the runner
    # saves their output under it. Model transformers leave it empty.
    release: date | None = None
    # Model transformers describe their columns; staged ones leave it empty.
    layout: Layout | None = None

    @abstractmethod
    def transform(self, db: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyRelation:
        """Build the dataset from the inputs and return it.

        Write it in SQL with db.sql(...), or build it up in Python. Either way,
        return the DuckDB result; the runner saves it.
        """

    def checks(self, db: duckdb.DuckDBPyConnection) -> list[CheckResult]:
        """Check the saved dataset (a table named self.name). None by default."""
        return []


# --- Checks shared by every transformer -------------------------------------


def expect_no_rows(db: duckdb.DuckDBPyConnection, name: str, sql: str) -> CheckResult:
    """Run a query that finds bad rows. The check passes if it finds none.

    This is the general form of a check: every other check below is built on it.
    For example, to check that no spending figure is negative:

        expect_no_rows(db, "spending: no negative amounts",
                       "SELECT * FROM spending WHERE amount < 0")
    """
    bad_rows = db.sql(sql)
    bad_count = db.sql(f"SELECT count(*) FROM ({sql})").fetchall()[0][0]
    if bad_count == 0:
        return CheckResult(name, passed=True, detail="no bad rows")
    examples = ", ".join(str(row) for row in bad_rows.limit(MAX_EXAMPLE_ROWS).fetchall())
    return CheckResult(
        name, passed=False, detail=f"{_count(bad_count, 'bad row')}, first: {examples}"
    )


def no_duplicate_keys(
    db: duckdb.DuckDBPyConnection, dataset: str, columns: Sequence[str]
) -> CheckResult:
    """Check that no combination of the key columns appears more than once.

    Each bad row shows the repeated key and how many times it appears.
    """
    key = ", ".join(_quoted(column) for column in columns)
    return expect_no_rows(
        db,
        f"{dataset}: no duplicate {', '.join(columns)}",
        f"SELECT {key}, count(*) AS copies FROM {_quoted(dataset)} "
        f"GROUP BY {key} HAVING count(*) > 1",
    )


def no_missing_values(
    db: duckdb.DuckDBPyConnection, dataset: str, columns: Sequence[str]
) -> CheckResult:
    """Check that the columns are filled in on every row.

    Empty or blank text counts as missing, so a label of "" fails too.
    """
    missing = " OR ".join(
        f"{_quoted(column)} IS NULL OR trim(CAST({_quoted(column)} AS VARCHAR)) = ''"
        for column in columns
    )
    return expect_no_rows(
        db,
        f"{dataset}: no missing {', '.join(columns)}",
        f"SELECT * FROM {_quoted(dataset)} WHERE {missing}",
    )


def layout_matches(db: duckdb.DuckDBPyConnection, transformer: Transformer) -> CheckResult:
    """Check that a model dataset's layout names every column once, and only real columns.

    The runner adds this check to every model dataset.
    """
    name = f"{transformer.name}: layout names every column once"
    layout = transformer.layout
    if layout is None:
        return CheckResult(name, passed=False, detail="the transformer has no layout")

    actual = [row[0] for row in db.sql(f"DESCRIBE {_quoted(transformer.name)}").fetchall()]
    named = list(layout.columns)
    problems = []
    if missing := [column for column in actual if column not in named]:
        problems.append(f"not in the layout: {', '.join(missing)}")
    if unknown := [column for column in named if column not in actual]:
        problems.append(f"in the layout but not the dataset: {', '.join(unknown)}")
    if repeated := sorted({column for column in named if named.count(column) > 1}):
        problems.append(f"named more than once: {', '.join(repeated)}")
    if bad_labels := [column for column in layout.labels if column not in layout.keys]:
        problems.append(f"labels for columns that are not keys: {', '.join(bad_labels)}")
    comparisons = (WHOLE, DECIMAL)
    if bad_kinds := [column for column, how in layout.values.items() if how not in comparisons]:
        problems.append(f"values neither WHOLE nor DECIMAL: {', '.join(bad_kinds)}")

    if problems:
        return CheckResult(name, passed=False, detail="; ".join(problems))
    return CheckResult(name, passed=True, detail=_count(len(actual), "column"))


def has_rows(db: duckdb.DuckDBPyConnection, dataset: str) -> CheckResult:
    """Check that the dataset is not empty."""
    row_count = db.sql(f"SELECT count(*) FROM {_quoted(dataset)}").fetchall()[0][0]
    name = f"{dataset}: has rows"
    if row_count == 0:
        return CheckResult(name, passed=False, detail="the dataset is empty")
    return CheckResult(name, passed=True, detail=_count(row_count, "row"))


def sql_value(value: str | int | float | date | None) -> str:
    """A Python value written as SQL: 'text', 42, 1.5, DATE '2025-11-27' or NULL."""
    if value is None:
        return "NULL"
    if isinstance(value, str):
        return sql_text(value)
    if isinstance(value, date):
        return f"DATE {sql_text(value.isoformat())}"
    if isinstance(value, float):
        return f"CAST({value!r} AS DOUBLE)"
    return str(value)


def sql_table(columns: Sequence[str], rows: Iterable[Sequence]) -> str:
    """Rows from Python written as a SQL table, to use in FROM or JOIN.

    For example, sql_table(["code", "kind"], [("on", "province")]) gives
    "SELECT * FROM (VALUES ('on', 'province')) AS t(code, kind)".
    """
    values = ", ".join("(" + ", ".join(sql_value(value) for value in row) + ")" for row in rows)
    return f"SELECT * FROM (VALUES {values}) AS t({', '.join(columns)})"


def _count(number: int, thing: str) -> str:
    """A number with its noun, plural when needed: "1 bad row", "3 bad rows"."""
    return f"{number} {thing}" if number == 1 else f"{number} {thing}s"


def sql_text(text: str) -> str:
    """Text written as a SQL string, with any single quotes doubled: 'Ontario'."""
    return "'" + text.replace("'", "''") + "'"


def _quoted(identifier: str) -> str:
    """A table or column name, quoted for SQL so any name works, e.g. "name_en"."""
    return '"' + identifier.replace('"', '""') + '"'
