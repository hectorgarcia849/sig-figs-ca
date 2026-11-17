"""Where every data file lives.

Every pipeline step asks this module where to read and write, so no other
module puts a folder path together itself. The layout is the same locally
(under ./data) and, later, in the cloud bucket, so syncing to the cloud is a
plain copy of the folder tree.

    data/
    ├── raw/source=statcan/table=10100005/release=2025-11-27/
    │       files exactly as downloaded, plus _manifest.json
    ├── staged/dataset=cofog_consolidated/release=2025-11-27/data.parquet
    │       one cleaned dataset per source table release
    ├── model/dataset=spending/build=20261114-153000/data.parquet
    │       the joined-up tables, produced by one build
    ├── serving/
    │   ├── build=20261114-153000/fiscal.duckdb + build_manifest.json
    │   └── current.json      record of the approved build
    └── logs/20261114-153000-build.log
            one log file per run of a pipeline command

Folders below the top level are named "label=value". DuckDB and other tools
read that pattern as a column, so a release date or build ID can be read
straight from the path.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from public_spend_tracker_pipeline.common.settings import DATA_ROOT

# --- The four stages --------------------------------------------------------

RAW = "raw"  # files exactly as downloaded, never changed, kept forever
STAGED = "staged"  # cleaned and typed, one dataset per source table
MODEL = "model"  # the joined-up tables the site is built on
SERVING = "serving"  # the database file the API serves

# Not a stage: one log file per run of a pipeline command.
LOGS = "logs"

# While a build runs, its staged files are written to a temporary work folder
# with this name start, and moved into place only if the whole build passes.
BUILD_WORK_FOLDER_PREFIX = ".building-"

# --- Names inside the folders -----------------------------------------------

# The written record of a completed download. Every extractor writes one, last,
# so a release folder only counts as complete once this file is in it.
MANIFEST_FILE_NAME = "_manifest.json"

# The single data file inside every staged and model folder.
PARQUET_FILE_NAME = "data.parquet"

# Inside each serving build folder: the database and the record of how it was built.
DATABASE_FILE_NAME = "fiscal.duckdb"
BUILD_MANIFEST_FILE_NAME = "build_manifest.json"

# The record of which build was approved and released.
CURRENT_BUILD_FILE_NAME = "current.json"

# Labels in "label=value" folder names.
RELEASE_LABEL = "release"
BUILD_LABEL = "build"

# Build IDs are the UTC date and time a build started, e.g. "20261114-153000".
# No colons (they cause trouble in file and cloud paths), and IDs sort in time order.
BUILD_ID_FORMAT = "%Y%m%d-%H%M%S"


# --- Raw: files as downloaded -----------------------------------------------


def raw_table_folder(source: str, table: str, data_root: Path = DATA_ROOT) -> Path:
    """The folder holding every stored release of one table.

    For example: data/raw/source=statcan/table=10100005
    """
    return data_root / RAW / f"source={source}" / f"table={table}"


def raw_release_folder(source: str, table: str, release: date, data_root: Path = DATA_ROOT) -> Path:
    """The folder holding one release of one table.

    For example: data/raw/source=statcan/table=10100005/release=2025-11-27
    """
    return raw_table_folder(source, table, data_root) / _labelled(
        RELEASE_LABEL, release.isoformat()
    )


def complete_releases(table_folder: Path) -> list[date]:
    """The release dates fully downloaded into a table folder, oldest first.

    A release counts only once its manifest has been written. Anything else in
    the folder (a temporary download folder, a release folder missing its
    manifest, a stray file) is ignored, so half-finished downloads are never read.
    """
    if not table_folder.is_dir():
        return []
    prefix = f"{RELEASE_LABEL}="
    releases = [
        date.fromisoformat(folder.name.removeprefix(prefix))
        for folder in table_folder.iterdir()
        if folder.name.startswith(prefix) and (folder / MANIFEST_FILE_NAME).is_file()
    ]
    return sorted(releases)


# --- Staged and model: Parquet datasets -------------------------------------


def staged_file(dataset: str, release: date, data_root: Path = DATA_ROOT) -> Path:
    """The Parquet file for one cleaned dataset, made from one source release.

    For example: data/staged/dataset=cofog_consolidated/release=2025-11-27/data.parquet
    """
    release_folder = _labelled(RELEASE_LABEL, release.isoformat())
    return data_root / STAGED / f"dataset={dataset}" / release_folder / PARQUET_FILE_NAME


def model_file(dataset: str, build_id: str, data_root: Path = DATA_ROOT) -> Path:
    """The Parquet file for one model table, produced by one build.

    For example: data/model/dataset=spending/build=20261114-153000/data.parquet
    """
    build_folder = _labelled(BUILD_LABEL, build_id)
    return data_root / MODEL / f"dataset={dataset}" / build_folder / PARQUET_FILE_NAME


# --- Serving: the database the API serves -----------------------------------


def serving_build_folder(build_id: str, data_root: Path = DATA_ROOT) -> Path:
    """The folder holding one build's database and build manifest.

    For example: data/serving/build=20261114-153000
    """
    return data_root / SERVING / _labelled(BUILD_LABEL, build_id)


def stored_builds(data_root: Path = DATA_ROOT) -> list[str]:
    """The IDs of every build folder in serving/, oldest first, complete or not."""
    serving = data_root / SERVING
    if not serving.is_dir():
        return []
    prefix = f"{BUILD_LABEL}="
    return sorted(
        folder.name.removeprefix(prefix)
        for folder in serving.iterdir()
        if folder.is_dir() and folder.name.startswith(prefix)
    )


def current_build_file(data_root: Path = DATA_ROOT) -> Path:
    """The record of which build was approved and released: data/serving/current.json"""
    return data_root / SERVING / CURRENT_BUILD_FILE_NAME


def new_build_id(now: datetime | None = None) -> str:
    """A new build ID from the current UTC time, e.g. "20261114-153000".

    Pass `now` to get the ID for a particular moment (used by tests).
    """
    return (now or datetime.now(UTC)).strftime(BUILD_ID_FORMAT)


def _labelled(label: str, value: str) -> str:
    """A "label=value" folder name, e.g. "release=2025-11-27"."""
    return f"{label}={value}"


# --- Logs and build work ------------------------------------------------------


def log_file(run_id: str, run_name: str, data_root: Path = DATA_ROOT) -> Path:
    """The log file for one run of a pipeline command.

    For example: data/logs/20261114-153000-build.log
    """
    return data_root / LOGS / f"{run_id}-{run_name}.log"


def build_work_folder(build_id: str, data_root: Path = DATA_ROOT) -> Path:
    """The temporary folder a build writes its staged files to before moving them into place.

    For example: data/.building-20261114-153000
    """
    return data_root / f"{BUILD_WORK_FOLDER_PREFIX}{build_id}"
