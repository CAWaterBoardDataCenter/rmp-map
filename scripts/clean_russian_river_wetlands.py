"""
Russian River wetlands (RRARI): GeoPackage polygons → cleaned footprint for map build.

PAUSED: CEDEN station export (scripts/clean_russian_river.py) is not used on the map.
      Its output is kept under data/cleaned/_paused/ for reference.

Pseudocode:
  LOAD data/raw/russian_river_geopackage_raw.gpkg (layer RRARI_Polygons)
  REPROJECT to WGS84 (EPSG:4326), drop Z/M dimensions
  VALIDATE geometries
  WRITE data/cleaned/russian_river_wetlands.gpkg  (input to build_h3_geojson.py)
  WRITE data/cleaned/russian_river_wetlands_meta.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import pyogrio
from shapely import force_2d, make_valid

ROOT = Path(__file__).resolve().parent.parent
PROGRAM_ID = "russian_river"
RAW = ROOT / "data" / "raw" / "russian_river_geopackage_raw.gpkg"
LAYER = "RRARI_Polygons"
OUTPUT_GPKG = ROOT / "data" / "cleaned" / f"{PROGRAM_ID}_wetlands.gpkg"
OUTPUT_META = ROOT / "data" / "cleaned" / f"{PROGRAM_ID}_wetlands_meta.json"

KEEP_COLUMNS = [
    "level1",
    "level2",
    "wetland_type",
    "wetland_code",
    "vegetation",
    "source_data",
    "source_data_year",
    "source_org",
]


def main() -> None:
    if not RAW.exists():
        raise FileNotFoundError(
            f"Place Russian River wetland GeoPackage at {RAW.relative_to(ROOT)}"
        )

    info = pyogrio.read_info(RAW, layer=LAYER)
    feature_count = int(info.get("features", 0))
    if feature_count == 0:
        raise ValueError(f"{RAW.name} layer {LAYER!r} contains no features.")

    print(f"Reading {feature_count:,} polygons from {RAW.name}…")
    gdf = pyogrio.read_dataframe(RAW, layer=LAYER)

    missing = [c for c in KEEP_COLUMNS if c not in gdf.columns]
    if missing:
        raise ValueError(f"GeoPackage missing expected columns: {missing}")

    gdf = gdf[KEEP_COLUMNS + ["geometry"]].copy()
    gdf["geometry"] = gdf.geometry.apply(lambda g: force_2d(make_valid(g)))
    gdf = gdf[~gdf.geometry.is_empty].copy()
    gdf = gdf.set_crs(info.get("crs"), allow_override=True).to_crs(4326)

    bounds = [float(v) for v in gdf.total_bounds]
    if len(gdf) == 0:
        raise ValueError("No valid wetland polygons after geometry cleanup.")

    OUTPUT_GPKG.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(OUTPUT_GPKG, layer="wetlands", driver="GPKG")

    meta = {
        "program_id": PROGRAM_ID,
        "coverage_type": "area",
        "source_file": RAW.name,
        "layer": LAYER,
        "polygon_count": len(gdf),
        "bounds": [[bounds[1], bounds[0]], [bounds[3], bounds[2]]],
        "columns": KEEP_COLUMNS,
        "notes": (
            "Wetland footprint polygons (RRARI). Map hexes represent area coverage, "
            "not point sample stations."
        ),
    }
    OUTPUT_META.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(
        f"Russian River wetlands: {len(gdf):,} polygons -> "
        f"{OUTPUT_GPKG.relative_to(ROOT)}"
    )
    print(f"Metadata -> {OUTPUT_META.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
