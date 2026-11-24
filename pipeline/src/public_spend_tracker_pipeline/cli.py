"""The pst command: one front door to the pipeline.

    pst extract   download new Statistics Canada and Elections Canada releases
    pst build     build and check the database from everything downloaded
    pst update    extract, then build if anything new arrived: the everyday command
    pst status    show downloads, builds and the approved build (changes nothing)
    pst approve   approve a build: the one the public site shows
    pst export    write a build's figures as JSON for the site (web/data/)
    pst sync      copy new files between data/ and the Cloud Storage bucket
    pst diff      what changed between a build and the approved build

Run it from anywhere in the repository with "uv run pst <subcommand>".

Every subcommand accepts --data-root to use another data folder, e.g.
"pst --data-root /tmp/test build". Without it, the PST_DATA_ROOT environment
variable is used, and without that, ./data.

approve takes an optional build ID (the newest complete build by default).
export takes --build (which build; the approved one by default) and --out
(where to write; web/data/ by default).
diff takes an optional build ID (the newest complete build by default) and
--against (the build to compare with; the approved one by default).
sync takes pull or push, plus --with-approval (push the approval too),
--dry-run (list what would be copied) and --bucket (another bucket).

Exit codes: 0 when everything worked, 1 when anything failed.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from public_spend_tracker_pipeline.build.needed import reasons_to_build
from public_spend_tracker_pipeline.build.run import build_everything
from public_spend_tracker_pipeline.common.paths import (
    BUILD_MANIFEST_FILE_NAME,
    complete_releases,
    raw_table_folder,
    serving_build_folder,
    stored_builds,
)
from public_spend_tracker_pipeline.common.settings import (
    DATA_BUCKET,
    DATA_ROOT,
    ELECTIONS_FILES,
    STATCAN_TABLES,
    WEB_DATA_FOLDER,
)
from public_spend_tracker_pipeline.common.sync import DIRECTIONS, Direction, sync_data
from public_spend_tracker_pipeline.extract import elections, statcan
from public_spend_tracker_pipeline.extract.run import run_extract
from public_spend_tracker_pipeline.release.approve import approve_build, approved_build
from public_spend_tracker_pipeline.release.diff import checks_passed, diff_builds
from public_spend_tracker_pipeline.release.export import export_site
from public_spend_tracker_pipeline.transform.model_sources import table_number

# How many builds "pst status" lists, newest first.
BUILDS_SHOWN = 10

# Column widths in "pst status": Statistics Canada table numbers ("10-10-0005-01")
# and our names for tables and files.
TABLE_NUMBER_WIDTH = 13
NAME_WIDTH = 28

# What "pst status" shows in the table-number column for Elections Canada files.
ELECTIONS_LABEL = "elections.ca"

SUCCESS = 0
FAILURE = 1


# --- Subcommands ------------------------------------------------------------


def extract(data_root: Path) -> int:
    """Download new Statistics Canada and Elections Canada releases."""
    return run_extract(data_root)


def build(data_root: Path) -> int:
    """Build and check the database from everything downloaded."""
    return build_everything(data_root)


def update(data_root: Path) -> int:
    """Extract, then build if anything new arrived.

    Stops before building if any download failed: a failed download could mean
    a new release was missed, so it is better to find out than to build from
    data that may be out of date. Builds only when the downloads are newer than
    the newest build (see build/needed.py); "pst build" always builds.
    """
    if run_extract(data_root) != SUCCESS:
        print("Some downloads failed, so nothing was built.", file=sys.stderr)
        return FAILURE
    reasons = reasons_to_build(data_root)
    if not reasons:
        print("Nothing new: the newest build already uses every download. Nothing was built.")
        return SUCCESS
    for reason in reasons:
        print(f"Building: {reason}")
    return build_everything(data_root)


def status(data_root: Path) -> int:
    """Show what is on disk: downloads, builds and the approved build. Changes nothing."""
    print(f"Data folder: {data_root}")
    print()
    print("Downloads (newest release of each table)")
    for line in _download_lines(data_root):
        print(f"  {line}")
    print()
    print("Builds (newest first)")
    for line in _build_lines(data_root):
        print(f"  {line}")
    print()
    print(f"Approved build: {approved_build(data_root) or 'none yet'}")
    return SUCCESS


def approve(data_root: Path, build: str | None = None) -> int:
    """Approve a build: the one the public site shows."""
    return approve_build(data_root, build)


def export(data_root: Path, build: str | None = None, out: Path = WEB_DATA_FOLDER) -> int:
    """Write a build's figures as JSON for the site (web/data/)."""
    return export_site(data_root, build, out)


def sync(
    data_root: Path,
    direction: Direction,
    bucket: str = DATA_BUCKET,
    with_approval: bool = False,
    dry_run: bool = False,
) -> int:
    """Copy new files between data/ and the Cloud Storage bucket."""
    return sync_data(data_root, direction, bucket, with_approval, dry_run)


def diff(data_root: Path, build: str | None = None, against: str | None = None) -> int:
    """What changed between a build and the approved build."""
    return diff_builds(data_root, build, against)


# --- What "status" shows ----------------------------------------------------


