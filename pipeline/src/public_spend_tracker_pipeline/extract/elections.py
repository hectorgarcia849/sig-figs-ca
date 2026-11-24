"""Download Elections Canada files exactly as published.

Elections Canada has no API that reports release dates, and its "last changed"
dates cannot be trusted: its website runs on several servers, and each one
reports its own date for the very same file (checked November 2026). So a new
release is recognised by its contents instead:

1. Download the file and take its fingerprint (sha256).
2. If the fingerprint matches the newest release we already have, nothing
   changed: the download is thrown away.
3. Otherwise it is stored as a new release, dated the day we first saw it.

Each file is checked at most once a day: if today's release is already
stored, the file is not downloaded again.

It never opens or changes the downloaded files. Cleaning them up is the job of
the transformers.

Where one release ends up:

    data/raw/source=elections/table=ge45_results_by_candidate/release=2026-11-24/
        table_tableau12.csv   the file, exactly as downloaded
        _manifest.json        what we downloaded, from where, when, and its licence

Like every extractor, it downloads into a temporary folder that becomes the
release folder only once everything is saved (see extract/files.py).

"pst extract" runs this together with the other sources.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import UTC, date, datetime
from pathlib import Path

import httpx

from public_spend_tracker_pipeline.common.paths import (
    MANIFEST_FILE_NAME,
    complete_releases,
    raw_release_folder,
    raw_table_folder,
)
from public_spend_tracker_pipeline.common.settings import (
    DATA_ROOT,
    ELECTIONS_FILES,
    ElectionsFile,
)
from public_spend_tracker_pipeline.extract.files import (
    ZIP_SIGNATURE,
    DownloadedFile,
    ExtractError,
    ExtractResult,
    looks_like_web_page,
    new_release_folder,
    save_download,
    web_page_title,
)

log = logging.getLogger(__name__)

# Name of this source in folder paths and manifests.
SOURCE_NAME = "elections"

# The response header with the date the server says it last changed the file.
# Recorded in the manifest for reference only (see the note at the top).
LAST_MODIFIED_HEADER = "Last-Modified"

# Files with this ending must be zip files.
ZIP_FILE_ENDING = ".zip"


class ElectionsCanadaError(ExtractError):
    """Elections Canada answered, but not with the file we asked for."""


class _SameAsStored(Exception):
    """The download matches the newest stored release, so it is thrown away."""


def _label(source_file: ElectionsFile) -> str:
    """How the log names a file, e.g. "elections ge45_results_by_candidate"."""
    return f"{SOURCE_NAME} {source_file.name}"


def file_name(source_file: ElectionsFile) -> str:
    """The name the file is saved under: the end of its address, e.g. "table_tableau12.csv"."""
    return source_file.url.rsplit("/", 1)[-1]


def newest_release(source_file: ElectionsFile, data_root: Path) -> tuple[date, str] | None:
    """The newest stored release of a file and its fingerprint; None if there is none yet."""
    releases = complete_releases(raw_table_folder(SOURCE_NAME, source_file.name, data_root))
    if not releases:
        return None
    newest = releases[-1]
    folder = raw_release_folder(SOURCE_NAME, source_file.name, newest, data_root)
    manifest = json.loads((folder / MANIFEST_FILE_NAME).read_text(encoding="utf-8"))
    return newest, manifest["files"][0]["sha256"]


def _start_checker(source_file: ElectionsFile):
    """A check that the start of a download is the kind of file we expect.

    Zip files must start with the zip signature; any file must not be a web
    page (Elections Canada's site answers missing or unavailable files with one).
    """
    name = file_name(source_file)

    def check_start(start: bytes) -> None:
        if looks_like_web_page(start) or (
            name.endswith(ZIP_FILE_ENDING) and not start.startswith(ZIP_SIGNATURE)
        ):
            title = web_page_title(start.decode("utf-8", errors="replace"))
            shown = f' ("{title}")' if title else ""
            raise ElectionsCanadaError(
                f"Elections Canada sent something else{shown} instead of the file {name}."
            )

    return check_start


def write_manifest(
    folder: Path,
    source_file: ElectionsFile,
    released: date,
    last_modified: str | None,
    downloaded: DownloadedFile,
) -> None:
    """Write the manifest: what we downloaded, from where, when, and its licence."""
    manifest = {
        "source": SOURCE_NAME,
        "table_name": source_file.name,
        "purpose": source_file.purpose,
        "release": released.isoformat(),
        "server_last_modified": last_modified,
        "listing_url": source_file.listing_url,
        "licence": source_file.licence,
        "licence_url": source_file.licence_url,
        "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "files": [asdict(downloaded)],
    }
    text = json.dumps(manifest, indent=2, ensure_ascii=False)
    (folder / MANIFEST_FILE_NAME).write_text(text + "\n", encoding="utf-8")


def extract_file(
    client: httpx.Client,
    source_file: ElectionsFile,
    data_root: Path = DATA_ROOT,
    today: date | None = None,
) -> ExtractResult:
    """Download a file and store it as a new release if its contents changed.

    today is the date a new release is stored under: the current UTC date
    unless given (tests give it).
    """
    today = today or datetime.now(UTC).date()
    stored = newest_release(source_file, data_root)
    if stored and stored[0] >= today:
        return ExtractResult(_label(source_file), "already_current", stored[0])

    release_folder = raw_release_folder(SOURCE_NAME, source_file.name, today, data_root)
    try:
        with new_release_folder(release_folder) as folder:
            with client.stream("GET", source_file.url) as response:
                response.raise_for_status()
                downloaded = save_download(
                    response,
                    folder / file_name(source_file),
                    source_file.language,
                    _start_checker(source_file),
                )
                last_modified = response.headers.get(LAST_MODIFIED_HEADER)
            if stored and downloaded.sha256 == stored[1]:
                raise _SameAsStored  # leaving the block this way deletes the download
            write_manifest(folder, source_file, today, last_modified, downloaded)
    except _SameAsStored:
        return ExtractResult(_label(source_file), "already_current", stored[0])

    return ExtractResult(_label(source_file), "downloaded", today)


def extract_all(
    client: httpx.Client,
    files: tuple[ElectionsFile, ...] = ELECTIONS_FILES,
    data_root: Path = DATA_ROOT,
) -> list[ExtractResult]:
    """Extract every file. A failure on one file does not stop the others."""
    results = []
    for source_file in files:
        try:
            result = extract_file(client, source_file, data_root)
        except (ExtractError, httpx.HTTPError) as error:
            result = ExtractResult(_label(source_file), "failed", message=str(error))
        log.info(result.describe())
        results.append(result)
    return results
