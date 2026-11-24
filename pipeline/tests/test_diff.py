"""Tests for "pst diff": comparing two builds and reporting what changed.

Each test makes two tiny builds with known differences:

    OLD  fiscal years 2023-24 and 2024-25, Statistics Canada release 2025-11-27
    NEW  the same, plus 2025-26, release 2026-11-26; Ontario's 2024-25 health
         spending and its hospital sub-function revised up; Quebec's health
         spending revised down; Ontario's 2024 CPI revised (fiscal and calendar)
"""

import csv
import json
from datetime import date

import duckdb
import pytest

from public_spend_tracker_pipeline.common.paths import (
    BUILD_MANIFEST_FILE_NAME,
    DATABASE_FILE_NAME,
    current_build_file,
    serving_build_folder,
)
from public_spend_tracker_pipeline.release.approve import approve
from public_spend_tracker_pipeline.release.diff import (
    DiffError,
    compare_builds,
    diff_builds,
    money,
    plain_number,
    report,
    year_label,
)
from public_spend_tracker_pipeline.transform.base import sql_table

OLD = "20261116-164845"
NEW = "20261126-153000"
BILLION = 1_000_000_000

JURISDICTIONS = [("ca", "Canada", 1), ("qc", "Quebec", 6), ("on", "Ontario", 7)]
FUNCTIONS = [("701", 1, "General public services"), ("707", 1, "Health"),
             ("7073", 2, "Hospital services")]  # fmt: skip


def spending_rows(years, changes=None, leave_out=()):
    """Spending for every view, place and function: 10 billion each, unless changed."""
    places = {"canada": ["ca"], "federal": ["ca"], "province_wide": ["ca", "qc", "on"]}
    rows = []
    for view, codes in places.items():
        for code in codes:
            for function_id, *_ in FUNCTIONS:
                for year in years:
                    key = (view, code, function_id, year)
                    if key in leave_out:
                        continue
                    amount = (changes or {}).get(key, 10 * BILLION)
                    status = "preliminary" if year == max(years) else "revised"
                    rows.append((*key, amount, status))
    return rows


def make_build(
    data_root, build_id, years, release, spending, cpi_2024=110.0, checks=3, municipal_2024=None
):
    folder = serving_build_folder(build_id, data_root)
    folder.mkdir(parents=True)
    db = duckdb.connect(str(folder / DATABASE_FILE_NAME))

    def create(name, columns, rows):
        db.sql(f"CREATE TABLE {name} AS {sql_table(columns, rows)}")

    create("jurisdictions", ["code", "name_en", "sort_order"], JURISDICTIONS)
    create("functions", ["function_id", "level", "name_en"], FUNCTIONS)
    create("spending",
        ["view", "jurisdiction", "function_id", "fiscal_year", "amount", "revision_status"],
        spending)  # fmt: skip
    create("municipal_transfers", ["jurisdiction", "fiscal_year", "amount"],
           [("on", year, municipal_2024 if year == 2024 and municipal_2024 else 5 * BILLION)
            for year in years])  # fmt: skip
    create("context", ["jurisdiction", "series", "basis", "year", "value"],
        [("on", "cpi", basis, 2024, cpi_2024) for basis in ("calendar", "fiscal")]
        + [("on", "population", "calendar", 2024, 16_000_000.0)])  # fmt: skip
    create("sources", ["source_id", "table_number", "title_en", "release"],
           [("statcan-10100005", "10-10-0005-01", "Government finance", release)])  # fmt: skip
    db.close()
    manifest = {"datasets": [{"checks": [{}] * checks}], "serving": {"checks": [{}]}}
    (folder / BUILD_MANIFEST_FILE_NAME).write_text(json.dumps(manifest), encoding="utf-8")


HEALTH_ON = ("province_wide", "on", "707", 2024)
HOSPITALS_ON = ("province_wide", "on", "7073", 2024)
HEALTH_QC = ("province_wide", "qc", "707", 2024)


