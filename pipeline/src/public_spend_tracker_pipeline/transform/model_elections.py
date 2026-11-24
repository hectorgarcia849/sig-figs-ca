"""Ridings, parties and federal election results, ready for the riding map.

Four datasets:

    ridings              The 343 federal ridings: number, current English and
                         French names, and province or territory.
    parties              Every party a candidate stood for, from
                         settings.PARTIES, with full and short names.
    election_districts   One row per riding per election: the riding's name on
                         election day, electors, ballots and turnout.
    election_candidates  One row per candidate per election: name, party,
                         votes, share of the vote, and whether they won (with
                         the winner's lead over the runner-up).

Ridings are identified by their number everywhere ("35105"), never by name:
names change (an act of Parliament renamed several in 2026), numbers do not.
So a riding's current name is in ridings, and its name on election day is in
election_districts.

Results are keyed by election (settings.ELECTIONS), so by-elections can be added
as more rows. Each dataset uses the newest release of its staged inputs.

The checks tie the two results tables to each other and to the boundaries, so
a mismatch between Elections Canada's files stops the build instead of
reaching the map.
"""

from __future__ import annotations

import duckdb

from public_spend_tracker_pipeline.common.paths import MODEL
from public_spend_tracker_pipeline.common.settings import (
    ELECTIONS,
    JURISDICTION_BY_GEOGRAPHIC_CODE,
    PARTIES,
    RIDING_BOUNDARIES_DATASET,
    RIDING_COUNT,
)
from public_spend_tracker_pipeline.transform.base import (
    DECIMAL,
    WHOLE,
    CheckResult,
    Layout,
    Transformer,
    expect_no_rows,
    no_duplicate_keys,
    no_missing_values,
    sql_table,
    sql_text,
)
from public_spend_tracker_pipeline.transform.staged_elections import source_id
from public_spend_tracker_pipeline.transform.statcan_sql import latest_release

# How far a riding's published vote shares may add up from 100%. Each share is
# rounded to one decimal, so with a dozen candidates the rounding alone can
# reach about 0.6 points.
VOTE_SHARE_TOLERANCE = 1.0

# How many digits of a riding's number give its province or territory.
GEOGRAPHIC_CODE_DIGITS = 2

# What Elections Canada puts after a candidate's name when they were the
# riding's MP going into the election ("** Incumbent" in their legend).
INCUMBENT_MARK = " **"

# The results tables write a riding's name with "--" for each dash, and both
# languages in one: "Acadie--Annapolis", "Central Nova/Nova-Centre". The
# boundary file uses a real dash (—) and has a column per language.
RESULTS_DASH = "--"
NAME_DASH = "—"
LANGUAGE_SEPARATOR = "/"

# November 2026: the boundary file has a few names repeated, joined by commas
# and cut off at 100 characters, e.g. "Halifax,Halifax". No riding name has a
# comma, so a name whose comma-separated parts all repeat the first is that
# first part. Any other comma stops the build (see Ridings.checks).
REPEAT_SEPARATOR = ","


def _first_of_repeated(column: str) -> str:
    """SQL for a name with any repeats removed: "Halifax,Halifax" -> "Halifax".

    Only when every part repeats the first (the last may be cut short);
    otherwise the name is kept as it is.
    """
    parts = f"string_split({column}, '{REPEAT_SEPARATOR}')"
    return f"""CASE
        WHEN list_bool_and(list_transform({parts}, lambda part: starts_with({parts}[1], part)))
        THEN {parts}[1] ELSE {column} END"""


def _comparable(column: str) -> str:
    """SQL for a name ready to compare: every kind of dash and apostrophe made the same.

    The two Elections Canada files differ in such details ("L’Érable" and
    "L'Érable"), which are not renames.
    """
    return f"translate({column}, '—–’', '--''')"


DISTRICTS_DATASETS = tuple(election.districts_dataset for election in ELECTIONS)
CANDIDATES_DATASETS = tuple(election.candidates_dataset for election in ELECTIONS)


