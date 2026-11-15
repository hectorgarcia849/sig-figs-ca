"""Logging, set up once for every pipeline command.

Each run of a command (extract, build) calls start_logging(), which sends
every message to two places:

    the screen  short lines: just the message
    a log file  one per run, e.g. data/logs/20261115-153000-build.log, where
                every line has the time (UTC, like build IDs), level and step,
                errors include their full details, and extra detail lines
                (DEBUG) that would clutter the screen are kept too

Problems that need attention always start with one of two markers, so
searching the logs for them finds every one:

    SOURCE CHANGED  Statistics Canada changed a table's layout
    CHECK FAILED    a dataset did not pass one of its checks

For example:

    2026-11-15 15:30:01 UTC DEBUG   staged_statcan  10100005 cofog_consolidated ...: read 15,300
    2026-11-15 15:30:03 UTC ERROR   build           SOURCE CHANGED 10100024 cofog_by_component ...
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

from public_spend_tracker_pipeline.paths import log_file
from public_spend_tracker_pipeline.settings import DATA_ROOT

# Markers that start every message about a problem needing attention.
SOURCE_CHANGED = "SOURCE CHANGED"
CHECK_FAILED = "CHECK FAILED"

# How lines look on the screen and in the log file. The step is the name of
# the file the message came from, e.g. "build" or "staged_statcan".
SCREEN_FORMAT = "%(message)s"
FILE_FORMAT = "%(asctime)s %(levelname)-7s %(module)-15s %(message)s"
FILE_DATE_FORMAT = "%Y-%m-%d %H:%M:%S UTC"

# Libraries that log every web request; we only want their warnings.
NOISY_LIBRARIES = ("httpx", "httpcore")

# Marks the handlers we add, so starting logging again replaces them
# instead of printing every line twice.
OUR_HANDLER = "public_spend_tracker"


def start_logging(run_name: str, run_id: str, data_root: Path = DATA_ROOT) -> Path:
    """Send log messages to the screen and to this run's log file. Returns the file's path.

    run_name  The command, e.g. "build" or "extract".
    run_id    When the run started, e.g. "20261115-153000" (see paths.new_build_id).
    """
    path = log_file(run_id, run_name, data_root)
    path.parent.mkdir(parents=True, exist_ok=True)

    screen = logging.StreamHandler(sys.stderr)
    screen.setLevel(logging.INFO)
    screen.setFormatter(logging.Formatter(SCREEN_FORMAT))

    file_format = logging.Formatter(FILE_FORMAT, datefmt=FILE_DATE_FORMAT)
    file_format.converter = time.gmtime  # UTC, like build IDs
    file = logging.FileHandler(path, encoding="utf-8")
    file.setLevel(logging.DEBUG)
    file.setFormatter(file_format)

    stop_logging()
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    for handler in (screen, file):
        handler.set_name(OUR_HANDLER)
        root.addHandler(handler)
    for library in NOISY_LIBRARIES:
        logging.getLogger(library).setLevel(logging.WARNING)
    return path


def stop_logging() -> None:
    """Finish writing and close the handlers start_logging added."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        if handler.get_name() == OUR_HANDLER:
            root.removeHandler(handler)
            handler.close()
