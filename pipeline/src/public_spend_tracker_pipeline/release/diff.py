"""What changed between two builds: the report you read before approving one.

Run it from the repository root with:

    uv run pst diff                          the newest build against the approved build
    uv run pst diff <build_id>               a particular build against the approved build
    uv run pst diff <build_id> --against <other_build_id>

It opens both builds' databases read-only and compares every model dataset
row by row (release/compare.py), using the layout each dataset declares. So a
new source is covered as soon as its transformer has a layout. It prints a
report (Markdown, so it reads well in a GitHub issue too) and saves, in the
newer build's folder:

    changes-vs-<other build>.md        the report
    changes-vs-<other build>/<dataset>.csv
                                       every change in one dataset, one line per
                                       changed value (only datasets that changed)

Each name includes the build compared with, so a comparison is never
overwritten by another (the bucket never overwrites files: see sync.py).

What the report covers, in order:

    Needs attention       rows, columns or datasets that are gone (should never happen)
    New source releases   which Statistics Canada tables have a new release
    Changes by dataset    rows added and removed, values revised, other changes
    Years covered         years of spending added
    Headline              total spending by all governments, federal and all provinces
    Revised spending      by government, and the 25 largest revisions
    Other revisions       the largest revisions in every other dataset
    Population, prices and GDP   how many values were revised (these move
                          per-person, inflation-adjusted and share-of-GDP figures)
    Checks                how many passed

A whole-number value (e.g. dollars, which Statistics Canada rounds to the
nearest million) is revised if it changed at all. A decimal value (e.g. a
price index averaged over 12 months) is revised only if it moved by more than
rounding noise: see compare.DECIMAL_TOLERANCE.
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass
from pathlib import Path

import duckdb

from public_spend_tracker_pipeline.build.run import model_transformers
from public_spend_tracker_pipeline.common.logs import start_logging, stop_logging
from public_spend_tracker_pipeline.common.paths import (
    BUILD_MANIFEST_FILE_NAME,
    DATABASE_FILE_NAME,
    new_build_id,
    serving_build_folder,
)
from public_spend_tracker_pipeline.common.settings import DATA_ROOT
from public_spend_tracker_pipeline.release.approve import (
    ApprovalError,
    approved_build,
    is_complete,
    newest_complete_build,
)
from public_spend_tracker_pipeline.release.compare import (
    IN_BOTH,
    NEW,
    OLD,
    OLD_ONLY,
    REMOVED,
    REVISED,
    TableChanges,
    compare_tables,
    label_name,
    tables_without_layout,
)
from public_spend_tracker_pipeline.transform.base import Layout, sql_text

log = logging.getLogger(__name__)

# How many of the largest revisions, and of any removed rows, the report lists.
LARGEST_REVISIONS_SHOWN = 25
LARGEST_OTHER_REVISIONS_SHOWN = 10
REMOVED_SHOWN = 25

# The four views, in the order the report lists them, with their names.
VIEW_NAMES = {
    "canada": "All governments combined",
    "federal": "Federal government",
    "province_wide": "Province-wide",
    "provincial_government": "Provincial government only",
}

# The datasets the report has its own sections for.
SPENDING = "spending"
CONTEXT = "context"

# A key column with this name holds a fiscal year by its start (2024 means 2024-25).
FISCAL_YEAR_KEY = "fiscal_year"

# Context series, with their names.
CONTEXT_NAMES = {"population": "Population", "cpi": "Prices (CPI)", "gdp": "GDP"}

CHANGES_FILE = "changes-vs-{other}.md"
CHANGES_FOLDER = "changes-vs-{other}"
CHANGES_TABLE_FILE = "{table}.csv"

# Tables in the database that belong to the build itself, not to a model dataset.
BUILD_TABLES = ("build_info",)


class DiffError(Exception):
    """Two builds could not be compared, e.g. one of them is not complete."""


# --- What a comparison finds ------------------------------------------------


@dataclass(frozen=True)
class Revision:
    """One spending figure whose dollars changed."""

    government: str
    view: str
    function_id: str
    function: str
    fiscal_year: int
    was: int
    now: int
    status_was: str | None
    status_now: str | None

    @property
    def change(self) -> int:
        return self.now - self.was

    @property
    def change_percent(self) -> float | None:
        return None if self.was == 0 else self.change / abs(self.was) * 100


@dataclass(frozen=True)
class GovernmentRevisions:
    """How a government's figures were revised, in one view."""

    government: str
    view: str
    figures: int  # functions and sub-functions
    net_change: int  # the 10 functions only (sub-functions add up to them)


