"""Tests for comparing two builds table by table (release/compare.py).

They use a made-up "prices" dataset with its own layout, in two in-memory
databases attached as "new" and "old", so they show the comparison works for
any dataset, not just the ones we have today.
"""

import duckdb
import pytest

from public_spend_tracker_pipeline.build.run import model_transformers
from public_spend_tracker_pipeline.release.compare import (
    ADDED,
    IN_BOTH,
    NEW_ONLY,
    OLD_ONLY,
    REMOVED,
    REVISED,
    compare_tables,
    label_name,
    tables_without_layout,
)
from public_spend_tracker_pipeline.transform.base import DECIMAL, WHOLE, Layout, sql_table

PLACES = Layout(keys=("code",), tracked=("name_en",))
PRICES = Layout(
    keys=("place", "year"),
    values={"index": DECIMAL, "dollars": WHOLE},
    tracked=("status",),
    ignored=("release",),
    labels={"place": "places"},
)
LAYOUTS = [("places", PLACES), ("prices", PRICES)]
PRICE_COLUMNS = ["place", "year", "index", "dollars", "status", "release"]


def builds(old_prices, new_prices, old_places=None, new_places=None):
    """A database with two builds attached, "old" and "new", holding the given rows."""
    db = duckdb.connect()
    for alias, prices, places in (
        ("old", old_prices, old_places or [("on", "Ontario")]),
        ("new", new_prices, new_places or [("on", "Ontario")]),
    ):
        db.sql(f"ATTACH ':memory:' AS {alias}")
        db.sql(f"CREATE TABLE {alias}.places AS {sql_table(['code', 'name_en'], places)}")
        if prices is not None:
            db.sql(f"CREATE TABLE {alias}.prices AS {sql_table(PRICE_COLUMNS, prices)}")
    return db


def prices_changes(db):
    return next(t for t in compare_tables(db, LAYOUTS) if t.table == "prices")


def test_unchanged_builds_have_no_changes():
    rows = [("on", 2024, 150.0, 1_000, "final", "2026-01-01")]
    changes = compare_tables(builds(rows, rows), LAYOUTS)
    assert [(t.table, t.found_in, t.has_changes) for t in changes] == [
        ("places", IN_BOTH, False),
        ("prices", IN_BOTH, False),
    ]


def test_each_kind_of_change_is_one_line_with_names_next_to_codes():
    old = [
        ("on", 2023, 150.0, 1_000, "final", "2026-01-01"),
        ("on", 2024, 152.0, 2_000, "preliminary", "2026-01-01"),
    ]
    new = [
        ("on", 2024, 153.0, 2_500, "revised", "2026-11-01"),  # release alone is ignored
        ("on", 2025, 155.0, 3_000, "preliminary", "2026-11-01"),
    ]
    changes = prices_changes(builds(old, new))

    assert changes.header == (
        "what", "place", "year", label_name("place"), "column", "was", "now", "change",
        "change_percent",
    )  # fmt: skip
    assert [line[:5] + line[5:7] for line in changes.lines] == [
        (REMOVED, "on", 2023, "Ontario", "dollars", "1000", None),
        (REMOVED, "on", 2023, "Ontario", "index", "150.0", None),
        (REVISED, "on", 2024, "Ontario", "dollars", "2000", "2500"),
        (REVISED, "on", 2024, "Ontario", "index", "152.0", "153.0"),
        (REVISED, "on", 2024, "Ontario", "status", "preliminary", "revised"),
        (ADDED, "on", 2025, "Ontario", "dollars", None, "3000"),
        (ADDED, "on", 2025, "Ontario", "index", None, "155.0"),
    ]
    dollars = changes.lines[2]
    assert (changes.field(dollars, "change"), changes.field(dollars, "change_percent")) == (
        500.0,
        25.0,
    )
    assert (changes.rows_added, changes.rows_removed) == (1, 1)
    assert (changes.values_revised, changes.tracked_changed) == (2, 1)
    assert changes.needs_attention  # a row is gone


def test_rounding_noise_is_ignored_for_decimals_but_not_whole_numbers():
    old = [("on", 2024, 150.0, 1_000, "final", "2026-01-01")]
    new = [("on", 2024, 150.0 + 1e-12, 1_001, "final", "2026-01-01")]
    changes = prices_changes(builds(old, new))
    assert [changes.field(line, "column") for line in changes.lines] == ["dollars"]


def test_a_value_that_appears_or_disappears_is_revised():
    old = [("on", 2024, None, 1_000, "final", "2026-01-01")]
    new = [("on", 2024, 150.0, None, "final", "2026-01-01")]
    changes = prices_changes(builds(old, new))
    assert sorted(changes.field(line, "column") for line in changes.lines) == ["dollars", "index"]


def test_a_dataset_without_values_lists_rows_added_and_removed():
    changes = compare_tables(
        builds(None, None, old_places=[("on", "Ontario")], new_places=[("qc", "Quebec")]),
        LAYOUTS,
    )[0]
    assert [(line[0], line[1]) for line in changes.lines] == [(REMOVED, "on"), (ADDED, "qc")]


def test_a_new_dataset_counts_its_rows_without_listing_them():
    rows = [("on", 2024, 150.0, 1_000, "final", "2026-01-01")]
    changes = prices_changes(builds(None, rows))
    assert (changes.found_in, changes.rows_added, changes.lines) == (NEW_ONLY, 1, ())
    assert not changes.needs_attention


def test_a_dataset_gone_from_the_new_build_needs_attention():
    rows = [("on", 2024, 150.0, 1_000, "final", "2026-01-01")]
    changes = prices_changes(builds(rows, None))
    assert changes.found_in == OLD_ONLY
    assert changes.needs_attention


def test_columns_added_or_removed_are_noted_and_missing_keys_stop_the_comparison():
    rows = [("on", 2024, 150.0, 1_000, "final", "2026-01-01")]
    db = builds(rows, rows)
    db.sql("ALTER TABLE new.prices ADD COLUMN note VARCHAR")
    db.sql("ALTER TABLE new.prices DROP COLUMN status")
    changes = prices_changes(db)
    assert (changes.columns_added, changes.columns_removed) == (("note",), ("status",))
    assert changes.needs_attention

    db.sql("ALTER TABLE new.prices DROP COLUMN year")
    assert prices_changes(db).problem == "key columns missing: year"


def test_tables_without_a_layout_are_found_with_where_they_are():
    rows = [("on", 2024, 150.0, 1_000, "final", "2026-01-01")]
    db = builds(rows, rows)
    db.sql("CREATE TABLE new.build_info AS SELECT 1 AS x")
    db.sql("CREATE TABLE old.build_info AS SELECT 1 AS x")
    db.sql("CREATE TABLE old.retired AS SELECT 1 AS x")
    assert tables_without_layout(db, LAYOUTS) == {"build_info": IN_BOTH, "retired": OLD_ONLY}


@pytest.mark.parametrize("transformer", model_transformers({}), ids=lambda t: t.name)
def test_every_model_dataset_has_a_layout_whose_labels_name_model_datasets(transformer):
    model_datasets = {t.name for t in model_transformers({})}
    assert transformer.layout is not None
    assert transformer.layout.keys
    assert set(transformer.layout.labels.values()) <= model_datasets