@pytest.fixture
def data_root(tmp_path):
    make_build(tmp_path, OLD, [2023, 2024], date(2025, 11, 27), spending_rows([2023, 2024]))
    revised = {HEALTH_ON: 12 * BILLION, HOSPITALS_ON: 11 * BILLION, HEALTH_QC: 9_500_000_000}
    make_build(
        tmp_path, NEW, [2023, 2024, 2025], date(2026, 11, 26),
        spending_rows([2023, 2024, 2025], revised), cpi_2024=111.0, checks=4,
    )  # fmt: skip
    return tmp_path


def test_revisions_are_found_largest_first(data_root):
    comparison = compare_builds(NEW, OLD, data_root)
    assert [(r.government, r.function, r.change) for r in comparison.revisions] == [
        ("Ontario", "Health", 2 * BILLION),
        ("Ontario", "Hospital services", 1 * BILLION),
        ("Quebec", "Health", -500_000_000),
    ]
    assert comparison.revisions[0].change_percent == pytest.approx(20.0)


def test_revisions_by_government_count_every_figure_but_net_only_functions(data_root):
    by_government = compare_builds(NEW, OLD, data_root).by_government
    assert [(g.government, g.figures, g.net_change) for g in by_government] == [
        ("Quebec", 1, -500_000_000),
        ("Ontario", 2, 2 * BILLION),  # hospitals are part of health, so not added again
    ]


def test_new_years_releases_and_totals_are_reported(data_root):
    comparison = compare_builds(NEW, OLD, data_root)
    assert comparison.old_years == (2023, 2024)
    assert comparison.new_years == (2023, 2025)
    spending = comparison.table("spending")
    assert spending.rows_added == 15  # 5 view-place pairs x 3 functions, for 2025-26
    assert spending.rows_removed == 0
    assert [(r.table_number, r.was, r.now) for r in comparison.new_releases] == [
        ("10-10-0005-01", "2025-11-27", "2026-11-26")
    ]
    provinces_2024 = next(
        t for t in comparison.totals
        if t.government == "All provinces and territories" and t.fiscal_year == 2024
    )  # fmt: skip
    assert (provinces_2024.was, provinces_2024.now) == (20 * BILLION, 20 * BILLION)
    added_year = [t for t in comparison.totals if t.fiscal_year == 2025]
    assert all(t.was is None and t.now == 20 * BILLION for t in added_year)


def test_every_dataset_is_compared_by_its_layout(data_root):
    comparison = compare_builds(NEW, OLD, data_root)
    summary = {
        t.table: (t.rows_added, t.rows_removed, t.values_revised, t.tracked_changed)
        for t in comparison.tables
    }
    assert summary == {
        "jurisdictions": (0, 0, 0, 0),
        "functions": (0, 0, 0, 0),
        "spending": (15, 0, 3, 15),  # 15 figures went from preliminary to revised
        "municipal_transfers": (1, 0, 0, 0),  # 2025-26 added
        "context": (0, 0, 2, 0),  # Ontario's 2024 CPI, fiscal and calendar
        "sources": (0, 0, 0, 1),  # the new release
    }
    assert (comparison.old_checks, comparison.new_checks) == (4, 5)


def test_vanished_figures_need_attention(tmp_path):
    years = [2023, 2024]
    make_build(tmp_path, OLD, years, date(2025, 11, 27), spending_rows(years))
    make_build(tmp_path, NEW, years, date(2025, 11, 27),
               spending_rows(years, leave_out={HEALTH_QC}))  # fmt: skip
    comparison = compare_builds(NEW, OLD, tmp_path)
    assert comparison.table("spending").rows_removed == 1
    text = report(comparison)
    assert (
        "- **spending**: 1 row in the approved build missing from the new build:\n"
        "  - province_wide, Quebec, Health, 2024-25\n"
    ) in text
    assert text.index("Needs attention") < text.index("Revised spending")


def test_an_unfinished_build_cannot_be_compared(data_root):
    (serving_build_folder(NEW, data_root) / BUILD_MANIFEST_FILE_NAME).unlink()
    with pytest.raises(DiffError, match="not complete"):
        compare_builds(NEW, OLD, data_root)


