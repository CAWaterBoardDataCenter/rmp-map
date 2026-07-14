"""
Template: raw program export → unified cleaned station CSV.

Copy this file to clean_<program>.py and fill in the CONFIG section.
Each program's raw file can have any column names; the output must match
the unified schema documented in README.md and scripts/_schema.py.

Output: data/cleaned/<program_id>.csv

Pseudocode:
  LOAD raw export (delimiter / Excel sheet configured below)
  [OPTIONAL] FILTER rows (program-specific — see README per-program notes)
  MAP raw columns → unified schema
  DEDUPE one row per station_id
  DROP rows with missing, invalid, or (0,0) lat/lon
  WRITE data/cleaned/<program_id>.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _schema import OUTPUT_COLUMNS

ROOT = Path(__file__).resolve().parent.parent

# --- CONFIG (edit per program) -----------------------------------------------

PROGRAM_ID = "example"  # slug used by the map: delta | sf_bay | klamath_basin | smc
PROGRAM_LABEL = "Example Program"  # human-readable; for your notes only

RAW_FILE = ROOT / "data" / "raw" / "example_raw.csv"  # your download, any name
OUTPUT_FILE = ROOT / "data" / "cleaned" / f"{PROGRAM_ID}.csv"

# Map raw column names → unified schema (only include columns you have)
COLUMN_MAP = {
    # "RawColumnName": "unified_name",
    "StationCode": "station_id",
    "StationName": "station_name",
    "Latitude": "lat",
    "Longitude": "lon",
    "county_name": "county",
    "WBTypeName": "waterbody",
}

# Column used to deduplicate rows into one record per physical station
ID_COLUMN_RAW = "StationCode"

# Set sep="\t" for TSV exports
CSV_SEP = ","

# -----------------------------------------------------------------------------


def main() -> None:
    if not RAW_FILE.exists():
        raise FileNotFoundError(f"Raw file not found: {RAW_FILE}")

    df = pd.read_csv(RAW_FILE, sep=CSV_SEP, low_memory=False)

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

    # Keep only unified columns that exist
    out_cols = [c for c in OUTPUT_COLUMNS if c in stations.columns]
    stations = stations[out_cols]

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    stations.to_csv(OUTPUT_FILE, index=False)
    print(f"{PROGRAM_LABEL}: {len(stations)} stations -> {OUTPUT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
