"""Pieces every extractor shares: saving a download and storing a release safely.

Each source (Statistics Canada, Elections Canada...) finds out in its own way
what the latest release is and where to download it. Once it knows, the steps
are the same for all of them:

1. Make a temporary folder next to where the release will live
   (new_release_folder).
2. Save each file into it, fingerprinting it as it arrives and refusing it if
   it is not what we expected, for example a "site unavailable" web page
   instead of a zip file (save_download).
3. Write the manifest, then rename the temporary folder to the release folder.

So a release folder always holds a complete download, and a failed run leaves
nothing behind: the next run simply tries again.
"""

from __future__ import annotations

import hashlib
import html
import re
import shutil
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

import httpx

from public_spend_tracker_pipeline.common.paths import MANIFEST_FILE_NAME

# Start of the name of the temporary folder used while downloading.
TEMP_FOLDER_PREFIX = ".incomplete-"

# Downloads are read and written in pieces of this size, so large files never
# need to fit in memory at once.
DOWNLOAD_CHUNK_BYTES = 1024 * 1024

# Every zip file starts with these bytes.
ZIP_SIGNATURE = b"PK\x03\x04"

# The most of a web page's title quoted in an error.
MAX_TITLE_CHARACTERS = 120


class ExtractError(Exception):
    """A source answered, but not with what we asked for. Each source has its own kind."""


@dataclass(frozen=True)
class DownloadedFile:
    """One file we downloaded, with a fingerprint to prove what it contained.

    language  Which language the file is in: "en", "fr", or "en,fr" for a file
              that has both.
    sha256    A fingerprint of the file's contents. If even one byte changes,
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
    """What happened when we tried to extract one table or file.

    label  How the log names it, e.g. "10100005 cofog_consolidated".
    """

    label: str
    status: ExtractStatus
    release_date: date | None = None
    message: str = ""

    def describe(self) -> str:
        """One line for the log.

        For example: "10100005 cofog_consolidated: downloaded release 2025-11-27".
        """
        if self.status == "downloaded":
            return f"{self.label}: downloaded release {self.release_date}"
        if self.status == "already_current":
            return f"{self.label}: already have release {self.release_date}"
        return f"{self.label}: FAILED - {self.message}"


def save_download(
    response: httpx.Response,
    path: Path,
    language: str,
    check_start: Callable[[bytes], None],
) -> DownloadedFile:
    """Save a streamed download to a file, fingerprinting it as it arrives.

    check_start is shown the first piece of the file before anything is
    written, and raises an error if the file is not what we expected (for
    example a web page instead of a zip file), so it is never saved.
    """
    fingerprint = hashlib.sha256()
    size_bytes = 0
    with open(path, "wb") as file:
        for chunk in response.iter_bytes(DOWNLOAD_CHUNK_BYTES):
            if size_bytes == 0:
                check_start(chunk)
            file.write(chunk)
            fingerprint.update(chunk)
            size_bytes += len(chunk)
    return DownloadedFile(
        name=path.name,
        language=language,
        url=str(response.url),
        sha256=fingerprint.hexdigest(),
        size_bytes=size_bytes,
    )


@contextmanager
def new_release_folder(release_folder: Path) -> Iterator[Path]:
    """A temporary folder to download a release into, renamed to release_folder at the end.

    Use it in a "with" block. If the block finishes, the temporary folder
    becomes the release folder; if anything in it fails, the temporary folder
    is deleted and nothing is left behind.

    Raises ExtractError if release_folder already exists without a manifest:
    an earlier download was interrupted in a way we cannot tidy up safely.
    """
    if release_folder.exists():
        raise ExtractError(
            f"{release_folder} exists but has no {MANIFEST_FILE_NAME}, so it is incomplete. "
            "Delete that folder and run again."
        )
    table_folder = release_folder.parent
    table_folder.mkdir(parents=True, exist_ok=True)
    temp_folder = Path(tempfile.mkdtemp(prefix=TEMP_FOLDER_PREFIX, dir=table_folder))
    try:
        yield temp_folder
        temp_folder.rename(release_folder)
    finally:
        # Only still there if something above failed: remove the partial download.
        shutil.rmtree(temp_folder, ignore_errors=True)


def looks_like_web_page(start: bytes) -> bool:
    """Whether the start of a download is a web page rather than data.

    Sites under maintenance often answer every address with a web page and a
    "worked" status code, so a download can succeed and still hold the wrong thing.
    """
    text = start.lstrip(b"\xef\xbb\xbf \t\r\n").lower()  # skip a byte-order mark and spaces
    return text.startswith((b"<!doctype html", b"<html"))


def web_page_title(page: str) -> str:
    """The title of a web page, tidied and shortened for an error message; "" if none.

    For example: "Statistics Canada - We're sorry! The website is currently unavailable".
    """
    found = re.search(r"<title>(.*?)</title>", page, re.IGNORECASE | re.DOTALL)
    title = " ".join(html.unescape(found.group(1)).split()) if found else ""
    if len(title) > MAX_TITLE_CHARACTERS:
        title = title[:MAX_TITLE_CHARACTERS].rstrip() + "…"
    return title