def test_the_report_reads_as_markdown(data_root):
    text = report(compare_builds(NEW, OLD, data_root))
    assert text.startswith(f"## What changed: build {NEW} compared with approved build {OLD}")
    assert "2023-24 to 2024-25 -> **2023-24 to 2025-26** (15 new spending figures)." in text
    assert (
        "| Ontario | Province-wide | Health | 2024-25 | $10.0B | $12.0B | +$2.0B (+20.0%) |" in text
    )
    assert f"Every change is listed in `changes-vs-{OLD}/<dataset>.csv`" in text
    assert "| spending | 15 | 0 | 3 | 15 in revision_status |" in text
    assert "No changes: jurisdictions, functions." in text
    assert "Values revised: Population: 0; Prices (CPI): 2; GDP: 0." in text


def test_diff_compares_the_newest_build_with_the_approved_one_and_saves_every_change(
    data_root, capsys
):
    approve(OLD, data_root)
    assert diff_builds(data_root) == 0
    printed = capsys.readouterr().out
    assert printed.startswith(f"## What changed: build {NEW} compared with approved build {OLD}")

    folder = serving_build_folder(NEW, data_root)
    assert (folder / f"changes-vs-{OLD}.md").read_text(encoding="utf-8") == printed
    changes = folder / f"changes-vs-{OLD}"
    assert sorted(path.name for path in changes.iterdir()) == [
        "context.csv", "municipal_transfers.csv", "sources.csv", "spending.csv",
    ]  # fmt: skip
    with (changes / "spending.csv").open(encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 3 + 15 + 15  # amounts revised, statuses changed, figures added
    assert rows[0] == {
        "what": "revised", "view": "province_wide", "jurisdiction": "on", "function_id": "707",
        "fiscal_year": "2024", "jurisdiction_name": "Ontario", "function_name": "Health",
        "column": "amount", "was": str(10 * BILLION), "now": str(12 * BILLION),
        "change": str(2 * BILLION), "change_percent": "20.0",
    }  # fmt: skip
    assert {row["what"] for row in rows} == {"revised", "added"}


def test_comparing_with_a_build_that_is_not_approved_says_so(data_root, capsys):
    assert diff_builds(data_root, NEW, against=OLD) == 0
    assert f"compared with build {OLD}" in capsys.readouterr().out


def test_nothing_to_compare_without_an_approval_or_with_the_approved_build(data_root, capsys):
    assert diff_builds(data_root) == 0
    assert "No build is approved yet" in capsys.readouterr().out
    assert not list(serving_build_folder(NEW, data_root).glob("changes-*"))

    approve(NEW, data_root)
    assert current_build_file(data_root).is_file()
    assert diff_builds(data_root) == 0
    assert "is the approved build: nothing to compare" in capsys.readouterr().out


def test_money_and_years_are_written_plainly():
    assert money(1_137_100_000_000) == "$1,137.1B"
    assert money(350_000_000) == "$350M"
    assert money(-500_000_000, signed=True) == "-$500M"
    assert money(2 * BILLION, signed=True) == "+$2.0B"
    assert money(None) == "no figure"
    assert year_label(2024) == "2024-25"
    assert year_label(2099) == "2099-00"


def test_rounding_noise_in_decimals_is_not_a_revision_but_any_dollar_is(tmp_path):
    years = [2023, 2024]
    make_build(tmp_path, OLD, years, date(2025, 11, 27), spending_rows(years), cpi_2024=110.0)
    make_build(
        tmp_path, NEW, years, date(2025, 11, 27), spending_rows(years),
        cpi_2024=110.0 + 1e-13, municipal_2024=5 * BILLION + 1,
    )  # fmt: skip
    comparison = compare_builds(NEW, OLD, tmp_path)
    assert comparison.table("context").values_revised == 0
    assert comparison.table("municipal_transfers").values_revised == 1
    assert "| Ontario, 2024-25 | amount | 5,000,000,000 | 5,000,000,001 | +1 (+0.0%) |" in report(
        comparison
    )


def test_numbers_are_written_plainly():
    assert plain_number("18410000000") == "18,410,000,000"
    assert plain_number("132.2") == "132.2"
    assert plain_number(0.04166666, signed=True) == "+0.0417"
    assert plain_number(-466000000.0, signed=True) == "-466,000,000"
    assert plain_number(None) == ""
