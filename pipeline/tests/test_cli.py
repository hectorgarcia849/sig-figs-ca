"""Tests for the pst command.

Extract and build are replaced with stand-ins, so nothing real runs.
"""

import json
from datetime import date
from pathlib import Path

import pytest

from public_spend_tracker_pipeline import cli
from public_spend_tracker_pipeline.common.paths import (
    BUILD_MANIFEST_FILE_NAME,
    MANIFEST_FILE_NAME,
    current_build_file,
    raw_release_folder,
    serving_build_folder,
)
from public_spend_tracker_pipeline.common.settings import WEB_DATA_FOLDER


class StandIns:
    """Records which steps ran, with which data folder, and returns chosen exit codes."""

    def __init__(self, monkeypatch, extract_code=0, build_code=0, reasons=("something new",)):
        self.calls = []
        monkeypatch.setattr(cli, "reasons_to_build", lambda data_root: list(reasons))
        monkeypatch.setattr(cli, "sync_data", self.sync_stand_in)
        monkeypatch.setattr(cli, "diff_builds", self.diff_stand_in)
        monkeypatch.setattr(cli, "run_extract", self.stand_in("extract", extract_code))
        monkeypatch.setattr(cli, "build_everything", self.stand_in("build", build_code))
        monkeypatch.setattr(cli, "export_site", self.export_stand_in)
        monkeypatch.setattr(cli, "approve_build", self.approve_stand_in)

    def stand_in(self, step, code):
        def run(data_root):
            self.calls.append((step, data_root))
            return code

        return run

    def diff_stand_in(self, data_root, build_id, against):
        self.calls.append(("diff", data_root, build_id, against))
        return 0

    def sync_stand_in(self, data_root, direction, bucket, with_approval, dry_run):
        self.calls.append(("sync", data_root, direction, bucket, with_approval, dry_run))
        return 0

    def approve_stand_in(self, data_root, build_id):
        self.calls.append(("approve", data_root, build_id))
        return 0

    def export_stand_in(self, data_root, build_id, destination):
        self.calls.append(("export", data_root, build_id, destination))
        return 0


def test_help_lists_every_subcommand(capsys):
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["--help"])
    assert exit_info.value.code == 0
    help_text = capsys.readouterr().out
    for subcommand in ("extract", "build", "update", "status", "diff", "approve", "export", "sync"):
        assert subcommand in help_text


def test_data_root_is_passed_to_the_step(monkeypatch, tmp_path):
    steps = StandIns(monkeypatch)
    assert cli.main(["--data-root", str(tmp_path), "build"]) == 0
    assert steps.calls == [("build", tmp_path)]


def test_update_extracts_then_builds(monkeypatch, tmp_path):
    steps = StandIns(monkeypatch)
    assert cli.main(["--data-root", str(tmp_path), "update"]) == 0
    assert steps.calls == [("extract", tmp_path), ("build", tmp_path)]


def test_update_does_not_build_when_nothing_new_arrived(monkeypatch, tmp_path, capsys):
    steps = StandIns(monkeypatch, reasons=())
    assert cli.main(["--data-root", str(tmp_path), "update"]) == 0
    assert steps.calls == [("extract", tmp_path)]
    assert "Nothing new" in capsys.readouterr().out


def test_diff_defaults_to_the_newest_build_against_the_approved_one(monkeypatch, tmp_path):
    steps = StandIns(monkeypatch)
    root = ["--data-root", str(tmp_path)]
    assert cli.main([*root, "diff"]) == 0
    assert cli.main([*root, "diff", "20261126-153000", "--against", "20261116-164845"]) == 0
    assert steps.calls == [
        ("diff", tmp_path, None, None),
        ("diff", tmp_path, "20261126-153000", "20261116-164845"),
    ]


