"""Download new releases from every source: what "pst extract" runs.

Runs each source's extractor in turn with one connection and one log file. A
failure in one source does not stop the others, but makes the whole run count
as failed, so "pst update" will not build from data that may be out of date.
"""

from __future__ import annotations

import logging
from pathlib import Path

from public_spend_tracker_pipeline.common.http_client import open_client
from public_spend_tracker_pipeline.common.logs import start_logging, stop_logging
from public_spend_tracker_pipeline.common.paths import new_build_id
from public_spend_tracker_pipeline.common.settings import DATA_ROOT
from public_spend_tracker_pipeline.extract import elections, statcan

log = logging.getLogger(__name__)

SUCCESS = 0
FAILURE = 1


def run_extract(data_root: Path = DATA_ROOT) -> int:
    """Extract every source into a data folder and report. Returns 1 if anything failed, else 0."""
    log_path = start_logging("extract", new_build_id(), data_root)
    try:
        with open_client() as client:
            results = statcan.extract_all(client, data_root=data_root)
            results += elections.extract_all(client, data_root=data_root)
        failed = [result for result in results if result.status == "failed"]
        if failed:
            log.error(f"{len(failed)} of {len(results)} downloads failed. Log: {log_path}")
            return FAILURE
        return SUCCESS
    finally:
        stop_logging()
