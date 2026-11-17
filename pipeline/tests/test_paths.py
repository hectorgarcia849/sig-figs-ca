"""Tests for where data files live. They run in a temporary folder."""

from datetime import UTC, date, datetime
from pathlib import Path

from public_spend_tracker_pipeline.common.paths import (
    MANIFEST_FILE_NAME,
    complete_releases,
    current_build_file,
    model_file,
    new_build_id,
    raw_release_folder,
    raw_table_folder,
    serving_build_folder,
    staged_file,
)

ROOT = Path("data")
RELEASE = date(2025, 11, 27)
BUILD_ID = "20261114-153000"


def test_each_path_matches_the_agreed_layout():
    assert raw_table_folder("statcan", "10100005", ROOT) == Path(
        "data/raw/source=statcan/table=10100005"
    )
    assert raw_release_folder("statcan", "10100005", RELEASE, ROOT) == Path(
        "data/raw/source=statcan/table=10100005/release=2025-11-27"
    )
    assert staged_file("cofog_consolidated", RELEASE, ROOT) == Path(
        "data/staged/dataset=cofog_consolidated/release=2025-11-27/data.parquet"
    )
    assert model_file("spending", BUILD_ID, ROOT) == Path(
        "data/model/dataset=spending/build=20261114-153000/data.parquet"
    )
    assert serving_build_folder(BUILD_ID, ROOT) == Path("data/serving/build=20261114-153000")
    assert current_build_file(ROOT) == Path("data/serving/current.json")


def make_release(table_folder: Path, release: str, with_manifest: bool = True) -> None:
    """Create a release folder, with or without its manifest."""
    folder = table_folder / f"release={release}"
    folder.mkdir(parents=True)
    if with_manifest:
        (folder / MANIFEST_FILE_NAME).write_text("{}")


def test_complete_releases_are_listed_oldest_first(tmp_path):
    make_release(tmp_path, "2025-11-27")
    make_release(tmp_path, "2024-11-28")
    make_release(tmp_path, "2026-11-26")
    assert complete_releases(tmp_path) == [
        date(2024, 11, 28),
        date(2025, 11, 27),
        date(2026, 11, 26),
    ]


def test_unfinished_and_stray_items_are_ignored(tmp_path):
    make_release(tmp_path, "2025-11-27")
    make_release(tmp_path, "2026-11-26", with_manifest=False)  # download never finished
    (tmp_path / ".incomplete-abc123").mkdir()  # download in progress
    (tmp_path / "notes.txt").write_text("stray file")
    assert complete_releases(tmp_path) == [date(2025, 11, 27)]


def test_missing_table_folder_has_no_releases(tmp_path):
    assert complete_releases(tmp_path / "never_downloaded") == []


def test_build_id_format():
    moment = datetime(2026, 11, 14, 15, 30, 0, tzinfo=UTC)
    assert new_build_id(moment) == BUILD_ID


def test_build_ids_sort_in_time_order():
    earlier = new_build_id(datetime(2026, 9, 30, 23, 59, 59, tzinfo=UTC))
    later = new_build_id(datetime(2026, 11, 14, 8, 0, 0, tzinfo=UTC))
    assert sorted([later, earlier]) == [earlier, later]
