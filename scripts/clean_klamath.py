"""Klamath Basin (KBMP): KBMP monitoring-locations XLSX → data/cleaned/klamath_basin.csv

Unlike Delta/SF Bay/SMC (flat delimited exports), Klamath raw data is an Excel
workbook from KBMP. Requires openpyxl (see requirements.txt).

Pseudocode:
  LOAD Excel sheet KBMP_Monitoring_Locations (one row per monitoring effort)
  MAP KBMP ID, Site Name, Latitude, Longitude, … → unified schema
  DEDUPE one row per station_id (KBMP ID) — 2,440 unique locations in 2025-07-21 export
  DROP rows with missing, invalid, or (0,0) lat/lon
  WRITE data/cleaned/klamath_basin.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _schema import OUTPUT_COLUMNS

ROOT = Path(__file__).resolve().parent.parent
PROGRAM_ID = "klamath_basin"

# KBMP publishes dated metadata workbooks; update RAW if you download a newer file.
RAW = ROOT / "data" / "raw" / "KBMP_Monitoring_Locations_Metadata_20250721.xlsx"
RAW_SHEET = "KBMP_Monitoring_Locations"
OUTPUT = ROOT / "data" / "cleaned" / f"{PROGRAM_ID}.csv"

COLUMN_MAP = {
    "KBMP ID": "station_id",
    "Site Name": "station_name",
    "Latitude": "lat",
    "Longitude": "lon",
    "Subbasin": "subbasin",
    "Waterbody": "waterbody",
    "Organization Name": "organization",
}


def main() -> None:
    if not RAW.exists():
        raise FileNotFoundError(f"Place KBMP metadata workbook at {RAW.relative_to(ROOT)}")

    df = pd.read_excel(RAW, sheet_name=RAW_SHEET)

    missing = [c for c in COLUMN_MAP if c not in df.columns]
    if missing:
        raise ValueError(f"Workbook sheet {RAW_SHEET!r} missing expected columns: {missing}")

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
    print(f"Klamath Basin: {len(stations)} stations -> {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
