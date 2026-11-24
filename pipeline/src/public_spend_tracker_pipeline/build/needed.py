"""Whether a new build is needed: are the downloads newer than the newest build?

"pst update" downloads, then builds only if this says there is something new.
Run every weekday, it would otherwise make an identical build every day.

The newest complete build's manifest records which release of each table it
used. If any table's newest download is a different release, or there is no
complete build yet, a build is needed. Nothing is remembered between runs, so
a build that failed (for example after Statistics Canada changed a table) is
simply tried again the next time.
"""

from __future__ import annotations

import json
from pathlib import Path

from public_spend_tracker_pipeline.common.paths import (
    BUILD_MANIFEST_FILE_NAME,
    complete_releases,
    raw_table_folder,
    serving_build_folder,
    stored_builds,
)
from public_spend_tracker_pipeline.common.settings import (
    DATA_ROOT,
    ELECTIONS_FILES,
    STATCAN_TABLES,
)
from public_spend_tracker_pipeline.extract import elections, statcan


def reasons_to_build(data_root: Path = DATA_ROOT) -> list[str]:
    """Why a new build is needed, one line per reason; empty if none is."""
    manifests = [
        serving_build_folder(build_id, data_root) / BUILD_MANIFEST_FILE_NAME
        for build_id in stored_builds(data_root)
    ]
    complete = [manifest for manifest in manifests if manifest.is_file()]
    if not complete:
        return ["there is no complete build yet"]

    newest = json.loads(complete[-1].read_text(encoding="utf-8"))
    used = {source["table_name"]: source["release"] for source in newest["sources"]}

    folders = [
        (table.name, raw_table_folder(statcan.SOURCE_NAME, table.product_id, data_root))
        for table in STATCAN_TABLES
    ] + [
        (source_file.name, raw_table_folder(elections.SOURCE_NAME, source_file.name, data_root))
        for source_file in ELECTIONS_FILES
    ]

    reasons = []
    for name, folder in folders:
        releases = complete_releases(folder)
        if not releases:
            continue  # never downloaded: the build will say so
        downloaded = releases[-1].isoformat()
        if used.get(name) != downloaded:
            reasons.append(
                f"{name}: release {downloaded} is not in build {newest['build_id']} "
                f"(it used {used.get(name, 'none')})"
            )
    return reasons
