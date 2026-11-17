"""Tests for the transformer base class and shared checks.

They run on an in-memory DuckDB database with small made-up tables, so no
files are read or written.
"""

import duckdb
import pytest

from public_spend_tracker_pipeline.common.paths import MODEL
from public_spend_tracker_pipeline.transform.base import (
    Transformer,
    expect_no_rows,
    has_rows,
    no_duplicate_keys,
    no_missing_values,
)


@pytest.fixture
def db() -> duckdb.DuckDBPyConnection:
    """An empty in-memory database for each test."""
    return duckdb.connect()


def make_governments(db: duckdb.DuckDBPyConnection, rows: str) -> None:
    """Create a small "governments" table from SQL VALUES rows."""
    db.sql(f"CREATE TABLE governments AS SELECT * FROM (VALUES {rows}) AS t(code, name_fr)")


class Governments(Transformer):
    """A small example transformer, written the way real ones will be."""

    name = "governments"
    description = "Every government we cover, with English and French names"
    stage = MODEL
    inputs = ("cofog_consolidated",)

    def transform(self, db):
        return db.sql("""
            SELECT DISTINCT geo_code AS code, geo_en AS name_en, geo_fr AS name_fr
            FROM cofog_consolidated
        """)

    def checks(self, db):
        return [
            has_rows(db, self.name),
            no_duplicate_keys(db, self.name, ["code"]),
            no_missing_values(db, self.name, ["name_en", "name_fr"]),
        ]


def test_transformer_without_transform_cannot_be_created():
    class Unfinished(Transformer):
        name = "unfinished"
        description = "Forgot to write transform()"
        stage = MODEL

    with pytest.raises(TypeError):
        Unfinished()


def test_example_transformer_runs_end_to_end(db):
    db.sql("""
        CREATE TABLE cofog_consolidated AS SELECT * FROM (VALUES
            ('on', 'Ontario', 'Ontario', 2023),
            ('on', 'Ontario', 'Ontario', 2024),
            ('qc', 'Quebec', 'Québec', 2024)
        ) AS t(geo_code, geo_en, geo_fr, year)
    """)
    transformer = Governments()

    # What the runner will do: save the result under the dataset's name, then check it.
    transformer.transform(db).create(transformer.name)
    results = transformer.checks(db)

    assert all(result.passed for result in results), results
    assert db.sql("SELECT code FROM governments ORDER BY code").fetchall() == [("on",), ("qc",)]


def test_expect_no_rows_passes_when_nothing_is_found(db):
    make_governments(db, "('on', 'Ontario')")
    result = expect_no_rows(db, "no Nunavut", "SELECT * FROM governments WHERE code = 'nu'")
    assert result.passed
    assert result.detail == "no bad rows"


def test_expect_no_rows_fails_and_shows_bad_rows(db):
    make_governments(db, "('on', 'Ontario'), ('qc', 'Québec')")
    result = expect_no_rows(db, "no Quebec", "SELECT * FROM governments WHERE code = 'qc'")
    assert not result.passed
    assert result.detail == "1 bad row, first: ('qc', 'Québec')"


def test_no_duplicate_keys(db):
    make_governments(db, "('on', 'Ontario'), ('on', 'Ontario'), ('qc', 'Québec')")
    result = no_duplicate_keys(db, "governments", ["code"])
    assert not result.passed
    assert result.name == "governments: no duplicate code"
    assert "('on', 2)" in result.detail  # the key and how many times it appears

    db.sql("DELETE FROM governments WHERE code = 'on'")
    assert no_duplicate_keys(db, "governments", ["code"]).passed


@pytest.mark.parametrize("missing_label", ["NULL", "''", "'   '"])
def test_no_missing_values_catches_null_and_blank(db, missing_label):
    make_governments(db, f"('on', 'Ontario'), ('qc', {missing_label})")
    result = no_missing_values(db, "governments", ["name_fr"])
    assert not result.passed
    assert result.detail.startswith("1 bad row,")


def test_no_missing_values_passes_when_filled_in(db):
    make_governments(db, "('on', 'Ontario'), ('qc', 'Québec')")
    assert no_missing_values(db, "governments", ["code", "name_fr"]).passed


def test_has_rows(db):
    db.sql("CREATE TABLE governments (code VARCHAR, name_fr VARCHAR)")
    assert not has_rows(db, "governments").passed

    db.sql("INSERT INTO governments VALUES ('on', 'Ontario')")
    result = has_rows(db, "governments")
    assert result.passed
    assert result.detail == "1 row"
