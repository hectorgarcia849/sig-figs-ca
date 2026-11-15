"""Tests for the shared logging setup."""

import logging
import re

from public_spend_tracker_pipeline.logs import OUR_HANDLER, start_logging, stop_logging

# e.g. "2026-11-15 15:30:01 UTC INFO    test_logs       hello"
LINE_PATTERN = re.compile(r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d UTC (\w+)\s+(\w+)\s+(.*)$")


def our_handlers():
    return [h for h in logging.getLogger().handlers if h.get_name() == OUR_HANDLER]


def test_log_file_lines_have_time_level_step_and_message(tmp_path):
    path = start_logging("build", "20261115-153000", tmp_path)
    try:
        logging.getLogger("public_spend_tracker_pipeline.test").info("hello")
        logging.getLogger("public_spend_tracker_pipeline.test").debug("detail for the file")
    finally:
        stop_logging()

    assert path == tmp_path / "logs" / "20261115-153000-build.log"
    lines = path.read_text(encoding="utf-8").splitlines()
    assert [LINE_PATTERN.match(line).groups() for line in lines] == [
        ("INFO", "test_logs", "hello"),
        ("DEBUG", "test_logs", "detail for the file"),
    ]


def test_starting_twice_does_not_print_lines_twice(tmp_path):
    start_logging("build", "20261115-153000", tmp_path)
    start_logging("build", "20261115-153001", tmp_path)
    try:
        assert len(our_handlers()) == 2  # one screen, one file
    finally:
        stop_logging()
    assert our_handlers() == []