@dataclass(frozen=True)
class Total:
    """Total spending by one government (the 10 functions) in one year, in two builds."""

    government: str
    fiscal_year: int
    was: int | None
    now: int | None


@dataclass(frozen=True)
class SourceRelease:
    table_number: str
    title: str
    was: str | None  # None if the table is new
    now: str


@dataclass(frozen=True)
class Comparison:
    """Everything the report says about two builds."""

    new_build: str
    old_build: str
    old_is_approved: bool  # whether the earlier build is the approved one
    tables: list[TableChanges]  # every model dataset, in build order
    unexpected_tables: dict[str, str]  # tables with no layout found in one build only
    new_releases: list[SourceRelease]
    old_years: tuple[int, int]
    new_years: tuple[int, int]
    totals: list[Total]
    revisions: list[Revision]  # largest change first
    by_government: list[GovernmentRevisions]
    old_checks: int
    new_checks: int

    def table(self, name: str) -> TableChanges:
        return next(table for table in self.tables if table.table == name)


# --- Comparing --------------------------------------------------------------


def layouts() -> list[tuple[str, Layout]]:
    """Every model dataset's name and layout, in the order the build lists them."""
    return [(transformer.name, transformer.layout) for transformer in model_transformers({})]


def compare_builds(
    new_build: str, old_build: str, data_root: Path = DATA_ROOT, old_is_approved: bool = True
) -> Comparison:
    """Compare two complete builds' databases. Nothing is changed."""
    for build_id in (new_build, old_build):
        if not is_complete(build_id, data_root):
            raise DiffError(
                f"Build {build_id} is not complete (it has no {BUILD_MANIFEST_FILE_NAME})"
            )

    db = duckdb.connect()
    try:
        for alias, build_id in ((NEW, new_build), (OLD, old_build)):
            database = serving_build_folder(build_id, data_root) / DATABASE_FILE_NAME
            db.sql(f"ATTACH {sql_text(str(database))} AS {alias} (READ_ONLY)")
        names = _Names(db)
        described = layouts()
        unexpected = {
            table: where
            for table, where in tables_without_layout(db, described).items()
            if where != IN_BOTH and table not in BUILD_TABLES
        }
        return Comparison(
            new_build=new_build,
            old_build=old_build,
            old_is_approved=old_is_approved,
            tables=compare_tables(db, described),
            unexpected_tables=unexpected,
            new_releases=_new_releases(db),
            old_years=_years(db, OLD),
            new_years=_years(db, NEW),
            totals=_totals(db, names),
            revisions=_revisions(db, names),
            by_government=_by_government(db, names),
            old_checks=checks_passed(old_build, data_root),
            new_checks=checks_passed(new_build, data_root),
        )
    finally:
        db.close()


class _Names:
    """English names of governments and functions, from the new build."""

    def __init__(self, db: duckdb.DuckDBPyConnection):
        self.places = dict(db.sql("SELECT code, name_en FROM new.jurisdictions").fetchall())
        self.functions = dict(db.sql("SELECT function_id, name_en FROM new.functions").fetchall())

    def government(self, view: str, jurisdiction: str) -> str:
        """The government a row is about, read the way its view means it."""
        if view in ("canada", "federal"):
            return VIEW_NAMES[view]
        if jurisdiction == "ca":
            return "All provinces and territories"
        return self.places.get(jurisdiction, jurisdiction)


_SPENDING_KEYS = "view, jurisdiction, function_id, fiscal_year"


def _new_releases(db: duckdb.DuckDBPyConnection) -> list[SourceRelease]:
    rows = db.sql(
        "SELECT n.table_number, n.title_en, o.release, n.release "
        "FROM new.sources AS n LEFT JOIN old.sources AS o USING (source_id) "
        "WHERE n.release IS DISTINCT FROM o.release ORDER BY n.table_number"
    ).fetchall()
    return [
        SourceRelease(number, title, was and was.isoformat(), now.isoformat())
        for number, title, was, now in rows
    ]


