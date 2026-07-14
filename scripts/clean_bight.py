"""Southern California Bight: bight_raw.tsv (tab-separated) → data/cleaned/bight.csv

Pseudocode:
  LOAD tab-separated bight_raw.tsv — only station columns (usecols; ~800k analyte rows)
  EXTRACT batch_year from PARENTPROJECT (1994 pilot, then 5-year survey cycles)
  MAP STATIONCODE, STATIONNAME, LATITUDE, LONGITUDE, … → unified schema
  DEDUPE one row per (batch_year, lat, lon) — same coords may reappear in later batches
  DROP rows with missing, invalid, or (0,0) lat/lon
  WRITE data/cleaned/bight.csv
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _schema import OUTPUT_COLUMNS

ROOT = Path(__file__).resolve().parent.parent
PROGRAM_ID = "bight"
RAW = ROOT / "data" / "raw" / "bight_raw.tsv"
OUTPUT = ROOT / "data" / "cleaned" / f"{PROGRAM_ID}.csv"

# Read only columns needed for station footprint — avoids loading analyte fields.
USECOLS = [
    "STATIONCODE",
    "STATIONNAME",
    "LATITUDE",
    "LONGITUDE",
    "COUNTY",
    "WATERBODY_TYPE",
    "HUC8_NAME",
    "SAMPLEAGENCY",
    "PARENTPROJECT",
]

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

BATCH_YEAR_RE = re.compile(r"(?:19|20)\d{2}")


def batch_year(parent_project: str) -> str | None:
    match = BATCH_YEAR_RE.search(str(parent_project))
    return match.group(0) if match else None


def main() -> None:
    if not RAW.exists():
        raise FileNotFoundError(
            f"Place Southern California Bight raw export at {RAW.relative_to(ROOT)}"
        )

    df = pd.read_csv(RAW, sep="\t", usecols=USECOLS, low_memory=False)

    missing = [c for c in COLUMN_MAP if c not in df.columns]
    if missing:
        raise ValueError(f"Raw file missing expected columns: {missing}")

    stations = df[list(COLUMN_MAP.keys())].rename(columns=COLUMN_MAP)
    stations["batch_year"] = df["PARENTPROJECT"].map(batch_year)

    stations["lat"] = pd.to_numeric(stations["lat"], errors="coerce")
    stations["lon"] = pd.to_numeric(stations["lon"], errors="coerce")
    stations = stations.dropna(subset=["lat", "lon", "batch_year"])
    stations = stations[(stations["lat"] != 0) | (stations["lon"] != 0)]

    # Unique physical location per survey batch; keep first station metadata at each point.
    stations = stations.drop_duplicates(subset=["batch_year", "lat", "lon"], keep="first")

    out_cols = [c for c in OUTPUT_COLUMNS if c in stations.columns]
    out_cols.append("batch_year")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    stations[out_cols].to_csv(OUTPUT, index=False)

    year_counts = stations["batch_year"].value_counts().sort_index().to_dict()
    print(
        f"Southern California Bight: {len(stations)} stations ({year_counts}) "
        f"-> {OUTPUT.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
