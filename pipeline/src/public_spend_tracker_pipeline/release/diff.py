"""What changed between two builds: the report you read before approving one.

Run it from the repository root with:

    uv run pst diff                          the newest build against the approved build
    uv run pst diff <build_id>               a particular build against the approved build
    uv run pst diff <build_id> --against <other_build_id>

It opens both builds' databases read-only, compares their tables row by row,
prints a report (Markdown, so it reads well in a GitHub issue too), and saves
two files in the newer build's folder:

    changes-vs-<other build>.md     the report
    revisions-vs-<other build>.csv  every revised spending figure, one row each

Each file names the build it was compared with, so a comparison is never
overwritten by another (the bucket never overwrites files: see sync.py).

What the report covers, in order:

    Needs attention     figures that existed before and are gone now (should never happen)
    New source releases which Statistics Canada tables have a new release
    Years covered       years added, and how many new figures
    Headline            total spending by all governments, federal and all provinces
    Revised figures     how many changed, by government, and the 25 largest
    Population, prices and GDP   how many values were revised (these move per-person,
                        inflation-adjusted and share-of-GDP figures)
    Checks              how many passed

A revision is any change to a figure's dollars in a year both builds have.
Statistics Canada rounds to the nearest million, so every change is real.
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass
from pathlib import Path

import duckdb

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
from public_spend_tracker_pipeline.transform.base import sql_text

log = logging.getLogger(__name__)

# How many of the largest revisions, and of any vanished figures, the report lists.
LARGEST_REVISIONS_SHOWN = 25
VANISHED_SHOWN = 25

# The four views, in the order the report lists them, with their names.
VIEW_NAMES = {
    "canada": "All governments combined",
    "federal": "Federal government",
    "province_wide": "Province-wide",
    "provincial_government": "Provincial government only",
}

# Context series compared, with their names. Values are compared as
# published (calendar basis); fiscal-year values are worked out from them.
CONTEXT_NAMES = {"population": "Population", "cpi": "Prices (CPI)", "gdp": "GDP"}
CONTEXT_BASIS_COMPARED = "calendar"

CHANGES_FILE = "changes-vs-{other}.md"
REVISIONS_FILE = "revisions-vs-{other}.csv"


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
    vanished: list[str]  # figures in the old build missing from the new
    new_releases: list[SourceRelease]
    old_years: tuple[int, int]
    new_years: tuple[int, int]
    added_figures: int
    totals: list[Total]
    revisions: list[Revision]  # largest change first
    by_government: list[GovernmentRevisions]
    status_changes: int
    municipal_revisions: int
    context_revisions: dict[str, int]
    old_checks: int
    new_checks: int


# --- Comparing --------------------------------------------------------------


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
        for alias, build_id in (("new", new_build), ("old", old_build)):
            database = serving_build_folder(build_id, data_root) / DATABASE_FILE_NAME
            db.sql(f"ATTACH {sql_text(str(database))} AS {alias} (READ_ONLY)")
        names = _Names(db)
        return Comparison(
            new_build=new_build,
            old_build=old_build,
            old_is_approved=old_is_approved,
            vanished=_vanished(db, names),
            new_releases=_new_releases(db),
            old_years=_years(db, "old"),
            new_years=_years(db, "new"),
            added_figures=_count(
                db,
                "SELECT count(*) FROM new.spending "
                "ANTI JOIN old.spending USING (view, jurisdiction, function_id, fiscal_year)",
            ),
            totals=_totals(db, names),
            revisions=_revisions(db, names),
            by_government=_by_government(db, names),
            status_changes=_count(
                db,
                "SELECT count(*) FROM new.spending AS n JOIN old.spending AS o "
                "USING (view, jurisdiction, function_id, fiscal_year) "
                "WHERE n.revision_status IS DISTINCT FROM o.revision_status",
            ),
            municipal_revisions=_count(
                db,
                "SELECT count(*) FROM new.municipal_transfers AS n "
                "JOIN old.municipal_transfers AS o USING (jurisdiction, fiscal_year) "
                "WHERE n.amount IS DISTINCT FROM o.amount",
            ),
            context_revisions=_context_revisions(db),
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
        self.top_level = {
            function_id
            for (function_id,) in db.sql(
                "SELECT function_id FROM new.functions WHERE level = 1"
            ).fetchall()
        }

    def government(self, view: str, jurisdiction: str) -> str:
        """The government a row is about, read the way its view means it."""
        if view in ("canada", "federal"):
            return VIEW_NAMES[view]
        if jurisdiction == "ca":
            return "All provinces and territories"
        return self.places.get(jurisdiction, jurisdiction)


_SPENDING_KEYS = "view, jurisdiction, function_id, fiscal_year"


def _count(db: duckdb.DuckDBPyConnection, query: str) -> int:
    return db.sql(query).fetchall()[0][0]


def _vanished(db: duckdb.DuckDBPyConnection, names: _Names) -> list[str]:
    spending = db.sql(
        f"SELECT {_SPENDING_KEYS} FROM old.spending "
        f"ANTI JOIN new.spending USING ({_SPENDING_KEYS}) ORDER BY {_SPENDING_KEYS}"
    ).fetchall()
    municipal = db.sql(
        "SELECT jurisdiction, fiscal_year FROM old.municipal_transfers "
        "ANTI JOIN new.municipal_transfers USING (jurisdiction, fiscal_year) ORDER BY ALL"
    ).fetchall()
    return [
        f"{names.government(view, place)}, {VIEW_NAMES[view].lower()}: "
        f"{names.functions.get(function_id, function_id)}, {year_label(year)}"
        for view, place, function_id, year in spending
    ] + [
        f"{names.government('province_wide', place)}: municipal transfers, {year_label(year)}"
        for place, year in municipal
    ]


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
    old_latest = _years(db, "old")[1]
    new_latest = _years(db, "new")[1]

    def total(build: str, view: str, place: str, year: int) -> int | None:
        return db.sql(
            f"SELECT sum(s.amount) FROM {build}.spending AS s "
            f"JOIN {build}.functions AS f USING (function_id) "
            f"WHERE f.level = 1 AND s.view = {sql_text(view)} "
            f"AND s.jurisdiction = {sql_text(place)} AND s.fiscal_year = {year}"
        ).fetchall()[0][0]

    return [
        Total(names.government(view, place), year, total("old", view, place, year),
              total("new", view, place, year))
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


def _context_revisions(db: duckdb.DuckDBPyConnection) -> dict[str, int]:
    rows = dict(
        db.sql(
            "SELECT n.series, count(*) FROM new.context AS n "
            "JOIN old.context AS o USING (jurisdiction, series, basis, year) "
            f"WHERE n.basis = {sql_text(CONTEXT_BASIS_COMPARED)} "
            "AND n.value IS DISTINCT FROM o.value GROUP BY n.series"
        ).fetchall()
    )
    return {series: rows.get(series, 0) for series in CONTEXT_NAMES}


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


def _change(was: int | None, now: int | None) -> str:
    if was is None or now is None:
        return ""
    change = now - was
    if change == 0:
        return "no change"
    return (
        f"{money(change, signed=True)} ({percent(None if was == 0 else change / abs(was) * 100)})"
    )


def _figures(count: int) -> str:
    """ "1 figure is" or "3 figures are" (for "... missing")."""
    return "1 figure is" if count == 1 else f"{count:,} figures are"


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return lines


def report(comparison: Comparison) -> str:
    """The report, in Markdown."""
    c = comparison
    revisions_file = REVISIONS_FILE.format(other=c.old_build)
    earlier = "approved build" if c.old_is_approved else "build"
    before = "Approved" if c.old_is_approved else "Earlier"
    lines = [f"## What changed: build {c.new_build} compared with {earlier} {c.old_build}", ""]

    lines += ["### Needs attention", ""]
    if c.vanished:
        lines.append(
            f"**{_figures(len(c.vanished))} in the {earlier} missing from the new build.**"
        )
        lines += [f"- {item}" for item in c.vanished[:VANISHED_SHOWN]]
        if len(c.vanished) > VANISHED_SHOWN:
            lines.append(f"- ... and {len(c.vanished) - VANISHED_SHOWN} more")
    else:
        lines.append(f"Nothing: every figure in the {earlier} is still there.")
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

    old_range = f"{year_label(c.old_years[0])} to {year_label(c.old_years[1])}"
    new_range = f"{year_label(c.new_years[0])} to {year_label(c.new_years[1])}"
    lines += ["### Years covered", ""]
    if old_range == new_range:
        lines.append(f"{new_range}, unchanged ({c.added_figures:,} new spending figures).")
    else:
        lines.append(f"{old_range} -> **{new_range}** ({c.added_figures:,} new spending figures).")
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

    lines += ["### Revised figures", ""]
    if c.revisions:
        lines.append(
            f"{len(c.revisions):,} spending figures changed in years both builds have. "
            f"Every one is in `{revisions_file}`, saved with the build."
        )
        lines.append(
            f"{c.status_changes:,} figures changed revision status (e.g. preliminary to revised)."
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
        if c.status_changes:
            lines.append(f"{c.status_changes:,} figures changed revision status.")
    if c.municipal_revisions:
        lines += ["", f"Municipal transfers: {c.municipal_revisions:,} figures revised."]
    lines.append("")

    lines += ["### Population, prices and GDP", ""]
    revised = [f"{name}: {c.context_revisions[series]:,}" for series, name in CONTEXT_NAMES.items()]
    lines.append(f"Values revised, as published: {'; '.join(revised)}.")
    if any(c.context_revisions.values()):
        lines.append(
            "These change per-person, inflation-adjusted and share-of-GDP figures, "
            "even where spending did not change."
        )
    lines.append("")

    lines += ["### Checks", "", f"{c.new_checks} checks passed ({earlier}: {c.old_checks})."]
    return "\n".join(lines) + "\n"


def write_revisions(revisions: list[Revision], path: Path) -> None:
    """Every revision as CSV, largest first, with exact dollars for sorting and adding up."""
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([
            "government", "counted_as", "function_id", "function", "fiscal_year",
            "was", "now", "change", "change_percent", "status_was", "status_now",
        ])  # fmt: skip
        for r in revisions:
            change_percent = r.change_percent
            writer.writerow([
                r.government, r.view, r.function_id, r.function, year_label(r.fiscal_year),
                r.was, r.now, r.change,
                "" if change_percent is None else round(change_percent, 2),
                r.status_was or "", r.status_now or "",
            ])  # fmt: skip


# --- Command ----------------------------------------------------------------


def diff_builds(
    data_root: Path = DATA_ROOT, build_id: str | None = None, against: str | None = None
) -> int:
    """Compare a build (the newest by default) with another (the approved one by default).

    Prints the report and saves it, with every revision as CSV, in the build's
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
        write_revisions(comparison.revisions, folder / REVISIONS_FILE.format(other=old))
        print(text, end="")
        log.info(f"Saved in {folder}: {CHANGES_FILE.format(other=old)}, "
                 f"{REVISIONS_FILE.format(other=old)}")  # fmt: skip
        return 0
    except (DiffError, ApprovalError, duckdb.Error) as error:
        log.error(f"Nothing compared: {error}")
        return 1
    finally:
        stop_logging()
