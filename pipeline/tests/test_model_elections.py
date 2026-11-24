"""Tests for ridings, parties and election results, built from small made-up staged tables.

Two ridings stand in for the 343: Avalon (Newfoundland and Labrador), whose
name the boundary file repeats ("Avalon,Avalon"), and a Toronto riding renamed
since the election. The riding count check is told to expect two.
"""

from datetime import date

import duckdb
import pytest

from public_spend_tracker_pipeline.transform import model_elections
from public_spend_tracker_pipeline.transform.base import sql_table
from public_spend_tracker_pipeline.transform.model_elections import (
    ElectionCandidates,
    ElectionDistricts,
    Parties,
    Ridings,
)

OLD_RELEASE = date(2026, 11, 20)
RELEASE = date(2026, 11, 24)

BOUNDARIES = [
    ("10001", "Avalon,Avalon", "Avalon,Avalon"),
    ("35105", "Taiaiako'n—Parkdale—High Park", "Taiaiako'n—Parkdale—High Park"),
]
DISTRICTS = [
    # district_number, district_name, valid, rejected, total, elected_candidate
    ("10001", "Avalon", 44516, 389, 44905, "Connors, Paul Liberal/Libéral"),
    ("35105", "Parkdale--High Park/Parkdale--High Park", 60000, 300, 60300,
     "Taylor, Karim NDP-New Democratic Party/NPD-Nouveau Parti démocratique"),
]  # fmt: skip
CANDIDATES = [
    # district_number, candidate, votes, vote_share_pct, majority, majority_pct
    ("10001", "Paul Connors ** Liberal/Libéral", 27563, 61.9, 10610, 23.8),
    ("10001", "Steve Kent Conservative/Conservateur", 16953, 38.1, None, None),
    ("35105", "Karim Taylor NDP-New Democratic Party/NPD-Nouveau Parti démocratique",
     35000, 58.3, 10000, 16.6),
    ("35105", "Jo Smith Green Party/Parti Vert", 25000, 41.7, None, None),
]  # fmt: skip


def make_staged(db, districts=DISTRICTS, candidates=CANDIDATES):
    """The staged tables and jurisdictions, as the model step offers them.

    The boundary table also holds an older release with an old name, to show
    only the newest release is used.
    """
    old = [("10001", "Old Avalon", "Old Avalon")]
    boundaries = [(*row, OLD_RELEASE) for row in old] + [(*row, RELEASE) for row in BOUNDARIES]
    db.sql(f"""CREATE TABLE federal_electoral_districts AS
        {sql_table(["district_number", "name_en", "name_fr", "release"], boundaries)}""")
    db.sql(f"""CREATE TABLE jurisdictions AS
        {sql_table(["code"], [("ca",), ("nl",), ("on",)])}""")
    db.sql(f"""CREATE TABLE ge45_results_by_district AS
        SELECT *, 80000 AS population, 70000 AS electors, 200 AS voting_desks,
               64.1 AS turnout_pct, DATE '{RELEASE}' AS release
        FROM ({sql_table(["district_number", "district_name", "valid_ballots",
                          "rejected_ballots", "total_ballots", "elected_candidate"],
                         districts)})""")  # fmt: skip
    db.sql(f"""CREATE TABLE ge45_results_by_candidate AS
        SELECT *, 'Somewhere' AS residence, 'Someone' AS occupation,
               DATE '{RELEASE}' AS release
        FROM ({sql_table(["district_number", "candidate", "votes", "vote_share_pct",
                          "majority", "majority_pct"], candidates)})""")  # fmt: skip


def build(db):
    """Run the four transformers in order. Returns every failed check's name."""
    failed = []
    for transformer in (Ridings(), Parties(), ElectionDistricts(), ElectionCandidates()):
        transformer.transform(db).create(transformer.name)
        failed += [check.name for check in transformer.checks(db) if not check.passed]
    return failed


@pytest.fixture(autouse=True)
def two_ridings(monkeypatch):
    monkeypatch.setattr(model_elections, "RIDING_COUNT", 2)


