"""Tests for "pst sync": which gcloud commands run, in which order, and what they leave out.

gcloud is never run: the commands are checked as written, and a stand-in
runner records them.
"""

import re
from pathlib import Path

import pytest

from public_spend_tracker_pipeline.common.sync import (
    EXCLUDE_FROM_FIRST_PASS,
    EXCLUDE_FROM_SECOND_PASS,
    SyncError,
    run_sync,
    sync_commands,
    sync_data,
)

BUCKET = "gs://test-bucket"
DATA = Path("data")

DOWNLOAD = "raw/source=statcan/table=10100005/release=2025-11-27/10100005-eng.zip"
DOWNLOAD_MANIFEST = "raw/source=statcan/table=10100005/release=2025-11-27/_manifest.json"
DATABASE = "serving/build=20261116-164845/fiscal.duckdb"
BUILD_MANIFEST = "serving/build=20261116-164845/build_manifest.json"
APPROVAL = "serving/current.json"
LOG = "logs/20261116-164845-build.log"
WORK_FILE = ".building-20261116-170000/staged/data.parquet"
APPROVAL_BEING_WRITTEN = "serving/.current.json.writing"


def left_out(pattern: str, path: str) -> bool:
    return re.search(pattern, path) is not None


@pytest.mark.parametrize("path", [DOWNLOAD, DATABASE, LOG])
def test_the_first_pass_copies_data_files(path):
    assert not left_out(EXCLUDE_FROM_FIRST_PASS, path)
    assert left_out(EXCLUDE_FROM_SECOND_PASS, path)


@pytest.mark.parametrize("path", [DOWNLOAD_MANIFEST, BUILD_MANIFEST])
def test_manifests_wait_for_the_second_pass(path):
    assert left_out(EXCLUDE_FROM_FIRST_PASS, path)
    assert not left_out(EXCLUDE_FROM_SECOND_PASS, path)


@pytest.mark.parametrize("path", [APPROVAL, WORK_FILE, APPROVAL_BEING_WRITTEN])
def test_rsync_never_copies_the_approval_or_work_files(path):
    assert left_out(EXCLUDE_FROM_FIRST_PASS, path)
    assert left_out(EXCLUDE_FROM_SECOND_PASS, path)


def test_a_pull_copies_data_then_manifests_then_the_approval():
    first, second, approval = sync_commands("pull", DATA, BUCKET)
    assert first[:5] == ["gcloud", "storage", "rsync", BUCKET, "data"]
    assert second[:5] == ["gcloud", "storage", "rsync", BUCKET, "data"]
    for rsync in (first, second):
        assert "--recursive" in rsync
        assert "--no-clobber" in rsync  # nothing at the other end is overwritten
        assert "--delete-unmatched-destination-objects" not in rsync  # nothing is deleted
    assert first[-1] == f"--exclude={EXCLUDE_FROM_FIRST_PASS}"
    assert second[-1] == f"--exclude={EXCLUDE_FROM_SECOND_PASS}"
    assert approval == [
        "gcloud", "storage", "cp", f"{BUCKET}/{APPROVAL}", f"data/{APPROVAL}",
    ]  # fmt: skip


def test_a_push_leaves_the_approval_unless_asked():
    commands = sync_commands("push", DATA, BUCKET)
    assert len(commands) == 2
    assert commands[0][3:5] == ["data", BUCKET]

    *_, approval = sync_commands("push", DATA, BUCKET, with_approval=True)
    assert approval == [
        "gcloud", "storage", "cp", f"data/{APPROVAL}", f"{BUCKET}/{APPROVAL}",
    ]  # fmt: skip


def test_a_dry_run_copies_nothing():
    commands = sync_commands("pull", DATA, BUCKET, dry_run=True)
    assert len(commands) == 2  # the approval copy has no dry run, so it is only reported
    assert all("--dry-run" in command for command in commands)


class Recorder:
    """Stands in for running gcloud: records each command, and fails the one asked to."""

    def __init__(self, fail_at: int | None = None):
        self.commands = []
        self.fail_at = fail_at

    def __call__(self, command):
        self.commands.append(list(command))
        return 1 if len(self.commands) == self.fail_at else 0


def test_run_sync_runs_every_command_in_order(tmp_path):
    recorder = Recorder()
    run_sync("pull", tmp_path / "data", BUCKET, run=recorder)
    assert recorder.commands == sync_commands("pull", tmp_path / "data", BUCKET)
    assert (tmp_path / "data" / "serving").is_dir()  # somewhere for the approval to land


def test_run_sync_stops_at_the_first_failure_so_manifests_never_go_early(tmp_path):
    recorder = Recorder(fail_at=1)
    with pytest.raises(SyncError, match="exit code 1"):
        run_sync("push", tmp_path, BUCKET, run=recorder)
    assert len(recorder.commands) == 1


def test_sync_data_returns_1_when_a_copy_fails(tmp_path, monkeypatch):
    monkeypatch.setattr("public_spend_tracker_pipeline.common.sync._run", lambda command: 1)
    assert sync_data(tmp_path, "push", BUCKET) == 1
