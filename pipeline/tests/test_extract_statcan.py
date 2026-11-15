"""Tests for the Statistics Canada extractor.

These run offline: instead of the real Statistics Canada servers, the extractor
talks to a small fake that answers the same three kinds of request (table
details, download link, file download) with made-up content.
"""

import hashlib
import json

import httpx
import pytest

from public_spend_tracker_pipeline.extract.statcan import (
    MANIFEST_FILE_NAME,
    METADATA_FILE_NAME,
    StatCanError,
    extract_all,
    extract_table,
    raw_table_folder,
)
from public_spend_tracker_pipeline.settings import ENGLISH, FRENCH, StatCanTable

TABLE = StatCanTable(
    product_id="10100005",
    name="cofog_consolidated",
    purpose="test table",
    languages=(ENGLISH, FRENCH),
)
RELEASE_TIME = "2025-11-27T08:30"
RELEASE_FOLDER = "release=2025-11-27"
FILE_SUFFIX = {ENGLISH: "eng", FRENCH: "fra"}


class FakeStatCan:
    """Stands in for Statistics Canada's servers and records what was requested."""

    def __init__(self, release_time=RELEASE_TIME, details_status="SUCCESS", fail_downloads=False):
        self.release_time = release_time
        self.details_status = details_status
        self.fail_downloads = fail_downloads
        self.downloaded_paths: list[str] = []

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.answer))

    @staticmethod
    def file_content(name: str) -> bytes:
        return f"zip contents of {name}".encode()

    def answer(self, request: httpx.Request) -> httpx.Response:
        
        path = request.url.path
        response = httpx.Response(404, json={"status": "FAILED", "object": "Not found"})

        if path.endswith("/getCubeMetadata"):
            
            if self.details_status != "SUCCESS":
                response = httpx.Response(200, json=[{"status": "FAILED", "object": "No such table"}])

            else:
                details = {
                    "cubeTitleEn": "Test table",
                    "cubeTitleFr": "Tableau d'essai",
                    "releaseTime": self.release_time,
                    "cubeStartDate": "2008-01-01",
                    "cubeEndDate": "2024-01-01",
                }
                
                response = httpx.Response(200, json=[{"status": "SUCCESS", "object": details}])
        
        elif "/getFullTableDownloadCSV/" in path:
            product_id, language = path.split("/")[-2:]
            url = (
                f"https://www150.statcan.gc.ca/n1/tbl/csv/{product_id}-{FILE_SUFFIX[language]}.zip"
            )
            response = httpx.Response(200, json={"status": "SUCCESS", "object": url})
        
        elif path.endswith(".zip"):
            self.downloaded_paths.append(path)
            
            if self.fail_downloads:
                response = httpx.Response(500)
            else:
                response = httpx.Response(200, content=self.file_content(path.rsplit("/", 1)[-1]))

        return response


def test_downloads_new_release_with_manifest(tmp_path):
    fake = FakeStatCan()

    result = extract_table(fake.client(), TABLE, data_root=tmp_path)

    assert result.status == "downloaded"
    release = raw_table_folder(tmp_path, TABLE) / RELEASE_FOLDER
    
    assert sorted(path.name for path in release.iterdir()) == [
        "10100005-eng.zip",
        "10100005-fra.zip",
        MANIFEST_FILE_NAME,
        METADATA_FILE_NAME,
    ]
    
    manifest = json.loads((release / MANIFEST_FILE_NAME).read_text(encoding="utf-8"))
    assert manifest["product_id"] == "10100005"
    assert manifest["release_time"] == RELEASE_TIME
    assert manifest["title_fr"] == "Tableau d'essai"
    english = manifest["files"][0]
    expected = FakeStatCan.file_content("10100005-eng.zip")
    assert english["language"] == ENGLISH
    assert english["sha256"] == hashlib.sha256(expected).hexdigest()
    assert english["size_bytes"] == len(expected)


def test_skips_release_already_stored(tmp_path):
    extract_table(FakeStatCan().client(), TABLE, data_root=tmp_path)
    fake = FakeStatCan()

    result = extract_table(fake.client(), TABLE, data_root=tmp_path)

    assert result.status == "already_current"
    assert fake.downloaded_paths == []


def test_new_release_is_stored_beside_the_old_one(tmp_path):
    extract_table(FakeStatCan().client(), TABLE, data_root=tmp_path)

    extract_table(FakeStatCan(release_time="2026-11-26T08:30").client(), TABLE, data_root=tmp_path)

    folders = sorted(path.name for path in raw_table_folder(tmp_path, TABLE).iterdir())
    assert folders == [RELEASE_FOLDER, "release=2026-11-26"]


def test_failed_download_leaves_nothing_behind(tmp_path):
    results = extract_all(FakeStatCan(fail_downloads=True).client(), (TABLE,), data_root=tmp_path)

    assert results[0].status == "failed"
    assert list(raw_table_folder(tmp_path, TABLE).iterdir()) == []


def test_error_from_statcan_names_the_table(tmp_path):
    fake = FakeStatCan(details_status="FAILED")

    with pytest.raises(StatCanError, match="10100005.*No such table"):
        extract_table(fake.client(), TABLE, data_root=tmp_path)