def test_everything_passes_and_reads_well():
    db = duckdb.connect()
    make_staged(db)
    assert build(db) == []

    assert db.sql("SELECT code, name_en, jurisdiction, release FROM ridings").fetchall() == [
        ("10001", "Avalon", "nl", RELEASE),
        ("35105", "Taiaiako'n—Parkdale—High Park", "on", RELEASE),
    ]
    assert db.sql(
        "SELECT riding, name_at_election_en, name_at_election_fr, renamed FROM election_districts"
    ).fetchall() == [
        ("10001", "Avalon", "Avalon", False),
        ("35105", "Parkdale—High Park", "Parkdale—High Park", True),
    ]
    assert db.sql("SELECT candidate FROM election_candidates WHERE incumbent").fetchall() == [
        ("Paul Connors",)
    ]
    assert db.sql("""
        SELECT riding, candidate, party, elected, margin_votes, source_id
        FROM election_candidates ORDER BY riding, votes DESC
    """).fetchall() == [
        ("10001", "Paul Connors", "liberal", True, 10610, "elections-ge45_results_by_candidate"),
        ("10001", "Steve Kent", "conservative", False, None, "elections-ge45_results_by_candidate"),
        ("35105", "Karim Taylor", "ndp", True, 10000, "elections-ge45_results_by_candidate"),
        ("35105", "Jo Smith", "green", False, None, "elections-ge45_results_by_candidate"),
    ]  # fmt: skip


def test_parties_have_names_in_both_languages():
    db = duckdb.connect()
    Parties().transform(db).create("parties")
    assert db.sql(
        "SELECT name_en, name_fr, short_fr FROM parties WHERE code = 'ndp'"
    ).fetchall() == [("NDP-New Democratic Party", "NPD-Nouveau Parti démocratique", "NPD")]


def test_unknown_party_stops_the_build():
    db = duckdb.connect()
    candidates = [*CANDIDATES[:3], ("35105", "Jo Smith Brand New Party/Nouveau Parti", 25000,
                                    41.7, None, None)]  # fmt: skip
    make_staged(db, candidates=candidates)
    assert build(db) == ["election_candidates: every candidate's party is in settings.PARTIES"]


def test_two_winners_stop_the_build():
    db = duckdb.connect()
    candidates = [*CANDIDATES[:3], ("35105", "Jo Smith Green Party/Parti Vert", 25000, 41.7,
                                    1, 0.1)]  # fmt: skip
    make_staged(db, candidates=candidates)
    assert "election_candidates: each riding has exactly one winner" in build(db)


def test_votes_that_do_not_add_up_stop_the_build():
    db = duckdb.connect()
    districts = [DISTRICTS[0], ("35105", "Parkdale—High Park", 59999, 300, 60299,
                                DISTRICTS[1][5])]  # fmt: skip
    make_staged(db, districts=districts)
    assert build(db) == [
        "election_candidates: candidates' votes add up to the riding's valid ballots"
    ]


def test_winner_disagreeing_with_results_by_district_stops_the_build():
    db = duckdb.connect()
    districts = [DISTRICTS[0], (*DISTRICTS[1][:5], "Smith, Jo Green Party/Parti Vert")]
    make_staged(db, districts=districts)
    assert build(db) == ["election_candidates: each winner's party matches the results by district"]


def test_riding_missing_from_a_general_election_stops_the_build():
    db = duckdb.connect()
    make_staged(db, districts=DISTRICTS[:1], candidates=CANDIDATES[:2])
    assert build(db) == ["election_districts: every riding has results in each general election"]


def test_riding_in_an_unknown_province_stops_the_build():
    db = duckdb.connect()
    make_staged(db)
    db.sql("UPDATE federal_electoral_districts SET district_number = '99001' "
           "WHERE district_number = '10001'")  # fmt: skip
    failed = build(db)
    assert "ridings: no missing name_en, name_fr, jurisdiction" in failed


def test_dash_and_apostrophe_styles_are_not_renames():
    db = duckdb.connect()
    make_staged(db)
    db.sql("""UPDATE federal_electoral_districts SET name_en = 'Mégantic—L’Érable'
              WHERE district_number = '35105'""")
    db.sql("""UPDATE ge45_results_by_district SET district_name = 'Mégantic-L''Érable'
              WHERE district_number = '35105'""")
    assert build(db) == []
    assert db.sql("SELECT bool_or(renamed) FROM election_districts").fetchall() == [(False,)]


def test_a_name_with_a_real_comma_stops_the_build():
    db = duckdb.connect()
    make_staged(db)
    db.sql("""UPDATE federal_electoral_districts SET name_en = 'Avalon, North'
              WHERE district_number = '10001'""")
    assert "ridings: no name has a comma (a repeated name not tidied)" in build(db)
