"""H3 hex coverage from wetland / polygon footprints (used by build_h3_geojson.py)."""

from __future__ import annotations

from collections import Counter, defaultdict

import h3
from h3 import geo_to_h3shape
from shapely import force_2d, make_valid

# Degrees² — polygons smaller than this use centroid cell assignment (faster).
TINY_POLYGON_AREA = 1e-7

# Simplify tolerance (degrees) before overlap polyfill on larger polygons.
SIMPLIFY_BY_RESOLUTION: dict[int, float] = {
    6: 0.003,
    7: 0.001,
    8: 0.0003,
}


def polygon_to_h3_cells(geom, resolution: int) -> set[str]:
    """Map one polygon geometry to H3 cells at the given resolution."""
    geom = force_2d(make_valid(geom))
    if geom.is_empty:
        return set()

    if geom.area > TINY_POLYGON_AREA:
        tol = SIMPLIFY_BY_RESOLUTION.get(resolution, 0.0)
        if tol > 0:
            geom = geom.simplify(tol, preserve_topology=True)
        if not geom.is_empty:
            try:
                shape = geo_to_h3shape(geom.__geo_interface__)
                return set(
                    h3.polygon_to_cells_experimental(
                        shape, resolution, contain="overlap"
                    )
                )
            except Exception:
                pass

    centroid = geom.centroid
    return {h3.latlng_to_cell(centroid.y, centroid.x, resolution)}


def aggregate_polygon_hexes(
    polygons,
    attributes: list[dict],
    resolution: int,
) -> dict[str, dict]:
    """
    Assign polygons to H3 cells and aggregate metadata per cell.

    Returns h3_index -> {polygon_count, wetland_types, level1_types, ...}
    """
    cell_polygons: dict[str, list[int]] = defaultdict(list)

    for idx, geom in enumerate(polygons):
        for cell in polygon_to_h3_cells(geom, resolution):
            cell_polygons[cell].append(idx)

    aggregated: dict[str, dict] = {}
    for h3_index, poly_indices in cell_polygons.items():
        wetland_types = Counter()
        level1_types = Counter()
        for i in poly_indices:
            attrs = attributes[i]
            if wt := attrs.get("wetland_type"):
                wetland_types[str(wt)] += 1
            if l1 := attrs.get("level1"):
                level1_types[str(l1)] += 1

        def top_summary(counter: Counter, limit: int = 3) -> str:
            return ", ".join(name for name, _ in counter.most_common(limit))

        aggregated[h3_index] = {
            "polygon_count": len(poly_indices),
            "wetland_summary": top_summary(wetland_types),
            "level1_summary": top_summary(level1_types),
        }

    return aggregated


def h3_cell_to_feature(
    h3_index: str,
    cell_meta: dict,
    program_id: str,
    program_label: str,
    resolution: int,
) -> dict:
    """Build a map hex GeoJSON feature for polygon-derived coverage."""
    boundary = h3.cell_to_boundary(h3_index)
    coordinates = [[[lon, lat] for lat, lon in boundary]]
    coordinates[0].append(coordinates[0][0])

    polygon_count = cell_meta["polygon_count"]
    return {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": coordinates},
        "properties": {
            "h3_index": h3_index,
            "station_count": polygon_count,
            "polygon_count": polygon_count,
            "coverage_type": "area",
            "wetland_summary": cell_meta.get("wetland_summary", ""),
            "level1_summary": cell_meta.get("level1_summary", ""),
            "program_id": program_id,
            "program": program_label,
            "resolution": resolution,
            "stations": [],
        },
    }
