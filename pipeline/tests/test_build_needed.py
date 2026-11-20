"""Tests for deciding whether a new build is needed (pst update)."""

import json
from datetime import date

from public_spend_tracker_pipeline.build.needed import reasons_to_build
from public_spend_tracker_pipeline.common.paths import (
    BUILD_MANIFEST_FILE_NAME,
    MANIFEST_FILE_NAME,
    raw_release_folder,
    serving_build_folder,
)
from public_spend_tracker_pipeline.common.settings import STATCAN_TABLES

RELEASE = date(2025, 11, 27)
NEWER = date(2026, 11, 26)
BUILD = "20261116-164845"


def download(data_root, table, release):
    folder = raw_release_folder("statcan", table.product_id, release, data_root)
    folder.mkdir(parents=True)
    (folder / MANIFEST_FILE_NAME).write_text("{}", encoding="utf-8")


def make_build(data_root, build_id, releases, complete=True):
    folder = serving_build_folder(build_id, data_root)
    folder.mkdir(parents=True)
    if complete:
        sources = [
            {"table_name": table.name, "release": release.isoformat()}
            for table, release in releases.items()
        ]
        manifest = {"build_id": build_id, "sources": sources}
        (folder / BUILD_MANIFEST_FILE_NAME).write_text(json.dumps(manifest), encoding="utf-8")


def every_table_downloaded(data_root):
    for table in STATCAN_TABLES:
        download(data_root, table, RELEASE)
    return dict.fromkeys(STATCAN_TABLES, RELEASE)


def test_a_build_is_needed_when_there_is_none(tmp_path):
    every_table_downloaded(tmp_path)
    assert reasons_to_build(tmp_path) == ["there is no complete build yet"]


def test_no_build_is_needed_when_the_newest_build_uses_every_download(tmp_path):
    make_build(tmp_path, BUILD, every_table_downloaded(tmp_path))
    assert reasons_to_build(tmp_path) == []


def test_a_new_release_needs_a_build(tmp_path):
    make_build(tmp_path, BUILD, every_table_downloaded(tmp_path))
    first = STATCAN_TABLES[0]
    download(tmp_path, first, NEWER)
    assert reasons_to_build(tmp_path) == [
        f"{first.name}: release 2026-11-26 is not in build {BUILD} (it used 2025-11-27)"
    ]


def test_an_unfinished_build_does_not_count(tmp_path):
    releases = every_table_downloaded(tmp_path)
    make_build(tmp_path, BUILD, releases)
    first = STATCAN_TABLES[0]
    download(tmp_path, first, NEWER)
    make_build(tmp_path, "20261126-153000", {}, complete=False)  # failed: no manifest
    assert len(reasons_to_build(tmp_path)) == 1  # still compared with the last complete build
