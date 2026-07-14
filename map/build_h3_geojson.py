"""
Build multi-resolution H3 hex GeoJSON layers from unified cleaned station CSVs.

Discovers programs from data/cleaned/*.csv and writes/replaces:
  data/geojson/r6/{program_id}.geojson   (~5 km hexes)
  data/geojson/r7/{program_id}.geojson   (~3 km hexes)
  data/geojson/r8/{program_id}.geojson   (~1 km hexes)
  data/geojson/manifest.json

Removes stale program layers and legacy flat filenames on each run.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import h3
import pandas as pd
import pyogrio

ROOT = Path(__file__).resolve().parent.parent
CLEANED_DIR = ROOT / "data" / "cleaned"
OUTPUT_DIR = ROOT / "data" / "geojson"
MAP_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(MAP_DIR))
from _schema import REQUIRED_COLUMNS  # noqa: E402
from polygon_coverage import (  # noqa: E402
    aggregate_polygon_hexes,
    h3_cell_to_feature,
)

RESOLUTIONS: dict[int, str] = {
    6: "5km",
    7: "3km",
    8: "1km",
}

LEGACY_GEOJSON_RE = re.compile(
    r"^(?P<program_id>.+)_r(?P<resolution>[678])\.geojson$"
)

PROGRAM_METADATA: dict[str, dict] = {
    "delta": {
        "label": "Delta",
        "bounds": {"lat": (37.0, 39.5), "lon": (-123.0, -120.5)},
    },
    "sf_bay": {
        "label": "SF Bay",
        "bounds": {"lat": (37.0, 38.5), "lon": (-123.0, -121.5)},
    },
    "klamath_basin": {
        "label": "Klamath Basin",
        "bounds": {"lat": (40.0, 43.5), "lon": (-125.0, -115.0)},
    },
    "smc": {
        "label": "SMC",
        "bounds": {"lat": (32.0, 35.0), "lon": (-120.5, -116.0)},
    },
    "russian_river": {
        "label": "Russian River",
        "source": "polygons",
        "cleaned_file": "russian_river_wetlands.gpkg",
        "layer": "wetlands",
        "bounds": {"lat": (38.55, 38.68), "lon": (-122.86, -122.79)},
    },
    "bight": {
        "label": "Southern California Bight",
        "bounds": {"lat": (32.0, 35.0), "lon": (-121.5, -117.0)},
    },
}


class BuildError(Exception):
    """Raised when build input/output validation fails."""


def discover_program_ids() -> list[str]:
    if not CLEANED_DIR.exists():
        return []

    ids = {path.stem for path in CLEANED_DIR.glob("*.csv")}
    for program_id, meta in PROGRAM_METADATA.items():
        if meta.get("source") != "polygons":
            continue
        cleaned = CLEANED_DIR / meta.get("cleaned_file", f"{program_id}_wetlands.gpkg")
        if cleaned.exists():
            ids.add(program_id)
    return sorted(ids)


def program_config(program_id: str) -> dict:
    meta = PROGRAM_METADATA.get(program_id, {})
    config = {
        "label": meta.get("label", program_id.replace("_", " ").title()),
    }
    for key in ("bounds", "source", "cleaned_file", "layer"):
        if key in meta:
            config[key] = meta[key]
    return config


def resolution_dir(resolution: int) -> Path:
    if resolution not in RESOLUTIONS:
        raise BuildError(f"Unsupported H3 resolution: {resolution}")
    return OUTPUT_DIR / f"r{resolution}"


def geojson_output_path(program_id: str, resolution: int) -> Path:
    return resolution_dir(resolution) / f"{program_id}.geojson"


def geojson_manifest_relpath(program_id: str, resolution: int) -> str:
    return f"r{resolution}/{program_id}.geojson"


def migrate_legacy_geojson() -> list[str]:
    """Move old flat files like delta_r6.geojson → r6/delta.geojson."""
    if not OUTPUT_DIR.exists():
        return []

    moved: list[str] = []
    for path in sorted(OUTPUT_DIR.glob("*.geojson")):
        match = LEGACY_GEOJSON_RE.match(path.name)
        if not match:
            continue

        program_id = match.group("program_id")
        resolution = int(match.group("resolution"))
        target = geojson_output_path(program_id, resolution)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            path.unlink()
            moved.append(f"removed duplicate legacy {path.name}")
        else:
            path.replace(target)
            moved.append(f"{path.name} -> {target.relative_to(OUTPUT_DIR)}")
    return moved


def cleanup_stale_geojson(active_program_ids: set[str]) -> list[str]:
    """Remove GeoJSON for programs no longer present in data/cleaned/."""
    removed: list[str] = []

    for resolution in RESOLUTIONS:
        folder = resolution_dir(resolution)
        if not folder.exists():
            continue
        for path in sorted(folder.glob("*.geojson")):
            if path.stem in active_program_ids:
                continue
            path.unlink()
            removed.append(str(path.relative_to(OUTPUT_DIR)))

    if OUTPUT_DIR.exists():
        for path in sorted(OUTPUT_DIR.glob("*.geojson")):
            match = LEGACY_GEOJSON_RE.match(path.name)
            if match and match.group("program_id") not in active_program_ids:
                path.unlink()
                removed.append(path.name)

    return removed


def validate_program_id(program_id: str) -> None:
    if not program_id or not re.fullmatch(r"[a-z][a-z0-9_]*", program_id):
        raise BuildError(
            f"Invalid program_id {program_id!r}. "
            "Cleaned CSV stem must match [a-z][a-z0-9_]*."
        )


def validate_cleaned_csv(path: Path, stations: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in stations.columns]
    if missing:
        raise BuildError(
            f"{path.name} missing required columns {missing}. "
            f"Expected: {list(REQUIRED_COLUMNS)}."
        )

    if stations.empty:
        return

    if stations["station_id"].duplicated().any():
        dupes = stations.loc[stations["station_id"].duplicated(), "station_id"].head(5)
        raise BuildError(
            f"{path.name} has duplicate station_id values, e.g. {dupes.tolist()}"
        )

    lat = stations["lat"]
    lon = stations["lon"]
    if not lat.between(-90, 90).all():
        raise BuildError(f"{path.name} has lat values outside [-90, 90].")
    if not lon.between(-180, 180).all():
        raise BuildError(f"{path.name} has lon values outside [-180, 180].")


def validate_geojson(geojson: dict, program_id: str, resolution: int) -> None:
    if geojson.get("type") != "FeatureCollection":
        raise BuildError(
            f"{program_id} r{resolution}: expected FeatureCollection, "
            f"got {geojson.get('type')!r}."
        )
    features = geojson.get("features")
    if not isinstance(features, list):
        raise BuildError(f"{program_id} r{resolution}: features must be a list.")

    for i, feature in enumerate(features):
        if feature.get("type") != "Feature":
            raise BuildError(
                f"{program_id} r{resolution}: feature {i} is not a GeoJSON Feature."
            )
        props = feature.get("properties") or {}
        if props.get("program_id") != program_id:
            raise BuildError(
                f"{program_id} r{resolution}: feature {i} program_id mismatch "
                f"({props.get('program_id')!r})."
            )
        if props.get("resolution") != resolution:
            raise BuildError(
                f"{program_id} r{resolution}: feature {i} resolution mismatch "
                f"({props.get('resolution')!r})."
            )
        if props.get("coverage_type") == "area":
            if "polygon_count" not in props:
                raise BuildError(
                    f"{program_id} r{resolution}: area feature {i} missing polygon_count."
                )
            continue
        if not isinstance(props.get("stations"), list):
            raise BuildError(
                f"{program_id} r{resolution}: feature {i} missing stations list."
            )


def normalize_coordinates(stations: pd.DataFrame, config: dict) -> pd.DataFrame:
    stations = stations.copy()
    bounds = config.get("bounds")
    if bounds:
        lat_min, lat_max = bounds["lat"]
        lon_min, lon_max = bounds["lon"]
        before = len(stations)
        stations = stations[
            (stations["lat"] >= lat_min)
            & (stations["lat"] <= lat_max)
            & (stations["lon"] >= lon_min)
            & (stations["lon"] <= lon_max)
        ]
        dropped = before - len(stations)
        if dropped:
            print(
                f"  filtered {dropped} out-of-bounds station(s) using PROGRAM_METADATA bounds"
            )

    western_us = (stations["lat"] >= 32) & (stations["lat"] <= 50)
    positive_lon = (stations["lon"] > 0) & (stations["lon"] < 130)
    stations.loc[western_us & positive_lon, "lon"] = -stations.loc[
        western_us & positive_lon, "lon"
    ]
    return stations


def load_stations(program_id: str, config: dict) -> pd.DataFrame:
    validate_program_id(program_id)
    path = CLEANED_DIR / f"{program_id}.csv"
    if not path.exists():
        raise BuildError(
            f"Missing cleaned file: {path.relative_to(ROOT)}\n"
            f"Run scripts/clean_{program_id}.py first."
        )

    try:
        stations = pd.read_csv(path)
    except pd.errors.EmptyDataError as exc:
        raise BuildError(f"{path.name} is empty.") from exc
    except Exception as exc:
        raise BuildError(f"Failed to read {path.name}: {exc}") from exc

    stations = stations.drop_duplicates(subset=["station_id"])
    stations["lat"] = pd.to_numeric(stations["lat"], errors="coerce")
    stations["lon"] = pd.to_numeric(stations["lon"], errors="coerce")
    stations = stations.dropna(subset=["lat", "lon"])
    stations = stations[(stations["lat"] != 0) | (stations["lon"] != 0)]
    validate_cleaned_csv(path, stations)
    return normalize_coordinates(stations, config)


def compute_map_bounds(stations: pd.DataFrame) -> list[list[float]] | None:
    if stations.empty:
        return None
    lat_min = float(stations["lat"].min())
    lat_max = float(stations["lat"].max())
    lon_min = float(stations["lon"].min())
    lon_max = float(stations["lon"].max())
    if not all(map(pd.notna, [lat_min, lat_max, lon_min, lon_max])):
        raise BuildError("Could not compute finite map bounds from station coordinates.")
    return [[lat_min, lon_min], [lat_max, lon_max]]


def station_record(row: pd.Series) -> dict:
    record = {
        "station_id": str(row["station_id"]),
        "station_name": str(row["station_name"]) if pd.notna(row["station_name"]) else "",
        "lat": round(float(row["lat"]), 6),
        "lon": round(float(row["lon"]), 6),
    }
    for col in row.index:
        if col in {"lat", "lon", "station_id", "station_name", "h3_index"}:
            continue
        if pd.notna(row[col]):
            record[col] = str(row[col])
    return record


def stations_to_geojson(
    stations: pd.DataFrame, program_id: str, program_label: str, resolution: int
) -> dict:
    if stations.empty:
        return {"type": "FeatureCollection", "features": []}

    stations = stations.copy()
    try:
        stations["h3_index"] = [
            h3.latlng_to_cell(lat, lon, resolution)
            for lat, lon in zip(stations["lat"], stations["lon"], strict=True)
        ]
    except Exception as exc:
        raise BuildError(
            f"{program_id} r{resolution}: H3 indexing failed: {exc}"
        ) from exc

    features = []
    for h3_index, group in stations.groupby("h3_index"):
        station_list = [station_record(row) for _, row in group.iterrows()]
        try:
            boundary = h3.cell_to_boundary(h3_index)
        except Exception as exc:
            raise BuildError(
                f"{program_id} r{resolution}: invalid H3 cell {h3_index}: {exc}"
            ) from exc
        coordinates = [[[lon, lat] for lat, lon in boundary]]
        coordinates[0].append(coordinates[0][0])

        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": coordinates},
                "properties": {
                    "h3_index": h3_index,
                    "station_count": len(station_list),
                    "program_id": program_id,
                    "program": program_label,
                    "resolution": resolution,
                    "stations": station_list,
                },
            }
        )

    geojson = {"type": "FeatureCollection", "features": features}
    validate_geojson(geojson, program_id, resolution)
    return geojson


def write_geojson(path: Path, geojson: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(geojson, f, separators=(",", ":"))
    except OSError as exc:
        raise BuildError(f"Failed to write {path.relative_to(ROOT)}: {exc}") from exc

    if not path.exists() or path.stat().st_size == 0:
        raise BuildError(f"Wrote empty file: {path.relative_to(ROOT)}")


def load_polygon_footprint(program_id: str, config: dict) -> tuple[list, list[dict], list[list[float]]]:
    validate_program_id(program_id)
    cleaned_file = config.get("cleaned_file", f"{program_id}_wetlands.gpkg")
    layer = config.get("layer", "wetlands")
    path = CLEANED_DIR / cleaned_file
    if not path.exists():
        raise BuildError(
            f"Missing polygon cleaned file: {path.relative_to(ROOT)}\n"
            f"Run scripts/clean_{program_id}_wetlands.py first."
        )

    try:
        info = pyogrio.read_info(path, layer=layer)
        if int(info.get("features", 0)) == 0:
            raise BuildError(f"{path.name} layer {layer!r} has no features.")
        gdf = pyogrio.read_dataframe(path, layer=layer)
    except BuildError:
        raise
    except Exception as exc:
        raise BuildError(f"Failed to read {path.name}: {exc}") from exc

    if gdf.empty:
        raise BuildError(f"{path.name} contains no polygon features.")

    attr_cols = [
        c for c in ("level1", "level2", "wetland_type", "wetland_code", "vegetation")
        if c in gdf.columns
    ]
    attributes = [
        {col: (str(row[col]) if pd.notna(row[col]) else "") for col in attr_cols}
        for _, row in gdf.iterrows()
    ]
    bounds = gdf.total_bounds.tolist()
    map_bounds = [[float(bounds[1]), float(bounds[0])], [float(bounds[3]), float(bounds[2])]]
    return list(gdf.geometry), attributes, map_bounds


def polygons_to_geojson(
    polygons,
    attributes: list[dict],
    program_id: str,
    program_label: str,
    resolution: int,
) -> dict:
    cell_meta = aggregate_polygon_hexes(polygons, attributes, resolution)
    features = [
        h3_cell_to_feature(h3_index, meta, program_id, program_label, resolution)
        for h3_index, meta in sorted(cell_meta.items())
    ]
    geojson = {"type": "FeatureCollection", "features": features}
    validate_geojson(geojson, program_id, resolution)
    return geojson


def build_polygon_program(program_id: str, config: dict) -> dict:
    polygons, attributes, map_bounds = load_polygon_footprint(program_id, config)
    polygon_count = len(polygons)
    program_manifest = {
        "label": config["label"],
        "coverage_type": "area",
        "bounds": map_bounds,
        "polygon_count": polygon_count,
        "station_count": polygon_count,
        "resolutions": {},
    }

    for resolution, label in RESOLUTIONS.items():
        geojson = polygons_to_geojson(
            polygons, attributes, program_id, config["label"], resolution
        )
        output_path = geojson_output_path(program_id, resolution)
        write_geojson(output_path, geojson)

        rel_path = geojson_manifest_relpath(program_id, resolution)
        program_manifest["resolutions"][str(resolution)] = rel_path
        print(
            f"{config['label']} r{resolution} ({label}): "
            f"{polygon_count:,} wetland polygons -> {len(geojson['features'])} hexes -> {rel_path}"
        )

    return program_manifest


def build_program(program_id: str, config: dict) -> dict:
    if config.get("source") == "polygons":
        return build_polygon_program(program_id, config)

    stations = load_stations(program_id, config)
    program_manifest = {
        "label": config["label"],
        "coverage_type": "stations",
        "bounds": compute_map_bounds(stations),
        "station_count": len(stations),
        "resolutions": {},
    }

    for resolution, label in RESOLUTIONS.items():
        geojson = stations_to_geojson(stations, program_id, config["label"], resolution)
        output_path = geojson_output_path(program_id, resolution)
        write_geojson(output_path, geojson)

        rel_path = geojson_manifest_relpath(program_id, resolution)
        program_manifest["resolutions"][str(resolution)] = rel_path
        print(
            f"{config['label']} r{resolution} ({label}): "
            f"{len(stations)} stations -> {len(geojson['features'])} hexes -> {rel_path}"
        )

    return program_manifest


def validate_manifest(manifest: dict, program_ids: list[str]) -> None:
    if manifest.get("resolutions") != RESOLUTIONS:
        raise BuildError("Manifest resolutions metadata is invalid.")
    programs = manifest.get("programs")
    if not isinstance(programs, dict):
        raise BuildError("Manifest programs section is missing or invalid.")
    for program_id in program_ids:
        if program_id not in programs:
            raise BuildError(f"Manifest missing program entry: {program_id}")
        entry = programs[program_id]
        for resolution in RESOLUTIONS:
            rel_path = entry.get("resolutions", {}).get(str(resolution))
            if not rel_path:
                raise BuildError(
                    f"Manifest missing r{resolution} path for {program_id}."
                )
            file_path = OUTPUT_DIR / rel_path
            if not file_path.exists():
                raise BuildError(
                    f"Manifest references missing file: {rel_path}"
                )


def main() -> None:
    program_ids = discover_program_ids()
    if not program_ids:
        raise BuildError(
            f"No active cleaned inputs found in {CLEANED_DIR.relative_to(ROOT)}"
        )

    migrated = migrate_legacy_geojson()
    if migrated:
        print("Migrated legacy GeoJSON layout:")
        for line in migrated:
            print(f"  {line}")

    active_program_ids = set(program_ids)
    removed = cleanup_stale_geojson(active_program_ids)
    if removed:
        print(f"Removed stale GeoJSON: {', '.join(removed)}")

    manifest = {"resolutions": RESOLUTIONS, "programs": {}}
    failures: list[str] = []

    for program_id in program_ids:
        config = program_config(program_id)
        try:
            manifest["programs"][program_id] = build_program(program_id, config)
        except BuildError as exc:
            failures.append(f"{program_id}: {exc}")
            print(f"ERROR — {program_id}: {exc}", file=sys.stderr)

    if not manifest["programs"]:
        raise BuildError("No programs built successfully.\n" + "\n".join(failures))

    manifest_path = OUTPUT_DIR / "manifest.json"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        validate_manifest(manifest, list(manifest["programs"].keys()))
        with manifest_path.open("w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
    except (BuildError, OSError, TypeError, ValueError) as exc:
        raise BuildError(f"Failed to write manifest: {exc}") from exc

    print(f"Wrote {manifest_path.relative_to(ROOT)}")
    if failures:
        print(
            f"\nCompleted with {len(failures)} error(s):\n  "
            + "\n  ".join(failures),
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except BuildError as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        sys.exit(1)