def test_sync_passes_on_its_choices(monkeypatch, tmp_path):
    steps = StandIns(monkeypatch)
    root = ["--data-root", str(tmp_path)]
    assert cli.main([*root, "sync", "pull"]) == 0
    assert (
        cli.main([*root, "sync", "push", "--with-approval", "--dry-run", "--bucket", "gs://b"]) == 0
    )
    assert steps.calls == [
        ("sync", tmp_path, "pull", "gs://ca-pol-econ-data", False, False),
        ("sync", tmp_path, "push", "gs://b", True, True),
    ]


def test_update_does_not_build_when_a_download_failed(monkeypatch, tmp_path, capsys):
    steps = StandIns(monkeypatch, extract_code=1)
    assert cli.main(["--data-root", str(tmp_path), "update"]) == 1
    assert steps.calls == [("extract", tmp_path)]
    assert "nothing was built" in capsys.readouterr().err


def test_failed_build_gives_exit_code_1(monkeypatch, tmp_path):
    StandIns(monkeypatch, build_code=1)
    assert cli.main(["--data-root", str(tmp_path), "build"]) == 1


def test_approve_defaults_to_the_newest_build(monkeypatch, tmp_path):
    steps = StandIns(monkeypatch)
    assert cli.main(["--data-root", str(tmp_path), "approve"]) == 0
    assert steps.calls == [("approve", tmp_path, None)]


def test_approve_takes_a_build_id(monkeypatch, tmp_path):
    steps = StandIns(monkeypatch)
    assert cli.main(["--data-root", str(tmp_path), "approve", "20261115-070145"]) == 0
    assert steps.calls == [("approve", tmp_path, "20261115-070145")]


def test_export_defaults_to_the_approved_build_and_web_data(monkeypatch, tmp_path):
    steps = StandIns(monkeypatch)
    assert cli.main(["--data-root", str(tmp_path), "export"]) == 0
    assert steps.calls == [("export", tmp_path, None, WEB_DATA_FOLDER)]


def test_export_options_are_passed_on(monkeypatch, tmp_path):
    steps = StandIns(monkeypatch)
    arguments = ["--data-root", str(tmp_path), "export", "--build", "20261116-152117"]
    assert cli.main([*arguments, "--out", "site_data"]) == 0
    assert steps.calls == [("export", tmp_path, "20261116-152117", Path("site_data"))]


# --- status -------------------------------------------------------------------


def write_json(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content), encoding="utf-8")


def test_status_on_an_empty_folder(tmp_path, capsys):
    assert cli.main(["--data-root", str(tmp_path), "status"]) == 0
    output = capsys.readouterr().out
    assert "10-10-0005-01  cofog_consolidated       not downloaded" in output
    assert "Builds (newest first)\n  none yet" in output
    assert "Approved build: none yet" in output


def test_status_shows_downloads_builds_and_the_approved_build(tmp_path, capsys):
    for release in (date(2024, 11, 28), date(2025, 11, 27)):
        write_json(
            raw_release_folder("statcan", "10100005", release, tmp_path) / MANIFEST_FILE_NAME, {}
        )
    write_json(
        serving_build_folder("20261115-070145", tmp_path) / BUILD_MANIFEST_FILE_NAME,
        {
            "finished_at": "2026-11-15T07:01:46+00:00",
            "datasets": [{"checks": [{}, {}]}, {"checks": [{}]}],
            "serving": {"checks": [{}, {}]},
        },
    )
    serving_build_folder("20261115-062210", tmp_path).mkdir(parents=True)  # never finished
    write_json(current_build_file(tmp_path), {"build_id": "20261115-070145"})

    assert cli.main(["--data-root", str(tmp_path), "status"]) == 0
    output = capsys.readouterr().out
    assert "10-10-0005-01  cofog_consolidated       2025-11-27   2 releases stored" in output
    assert (
        "  20261115-070145  complete    5 checks passed   2026-11-15 07:01 UTC\n"
        "  20261115-062210  incomplete  (no manifest)"
    ) in output
    assert "Approved build: 20261115-070145" in output
