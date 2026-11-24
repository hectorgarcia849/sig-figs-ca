"""Tests for the staged Elections Canada datasets, read from small made-up files."""

import io
import json
import zipfile

import duckdb
import pytest
import shapefile

from public_spend_tracker_pipeline.common.paths import MANIFEST_FILE_NAME
from public_spend_tracker_pipeline.common.settings import ELECTIONS_FILES
from public_spend_tracker_pipeline.transform.staged_elections import (
    RESULTS_BY_CANDIDATE,
    RESULTS_BY_DISTRICT,
    RESULTS_COLUMNS,
    StagedResultsTable,
    StagedRidingBoundaries,
    staged_elections_transformer,
)
from public_spend_tracker_pipeline.transform.staged_statcan import SourceChangedError

FILES = {source_file.name: source_file for source_file in ELECTIONS_FILES}
BOUNDARIES = FILES["federal_electoral_districts"]
BY_DISTRICT = FILES["ge45_results_by_district"]
BY_CANDIDATE = FILES["ge45_results_by_candidate"]

NL = "Newfoundland and Labrador/Terre-Neuve-et-Labrador"


def header(kind: str) -> str:
    return ",".join(f'"{column.published}"' for column in RESULTS_COLUMNS[kind])


DISTRICT_CSV = (
    "﻿" + header(RESULTS_BY_DISTRICT) + "\n"
    f'"{NL}","Avalon","10001",81781,70859,201,47030,99.2,389,.8,47419,66.9,'
    '"Connors, Paul Liberal/Libéral"\n'
    '"Nunavut","Nunavut","62001",36858,21912,58,7657,98.8,90,1.2,7747,35.4,'
    '"Idlout, Lori NDP-New Democratic Party/NPD-Nouveau Parti démocratique"\n'
)
CANDIDATE_CSV = (
    "﻿" + header(RESULTS_BY_CANDIDATE) + "\n"
    f'"{NL}","Avalon","10001","Paul Connors Liberal/Libéral","Conception Bay South, N.L.",'
    '"Executive Assistant/Adjoint de direction",27563,58.6,     10610,  22.6\n'
    f'"{NL}","Avalon","10001","Steve Kent Conservative/Conservateur","Portugal Cove, N.L.",'
    '"Consultant/Consultant",16953,36.0,,\n'
)