def _years(db: duckdb.DuckDBPyConnection, build: str) -> tuple[int, int]:
    """The first and latest fiscal years a build has spending figures for."""
    first, latest = db.sql(
        f"SELECT min(fiscal_year), max(fiscal_year) FROM {build}.spending"
    ).fetchall()[0]
    return first, latest


# The three headline totals: (view, jurisdiction) of each.
_HEADLINE = (("canada", "ca"), ("federal", "ca"), ("province_wide", "ca"))


def _totals(db: duckdb.DuckDBPyConnection, names: _Names) -> list[Total]:
    """Headline totals in the old build's latest year, and in any year the new build adds."""
    old_latest = _years(db, OLD)[1]
    new_latest = _years(db, NEW)[1]

    def total(build: str, view: str, place: str, year: int) -> int | None:
        return db.sql(
            f"SELECT sum(s.amount) FROM {build}.spending AS s "
            f"JOIN {build}.functions AS f USING (function_id) "
            f"WHERE f.level = 1 AND s.view = {sql_text(view)} "
            f"AND s.jurisdiction = {sql_text(place)} AND s.fiscal_year = {year}"
        ).fetchall()[0][0]

    return [
        Total(names.government(view, place), year, total(OLD, view, place, year),
              total(NEW, view, place, year))
        for year in range(old_latest, new_latest + 1)
        for view, place in _HEADLINE
    ]  # fmt: skip


def _revisions(db: duckdb.DuckDBPyConnection, names: _Names) -> list[Revision]:
    rows = db.sql(
        f"SELECT {_SPENDING_KEYS}, o.amount, n.amount, o.revision_status, n.revision_status "
        f"FROM new.spending AS n JOIN old.spending AS o USING ({_SPENDING_KEYS}) "
        "WHERE n.amount IS DISTINCT FROM o.amount "
        "ORDER BY abs(n.amount - o.amount) DESC, view, jurisdiction, function_id, fiscal_year"
    ).fetchall()
    return [
        Revision(
            government=names.government(view, place),
            view=VIEW_NAMES[view],
            function_id=function_id,
            function=names.functions.get(function_id, function_id),
            fiscal_year=year,
            was=was,
            now=now,
            status_was=status_was,
            status_now=status_now,
        )
        for view, place, function_id, year, was, now, status_was, status_now in rows
    ]


def _by_government(db: duckdb.DuckDBPyConnection, names: _Names) -> list[GovernmentRevisions]:
    """Revisions grouped by government and view, in the views' usual order."""
    view_order = list(VIEW_NAMES)
    rows = db.sql(
        f"SELECT n.view, n.jurisdiction, count(*), "
        f"  sum(CASE WHEN f.level = 1 THEN n.amount - o.amount ELSE 0 END), j.sort_order "
        f"FROM new.spending AS n JOIN old.spending AS o USING ({_SPENDING_KEYS}) "
        "JOIN new.functions AS f USING (function_id) "
        "JOIN new.jurisdictions AS j ON j.code = n.jurisdiction "
        "WHERE n.amount IS DISTINCT FROM o.amount "
        "GROUP BY n.view, n.jurisdiction, j.sort_order"
    ).fetchall()
    rows.sort(key=lambda row: (view_order.index(row[0]), row[4]))
    return [
        GovernmentRevisions(names.government(view, place), VIEW_NAMES[view], figures, int(net))
        for view, place, figures, net, _ in rows
    ]


def checks_passed(build_id: str, data_root: Path = DATA_ROOT) -> int:
    """How many checks a complete build passed, from its manifest."""
    manifest_file = serving_build_folder(build_id, data_root) / BUILD_MANIFEST_FILE_NAME
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    checks = sum(len(dataset["checks"]) for dataset in manifest["datasets"])
    if manifest.get("serving"):
        checks += len(manifest["serving"]["checks"])
    return checks


# --- Writing it down ----------------------------------------------------------


