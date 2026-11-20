"""Sync the data folder with the Cloud Storage bucket, which keeps the permanent copy.

Run it from the repository root with:

    uv run pst sync pull                  bucket -> data/
    uv run pst sync push                  data/ -> bucket
    uv run pst sync push --with-approval  also send data/serving/current.json
    uv run pst sync pull --dry-run        list what would be copied, copy nothing

The bucket has the same folders as data/ (see paths.py), so a sync is a plain
copy of the folder tree, made with "gcloud storage rsync". The rules that keep
it safe:

    Nothing is ever deleted, in either direction.
    Files already at the other end are never overwritten: downloads, builds
        and logs are never changed once written, so a file with the same name
        is the same file.
    Manifests go last. A download or build only counts as complete once its
        manifest exists, so manifests are copied in a second pass, after
        everything else. If a sync stops halfway, the other end sees an
        incomplete download or build, and ignores it.
    The approval (serving/current.json) is the one file that changes. A pull
        always brings the bucket's approval down: the bucket is where releases
        are approved. A push only sends it with --with-approval, so an old
        approval on a laptop never replaces a newer one. (The first push sends
        it, so the bucket always has one before anyone pulls.)
    Hidden work files and folders (names starting with "."), such as a build
        in progress, are never copied.
"""

from __future__ import annotations

import logging
import re
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Literal

from public_spend_tracker_pipeline.common.logs import start_logging, stop_logging
from public_spend_tracker_pipeline.common.paths import (
    BUILD_MANIFEST_FILE_NAME,
    CURRENT_BUILD_FILE_NAME,
    MANIFEST_FILE_NAME,
    SERVING,
    new_build_id,
)
from public_spend_tracker_pipeline.common.settings import DATA_BUCKET, DATA_ROOT

log = logging.getLogger(__name__)

Direction = Literal["pull", "push"]
DIRECTIONS: tuple[Direction, ...] = ("pull", "push")

# The command that does the copying. Installed with the Google Cloud CLI.
GCLOUD = "gcloud"

# Patterns for the paths a pass leaves out ("exclude"), as Python regular
# expressions matched against each path relative to the folder being synced.
# gcloud reads a comma as a separator between patterns, so none has a comma.
_ANY_FOLDER = r"(.*/)?"
_MANIFEST = rf"{_ANY_FOLDER}({re.escape(MANIFEST_FILE_NAME)}|{re.escape(BUILD_MANIFEST_FILE_NAME)})"
_HIDDEN = rf"{_ANY_FOLDER}\..*"
_APPROVAL = rf"{re.escape(SERVING)}/{re.escape(CURRENT_BUILD_FILE_NAME)}"

# Pass 1 leaves out manifests, the approval and hidden work files.
EXCLUDE_FROM_FIRST_PASS = rf"^({_MANIFEST}|{_HIDDEN}|{_APPROVAL})$"
# Pass 2 leaves out everything except manifests (and still hidden work files).
EXCLUDE_FROM_SECOND_PASS = rf"^((?!{_MANIFEST}$).*|{_HIDDEN})$"


class SyncError(Exception):
    """A copy failed, for example because the bucket could not be reached."""


def sync_commands(
    direction: Direction,
    data_root: Path = DATA_ROOT,
    bucket: str = DATA_BUCKET,
    with_approval: bool = False,
    dry_run: bool = False,
) -> list[list[str]]:
    """The gcloud commands for one sync, in the order they must run."""
    local = str(data_root)
    source, destination = (bucket, local) if direction == "pull" else (local, bucket)
    extra = ["--dry-run"] if dry_run else []

    def rsync(source: str, destination: str, exclude: str, *options: str) -> list[str]:
        return [
            GCLOUD, "storage", "rsync", source, destination,
            *options, f"--exclude={exclude}", *extra,
        ]  # fmt: skip

    commands = [
        rsync(source, destination, EXCLUDE_FROM_FIRST_PASS, "--recursive", "--no-clobber"),
        rsync(source, destination, EXCLUDE_FROM_SECOND_PASS, "--recursive", "--no-clobber"),
    ]
    # (gcloud's plain copy has no dry run, so a dry run only reports it: see sync_data.)
    if includes_approval(direction, with_approval) and not dry_run:
        # The approval always replaces the one at the other end. A plain copy,
        # not rsync: approval records all have the same length, and rsync can
        # skip a file whose size has not changed.
        approval = f"{SERVING}/{CURRENT_BUILD_FILE_NAME}"
        commands.append(
            [GCLOUD, "storage", "cp", f"{source}/{approval}", f"{destination}/{approval}"]
        )
    return commands


def includes_approval(direction: Direction, with_approval: bool) -> bool:
    """Whether a sync copies the approval: every pull, and a push only when asked."""
    return direction == "pull" or with_approval


Runner = Callable[[Sequence[str]], int]


def _run(command: Sequence[str]) -> int:
    """Run a command, showing its output, and return its exit code."""
    return subprocess.run(command, check=False).returncode


def run_sync(
    direction: Direction,
    data_root: Path = DATA_ROOT,
    bucket: str = DATA_BUCKET,
    with_approval: bool = False,
    dry_run: bool = False,
    run: Runner = _run,
) -> None:
    """Run every command of one sync in order, stopping at the first that fails.

    Pass `run` to replace running gcloud (used by tests).
    """
    if direction == "pull":
        data_root.mkdir(parents=True, exist_ok=True)
        (data_root / SERVING).mkdir(exist_ok=True)
    for command in sync_commands(direction, data_root, bucket, with_approval, dry_run):
        log.debug(" ".join(command))
        code = run(command)
        if code != 0:
            raise SyncError(f"{' '.join(command[:3])} stopped with exit code {code}")


def sync_data(
    data_root: Path = DATA_ROOT,
    direction: Direction = "pull",
    bucket: str = DATA_BUCKET,
    with_approval: bool = False,
    dry_run: bool = False,
) -> int:
    """Sync and report. Returns 0 if it worked, 1 if not."""
    start_logging("sync", new_build_id(), data_root)
    try:
        arrow = f"{bucket} -> {data_root}" if direction == "pull" else f"{data_root} -> {bucket}"
        log.info(f"Sync {direction}{' (dry run: nothing copied)' if dry_run else ''}: {arrow}")
        run_sync(direction, data_root, bucket, with_approval, dry_run)
        if dry_run and includes_approval(direction, with_approval):
            log.info(f"Would also copy the approval, {SERVING}/{CURRENT_BUILD_FILE_NAME}.")
        log.info("Sync finished.")
        return 0
    except SyncError as error:
        log.error(f"Sync stopped: {error}. Run it again: files already copied are skipped.")
        return 1
    finally:
        stop_logging()
