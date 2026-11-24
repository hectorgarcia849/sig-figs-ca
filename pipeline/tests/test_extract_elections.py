"""Tests for the Elections Canada extractor.

These run offline: instead of Elections Canada's real server, the extractor
talks to a small fake that serves made-up files.
"""

import hashlib
import json
from datetime import date

import httpx

from public_spend_tracker_pipeline.common.paths import MANIFEST_FILE_NAME, raw_table_folder
from public_spend_tracker_pipeline.common.settings import (
    ENGLISH_AND_FRENCH,
    OPEN_GOVERNMENT_LICENCE,
    OPEN_GOVERNMENT_LICENCE_URL,
    ElectionsFile,
)
from public_spend_tracker_pipeline.extract.elections import (
    SOURCE_NAME,
    extract_all,
    extract_file,
)
from public_spend_tracker_pipeline.extract.files import ZIP_SIGNATURE

CSV_FILE = ElectionsFile(
    name="ge45_results_by_candidate",
    purpose="test file",
    title_en="Test file",
    title_fr="Fichier d'essai",
    url="https://www.elections.ca/res/rep/off/ovrGE45/62/data_donnees/table_tableau12.csv",
    listing_url="https://www.elections.ca/res/rep/off/ovrGE45/home.html",
    listing_url_fr="https://www.elections.ca/res/rep/off/ovrGE45/accueil.html",
    licence=OPEN_GOVERNMENT_LICENCE,
    licence_url=OPEN_GOVERNMENT_LICENCE_URL,
    language=ENGLISH_AND_FRENCH,
)
ZIP_FILE = ElectionsFile(
    name="federal_electoral_districts",
    purpose="test file",
    title_en="Test file",
    title_fr="Fichier d'essai",
    url="https://www.elections.ca/res/cir/mapsCorner/edb/FederalElectoralDistricts_SHP.zip",
    listing_url="https://open.canada.ca/data/en/dataset/test",
    listing_url_fr="https://ouvert.canada.ca/data/fr/dataset/test",
    licence=OPEN_GOVERNMENT_LICENCE,
    licence_url=OPEN_GOVERNMENT_LICENCE_URL,
    language=ENGLISH_AND_FRENCH,
)

DAY_ONE = date(2026, 11, 24)
DAY_TWO = date(2026, 11, 25)
LAST_MODIFIED = "Wed, 12 Nov 2025 14:28:41 GMT"
CSV_CONTENT = "﻿Province,Electoral District Name/Nom de circonscription\n".encode()

# A shortened version of the page a web server sends for a missing file.
NOT_FOUND_PAGE = (
    "<!DOCTYPE html>\n<html><head><title>Page not found - Elections Canada</title>"
    "</head><body>...</body></html>"
)


