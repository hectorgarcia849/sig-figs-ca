"""The pst command: one front door to the pipeline.

    pst extract   download new Statistics Canada releases
    pst build     build and check the database from everything downloaded
    pst update    extract, then build: the everyday command
    pst status    show downloads, builds and the approved build (changes nothing)

Run it from anywhere in the repository with "uv run pst <subcommand>".

Every subcommand accepts --data-root to use another data folder, e.g.
"pst --data-root /tmp/test build". Without it, the PST_DATA_ROOT environment
variable is used, and without that, ./data.

Exit codes: 0 when everything worked, 1 when anything failed.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from public_spend_tracker_pipeline.build import build_everything
from public_spend_tracker_pipeline.extract.statcan import SOURCE_NAME, run_extract
from public_spend_tracker_pipeline.paths import (
    BUILD_MANIFEST_FILE_NAME,
    complete_releases,
    current_build_file,
    raw_table_folder,
    serving_build_folder,
    stored_builds,
)
from public_spend_tracker_pipeline.settings import DATA_ROOT, STATCAN_TABLES
from public_spend_tracker_pipeline.transform.model_sources import table_number

# How many builds "pst status" lists, newest first.
BUILDS_SHOWN = 10

SUCCESS = 0
FAILURE = 1


# --- Subcommands ------------------------------------------------------------


def extract(data_root: Path) -> int:
    """Download new Statistics Canada releases."""
    return run_extract(data_root)


def build(data_root: Path) -> int:
    """Build and check the database from everything downloaded."""
    return build_everything(data_root)


def update(data_root: Path) -> int:
    """Extract, then build. Stops before building if any download failed.

    A failed download could mean a new release was missed, so it is better to
    find out than to build from data that may be out of date.
    """
    if run_extract(data_root) != SUCCESS:
        print("Some downloads failed, so nothing was built.", file=sys.stderr)
        return FAILURE
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
    print(f"Approved build: {_approved_build(data_root)}")
    return SUCCESS


# --- What "status" shows ----------------------------------------------------


def _download_lines(data_root: Path) -> list[str]:
    """One line per table: its newest release and how many releases are stored."""
    lines = []
    for table in STATCAN_TABLES:
        releases = complete_releases(raw_table_folder(SOURCE_NAME, table.product_id, data_root))
        if releases:
            count = f"{len(releases)} release{'s' if len(releases) > 1 else ''} stored"
            newest = f"{releases[-1]}   {count}"
        else:
            newest = "not downloaded"
        lines.append(f"{table_number(table.product_id)}  {table.name:<24} {newest}")
    return lines


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
        checks = sum(len(dataset["checks"]) for dataset in manifest["datasets"])
        if manifest.get("serving"):
            checks += len(manifest["serving"]["checks"])
        finished = datetime.fromisoformat(manifest["finished_at"]).strftime("%Y-%m-%d %H:%M UTC")
        lines.append(f"{build_id}  complete    {checks} checks passed   {finished}")

    hidden = len(builds) - BUILDS_SHOWN
    if hidden > 0:
        lines.append(f"({hidden} older not shown)")
    return lines


def _approved_build(data_root: Path) -> str:
    """The build recorded in serving/current.json, or "none yet"."""
    path = current_build_file(data_root)
    if not path.is_file():
        return "none yet"
    return json.loads(path.read_text(encoding="utf-8")).get("build_id", "unknown")


# --- Reading the command line -----------------------------------------------


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
    for function in (extract, build, update, status):
        summary = function.__doc__.splitlines()[0]
        subcommand = subcommands.add_parser(function.__name__, help=summary, description=summary)
        subcommand.set_defaults(run=function)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the subcommand given on the command line. Returns its exit code."""
    arguments = make_parser().parse_args(argv)
    return arguments.run(arguments.data_root)


if __name__ == "__main__":
    sys.exit(main())
