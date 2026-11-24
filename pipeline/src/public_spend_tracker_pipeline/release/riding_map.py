"""Turn the riding boundary file into the small map the site draws.

Elections Canada's boundary file is an 18 MB shapefile of the ridings' legal
boundaries. Two things make it unsuitable for a web page as it is:

    - Legal boundaries take in water: Hudson Bay, the Arctic channels, the sea
      out to the North Pole, Vancouver's Burrard Inlet. Drawn as they are, they
      do not look like Canada.
    - It is far too detailed: a web map needs a few hundred kilobytes.

So mapshaper (a mapping tool installed with the site, see web/package.json):

    1. Cuts every riding back to the shoreline, using Natural Resources
       Canada's outline of Canada's land (settings.LAND_OUTLINE_FILE).
    2. Smooths away wiggles smaller than a set distance: SMALL_RIDING_METRES
       for most ridings, so city shorelines and borders stay close to real,
       and LARGE_RIDING_METRES for the few huge northern ridings whose Arctic
       coastline would otherwise make up most of the file. Borders between
       ridings stay shared, so ridings still meet exactly.
    3. Drops islands smaller than MIN_ISLAND_KM2, which are invisible at any
       zoom the site offers and add thousands of shapes.
    4. Writes TopoJSON, a compact map format, with each riding's number as
       its ID ("35105"). Names and results come from the other export files.

The map stays in the boundary file's own projection (Statistics Canada's
Lambert projection for Canada), in metres, so the site draws it as it is.

The releases used are the ones recorded in the build's manifest, so the map
always matches the build's ridings. The export stops if the map's ridings are
not exactly the build's.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import zipfile
from datetime import date
from pathlib import Path

from public_spend_tracker_pipeline.common.paths import (
    BUILD_MANIFEST_FILE_NAME,
    MANIFEST_FILE_NAME,
    raw_release_folder,
    serving_build_folder,
)
from public_spend_tracker_pipeline.common.settings import (
    DATA_ROOT,
    ELECTIONS_FILES,
    LAND_OUTLINE_FILE,
    REPOSITORY_ROOT,
    RIDING_BOUNDARIES_DATASET,
    PublishedFile,
)

# Smoothing: wiggles smaller than this many metres are smoothed away.
SMALL_RIDING_METRES = 100
LARGE_RIDING_METRES = 1_000

# A riding counts as large above this area: about 50 of the 343 ridings, all
# in the North or the far reaches of the provinces.
LARGE_RIDING_SQUARE_METRES = 20_000 * 1_000_000  # 20,000 km²

# Islands smaller than this are dropped.
MIN_ISLAND_KM2 = 1

# Coordinates are rounded to a grid this many steps wide across the map:
# about 50 m across Canada, finer than the smoothing.
QUANTIZATION = 100_000

# What the map's one layer is called, and the riding number column in the
# boundary file.
LAYER_NAME = "ridings"
NUMBER_FIELD = "ED_CF_NUM"

# In the land outline file: the layer with land polygons (the zip also holds
# its French twin and an ocean layer), and how its Canadian land is picked out.
LAND_LAYER = "AC_1M_BoundaryPolygons"
LAND_FILTER = "COUNTRY == 'Canada'"

# The parts of a shapefile mapshaper needs (the zips also hold PDFs and XML).
SHAPEFILE_PARTS = (".shp", ".shx", ".dbf", ".prj", ".cpg")

# How mapshaper is run: from the site's tools, installed by "just setup".
MAPSHAPER_COMMAND = ("pnpm", "--dir", str(REPOSITORY_ROOT / "web"), "exec", "mapshaper")

BOUNDARIES_FILE = next(f for f in ELECTIONS_FILES if f.name == RIDING_BOUNDARIES_DATASET)


class RidingMapError(Exception):
    """The map could not be made, or does not match the build's ridings."""


def downloaded_file(build_id: str, source_file: PublishedFile, data_root: Path = DATA_ROOT) -> Path:
    """The downloaded file of the release a build used, found from the build's manifest."""
    manifest_path = serving_build_folder(build_id, data_root) / BUILD_MANIFEST_FILE_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    used = [s for s in manifest.get("sources", []) if s["table_name"] == source_file.name]
    if not used:
        raise RidingMapError(f"Build {build_id}'s manifest lists no {source_file.name}")
    folder = raw_release_folder(
        source_file.source, source_file.name, date.fromisoformat(used[0]["release"]), data_root
    )
    download = json.loads((folder / MANIFEST_FILE_NAME).read_text(encoding="utf-8"))
    return folder / download["files"][0]["name"]