def year_label(year: int) -> str:
    """A fiscal year by its start: 2024 is "2024-25"."""
    return f"{year}-{(year + 1) % 100:02d}"


def money(amount: int | float | None, signed: bool = False) -> str:
    """Dollars in billions or millions, e.g. "$1,137.1B", "$350M"; "+$1.2B" when signed."""
    if amount is None:
        return "no figure"
    sign = ("+" if amount > 0 else "-" if amount < 0 else "") if signed else ""
    if not signed and amount < 0:
        sign = "-"
    size = abs(amount)
    if size >= 1e9:
        number = f"{size / 1e9:,.1f}B"
    elif size >= 1e6:
        number = f"{size / 1e6:,.0f}M"
    else:
        number = f"{size:,.0f}"
    return f"{sign}${number}"


def percent(value: float | None) -> str:
    return "" if value is None else f"{value:+.1f}%"


def plain_number(value: str | float | None, signed: bool = False) -> str:
    """A number as the report shows it: "18,410,000,000", "132.2", "+0.0417"; "" if none.

    Whole numbers get thousands separators; others keep up to 4 decimals.
    """
    if value is None or value == "":
        return ""
    number = float(value)
    sign = "+" if signed and number > 0 else ""
    if number.is_integer():
        return f"{sign}{number:,.0f}"
    return sign + f"{number:,.4f}".rstrip("0").rstrip(".")


def _change(was: int | None, now: int | None) -> str:
    if was is None or now is None:
        return ""
    change = now - was
    if change == 0:
        return "no change"
    return (
        f"{money(change, signed=True)} ({percent(None if was == 0 else change / abs(was) * 100)})"
    )


def _rows(count: int) -> str:
    """ "1 row" or "3 rows"."""
    return "1 row" if count == 1 else f"{count:,} rows"


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return lines


def describe_row(changes: TableChanges, line: tuple) -> str:
    """A changed row in words: its keys, with readable names where there are some.

    For example "province_wide, Quebec, Health, 2024-25". A key named
    fiscal_year is written as the fiscal year it means.
    """
    parts = []
    for key in changes.layout.keys:
        name = label_name(key)
        label = changes.field(line, name) if name in changes.header else None
        value = changes.field(line, key)
        if label is not None:
            parts.append(str(label))
        elif key == FISCAL_YEAR_KEY and isinstance(value, int):
            parts.append(year_label(value))
        else:
            parts.append(str(value))
    return ", ".join(parts)