class Ridings(Transformer):
    """The federal ridings, from the newest boundary file."""

    name = "ridings"
    description = "The 343 federal ridings, with English and French names and province"
    stage = MODEL
    inputs = (RIDING_BOUNDARIES_DATASET, "jurisdictions")
    layout = Layout(
        keys=("code",),
        tracked=("name_en", "name_fr", "jurisdiction"),
        ignored=("source_id", "release"),
    )

    def transform(self, db: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyRelation:
        """Each riding with the jurisdiction its number's first two digits point to."""
        provinces = sql_table(["geographic_code", "jurisdiction"],
                              JURISDICTION_BY_GEOGRAPHIC_CODE.items())  # fmt: skip
        return db.sql(f"""
            SELECT
                b.district_number AS code,
                {_first_of_repeated("b.name_en")} AS name_en,
                {_first_of_repeated("b.name_fr")} AS name_fr,
                p.jurisdiction,
                {sql_text(source_id(RIDING_BOUNDARIES_DATASET))} AS source_id,
                b.release
            FROM {RIDING_BOUNDARIES_DATASET} AS b
            LEFT JOIN ({provinces}) AS p
                ON p.geographic_code = left(b.district_number, {GEOGRAPHIC_CODE_DIGITS})
            WHERE b.release = {latest_release(RIDING_BOUNDARIES_DATASET)}
            ORDER BY code
        """)

    def checks(self, db: duckdb.DuckDBPyConnection) -> list[CheckResult]:
        """One row per riding, the expected number of them, names and a known province."""
        return [
            no_duplicate_keys(db, self.name, self.layout.keys),
            no_missing_values(db, self.name, ["name_en", "name_fr", "jurisdiction"]),
            expect_no_rows(
                db,
                f"{self.name}: there are {RIDING_COUNT} ridings",
                f"SELECT count(*) AS ridings FROM {self.name} HAVING count(*) <> {RIDING_COUNT}",
            ),
            expect_no_rows(
                db,
                f"{self.name}: every jurisdiction is one we cover",
                f"""SELECT * FROM {self.name}
                    WHERE jurisdiction NOT IN (SELECT code FROM jurisdictions)""",
            ),
            expect_no_rows(
                db,
                f"{self.name}: no name has a comma (a repeated name not tidied)",
                f"""SELECT code, name_en, name_fr FROM {self.name}
                    WHERE contains(name_en, '{REPEAT_SEPARATOR}')
                       OR contains(name_fr, '{REPEAT_SEPARATOR}')""",
            ),
        ]


class Parties(Transformer):
    """Every party in settings.PARTIES, in the order listed there."""

    name = "parties"
    description = "Parties candidates stood for, with full and short English and French names"
    stage = MODEL
    layout = Layout(
        keys=("code",),
        tracked=("name_en", "name_fr", "short_en", "short_fr", "label", "sort_order"),
    )

    def transform(self, db: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyRelation:
        rows = [
            (p.code, p.name_en, p.name_fr, p.short_en, p.short_fr, p.label, order)
            for order, p in enumerate(PARTIES, start=1)
        ]
        return db.sql(sql_table(self.layout.columns, rows))

    def checks(self, db: duckdb.DuckDBPyConnection) -> list[CheckResult]:
        """Codes and labels are unique, and every name is filled in."""
        return [
            no_duplicate_keys(db, self.name, self.layout.keys),
            no_duplicate_keys(db, self.name, ["label"]),
            no_missing_values(db, self.name, ["name_en", "name_fr", "short_en", "short_fr"]),
        ]


class ElectionDistricts(Transformer):
    """Each riding's turnout in each election, from the results-by-district tables.

    name_at_election_en and _fr are the riding's name on election day, written
    the way the boundary file writes names. renamed says whether that differs
    from the riding's current name, ignoring dash and apostrophe styles.
    """

    name = "election_districts"
    description = "Electors, ballots and turnout in each riding at each federal election"
    stage = MODEL
    inputs = (*DISTRICTS_DATASETS, "ridings")
    layout = Layout(
        keys=("election", "riding"),
        values={
            "population": WHOLE, "electors": WHOLE, "voting_desks": WHOLE,
            "valid_ballots": WHOLE, "rejected_ballots": WHOLE, "total_ballots": WHOLE,
            "turnout_pct": DECIMAL,
        },
        tracked=("name_at_election_en", "name_at_election_fr", "renamed"),
        ignored=("source_id", "release"),
        labels={"riding": "ridings"},
    )  # fmt: skip

    def transform(self, db: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyRelation:
        """One block per election, stacked, with each riding's name then and now."""
        published = f"replace(district_name, '{RESULTS_DASH}', '{NAME_DASH}')"
        blocks = [
            f"""SELECT
                    {sql_text(election.code)} AS election,
                    district_number AS riding,
                    split_part({published}, '{LANGUAGE_SEPARATOR}', 1) AS name_at_election_en,
                    CASE WHEN contains({published}, '{LANGUAGE_SEPARATOR}')
                         THEN split_part({published}, '{LANGUAGE_SEPARATOR}', 2)
                         ELSE {published} END AS name_at_election_fr,
                    population, electors, voting_desks,
                    valid_ballots, rejected_ballots, total_ballots, turnout_pct,
                    {sql_text(source_id(election.districts_dataset))} AS source_id,
                    release
                FROM {election.districts_dataset}
                WHERE release = {latest_release(election.districts_dataset)}"""
            for election in ELECTIONS
        ]
        return db.sql(f"""
            SELECT d.*,
                {_comparable("d.name_at_election_en")} <> {_comparable("r.name_en")}
                    AS renamed
            FROM ({" UNION ALL ".join(blocks)}) AS d
            LEFT JOIN ridings AS r ON r.code = d.riding
            ORDER BY election, riding
        """)

    def checks(self, db: duckdb.DuckDBPyConnection) -> list[CheckResult]:
        """Every riding is real, every riding voted in a general election, ballots add up."""
        general = ", ".join(sql_text(e.code) for e in ELECTIONS if e.general) or "NULL"
        return [
            no_duplicate_keys(db, self.name, self.layout.keys),
            expect_no_rows(
                db,
                f"{self.name}: every riding is in ridings",
                f"SELECT * FROM {self.name} WHERE riding NOT IN (SELECT code FROM ridings)",
            ),
            expect_no_rows(
                db,
                f"{self.name}: every riding has results in each general election",
                f"""SELECT e.election, r.code AS riding
                    FROM ridings AS r
                    CROSS JOIN (SELECT unnest([{general}]) AS election) AS e
                    WHERE NOT EXISTS (
                        SELECT 1 FROM {self.name} AS d
                        WHERE d.election = e.election AND d.riding = r.code
                    )""",
            ),
            expect_no_rows(
                db,
                f"{self.name}: valid and rejected ballots add up to all ballots",
                f"""SELECT * FROM {self.name}
                    WHERE valid_ballots + rejected_ballots <> total_ballots""",
            ),
        ]


class ElectionCandidates(Transformer):
    """Every candidate's result, with their party split off their name.

    Elections Canada writes each candidate as their name followed by their
    party's label: "Paul Connors Liberal/Libéral". The party is the one in
    settings.PARTIES whose label the text ends with; the name is what is left.
    """

    name = "election_candidates"
    description = "Votes for every candidate in each riding at each federal election"
    stage = MODEL
    inputs = (*CANDIDATES_DATASETS, *DISTRICTS_DATASETS, "parties", "election_districts")
    layout = Layout(
        keys=("election", "riding", "candidate"),
        values={
            "votes": WHOLE, "vote_share_pct": DECIMAL,
            "margin_votes": WHOLE, "margin_pct": DECIMAL,
        },
        tracked=("party", "elected", "incumbent", "residence", "occupation"),
        ignored=("source_id", "release"),
        labels={"riding": "ridings"},
    )  # fmt: skip

    def transform(self, db: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyRelation:
        """Stack every election's candidates, then match each to its party.

        The winner is the one row with a "majority" (their lead over the
        runner-up); Elections Canada leaves it blank for everyone else. The
        riding's MP going into the election has INCUMBENT_MARK after their
        name, which becomes the incumbent column.
        """
        blocks = [
            f"""SELECT
                    {sql_text(election.code)} AS election, *,
                    {sql_text(source_id(election.candidates_dataset))} AS source_id
                FROM {election.candidates_dataset}
                WHERE release = {latest_release(election.candidates_dataset)}"""
            for election in ELECTIONS
        ]
        mark = sql_text(INCUMBENT_MARK)
        return db.sql(f"""
            WITH published AS ({" UNION ALL ".join(blocks)}),
            matched AS (
                SELECT
                    c.*,
                    p.code AS party,
                    -- Without a recognised party the published text is kept
                    -- whole, and the check on party shows it.
                    CASE WHEN p.code IS NULL THEN c.candidate
                         ELSE rtrim(left(c.candidate, length(c.candidate) - length(p.label)))
                    END AS name_and_mark
                FROM published AS c
                LEFT JOIN parties AS p ON ends_with(c.candidate, ' ' || p.label)
            )
            SELECT
                election,
                district_number AS riding,
                CASE WHEN ends_with(name_and_mark, {mark})
                     THEN rtrim(left(name_and_mark, length(name_and_mark) - length({mark})))
                     ELSE name_and_mark
                END AS candidate,
                votes,
                vote_share_pct,
                majority AS margin_votes,
                majority_pct AS margin_pct,
                party,
                majority IS NOT NULL AS elected,
                ends_with(name_and_mark, {mark}) AS incumbent,
                residence,
                occupation,
                source_id,
                release
            FROM matched
            ORDER BY election, riding, votes DESC
        """)

    def checks(self, db: duckdb.DuckDBPyConnection) -> list[CheckResult]:
        """Parties recognised, one winner with the most votes, and totals that agree."""
        return [
            no_duplicate_keys(db, self.name, self.layout.keys),
            expect_no_rows(
                db,
                f"{self.name}: every candidate's party is in settings.PARTIES",
                f"SELECT election, riding, candidate FROM {self.name} WHERE party IS NULL",
            ),
            expect_no_rows(
                db,
                f"{self.name}: each riding has exactly one winner",
                f"""SELECT d.election, d.riding, count(c.candidate) AS winners
                    FROM election_districts AS d
                    LEFT JOIN {self.name} AS c
                        ON c.election = d.election AND c.riding = d.riding AND c.elected
                    GROUP BY d.election, d.riding
                    HAVING count(c.candidate) <> 1""",
            ),
            expect_no_rows(
                db,
                f"{self.name}: each winner has the most votes",
                f"""SELECT w.election, w.riding, w.candidate, o.candidate AS beaten_by
                    FROM {self.name} AS w
                    JOIN {self.name} AS o
                        ON o.election = w.election AND o.riding = w.riding
                        AND NOT o.elected AND o.votes >= w.votes
                    WHERE w.elected""",
            ),
            expect_no_rows(
                db,
                f"{self.name}: candidates' votes add up to the riding's valid ballots",
                f"""SELECT d.election, d.riding, d.valid_ballots, sum(c.votes) AS votes
                    FROM election_districts AS d
                    JOIN {self.name} AS c ON c.election = d.election AND c.riding = d.riding
                    GROUP BY d.election, d.riding, d.valid_ballots
                    HAVING sum(c.votes) <> d.valid_ballots""",
            ),
            expect_no_rows(
                db,
                f"{self.name}: vote shares in each riding add up to 100%",
                f"""SELECT election, riding, sum(vote_share_pct) AS total
                    FROM {self.name}
                    GROUP BY election, riding
                    HAVING abs(sum(vote_share_pct) - 100) > {VOTE_SHARE_TOLERANCE}""",
            ),
            self._winner_matches_results_by_district(db),
        ]

    def _winner_matches_results_by_district(self, db: duckdb.DuckDBPyConnection) -> CheckResult:
        """The winner's party is the one in the results-by-district table's elected candidate.

        The two tables are published separately, so this catches them disagreeing.
        """
        blocks = [
            f"""SELECT {sql_text(election.code)} AS election,
                       district_number AS riding, elected_candidate
                FROM {election.districts_dataset}
                WHERE release = {latest_release(election.districts_dataset)}"""
            for election in ELECTIONS
        ]
        return expect_no_rows(
            db,
            f"{self.name}: each winner's party matches the results by district",
            f"""SELECT w.election, w.riding, w.candidate, d.elected_candidate
                FROM {self.name} AS w
                JOIN parties AS p ON p.code = w.party
                JOIN ({" UNION ALL ".join(blocks)}) AS d
                    ON d.election = w.election AND d.riding = w.riding
                WHERE w.elected AND NOT ends_with(d.elected_candidate, ' ' || p.label)""",
        )