class FakeElectionsCanada:
    """Stands in for Elections Canada's server and records what was requested."""

    def __init__(self, csv_content=CSV_CONTENT, send_page=False):
        self.csv_content = csv_content
        self.send_page = send_page
        self.requested_paths: list[str] = []

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.answer))

    def file_content(self, path: str) -> bytes:
        return ZIP_SIGNATURE + b"zip contents" if path.endswith(".zip") else self.csv_content

    def answer(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.requested_paths.append(path)
        headers = {"Last-Modified": LAST_MODIFIED}
        if self.send_page:
            return httpx.Response(200, headers=headers, html=NOT_FOUND_PAGE)
        return httpx.Response(200, headers=headers, content=self.file_content(path))


def stored_folders(tmp_path, source_file=CSV_FILE) -> list[str]:
    folder = raw_table_folder(SOURCE_NAME, source_file.name, tmp_path)
    return sorted(path.name for path in folder.iterdir())


def test_downloads_new_release_with_manifest_and_licence(tmp_path):
    result = extract_file(FakeElectionsCanada().client(), CSV_FILE, tmp_path, today=DAY_ONE)

    assert result.status == "downloaded"
    assert result.release_date == DAY_ONE
    folder = raw_table_folder(SOURCE_NAME, CSV_FILE.name, tmp_path) / "release=2026-11-24"
    assert sorted(path.name for path in folder.iterdir()) == [
        MANIFEST_FILE_NAME,
        "table_tableau12.csv",
    ]
    assert (folder / "table_tableau12.csv").read_bytes() == CSV_CONTENT

    manifest = json.loads((folder / MANIFEST_FILE_NAME).read_text(encoding="utf-8"))
    assert manifest["source"] == SOURCE_NAME
    assert manifest["table_name"] == "ge45_results_by_candidate"
    assert manifest["release"] == "2026-11-24"
    assert manifest["server_last_modified"] == LAST_MODIFIED
    assert manifest["licence"] == OPEN_GOVERNMENT_LICENCE
    assert manifest["licence_url"] == OPEN_GOVERNMENT_LICENCE_URL
    assert manifest["listing_url"] == CSV_FILE.listing_url
    downloaded = manifest["files"][0]
    assert downloaded["url"] == CSV_FILE.url
    assert downloaded["language"] == ENGLISH_AND_FRENCH
    assert downloaded["sha256"] == hashlib.sha256(CSV_CONTENT).hexdigest()
    assert downloaded["size_bytes"] == len(CSV_CONTENT)


def test_zip_file_is_saved(tmp_path):
    result = extract_file(FakeElectionsCanada().client(), ZIP_FILE, tmp_path, today=DAY_ONE)

    assert result.status == "downloaded"
    saved = (
        raw_table_folder(SOURCE_NAME, ZIP_FILE.name, tmp_path)
        / "release=2026-11-24"
        / "FederalElectoralDistricts_SHP.zip"
    )
    assert saved.read_bytes().startswith(ZIP_SIGNATURE)


def test_unchanged_file_is_not_stored_again(tmp_path):
    extract_file(FakeElectionsCanada().client(), CSV_FILE, tmp_path, today=DAY_ONE)

    result = extract_file(FakeElectionsCanada().client(), CSV_FILE, tmp_path, today=DAY_TWO)

    assert result.status == "already_current"
    assert result.release_date == DAY_ONE
    assert stored_folders(tmp_path) == ["release=2026-11-24"]  # no temporary folder left


def test_changed_file_is_stored_beside_the_old_one(tmp_path):
    extract_file(FakeElectionsCanada().client(), CSV_FILE, tmp_path, today=DAY_ONE)
    changed = FakeElectionsCanada(csv_content=b"Province,Corrected results\n")

    result = extract_file(changed.client(), CSV_FILE, tmp_path, today=DAY_TWO)

    assert result.status == "downloaded"
    assert stored_folders(tmp_path) == ["release=2026-11-24", "release=2026-11-25"]


def test_file_is_checked_at_most_once_a_day(tmp_path):
    extract_file(FakeElectionsCanada().client(), CSV_FILE, tmp_path, today=DAY_ONE)
    fake = FakeElectionsCanada(csv_content=b"Province,Changed later the same day\n")

    result = extract_file(fake.client(), CSV_FILE, tmp_path, today=DAY_ONE)

    assert result.status == "already_current"
    assert fake.requested_paths == []


def test_web_page_instead_of_file_is_never_saved(tmp_path):
    results = extract_all(FakeElectionsCanada(send_page=True).client(), (CSV_FILE,), tmp_path)

    assert results[0].status == "failed"
    assert results[0].message == (
        'Elections Canada sent something else ("Page not found - Elections Canada") '
        "instead of the file table_tableau12.csv."
    )
    assert stored_folders(tmp_path) == []


def test_zip_file_that_is_not_a_zip_is_never_saved(tmp_path):
    class NotAZip(FakeElectionsCanada):
        def file_content(self, path: str) -> bytes:
            return b"plain text"

    results = extract_all(NotAZip().client(), (ZIP_FILE,), tmp_path)

    assert results[0].status == "failed"
    assert "instead of the file FederalElectoralDistricts_SHP.zip" in results[0].message
    assert stored_folders(tmp_path, ZIP_FILE) == []


def test_one_failure_does_not_stop_the_other_files(tmp_path):
    class MissingCsv(FakeElectionsCanada):
        def answer(self, request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith(".csv"):
                return httpx.Response(404)
            return super().answer(request)

    results = extract_all(MissingCsv().client(), (CSV_FILE, ZIP_FILE), tmp_path)

    assert [result.status for result in results] == ["failed", "downloaded"]
    assert "404" in results[0].message
    assert stored_folders(tmp_path) == []
