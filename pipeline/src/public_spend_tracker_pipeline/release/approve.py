"""Approve a build: record which build the public site (and later the API) shows.

Run it from the repository root with:

    uv run pst approve                 approve the newest complete build
    uv run pst approve <build_id>      approve a particular build (e.g. to roll back)

Building never changes what the public sees. A build is only a candidate until
it is approved here, which writes data/serving/current.json:

    {"build_id": "20261116-164845",
     "approved_at": "2026-11-16T18:02:11+00:00",
     "replaces": "20261115-072257"}

"pst export" then exports the approved build by default, so the site is always
built from figures someone has looked at. The record holds no names or emails.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from public_spend_tracker_pipeline.common.logs import start_logging, stop_logging
from public_spend_tracker_pipeline.common.paths import (
    BUILD_MANIFEST_FILE_NAME,
    current_build_file,
    new_build_id,
    serving_build_folder,
    stored_builds,
)
from public_spend_tracker_pipeline.common.settings import DATA_ROOT

log = logging.getLogger(__name__)


class ApprovalError(Exception):
    """A build could not be approved or read, e.g. there is no complete build."""


def is_complete(build_id: str, data_root: Path = DATA_ROOT) -> bool:
    """Whether a build finished: every check passed and its manifest was written last."""
    return (serving_build_folder(build_id, data_root) / BUILD_MANIFEST_FILE_NAME).is_file()


def newest_complete_build(data_root: Path = DATA_ROOT) -> str:
    """The ID of the newest build that finished."""
    complete = [
        build_id for build_id in stored_builds(data_root) if is_complete(build_id, data_root)
    ]
    if not complete:
        raise ApprovalError("There is no complete build yet. Run: uv run pst build")
    return complete[-1]


def approved_build(data_root: Path = DATA_ROOT) -> str | None:
    """The ID of the approved build, or None if no build has been approved yet."""
    path = current_build_file(data_root)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))["build_id"]


def approve(
    build_id: str | None = None, data_root: Path = DATA_ROOT, now: datetime | None = None
) -> str:
    """Record a build (the newest complete one by default) as approved. Returns its ID.

    Pass `now` to set the approval time (used by tests).
    """
    build_id = build_id or newest_complete_build(data_root)
    if not is_complete(build_id, data_root):
        raise ApprovalError(
            f"Build {build_id} is not complete (it has no {BUILD_MANIFEST_FILE_NAME})"
        )

    record = {
        "build_id": build_id,
        "approved_at": (now or datetime.now(UTC)).isoformat(timespec="seconds"),
        "replaces": approved_build(data_root),
    }
    _write_whole(current_build_file(data_root), json.dumps(record, indent=2) + "\n")
    return build_id


def _write_whole(path: Path, text: str) -> None:
    """Write a file so readers see either the old version or the new, never half of one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.writing")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def approve_build(data_root: Path = DATA_ROOT, build_id: str | None = None) -> int:
    """Approve a build and say what changed. Returns 0 if it worked, 1 if not.

    The approval is logged, like every other command, so data/logs/ keeps a
    history of what was approved and when.
    """
    start_logging("approve", new_build_id(), data_root)
    try:
        previous = approved_build(data_root)
        approved = approve(build_id, data_root)
        if previous == approved:
            log.info(f"Build {approved} was already approved; approval time updated.")
        else:
            log.info(f"Approved build {approved} (was: {previous or 'none'}).")
        log.info("Next: just export, then just deploy-preview")
    except ApprovalError as error:
        log.error(f"Nothing approved: {error}")
        return 1
    finally:
        stop_logging()
    return 0