def report(comparison: Comparison) -> str:
    """The report, in Markdown."""
    c = comparison
    earlier = "approved build" if c.old_is_approved else "build"
    before = "Approved" if c.old_is_approved else "Earlier"
    folder = CHANGES_FOLDER.format(other=c.old_build)
    lines = [f"## What changed: build {c.new_build} compared with {earlier} {c.old_build}", ""]

    lines += ["### Needs attention", ""]
    attention = _attention(c, earlier)
    lines += attention or [f"Nothing: every row in the {earlier} is still there."]
    lines.append("")

    lines += ["### New source releases", ""]
    if c.new_releases:
        lines += _table(
            ["Table", f"{before} build used", "New build uses"],
            [
                [f"{r.table_number} {r.title}", r.was or "(new table)", r.now]
                for r in c.new_releases
            ],
        )
    else:
        lines.append("None: both builds use the same releases.")
    lines.append("")

    lines += ["### Changes by dataset", ""]
    changed = [t for t in c.tables if t.has_changes]
    if changed:
        lines += _table(
            ["Dataset", "Rows added", "Rows removed", "Values revised", "Other changes"],
            [
                [t.table, f"{t.rows_added:,}", f"{t.rows_removed:,}", f"{t.values_revised:,}",
                 _other_changes(t)]
                for t in changed
            ],
        )  # fmt: skip
        lines += [
            "",
            f"Every change is listed in `{folder}/<dataset>.csv`, saved with the build "
            "(one line per changed value).",
        ]
    else:
        lines.append("None: every dataset is the same in both builds.")
    unchanged = [t.table for t in c.tables if not t.has_changes]
    if changed and unchanged:
        lines.append(f"No changes: {', '.join(unchanged)}.")
    lines.append("")

    spending = c.table(SPENDING)
    old_range = f"{year_label(c.old_years[0])} to {year_label(c.old_years[1])}"
    new_range = f"{year_label(c.new_years[0])} to {year_label(c.new_years[1])}"
    added = f"{spending.rows_added:,} new spending figures"
    lines += ["### Years covered", ""]
    if old_range == new_range:
        lines.append(f"{new_range}, unchanged ({added}).")
    else:
        lines.append(f"{old_range} -> **{new_range}** ({added}).")
    lines.append("")

    lines += ["### Headline: total spending", ""]
    lines += _table(
        ["", "Year", before, "New", "Change"],
        [
            [
                t.government,
                year_label(t.fiscal_year),
                money(t.was),
                money(t.now),
                _change(t.was, t.now),
            ]
            for t in c.totals
        ],
    )
    lines.append("")

    lines += ["### Revised spending", ""]
    if c.revisions:
        lines.append(f"{len(c.revisions):,} spending figures changed in years both builds have.")
        if spending.tracked_changed:
            lines.append(
                f"{spending.tracked_changed:,} figures changed revision status "
                "(e.g. preliminary to revised)."
            )
        lines += ["", "By government (net change counts the 10 functions only):", ""]
        lines += _table(
            ["Government", "Counted as", "Figures changed", "Net change"],
            [
                [g.government, g.view, f"{g.figures:,}", money(g.net_change, signed=True)]
                for g in c.by_government
            ],
        )
        shown = c.revisions[:LARGEST_REVISIONS_SHOWN]
        lines += ["", f"Largest {len(shown)} revisions, by dollars:", ""]
        lines += _table(
            ["Government", "Counted as", "Function", "Year", "Was", "Now", "Change"],
            [
                [r.government, r.view, r.function, year_label(r.fiscal_year), money(r.was),
                 money(r.now), _change(r.was, r.now)]
                for r in shown
            ],
        )  # fmt: skip
    else:
        lines.append("None: no spending figure changed in years both builds have.")
        if spending.tracked_changed:
            lines.append(f"{spending.tracked_changed:,} figures changed revision status.")
    lines.append("")

    others = [t for t in c.tables if t.table != SPENDING and t.values_revised]
    if others:
        lines += ["### Other revisions", ""]
        for t in others:
            lines += _largest_revisions(t)
            lines.append("")

    lines += ["### Population, prices and GDP", ""]
    context = c.table(CONTEXT)
    revised = _context_revisions(context)
    lines.append(
        "Values revised: "
        + "; ".join(f"{name}: {revised[series]:,}" for series, name in CONTEXT_NAMES.items())
        + "."
    )
    if any(revised.values()):
        lines.append(
            "These change per-person, inflation-adjusted and share-of-GDP figures, "
            "even where spending did not change."
        )
    lines.append("")

    lines += ["### Checks", "", f"{c.new_checks} checks passed ({earlier}: {c.old_checks})."]
    return "\n".join(lines) + "\n"


def _attention(c: Comparison, earlier: str) -> list[str]:
    """Lines for the Needs attention section; empty when nothing needs attention."""
    lines = []
    for table, where in c.unexpected_tables.items():
        lines.append(f"- **{table}**: a table with no layout, found in the {where} only.")
    for t in c.tables:
        if not t.needs_attention:
            continue
        if t.problem:
            lines.append(f"- **{t.table}**: could not be compared ({t.problem}).")
        if t.found_in == OLD_ONLY:
            lines.append(f"- **{t.table}**: in the {earlier}, missing from the new build.")
        if t.columns_removed:
            lines.append(
                f"- **{t.table}**: columns missing from the new build: "
                f"{', '.join(t.columns_removed)}."
            )
        if t.rows_removed:
            lines.append(
                f"- **{t.table}**: {_rows(t.rows_removed)} in the {earlier} missing from the "
                "new build:"
            )
            removed = list(dict.fromkeys(describe_row(t, line) for line in t.lines
                                         if line[0] == REMOVED))  # fmt: skip
            lines += [f"  - {row}" for row in removed[:REMOVED_SHOWN]]
            if len(removed) > REMOVED_SHOWN:
                lines.append(f"  - ... and {len(removed) - REMOVED_SHOWN:,} more")
    return lines


