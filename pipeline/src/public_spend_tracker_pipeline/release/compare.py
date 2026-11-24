"""Compare two builds table by table, using each model dataset's layout.

Nothing here knows about spending, prices or any other particular table: every
model dataset describes its own columns (transform/base.py, Layout), and this
module compares whatever the layouts describe. A new source is covered as
soon as its transformer has a layout, which every build checks.

For each model dataset it finds, by key:

    removed   rows in the earlier build that are missing from the new one
    added     rows only in the new build
    revised   values that changed (a WHOLE value by any amount, a DECIMAL
              value by more than rounding noise) and tracked columns that
              changed, one line per column

It also notes datasets and columns found in only one of the builds.

Every change is one line, with the dataset's own key columns, a readable name
next to each labelled key (e.g. "Ontario" next to "on"), the column, and its
value in each build:

    what, <keys>, <key names>, column, was, now, change, change_percent

release/diff.py writes these lines to one CSV file per dataset and summarizes
them in the report.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

import duckdb

from public_spend_tracker_pipeline.transform.base import DECIMAL, Layout, sql_text

# What happened to a row or value (the "what" column).
REMOVED = "removed"
REVISED = "revised"
ADDED = "added"

# The order changes are listed in: what needs attention first.
WHAT_ORDER = (REMOVED, REVISED, ADDED)

# Where a dataset was found.
IN_BOTH = "both builds"
NEW_ONLY = "new build only"
OLD_ONLY = "earlier build only"

# A DECIMAL value counts as revised only if it moved by more than this share of
# its size: one part in a billion. Real revisions are far larger (the smallest
# step in a published price index is 0.1 on about 150, one part in 1,500), while
# the way computers add up decimals can move the last of about 16 digits.
DECIMAL_TOLERANCE = 1e-9

# The column of a reference dataset shown as a key's readable name.
LABEL_COLUMN = "name_en"

# Columns every change line has after the keys and their names.
CHANGE_COLUMNS = ("column", "was", "now", "change", "change_percent")

# Decimal places kept in change_percent.
PERCENT_DECIMALS = 4

# The two builds, as attached in the database (see release/diff.py).
NEW = "new"
OLD = "old"


@dataclass(frozen=True)
class TableChanges:
    """What changed in one model dataset between two builds.

    found_in         IN_BOTH, NEW_ONLY or OLD_ONLY
    new_rows         how many rows the dataset has in the new build
    columns_added    columns only in the new build
    columns_removed  columns only in the earlier build
    problem          why the dataset could not be compared, if it could not
    header           the names of each line's fields
    lines            every change, in WHAT_ORDER, largest change first
    """

    table: str
    layout: Layout
    found_in: str
    new_rows: int = 0
    columns_added: tuple[str, ...] = ()
    columns_removed: tuple[str, ...] = ()
    problem: str | None = None
    header: tuple[str, ...] = ()
    lines: tuple[tuple, ...] = ()

    @property
    def rows_added(self) -> int:
        """Rows only in the new build (or every row, for a new dataset)."""
        if self.found_in == NEW_ONLY:
            return self.new_rows
        return self._rows(ADDED)

    @property
    def rows_removed(self) -> int:
        return self._rows(REMOVED)

    @property
    def values_revised(self) -> int:
        """Number values that changed in rows both builds have."""
        return self._revisions(self.layout.values)

    @property
    def tracked_changed(self) -> int:
        """Tracked columns (e.g. revision_status) that changed in rows both builds have."""
        return self._revisions(self.layout.tracked)

    @property
    def needs_attention(self) -> bool:
        """Something is gone or could not be compared: worth a look before approving."""
        return bool(
            self.rows_removed or self.columns_removed or self.problem or self.found_in == OLD_ONLY
        )

    @property
    def has_changes(self) -> bool:
        return bool(
            self.lines or self.columns_added or self.needs_attention or self.found_in != IN_BOTH
        )

    def field(self, line: tuple, name: str):
        """One field of a change line, by name, e.g. field(line, "fiscal_year")."""
        return line[self.header.index(name)]

    def _rows(self, what: str) -> int:
        """Distinct rows (by key) with a change of one kind."""
        keys = len(self.layout.keys)
        return len({line[1 : 1 + keys] for line in self.lines if line[0] == what})

    def _revisions(self, columns) -> int:
        column = self.header.index("column") if self.header else 0
        return sum(1 for line in self.lines if line[0] == REVISED and line[column] in columns)


def compare_tables(
    db: duckdb.DuckDBPyConnection, layouts: Sequence[tuple[str, Layout]]
) -> list[TableChanges]:
    """Compare every dataset that has a layout, in the order given.

    The builds must be attached as "new" and "old". Nothing is changed.
    """
    return [_compare_table(db, table, layout, layouts) for table, layout in layouts]


def tables_without_layout(
    db: duckdb.DuckDBPyConnection, layouts: Sequence[tuple[str, Layout]]
) -> dict[str, str]:
    """Tables in either build that no layout describes, with where each was found.

    The serving tables (e.g. build_info) are expected here; anything else is a
    dataset that was added or removed without a layout.
    """
    described = {table for table, _ in layouts}
    found = {}
    for build, where in ((NEW, NEW_ONLY), (OLD, OLD_ONLY)):
        for table in _tables(db, build):
            if table not in described:
                found[table] = IN_BOTH if table in found else where
    return found


# --- Comparing one dataset -----------------------------------------------------


def _compare_table(
    db: duckdb.DuckDBPyConnection,
    table: str,
    layout: Layout,
    layouts: Sequence[tuple[str, Layout]],
) -> TableChanges:
    new_columns = _columns(db, NEW, table)
    old_columns = _columns(db, OLD, table)
    if not new_columns and not old_columns:
        return TableChanges(table, layout, IN_BOTH, problem="not found in either build")
    if not old_columns:
        return TableChanges(table, layout, NEW_ONLY, new_rows=_row_count(db, NEW, table))
    if not new_columns:
        return TableChanges(table, layout, OLD_ONLY)

    changes = TableChanges(
        table,
        layout,
        IN_BOTH,
        new_rows=_row_count(db, NEW, table),
        columns_added=tuple(c for c in new_columns if c not in old_columns),
        columns_removed=tuple(c for c in old_columns if c not in new_columns),
    )
    missing_keys = [key for key in layout.keys if key not in new_columns or key not in old_columns]
    if missing_keys:
        return replace(changes, problem=f"key columns missing: {', '.join(missing_keys)}")

    shared = [c for c in new_columns if c in old_columns]
    query = _changes_sql(db, table, layout, shared, layouts)
    result = db.sql(query)
    return replace(changes, header=tuple(result.columns), lines=tuple(result.fetchall()))


def _changes_sql(
    db: duckdb.DuckDBPyConnection,
    table: str,
    layout: Layout,
    shared: Sequence[str],
    layouts: Sequence[tuple[str, Layout]],
) -> str:
    """One query listing every change in a dataset, as described at the top of this module."""
    keys = layout.keys
    values = [c for c in layout.values if c in shared]
    tracked = [c for c in layout.tracked if c in shared]
    key_list = ", ".join(_quoted(k) for k in keys)
    new, old = f"{NEW}.{_quoted(table)}", f"{OLD}.{_quoted(table)}"

    def part(
        what: str,
        alias: str,
        column: str | None,
        was: str,
        now: str,
        change: str,
        change_percent: str,
        source: str,
        where: str = "",
    ) -> str:
        """One SELECT giving change lines, every column named."""
        named_keys = ", ".join(f"{alias}.{_quoted(k)} AS {_quoted(k)}" for k in keys)
        return (
            f"SELECT {sql_text(what)} AS what, {named_keys}, "
            f'{"NULL" if column is None else sql_text(column)} AS "column", '
            f"CAST({was} AS VARCHAR) AS was, CAST({now} AS VARCHAR) AS now, "
            f"CAST({change} AS DOUBLE) AS change, "
            f"CAST({change_percent} AS DOUBLE) AS change_percent "
            f"FROM {source} {where}"
        )

    def row_lines(what: str, alias: str, source: str, other: str) -> list[str]:
        """Lines for rows in one build only: one per value, or one per row if it has none."""
        rows = f"{source} AS {alias} ANTI JOIN {other} USING ({key_list})"
        if not values:
            return [part(what, alias, None, "NULL", "NULL", "NULL", "NULL", rows)]
        lines = []
        for column in values:
            value = f"{alias}.{_quoted(column)}"
            was, now = ("NULL", value) if what == ADDED else (value, "NULL")
            lines.append(part(what, alias, column, was, now, "NULL", "NULL", rows))
        return lines

    def revised_lines() -> list[str]:
        both = f"{new} AS n JOIN {old} AS o USING ({key_list})"
        lines = []
        for column in values:
            n, o = f"n.{_quoted(column)}", f"o.{_quoted(column)}"
            if layout.values[column] == DECIMAL:
                differs = (
                    f"(({n} IS NULL) <> ({o} IS NULL) OR "
                    f"abs({n} - {o}) > {DECIMAL_TOLERANCE} * greatest(abs({n}), abs({o})))"
                )
            else:
                differs = f"{n} IS DISTINCT FROM {o}"
            change = f"(CAST({n} AS DOUBLE) - CAST({o} AS DOUBLE))"
            percent = (
                f"round(100 * {change} / nullif(abs(CAST({o} AS DOUBLE)), 0), {PERCENT_DECIMALS})"
            )
            lines.append(
                part(REVISED, "n", column, o, n, change, percent, both, f"WHERE {differs}")
            )
        for column in tracked:
            n = f"CAST(n.{_quoted(column)} AS VARCHAR)"
            o = f"CAST(o.{_quoted(column)} AS VARCHAR)"
            lines.append(
                part(REVISED, "n", column, o, n, "NULL", "NULL", both,
                     f"WHERE {n} IS DISTINCT FROM {o}")
            )  # fmt: skip
        return lines

    parts = [
        *row_lines(REMOVED, "o", old, new),
        *revised_lines(),
        *row_lines(ADDED, "n", new, old),
    ]
    stacked = "\nUNION ALL\n".join(parts)
    label_columns, label_joins = _labels(db, layout, layouts)
    order = ", ".join(f"{sql_text(what)}" for what in WHAT_ORDER)
    return f"""
        SELECT c.what, {", ".join(f"c.{_quoted(k)}" for k in keys)}{label_columns},
               c."column", c.was, c.now, c.change, c.change_percent
        FROM ({stacked}) AS c
        {label_joins}
        ORDER BY list_position([{order}], c.what), c."column" NULLS FIRST,
                 abs(c.change) DESC NULLS LAST, {", ".join(f"c.{_quoted(k)}" for k in keys)}
    """


def _labels(
    db: duckdb.DuckDBPyConnection, layout: Layout, layouts: Sequence[tuple[str, Layout]]
) -> tuple[str, str]:
    """SQL adding a readable name for each labelled key, from the new build (else the old).

    For example {"jurisdiction": "jurisdictions"} adds "jurisdiction_name", the
    name_en of the jurisdictions row whose key matches.
    """
    reference_keys = {table: ref.keys[0] for table, ref in layouts}
    columns, joins = [], []
    for number, (key, reference) in enumerate(layout.labels.items()):
        if reference not in reference_keys:
            continue
        names = []
        for build in (NEW, OLD):
            if LABEL_COLUMN not in _columns(db, build, reference):
                continue
            alias = f"label{number}_{build}"
            joins.append(
                f"LEFT JOIN {build}.{_quoted(reference)} AS {alias} "
                f"ON {alias}.{_quoted(reference_keys[reference])} = c.{_quoted(key)}"
            )
            names.append(f"{alias}.{_quoted(LABEL_COLUMN)}")
        if names:
            columns.append(f"coalesce({', '.join(names)}) AS {_quoted(label_name(key))}")
    return "".join(f", {column}" for column in columns), "\n".join(joins)


def label_name(key: str) -> str:
    """The name of a key's readable-name column: "jurisdiction_name", "function_name"."""
    return f"{key.removesuffix('_id')}_name"


# --- Asking the builds about themselves ----------------------------------------


def _tables(db: duckdb.DuckDBPyConnection, build: str) -> list[str]:
    return [
        table
        for (table,) in db.sql(
            "SELECT table_name FROM information_schema.tables "
            f"WHERE table_catalog = {sql_text(build)} AND table_type = 'BASE TABLE' "
            "ORDER BY table_name"
        ).fetchall()
    ]


def _columns(db: duckdb.DuckDBPyConnection, build: str, table: str) -> list[str]:
    """A table's columns in one build, in order; empty if the build has no such table."""
    return [
        column
        for (column,) in db.sql(
            "SELECT column_name FROM information_schema.columns "
            f"WHERE table_catalog = {sql_text(build)} AND table_name = {sql_text(table)} "
            "ORDER BY ordinal_position"
        ).fetchall()
    ]


def _row_count(db: duckdb.DuckDBPyConnection, build: str, table: str) -> int:
    return db.sql(f"SELECT count(*) FROM {build}.{_quoted(table)}").fetchall()[0][0]


def _quoted(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'