def _download_lines(data_root: Path) -> list[str]:
    """One line per table or file: its newest release and how many releases are stored."""
    lines = []
    for table in STATCAN_TABLES:
        folder = raw_table_folder(statcan.SOURCE_NAME, table.product_id, data_root)
        lines.append(_download_line(table_number(table.product_id), table.name, folder))
    for source_file in ELECTIONS_FILES:
        folder = raw_table_folder(elections.SOURCE_NAME, source_file.name, data_root)
        lines.append(_download_line(ELECTIONS_LABEL, source_file.name, folder))
    return lines


def _download_line(label: str, name: str, folder: Path) -> str:
    """For example: "10-10-0005-01  cofog_consolidated   2025-11-27   2 releases stored"."""
    releases = complete_releases(folder)
    if releases:
        count = f"{len(releases)} release{'s' if len(releases) > 1 else ''} stored"
        newest = f"{releases[-1]}   {count}"
    else:
        newest = "not downloaded"
    return f"{label:<{TABLE_NUMBER_WIDTH}}  {name:<{NAME_WIDTH}} {newest}"


def _build_lines(data_root: Path) -> list[str]:
    """One line per build, newest first: complete (with checks and time) or incomplete."""
    builds = stored_builds(data_root)
    if not builds:
        return ["none yet"]

    lines = []
    for build_id in reversed(builds[-BUILDS_SHOWN:]):
        manifest_file = serving_build_folder(build_id, data_root) / BUILD_MANIFEST_FILE_NAME
        if not manifest_file.is_file():
            lines.append(f"{build_id}  incomplete  (no manifest)")
            continue
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        checks = checks_passed(build_id, data_root)
        finished = datetime.fromisoformat(manifest["finished_at"]).strftime("%Y-%m-%d %H:%M UTC")
        lines.append(f"{build_id}  complete    {checks} checks passed   {finished}")

    hidden = len(builds) - BUILDS_SHOWN
    if hidden > 0:
        lines.append(f"({hidden} older not shown)")
    return lines


# --- Reading the command line -----------------------------------------------


def _add_approve_options(subcommand: argparse.ArgumentParser) -> None:
    """The options only "pst approve" takes."""
    subcommand.add_argument(
        "build",
        nargs="?",
        metavar="BUILD_ID",
        help="the build to approve (default: the newest complete build)",
    )


def _add_export_options(subcommand: argparse.ArgumentParser) -> None:
    """The options only "pst export" takes."""
    subcommand.add_argument(
        "--build",
        metavar="BUILD_ID",
        help="the build to export (default: the approved build)",
    )
    subcommand.add_argument(
        "--out",
        type=Path,
        default=WEB_DATA_FOLDER,
        help="folder to write the JSON files to (default: web/data)",
    )


def _add_diff_options(subcommand: argparse.ArgumentParser) -> None:
    """The options only "pst diff" takes."""
    subcommand.add_argument(
        "build",
        nargs="?",
        metavar="BUILD_ID",
        help="the build to look at (default: the newest complete build)",
    )
    subcommand.add_argument(
        "--against",
        metavar="BUILD_ID",
        help="the build to compare it with (default: the approved build)",
    )


def _add_sync_options(subcommand: argparse.ArgumentParser) -> None:
    """The options only "pst sync" takes."""
    subcommand.add_argument(
        "direction",
        choices=DIRECTIONS,
        help="pull: bucket to data/; push: data/ to bucket",
    )
    subcommand.add_argument(
        "--with-approval",
        action="store_true",
        help="when pushing, also send serving/current.json (a pull always brings it)",
    )
    subcommand.add_argument(
        "--dry-run",
        action="store_true",
        help="list what would be copied, and copy nothing",
    )
    subcommand.add_argument(
        "--bucket",
        default=DATA_BUCKET,
        help="the bucket to sync with (default: PST_DATA_BUCKET, or gs://ca-pol-econ-data)",
    )


# Every subcommand, in the order "pst --help" lists them.
SUBCOMMANDS = (extract, build, update, status, diff, approve, export, sync)

# Subcommands with options of their own, and the function that adds them.
SUBCOMMAND_OPTIONS = {
    diff: _add_diff_options,
    approve: _add_approve_options,
    export: _add_export_options,
    sync: _add_sync_options,
}

# Options every subcommand shares, which are not passed on as subcommand options.
SHARED_OPTIONS = ("run", "data_root")


def make_parser() -> argparse.ArgumentParser:
    """The pst command line: one subcommand, plus the --data-root option."""
    parser = argparse.ArgumentParser(
        prog="pst",
        description="Download Canadian government spending data and build the database.",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=DATA_ROOT,
        help="data folder to use (default: PST_DATA_ROOT, or ./data)",
    )
    subcommands = parser.add_subparsers(title="subcommands", required=True, metavar="SUBCOMMAND")
    for function in SUBCOMMANDS:
        summary = function.__doc__.splitlines()[0]
        subcommand = subcommands.add_parser(function.__name__, help=summary, description=summary)
        subcommand.set_defaults(run=function)
        if function in SUBCOMMAND_OPTIONS:
            SUBCOMMAND_OPTIONS[function](subcommand)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the subcommand given on the command line. Returns its exit code."""
    arguments = make_parser().parse_args(argv)
    options = {name: value for name, value in vars(arguments).items() if name not in SHARED_OPTIONS}
    return arguments.run(arguments.data_root, **options)


if __name__ == "__main__":
    sys.exit(main())
