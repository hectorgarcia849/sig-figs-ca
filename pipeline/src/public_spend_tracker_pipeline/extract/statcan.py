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
folder only once everything has downloaded (see extract/files.py). So a release
folder always holds a complete download, and a failed run leaves nothing behind.

"pst extract" runs this together with the other sources.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import httpx

from public_spend_tracker_pipeline.common.paths import (
    MANIFEST_FILE_NAME,
    raw_release_folder,
)
from public_spend_tracker_pipeline.common.settings import (
    DATA_ROOT,
    STATCAN_API_URL,
    STATCAN_TABLES,
    StatCanTable,
)
from public_spend_tracker_pipeline.extract.files import (
    ZIP_SIGNATURE,
    DownloadedFile,
    ExtractError,
    ExtractResult,
    new_release_folder,
    save_download,
    web_page_title,
)

log = logging.getLogger(__name__)

# Name of this source in folder paths and manifests.
SOURCE_NAME = "statcan"

# Statistics Canada's description of the table, saved next to the downloads.
# (The manifest's file name comes from common/paths.py, since every extractor shares it.)
METADATA_FILE_NAME = "metadata.json"

# The status Statistics Canada's API reports when a request worked.
STATCAN_SUCCESS = "SUCCESS"

# Added to the error when Statistics Canada sends a web page instead of data:
# usually its "website is currently unavailable" page, during maintenance.
WEB_PAGE_HINT = "Its site may be down for maintenance: try again later."

__all__ = [  # ZIP_SIGNATURE is re-exported for the tests' fake server.
    "METADATA_FILE_NAME",
    "SOURCE_NAME",
    "ZIP_SIGNATURE",
    "StatCanError",
    "extract_all",
    "extract_table",
]


class StatCanError(ExtractError):
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


def _label(table: StatCanTable) -> str:
    """How the log names a table, e.g. "10100005 cofog_consolidated"."""
    return f"{table.product_id} {table.name}"


# --- Asking Statistics Canada -----------------------------------------------


def fetch_table_details(client: httpx.Client, product_id: str) -> TableDetails:
    """Ask Statistics Canada for a table's titles, coverage and latest release date."""
    response = client.post(
        f"{STATCAN_API_URL}/getCubeMetadata",
        json=[{"productId": int(product_id)}],
    )
    response.raise_for_status()
    what = f"the details of table {product_id}"
    table = _unwrap(_read_answer(response, what)[0], what)
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
    what = f"a download link for table {product_id} ({language})"
    return _unwrap(_read_answer(response, what), what)


def _read_answer(response: httpx.Response, what: str):
    """Read a Statistics Canada answer as data, or raise a clear error if it is not.

    When their site is down, the API answers with a web page (and a "worked"
    status code) instead of data.
    """
    try:
        return response.json()
    except json.JSONDecodeError:
        raise StatCanError(_web_page_error(response.text, what)) from None


def _web_page_error(page: str, what: str) -> str:
    """The error for a web page received instead of something we asked for.

    For example: 'Statistics Canada sent a web page ("We're sorry! The website
    is currently unavailable") instead of table 10100005. Its site may be down
    for maintenance: try again later.'
    """
    title = web_page_title(page)
    shown = f' ("{title}")' if title else ""
    return f"Statistics Canada sent a web page{shown} instead of {what}. {WEB_PAGE_HINT}"


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
    """Download one zip file into a folder, fingerprinting it as it arrives.

    Raises StatCanError if what arrives is not a zip file (for example their
    maintenance page), so it is never saved as a release.
    """
    name = url.rsplit("/", 1)[-1]

    def check_start(start: bytes) -> None:
        if not start.startswith(ZIP_SIGNATURE):
            page = start.decode("utf-8", errors="replace")
            raise StatCanError(_web_page_error(page, f"the zip file {name}"))

    with client.stream("GET", url) as response:
        response.raise_for_status()
        return save_download(response, folder / name, language, check_start)


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


# --- Putting it together ----------------------------------------------------


def extract_table(
    client: httpx.Client, table: StatCanTable, data_root: Path = DATA_ROOT
) -> ExtractResult:
    """Download a table's latest release, unless we already have it."""
    details = fetch_table_details(client, table.product_id)
    release_folder = raw_release_folder(
        SOURCE_NAME, table.product_id, details.release_date, data_root
    )
    if (release_folder / MANIFEST_FILE_NAME).exists():
        return ExtractResult(_label(table), "already_current", details.release_date)

    with new_release_folder(release_folder) as folder:
        files = [
            download_file(
                client,
                fetch_download_url(client, table.product_id, language),
                folder,
                language,
            )
            for language in table.languages
        ]
        (folder / METADATA_FILE_NAME).write_bytes(details.raw_response)
        write_manifest(folder, table, details, files)

    return ExtractResult(_label(table), "downloaded", details.release_date)


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
        except (ExtractError, httpx.HTTPError) as error:
            result = ExtractResult(_label(table), "failed", message=str(error))
        log.info(result.describe())
        results.append(result)
    return results
