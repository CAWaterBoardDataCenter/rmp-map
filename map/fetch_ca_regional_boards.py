"""
Download California Regional Water Quality Control Board boundaries (9 regions).

Source: California State Water Resources Control Board GIS
https://gispublic.waterboards.ca.gov/portalserver/rest/services/GAMA/RegionalBoardsWGS84/MapServer/0
"""

from __future__ import annotations

import json
import ssl
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT = ROOT / "data" / "ca_regional_boards.geojson"
SOURCE_URL = (
    "https://gispublic.waterboards.ca.gov/portalserver/rest/services/GAMA/"
    "RegionalBoardsWGS84/MapServer/0/query"
    "?where=1%3D1&outFields=rb,rb_name&f=geojson&outSR=4326"
)


def ring_centroid(ring: list[list[float]]) -> tuple[float, float]:
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    return sum(ys) / len(ys), sum(xs) / len(xs)


def feature_centroid(geometry: dict) -> tuple[float, float]:
    if geometry["type"] == "Polygon":
        return ring_centroid(geometry["coordinates"][0])
    if geometry["type"] == "MultiPolygon":
        largest = max(geometry["coordinates"], key=lambda poly: len(poly[0]))
        return ring_centroid(largest[0])
    raise ValueError(f"Unsupported geometry type: {geometry['type']}")


def main() -> None:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    with urllib.request.urlopen(SOURCE_URL, timeout=120, context=ctx) as response:
        data = json.load(response)

    features = data.get("features", [])
    if len(features) != 9:
        raise ValueError(f"Expected 9 regional boards, got {len(features)}")

    for feature in features:
        props = feature["properties"]
        region_num = props.get("rb")
        region_name = props.get("rb_name", "")
        lat, lon = feature_centroid(feature["geometry"])
        feature["properties"] = {
            "region_num": region_num,
            "name": region_name,
            "label": f"R{region_num} — {region_name}",
            "label_lat": round(lat, 6),
            "label_lon": round(lon, 6),
        }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))

    print(f"Wrote {len(features)} regional boards to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
