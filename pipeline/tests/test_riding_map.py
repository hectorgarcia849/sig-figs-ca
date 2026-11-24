"""Tests for the riding map: finding the files a build used, cutting and checking the map.

The mapshaper tests use two made-up ridings and a made-up land outline, and
are skipped where the site's tools (pnpm and mapshaper) are not installed.
"""

import io
import json
import shutil
import subprocess
import zipfile
from datetime import date

import pytest
import shapefile

from public_spend_tracker_pipeline.common.paths import (
    BUILD_MANIFEST_FILE_NAME,
    MANIFEST_FILE_NAME,
    raw_release_folder,
    serving_build_folder,
)
from public_spend_tracker_pipeline.common.settings import LAND_OUTLINE_FILE
from public_spend_tracker_pipeline.release import riding_map
from public_spend_tracker_pipeline.release.riding_map import (
    MAPSHAPER_COMMAND,
    RidingMapError,
    downloaded_file,
    map_riding_codes,
    write_riding_map,
)

# Statistics Canada's Lambert projection, as in the real boundary file.
LAMBERT = (
    'PROJCS["NAD_1983_Statistics_Canada_Lambert",GEOGCS["GCS_North_American_1983",'
    'DATUM["D_North_American_1983",SPHEROID["GRS_1980",6378137.0,298.257222101]],'
    'PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],'
    'PROJECTION["Lambert_Conformal_Conic"],PARAMETER["False_Easting",6200000.0],'
    'PARAMETER["False_Northing",3000000.0],PARAMETER["Central_Meridian",-91.8666666666667],'
    'PARAMETER["Standard_Parallel_1",49.0],PARAMETER["Standard_Parallel_2",77.0],'
    'PARAMETER["Latitude_Of_Origin",63.390675],UNIT["Meter",1.0]]'
)

# Two ridings side by side, 10 km squares; land covers only their left 15 km,
# so the right riding is cut in half (its other half is "water").
LEFT, RIGHT = (7_200_000, 900_000), (7_210_000, 900_000)
RIDING_SIZE = 10_000
LAND_EDGE = 7_215_000


def mapshaper_available() -> bool:
    if shutil.which("pnpm") is None:
        return False
    found = subprocess.run([*MAPSHAPER_COMMAND, "-v"], capture_output=True, check=False)
    return found.returncode == 0


needs_mapshaper = pytest.mark.skipif(
    not mapshaper_available(), reason="mapshaper is not installed (run: just setup)"
)


def square(x, y, width, height=RIDING_SIZE):
    return [[(x, y), (x, y + height), (x + width, y + height), (x + width, y), (x, y)]]


def shapefile_zip(folder, layer, fields, shapes) -> bytes:
    """A zipped shapefile with polygons and their records, in the Lambert projection."""
    parts = {ending: io.BytesIO() for ending in ("shp", "shx", "dbf")}
    writer = shapefile.Writer(shp=parts["shp"], shx=parts["shx"], dbf=parts["dbf"])
    for name, kind, size in fields:
        writer.field(name, kind, size)
    for rings, record in shapes:
        writer.poly(rings)
        writer.record(*record)
    writer.close()
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as zipped:
        for ending, content in parts.items():
            zipped.writestr(f"{folder}/{layer}.{ending}", content.getvalue())
        zipped.writestr(f"{folder}/{layer}.prj", LAMBERT)
        zipped.writestr(f"{folder}/{layer}.cpg", "UTF-8")
    return archive.getvalue()


def ridings_zip(tmp_path):
    content = shapefile_zip(
        "FederalElectoralDistricts_SHP", "ED_CF", [("ED_CF_NUM", "N", 11)],
        [(square(*LEFT, RIDING_SIZE), (10001,)), (square(*RIGHT, RIDING_SIZE), (35105,))],
    )  # fmt: skip
    path = tmp_path / "ridings.zip"
    path.write_bytes(content)
    return path