def _other_changes(t: TableChanges) -> str:
    """The Other changes cell: tracked columns that changed, and anything about the dataset."""
    notes = []
    if t.tracked_changed:
        tracked = {t.field(line, "column") for line in t.lines if line[0] == REVISED}
        tracked -= set(t.layout.values)
        notes.append(f"{t.tracked_changed:,} in {', '.join(sorted(tracked))}")
    if t.columns_added:
        notes.append(f"new columns: {', '.join(t.columns_added)}")
    if t.found_in != IN_BOTH:
        notes.append(f"dataset in the {t.found_in}")
    if t.problem:
        notes.append("not compared")
    return "; ".join(notes)


def _largest_revisions(t: TableChanges) -> list[str]:
    """A dataset's largest revisions, as a heading and a table."""
    revised = [
        line for line in t.lines
        if line[0] == REVISED and t.field(line, "column") in t.layout.values
    ]  # fmt: skip
    revised.sort(key=lambda line: abs(t.field(line, "change") or 0), reverse=True)
    shown = revised[:LARGEST_OTHER_REVISIONS_SHOWN]
    lines = [f"**{t.table}**: {t.values_revised:,} values revised; the {len(shown)} largest:", ""]
    lines += _table(
        ["Row", "Column", "Was", "Now", "Change"],
        [
            [
                describe_row(t, line),
                t.field(line, "column"),
                plain_number(t.field(line, "was")),
                plain_number(t.field(line, "now")),
                f"{plain_number(t.field(line, 'change'), signed=True)} "
                f"({percent(t.field(line, 'change_percent'))})",
            ]
            for line in shown
        ],
    )
    return lines


def _context_revisions(context: TableChanges) -> dict[str, int]:
    """How many context values were revised, by series (fiscal and calendar years together)."""
    revised = {series: 0 for series in CONTEXT_NAMES}
    for line in context.lines:
        if line[0] == REVISED and context.field(line, "column") in context.layout.values:
            series = context.field(line, "series")
            revised[series] = revised.get(series, 0) + 1
    return revised


def write_changes(tables: list[TableChanges], folder: Path) -> list[Path]:
    """Every change, one CSV file per dataset that changed. Returns the files written.

    Changes in whole numbers are written without a decimal point, so they add
    up exactly in a spreadsheet.
    """
    written = []
    for t in tables:
        if not t.lines:
            continue
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / CHANGES_TABLE_FILE.format(table=t.table)
        change = t.header.index("change")
        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(t.header)
            for line in t.lines:
                row = ["" if value is None else value for value in line]
                if isinstance(line[change], float) and line[change].is_integer():
                    row[change] = int(line[change])
                writer.writerow(row)
        written.append(path)
    return written


# --- Command ----------------------------------------------------------------


def diff_builds(
    data_root: Path = DATA_ROOT, build_id: str | None = None, against: str | None = None
) -> int:
    """Compare a build (the newest by default) with another (the approved one by default).

    Prints the report and saves it, with every change as CSV, in the build's
    folder. Returns 0 if it worked, 1 if not.
    """
    start_logging("diff", new_build_id(), data_root)
    try:
        new = build_id or newest_complete_build(data_root)
        approved = approved_build(data_root)
        old = against or approved
        if old is None:
            print("No build is approved yet, so there is nothing to compare with.")
            return 0
        if new == old:
            print(f"Build {new} is the approved build: nothing to compare.")
            return 0

        comparison = compare_builds(new, old, data_root, old_is_approved=old == approved)
        text = report(comparison)
        folder = serving_build_folder(new, data_root)
        (folder / CHANGES_FILE.format(other=old)).write_text(text, encoding="utf-8")
        written = write_changes(comparison.tables, folder / CHANGES_FOLDER.format(other=old))
        print(text, end="")
        saved = [CHANGES_FILE.format(other=old)] + [
            path.relative_to(folder).as_posix() for path in written
        ]
        log.info(f"Saved in {folder}: {', '.join(saved)}")
        return 0
    except (DiffError, ApprovalError, duckdb.Error) as error:
        log.error(f"Nothing compared: {error}")
        return 1
    finally:
        stop_logging()