def write_build_riding_map(
    build_id: str, destination: Path, riding_codes: set[str], data_root: Path = DATA_ROOT
) -> int:
    """Make the map from the boundary and land files a build used. Returns how many ridings."""
    return write_riding_map(
        downloaded_file(build_id, BOUNDARIES_FILE, data_root),
        downloaded_file(build_id, LAND_OUTLINE_FILE, data_root),
        destination,
        riding_codes,
    )


def write_riding_map(
    boundary_zip: Path, land_zip: Path, destination: Path, riding_codes: set[str]
) -> int:
    """Cut, smooth and save the riding map as TopoJSON. Returns how many ridings it holds.

    Raises RidingMapError if mapshaper is missing or fails, or if the map's
    ridings are not exactly riding_codes.
    """
    with tempfile.TemporaryDirectory() as temp:
        ridings = _unzip_shapefile(boundary_zip, Path(temp) / "ridings")
        land = _unzip_shapefile(land_zip, Path(temp) / "land", LAND_LAYER)
        smoothing = (
            f"this.area > {LARGE_RIDING_SQUARE_METRES} "
            f"? {LARGE_RIDING_METRES} : {SMALL_RIDING_METRES}"
        )
        _run_mapshaper([
            "-i", str(ridings), f"name={LAYER_NAME}",
            "-i", str(land), "name=land",
            "-filter", LAND_FILTER, "target=land",
            "-proj", f"match={LAYER_NAME}", "target=land",
            "-dissolve", "target=land",
            "-clip", "land", f"target={LAYER_NAME}",
            "-simplify", "variable", f"interval={smoothing}", "keep-shapes",
            f"target={LAYER_NAME}",
            "-filter-islands", f"min-area={MIN_ISLAND_KM2}km2", "remove-empty",
            f"target={LAYER_NAME}",
            "-each", f"code = String({NUMBER_FIELD})", f"target={LAYER_NAME}",
            "-filter-fields", "code", f"target={LAYER_NAME}",
            "-o", str(destination), "format=topojson", f"quantization={QUANTIZATION}",
            "id-field=code", f"target={LAYER_NAME}",
        ])  # fmt: skip
    found = map_riding_codes(destination)
    if set(found) != riding_codes or len(found) != len(riding_codes):
        missing = sorted(riding_codes - set(found))[:5]
        extra = sorted(set(found) - riding_codes)[:5]
        raise RidingMapError(
            f"The map has {len(found)} ridings, the build {len(riding_codes)}. "
            f"Missing from the map: {missing or 'none'}; not in the build: {extra or 'none'}"
        )
    return len(found)


def map_riding_codes(map_file: Path) -> list[str]:
    """The riding numbers in a TopoJSON map, one per shape, in file order."""
    topology = json.loads(map_file.read_text(encoding="utf-8"))
    shapes = topology["objects"][LAYER_NAME]["geometries"]
    return [shape.get("id") for shape in shapes]


def _unzip_shapefile(zip_path: Path, into: Path, layer: str | None = None) -> Path:
    """Take one shapefile's parts out of a zip. Returns the path of its .shp file.

    layer picks the shapefile by name when the zip holds several; without it,
    the zip must hold exactly one.
    """
    into.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as archive:
        names = [n for n in archive.namelist() if n.lower().endswith(SHAPEFILE_PARTS)]
        if layer is not None:
            names = [n for n in names if Path(n).stem == layer]
        shp = [n for n in names if n.lower().endswith(".shp")]
        if len(shp) != 1:
            wanted = f"one {layer}.shp" if layer else "one .shp file"
            raise RidingMapError(f"{zip_path.name} should hold {wanted}, it has {shp}")
        for name in names:
            (into / Path(name).name).write_bytes(archive.read(name))
    return into / Path(shp[0]).name


def _run_mapshaper(arguments: list[str]) -> None:
    """Run mapshaper, turning a missing tool or a failure into a clear error."""
    try:
        subprocess.run([*MAPSHAPER_COMMAND, *arguments], capture_output=True, text=True, check=True)
    except FileNotFoundError:
        raise RidingMapError(
            "pnpm is not installed, so the riding map cannot be made. Run: just setup"
        ) from None
    except subprocess.CalledProcessError as failure:
        detail = (failure.stderr or failure.stdout).strip()
        raise RidingMapError(
            f"mapshaper failed (if it is missing, run: just setup): {detail}"
        ) from None