def land_zip(tmp_path):
    x, y = LEFT
    content = shapefile_zip(
        "AC_1M_BoundaryPolygons_shp", "AC_1M_BoundaryPolygons",
        [("COUNTRY", "C", 50), ("POL_DIV", "C", 50)],
        [(square(x - 5_000, y - 5_000, LAND_EDGE - x + 5_000, 20_000), ("Canada", "Ontario")),
         (square(x, y - 50_000, 20_000, 20_000), ("United States", "New York"))],
    )  # fmt: skip
    path = tmp_path / "land.zip"
    path.write_bytes(content)
    return path


def widest_x(map_file) -> float:
    """The largest x coordinate in a TopoJSON map, decoding its arcs."""
    topology = json.loads(map_file.read_text(encoding="utf-8"))
    scale, translate = topology["transform"]["scale"], topology["transform"]["translate"]
    widest = None
    for arc in topology["arcs"]:
        x = 0
        for step in arc:
            x += step[0]
            real = x * scale[0] + translate[0]
            widest = real if widest is None else max(widest, real)
    return widest


# --- Cutting and smoothing with mapshaper -------------------------------------


@needs_mapshaper
def test_ridings_are_cut_back_to_the_land(tmp_path):
    out = tmp_path / "ridings.topo.json"

    count = write_riding_map(ridings_zip(tmp_path), land_zip(tmp_path), out, {"10001", "35105"})

    assert count == 2
    assert sorted(map_riding_codes(out)) == ["10001", "35105"]
    # The right riding ran to 7,220,000; the land stops at 7,215,000.
    assert widest_x(out) == pytest.approx(LAND_EDGE, abs=200)


@needs_mapshaper
def test_a_riding_missing_from_the_build_stops_the_export(tmp_path):
    with pytest.raises(RidingMapError, match="not in the build: \\['35105'\\]"):
        write_riding_map(ridings_zip(tmp_path), land_zip(tmp_path), tmp_path / "m.json",
                         {"10001"})  # fmt: skip


def test_a_land_file_without_its_land_layer_stops_the_export(tmp_path):
    wrong = tmp_path / "wrong.zip"
    wrong.write_bytes(shapefile_zip("x", "Something_Else", [("COUNTRY", "C", 50)],
                                    [(square(0, 0, 10), ("Canada",))]))  # fmt: skip
    with pytest.raises(RidingMapError, match="should hold one AC_1M_BoundaryPolygons.shp"):
        write_riding_map(ridings_zip(tmp_path), wrong, tmp_path / "m.json", {"10001"})


def test_missing_pnpm_gives_a_clear_error(tmp_path, monkeypatch):
    monkeypatch.setattr(riding_map, "MAPSHAPER_COMMAND", ("no-such-program-here",))
    with pytest.raises(RidingMapError, match="just setup"):
        write_riding_map(ridings_zip(tmp_path), land_zip(tmp_path), tmp_path / "m.json",
                         {"10001", "35105"})  # fmt: skip


# --- Finding the files a build used -----------------------------------------


def test_the_build_manifest_says_which_release_to_use(tmp_path):
    for release in ("2026-11-20", "2026-11-24"):
        folder = raw_release_folder(LAND_OUTLINE_FILE.source, LAND_OUTLINE_FILE.name,
                                    date.fromisoformat(release), tmp_path)  # fmt: skip
        folder.mkdir(parents=True)
        manifest = {"files": [{"name": "AC_1M_BoundaryPolygons.shp.zip"}]}
        (folder / MANIFEST_FILE_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    build = serving_build_folder("20261124-062740", tmp_path)
    build.mkdir(parents=True)
    sources = [{"table_name": "land_outline", "release": "2026-11-20"}]
    (build / BUILD_MANIFEST_FILE_NAME).write_text(json.dumps({"sources": sources}))

    found = downloaded_file("20261124-062740", LAND_OUTLINE_FILE, tmp_path)

    assert found.parent.name == "release=2026-11-20"
    assert found.name == "AC_1M_BoundaryPolygons.shp.zip"


def test_a_build_without_the_file_stops_the_export(tmp_path):
    build = serving_build_folder("20261124-062740", tmp_path)
    build.mkdir(parents=True)
    (build / BUILD_MANIFEST_FILE_NAME).write_text(json.dumps({"sources": []}))
    with pytest.raises(RidingMapError, match="lists no land_outline"):
        downloaded_file("20261124-062740", LAND_OUTLINE_FILE, tmp_path)