def release_folder(tmp_path, file_name: str, content: bytes):
    """A downloaded release: the file and its manifest."""
    folder = tmp_path / "release=2026-11-24"
    folder.mkdir()
    (folder / file_name).write_bytes(content)
    manifest = {"release": "2026-11-24", "files": [{"name": file_name}]}
    (folder / MANIFEST_FILE_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    return folder


def boundary_zip(fields=("ED_CF_NUM", "ED_NAMEE", "CF_NOMF"), encoding="UTF-8") -> bytes:
    """A zipped shapefile table with two ridings, like Elections Canada's."""
    table = io.BytesIO()
    writer = shapefile.Writer(dbf=table, shapeType=shapefile.NULL, encoding="utf-8")
    writer.field(fields[0], "N", 11)
    for name in fields[1:]:
        writer.field(name, "C", 100)
    writer.record(35105, "Taiaiako'n—Parkdale—High Park", "Taiaiako'n—Parkdale—High Park")
    writer.record(24001, "Abitibi—Baie-James—Nunavik—Eeyou", "Abitibi—Baie-James—Nunavik—Eeyou")
    writer.close()
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("FederalElectoralDistricts_SHP/ED_CF.dbf", table.getvalue())
        zipped.writestr("FederalElectoralDistricts_SHP/ED_CF.cpg", encoding)
    return archive.getvalue()


def stage(transformer):
    db = duckdb.connect()
    transformer.transform(db).create(transformer.name)
    return db, transformer.checks(db)


def test_each_file_gets_the_right_transformer(tmp_path):
    folder = release_folder(tmp_path, "file", b"")
    assert isinstance(staged_elections_transformer(BOUNDARIES, folder), StagedRidingBoundaries)
    district = staged_elections_transformer(BY_DISTRICT, folder)
    candidate = staged_elections_transformer(BY_CANDIDATE, folder)
    assert isinstance(district, StagedResultsTable) and district.kind == RESULTS_BY_DISTRICT
    assert isinstance(candidate, StagedResultsTable) and candidate.kind == RESULTS_BY_CANDIDATE
    assert str(candidate.release) == "2026-11-24"


def test_riding_boundaries_are_read_with_both_names(tmp_path):
    folder = release_folder(tmp_path, "FederalElectoralDistricts_SHP.zip", boundary_zip())
    db, checks = stage(StagedRidingBoundaries(BOUNDARIES, folder))
    assert all(check.passed for check in checks), checks
    assert db.sql("SELECT * FROM federal_electoral_districts").fetchall() == [
        ("24001", "Abitibi—Baie-James—Nunavik—Eeyou", "Abitibi—Baie-James—Nunavik—Eeyou"),
        ("35105", "Taiaiako'n—Parkdale—High Park", "Taiaiako'n—Parkdale—High Park"),
    ]


def test_renamed_boundary_column_stops_the_build(tmp_path):
    zipped = boundary_zip(fields=("FED_NUM", "ED_NAMEE", "CF_NOMF"))
    folder = release_folder(tmp_path, "FederalElectoralDistricts_SHP.zip", zipped)
    with pytest.raises(SourceChangedError, match="the columns changed"):
        stage(StagedRidingBoundaries(BOUNDARIES, folder))


def test_boundary_text_in_another_encoding_stops_the_build(tmp_path):
    folder = release_folder(
        tmp_path, "FederalElectoralDistricts_SHP.zip", boundary_zip(encoding="windows-1252")
    )
    with pytest.raises(SourceChangedError, match="windows-1252"):
        stage(StagedRidingBoundaries(BOUNDARIES, folder))


def test_results_by_district_are_typed_and_the_province_split(tmp_path):
    folder = release_folder(tmp_path, "table_tableau11.csv", DISTRICT_CSV.encode())
    db, checks = stage(StagedResultsTable(BY_DISTRICT, folder, RESULTS_BY_DISTRICT))
    assert all(check.passed for check in checks), checks
    rows = db.sql("""
        SELECT province_en, province_fr, district_number, electors, rejected_ballots_pct,
               turnout_pct, elected_candidate
        FROM ge45_results_by_district
    """).fetchall()
    assert rows == [
        ("Newfoundland and Labrador", "Terre-Neuve-et-Labrador", "10001", 70859, 0.8, 66.9,
         "Connors, Paul Liberal/Libéral"),
        ("Nunavut", "Nunavut", "62001", 21912, 1.2, 35.4,
         "Idlout, Lori NDP-New Democratic Party/NPD-Nouveau Parti démocratique"),
    ]  # fmt: skip


def test_only_the_winner_has_a_majority(tmp_path):
    folder = release_folder(tmp_path, "table_tableau12.csv", CANDIDATE_CSV.encode())
    db, checks = stage(StagedResultsTable(BY_CANDIDATE, folder, RESULTS_BY_CANDIDATE))
    assert all(check.passed for check in checks), checks
    rows = db.sql(
        "SELECT candidate, votes, majority, majority_pct FROM ge45_results_by_candidate"
    ).fetchall()
    assert rows == [
        ("Paul Connors Liberal/Libéral", 27563, 10610, 22.6),
        ("Steve Kent Conservative/Conservateur", 16953, None, None),
    ]


def test_changed_results_columns_stop_the_build(tmp_path):
    changed = CANDIDATE_CSV.replace("Votes Obtained/Votes obtenus", "Votes/Votes")
    folder = release_folder(tmp_path, "table_tableau12.csv", changed.encode())
    with pytest.raises(SourceChangedError, match="the columns changed"):
        stage(StagedResultsTable(BY_CANDIDATE, folder, RESULTS_BY_CANDIDATE))


def test_unreadable_number_fails_a_check(tmp_path):
    folder = release_folder(tmp_path, "table_tableau12.csv",
                            CANDIDATE_CSV.replace("27563", "27563x").encode())  # fmt: skip
    _, checks = stage(StagedResultsTable(BY_CANDIDATE, folder, RESULTS_BY_CANDIDATE))
    failed = [check for check in checks if not check.passed]
    assert len(failed) == 1 and "no missing" in failed[0].name
