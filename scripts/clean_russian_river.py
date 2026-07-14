"""Russian River MS4 (CEDEN) — PAUSED, not used on the map.

This script is kept for reference. Active Russian River coverage comes from
wetland polygons: scripts/clean_russian_river_wetlands.py

Output (if run): data/cleaned/_paused/russian_river_ceden.csv
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _schema import OUTPUT_COLUMNS

ROOT = Path(__file__).resolve().parent.parent
PROGRAM_ID = "russian_river"
RAW = ROOT / "data" / "raw" / "russian_river_raw.tsv"
OUTPUT = ROOT / "data" / "cleaned" / "_paused" / "russian_river_ceden.csv"

COLUMN_MAP = {
    "STATIONCODE": "station_id",
    "STATIONNAME": "station_name",
    "LATITUDE": "lat",
    "LONGITUDE": "lon",
    "COUNTY": "county",
    "WATERBODY_TYPE": "waterbody",
    "HUC8_NAME": "huc8",
    "SAMPLEAGENCY": "organization",
}


def permit_year(parent_project: str) -> str | None:
    match = re.search(r"(20\d{2})", str(parent_project))
    return match.group(1) if match else None


def main() -> None:
    if not RAW.exists():
        raise FileNotFoundError(
            f"Place Russian River raw export at {RAW.relative_to(ROOT)}"
        )

    df = pd.read_csv(RAW, sep="\t", low_memory=False)

    missing = [c for c in COLUMN_MAP if c not in df.columns]
    if missing:
        raise ValueError(f"Raw file missing expected columns: {missing}")

    if "PARENTPROJECT" not in df.columns:
        raise ValueError("Raw file missing expected column: PARENTPROJECT")

    stations = df[list(COLUMN_MAP.keys()) + ["PARENTPROJECT"]].rename(
        columns=COLUMN_MAP
    )
    stations["permit_year"] = stations["PARENTPROJECT"].map(permit_year)
    stations = stations.drop(columns=["PARENTPROJECT"])

    stations = stations.drop_duplicates(subset=["station_id"])
    stations = stations.dropna(subset=["lat", "lon"])
    stations["lat"] = pd.to_numeric(stations["lat"], errors="coerce")
    stations["lon"] = pd.to_numeric(stations["lon"], errors="coerce")
    stations = stations.dropna(subset=["lat", "lon"])
    stations = stations[(stations["lat"] != 0) | (stations["lon"] != 0)]

    out_cols = [c for c in OUTPUT_COLUMNS if c in stations.columns]
    if "permit_year" in stations.columns:
        out_cols.append("permit_year")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    stations[out_cols].to_csv(OUTPUT, index=False)
    year_counts = stations["permit_year"].value_counts().sort_index().to_dict()
    print(
        f"Russian River (CEDEN, paused): {len(stations)} stations ({year_counts}) "
        f"-> {OUTPUT.relative_to(ROOT)}"
    )
    print("Note: map uses wetland polygons via clean_russian_river_wetlands.py")


if __name__ == "__main__":
    main()
