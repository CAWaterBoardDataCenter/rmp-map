"""Delta RMP: delta_raw.tsv (tab-separated) → data/cleaned/delta.csv

Pseudocode:
  LOAD tab-separated delta_raw.tsv (CD3 analyte export; many rows per station)
  MAP STATIONCODE, STATIONNAME, LATITUDE, LONGITUDE, … → unified schema
  DEDUPE one row per station_id (STATIONCODE)
  DROP rows with missing, invalid, or (0,0) lat/lon
  WRITE data/cleaned/delta.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _schema import OUTPUT_COLUMNS

ROOT = Path(__file__).resolve().parent.parent
PROGRAM_ID = "delta"
RAW = ROOT / "data" / "raw" / "delta_raw.tsv"
OUTPUT = ROOT / "data" / "cleaned" / f"{PROGRAM_ID}.csv"

COLUMN_MAP = {
    "STATIONCODE": "station_id",
    "STATIONNAME": "station_name",
    "LATITUDE": "lat",
    "LONGITUDE": "lon",
    "COUNTY": "county",
    "WATERBODY_TYPE": "waterbody",
    "HUC8_NAME": "huc8",
}


def main() -> None:
    if not RAW.exists():
        raise FileNotFoundError(f"Place Delta raw export at {RAW.relative_to(ROOT)}")

    df = pd.read_csv(RAW, sep="\t", low_memory=False)

    missing = [c for c in COLUMN_MAP if c not in df.columns]
    if missing:
        raise ValueError(f"Raw file missing expected columns: {missing}")

    stations = df[list(COLUMN_MAP.keys())].rename(columns=COLUMN_MAP)
    stations = stations.drop_duplicates(subset=["station_id"])
    stations = stations.dropna(subset=["lat", "lon"])
    stations["lat"] = pd.to_numeric(stations["lat"], errors="coerce")
    stations["lon"] = pd.to_numeric(stations["lon"], errors="coerce")
    stations = stations.dropna(subset=["lat", "lon"])
    stations = stations[(stations["lat"] != 0) | (stations["lon"] != 0)]

    out_cols = [c for c in OUTPUT_COLUMNS if c in stations.columns]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    stations[out_cols].to_csv(OUTPUT, index=False)
    print(f"Delta: {len(stations)} stations -> {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
