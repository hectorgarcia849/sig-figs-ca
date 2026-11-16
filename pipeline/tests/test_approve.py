"""Tests for approving a build (data/serving/current.json)."""

import json
from datetime import UTC, datetime

import pytest

from public_spend_tracker_pipeline.approve import (
    ApprovalError,
    approve,
    approve_build,
    approved_build,
    newest_complete_build,
)
from public_spend_tracker_pipeline.paths import (
    BUILD_MANIFEST_FILE_NAME,
    current_build_file,
    serving_build_folder,
)

OLDER = "20261115-070145"
NEWER = "20261116-152117"
UNFINISHED = "20261116-170000"
APPROVED_AT = datetime(2026, 11, 16, 18, 2, 11, tzinfo=UTC)


def make_build(data_root, build_id, complete=True):
    """An empty build folder; a complete build also has its manifest."""
    folder = serving_build_folder(build_id, data_root)
    folder.mkdir(parents=True)
    if complete:
        (folder / BUILD_MANIFEST_FILE_NAME).write_text("{}", encoding="utf-8")


@pytest.fixture
def data_root(tmp_path):
    make_build(tmp_path, OLDER)
    make_build(tmp_path, NEWER)
    make_build(tmp_path, UNFINISHED, complete=False)
    return tmp_path


def record(data_root):
    return json.loads(current_build_file(data_root).read_text(encoding="utf-8"))


def test_newest_complete_build_skips_unfinished_ones(data_root):
    assert newest_complete_build(data_root) == NEWER


def test_no_complete_build_gives_a_clear_error(tmp_path):
    with pytest.raises(ApprovalError, match="no complete build yet"):
        newest_complete_build(tmp_path)


def test_nothing_is_approved_at_first(data_root):
    assert approved_build(data_root) is None


def test_approving_records_the_build_and_time(data_root):
    assert approve(data_root=data_root, now=APPROVED_AT) == NEWER
    assert record(data_root) == {
        "build_id": NEWER,
        "approved_at": "2026-11-16T18:02:11+00:00",
        "replaces": None,
    }
    assert approved_build(data_root) == NEWER


def test_an_older_build_can_be_approved_to_roll_back(data_root):
    approve(NEWER, data_root)
    approve(OLDER, data_root)
    assert record(data_root)["build_id"] == OLDER
    assert record(data_root)["replaces"] == NEWER


def test_an_unfinished_build_is_refused_and_the_approval_kept(data_root):
    approve(OLDER, data_root)
    with pytest.raises(ApprovalError, match="not complete"):
        approve(UNFINISHED, data_root)
    assert approved_build(data_root) == OLDER


def test_no_temporary_file_is_left_behind(data_root):
    approve(data_root=data_root)
    assert [path.name for path in current_build_file(data_root).parent.glob(".*")] == []


def test_approve_build_returns_0_and_logs_the_change(data_root, caplog):
    assert approve_build(data_root) == 0
    assert f"Approved build {NEWER} (was: none)" in caplog.text


def test_approve_build_returns_1_when_there_is_no_build(tmp_path):
    assert approve_build(tmp_path) == 1
    assert approved_build(tmp_path) is None
