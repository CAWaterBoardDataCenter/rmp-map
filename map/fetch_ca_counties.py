"""
Download California county boundaries and add label centroids for the web map.
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT = ROOT / "data" / "ca_counties.geojson"
SOURCE_URL = (
    "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/"
    "public/data/california-counties.geojson"
)


def ring_centroid(ring: list[list[float]]) -> tuple[float, float]:
  """Approximate centroid from the outer ring of a polygon."""
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
  with urllib.request.urlopen(SOURCE_URL, timeout=60) as response:
    data = json.load(response)

  for feature in data["features"]:
    lat, lon = feature_centroid(feature["geometry"])
    name = feature["properties"].get("name", "")
    feature["properties"] = {
      "name": name,
      "label_lat": round(lat, 6),
      "label_lon": round(lon, 6),
    }

  OUTPUT.parent.mkdir(parents=True, exist_ok=True)
  with OUTPUT.open("w", encoding="utf-8") as f:
    json.dump(data, f, separators=(",", ":"))

  print(f"Wrote {len(data['features'])} counties to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
  main()
