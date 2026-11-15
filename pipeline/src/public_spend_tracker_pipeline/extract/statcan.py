"""Download Statistics Canada tables exactly as published.

For each table we use (listed in settings.STATCAN_TABLES), this asks Statistics
Canada for the date of the table's latest release. If we have not stored that
release yet, it downloads the table (one zip file per language), saves the
files untouched, and writes a manifest saying what was downloaded, from where
and when.

It never opens or changes the downloaded files. Cleaning them up is the job of
the transformers.

Where one release ends up:

    data/raw/source=statcan/table=10100005/release=2025-11-27/
        10100005-eng.zip   the table, English
        10100005-fra.zip   the table, French
        metadata.json      Statistics Canada's description of the table
        _manifest.json     what we downloaded, from where, when

Files are first written to a temporary folder, which is renamed to the release
folder only once everything has downloaded. So a release folder always holds a
complete download, and a failed run leaves nothing behind: the next run simply
tries again.

Run it on its own from the repository root with:

    uv run python -m public_spend_tracker_pipeline.extract.statcan
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import ssl
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

import httpx

from public_spend_tracker_pipeline.settings import (
    DATA_ROOT,
    HTTP_MAX_ATTEMPTS,
    HTTP_TIMEOUT_SECONDS,
    STATCAN_API_URL,
    STATCAN_TABLES,
    TLS_KEY_EXCHANGE,
    USER_AGENT,
    StatCanTable,
)

log = logging.getLogger(__name__)

# Name of this source in folder paths and manifests.
SOURCE_NAME = "statcan"

# Files we write next to the downloaded tables.
MANIFEST_FILE_NAME = "_manifest.json"
METADATA_FILE_NAME = "metadata.json"

# Start of the name of the temporary folder used while downloading.
TEMP_FOLDER_PREFIX = ".incomplete-"

# Downloads are read and written in pieces of this size, so large files never
# need to fit in memory at once.
DOWNLOAD_CHUNK_BYTES = 1024 * 1024

# The status Statistics Canada's API reports when a request worked.
STATCAN_SUCCESS = "SUCCESS"


class StatCanError(Exception):
    """Statistics Canada answered, but not with the data we asked for."""


@dataclass(frozen=True)
class TableDetails:
    """What we need to know about a table before downloading it.

    release_time     When Statistics Canada published the latest release,
                     exactly as they write it, e.g. "2025-11-27T08:30".
    reference_start  First period the table covers, e.g. "2008-01-01".
    reference_end    Last period the table covers.
    raw_response     Statistics Canada's full answer, saved as metadata.json.
    """

    product_id: str
    title_en: str
    title_fr: str
    release_time: str
    reference_start: str
    reference_end: str
    raw_response: bytes

    @property
    def release_date(self) -> date:
        """The calendar day of the latest release."""
        return date.fromisoformat(self.release_time[:10])


@dataclass(frozen=True)
class DownloadedFile:
    """One file we downloaded, with a fingerprint to prove what it contained.

    sha256  A fingerprint of the file's contents. If even one byte changes,
            the fingerprint changes, so it shows the file is exactly what we
            downloaded.
    """

    name: str
    language: str
    url: str
    sha256: str
    size_bytes: int


ExtractStatus = Literal["downloaded", "already_current", "failed"]


@dataclass(frozen=True)
class ExtractResult:
    """What happened when we tried to extract one table."""

    table: StatCanTable
    status: ExtractStatus
    release_date: date | None = None
    message: str = ""

    def describe(self) -> str:
        """One line for the log.

        For example: "10100005 cofog_consolidated: downloaded release 2025-11-27".
        """
        label = f"{self.table.product_id} {self.table.name}"
        if self.status == "downloaded":
            return f"{label}: downloaded release {self.release_date}"
        if self.status == "already_current":
            return f"{label}: already have release {self.release_date}"
        return f"{label}: FAILED - {self.message}"


# --- Asking Statistics Canada -----------------------------------------------


def fetch_table_details(client: httpx.Client, product_id: str) -> TableDetails:
    """Ask Statistics Canada for a table's titles, coverage and latest release date."""
    response = client.post(
        f"{STATCAN_API_URL}/getCubeMetadata",
        json=[{"productId": int(product_id)}],
    )
    response.raise_for_status()
    table = _unwrap(response.json()[0], f"the details of table {product_id}")
    try:
        return TableDetails(
            product_id=product_id,
            title_en=table["cubeTitleEn"],
            title_fr=table["cubeTitleFr"],
            release_time=table["releaseTime"],
            reference_start=table["cubeStartDate"],
            reference_end=table["cubeEndDate"],
            raw_response=response.content,
        )
    except KeyError as missing:
        raise StatCanError(
            f"Statistics Canada's details for table {product_id} are missing {missing}"
        ) from None


def fetch_download_url(client: httpx.Client, product_id: str, language: str) -> str:
    """Ask Statistics Canada for the link to a table's full download in one language."""
    response = client.get(f"{STATCAN_API_URL}/getFullTableDownloadCSV/{product_id}/{language}")
    response.raise_for_status()
    return _unwrap(response.json(), f"a download link for table {product_id} ({language})")


def _unwrap(answer: dict, what: str):
    """Return the useful part of a Statistics Canada answer, or raise a clear error.

    Every answer from their API looks like {"status": ..., "object": ...}. When
    the status is not "SUCCESS", "object" holds their explanation instead of data.
    """
    if answer.get("status") != STATCAN_SUCCESS:
        raise StatCanError(f"Statistics Canada could not provide {what}: {answer.get('object')}")
    return answer["object"]


# --- Downloading and saving -------------------------------------------------


def download_file(client: httpx.Client, url: str, folder: Path, language: str) -> DownloadedFile:
    """Download one file into a folder, fingerprinting it as it arrives."""
    name = url.rsplit("/", 1)[-1]
    fingerprint = hashlib.sha256()
    size_bytes = 0
    with client.stream("GET", url) as response:
        response.raise_for_status()
        with open(folder / name, "wb") as file:
            for chunk in response.iter_bytes(DOWNLOAD_CHUNK_BYTES):
                file.write(chunk)
                fingerprint.update(chunk)
                size_bytes += len(chunk)
    return DownloadedFile(
        name=name,
        language=language,
        url=url,
        sha256=fingerprint.hexdigest(),
        size_bytes=size_bytes,
    )


def write_manifest(
    folder: Path, table: StatCanTable, details: TableDetails, files: list[DownloadedFile]
) -> None:
    """Write the manifest: the record of what we downloaded, from where and when."""
    manifest = {
        "source": SOURCE_NAME,
        "product_id": table.product_id,
        "table_name": table.name,
        "title_en": details.title_en,
        "title_fr": details.title_fr,
        "release_time": details.release_time,
        "reference_period": {
            "start": details.reference_start,
            "end": details.reference_end,
        },
        "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "files": [asdict(file) for file in files],
    }
    text = json.dumps(manifest, indent=2, ensure_ascii=False)
    (folder / MANIFEST_FILE_NAME).write_text(text + "\n", encoding="utf-8")


def raw_table_folder(data_root: Path, table: StatCanTable) -> Path:
    """The folder holding every release we have stored for a table."""
    return data_root / "raw" / f"source={SOURCE_NAME}" / f"table={table.product_id}"


# --- Putting it together ----------------------------------------------------


def extract_table(
    client: httpx.Client, table: StatCanTable, data_root: Path = DATA_ROOT
) -> ExtractResult:
    """Download a table's latest release, unless we already have it."""
    details = fetch_table_details(client, table.product_id)
    table_folder = raw_table_folder(data_root, table)
    release_folder = table_folder / f"release={details.release_date.isoformat()}"

    if (release_folder / MANIFEST_FILE_NAME).exists():
        return ExtractResult(table, "already_current", details.release_date)
    if release_folder.exists():
        raise StatCanError(
            f"{release_folder} exists but has no manifest, so it is incomplete. "
            "Delete that folder and run again."
        )

    table_folder.mkdir(parents=True, exist_ok=True)
    temp_folder = Path(tempfile.mkdtemp(prefix=TEMP_FOLDER_PREFIX, dir=table_folder))
    try:
        files = [
            download_file(
                client,
                fetch_download_url(client, table.product_id, language),
                temp_folder,
                language,
            )
            for language in table.languages
        ]
        (temp_folder / METADATA_FILE_NAME).write_bytes(details.raw_response)
        write_manifest(temp_folder, table, details, files)
        temp_folder.rename(release_folder)
    finally:
        # Only still there if something above failed: remove the partial download.
        shutil.rmtree(temp_folder, ignore_errors=True)

    return ExtractResult(table, "downloaded", details.release_date)


def extract_all(
    client: httpx.Client,
    tables: tuple[StatCanTable, ...] = STATCAN_TABLES,
    data_root: Path = DATA_ROOT,
) -> list[ExtractResult]:
    """Extract every table. A failure on one table does not stop the others."""
    results = []
    for table in tables:
        try:
            result = extract_table(client, table, data_root)
        except (StatCanError, httpx.HTTPError) as error:
            result = ExtractResult(table, "failed", message=str(error))
        log.info(result.describe())
        results.append(result)
    return results


def open_client() -> httpx.Client:
    """A web client set up for Statistics Canada.

    Retries only cover failed connections for now. http_client.py (the next
    script) will replace this with retries on server errors too.
    """
    encryption = ssl.create_default_context()
    encryption.set_ecdh_curve(TLS_KEY_EXCHANGE)  # see settings.TLS_KEY_EXCHANGE for why
    return httpx.Client(
        timeout=HTTP_TIMEOUT_SECONDS,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        transport=httpx.HTTPTransport(verify=encryption, retries=HTTP_MAX_ATTEMPTS - 1),
    )


def main() -> int:
    """Extract every table and report. Returns 1 if any table failed, else 0."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    # httpx logs every request at INFO level; keep our output to one line per table.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    with open_client() as client:
        results = extract_all(client)
    failed = [result for result in results if result.status == "failed"]
    if failed:
        log.error(f"{len(failed)} of {len(results)} tables failed.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
