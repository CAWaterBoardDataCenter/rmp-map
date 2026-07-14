"""SMC: smc_raw.tsv → data/cleaned/smc.csv

Southern California Stormwater Monitoring Coalition station export.

Pseudocode:
  LOAD tab-separated smc_raw.tsv
  IF column "probabilistic" (or common typo "probablistic") exists:
      KEEP rows where probabilistic == False          # fixed / non-draw sites (~5k rows)
      LOCATION_ID = masterid column                 # SMC location key
  ELSE IF CD3 analyte columns present (STATIONCODE, LATITUDE, …):
      DERIVE probabilistic = STATIONNAME contains "Random"   # SMC names draw sites "… Random Site …"
      KEEP rows where probabilistic == False
      LOCATION_ID = STATIONLUROWID (fallback: STATIONCODE)
  MAP location fields → unified schema (station_id, station_name, lat, lon, …)
  DEDUPE one row per LOCATION_ID
  DROP rows with missing or invalid lat/lon
  WRITE data/cleaned/smc.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _schema import OUTPUT_COLUMNS

ROOT = Path(__file__).resolve().parent.parent
PROGRAM_ID = "smc"
RAW = ROOT / "data" / "raw" / "smc_raw.tsv"
OUTPUT = ROOT / "data" / "cleaned" / f"{PROGRAM_ID}.csv"

# Station-list export (SMC portal / smc_stations style)
STATION_LIST_COLUMN_MAP = {
    "masterid": "station_id",
    "stationname": "station_name",
    "latitude": "lat",
    "longitude": "lon",
    "county": "county",
}

# CD3 analyte export (same column names as Delta / SF Bay)
CD3_COLUMN_MAP = {
    "STATIONLUROWID": "station_id",
    "STATIONNAME": "station_name",
    "LATITUDE": "lat",
    "LONGITUDE": "lon",
    "COUNTY": "county",
    "WATERBODY_TYPE": "waterbody",
    "HUC12_NAME": "huc8",
}


def _find_column(df: pd.DataFrame, *candidates: str) -> str | None:
    lookup = {str(c).lower(): c for c in df.columns}
    for name in candidates:
        hit = lookup.get(name.lower())
        if hit is not None:
            return hit
    return None


def _is_false(value: object) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, bool):
        return not value
    text = str(value).strip().lower()
    return text in {"false", "f", "0", "no", "n"}


def _filter_non_probabilistic(df: pd.DataFrame, prob_col: str) -> pd.DataFrame:
    mask = df[prob_col].map(_is_false)
    return df.loc[mask].copy()


def _load_station_list(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    prob_col = _find_column(df, "probabilistic", "probablistic")
    if prob_col is None:
        raise ValueError("Station-list format requires a probabilistic (or probablistic) column")

    id_col = _find_column(df, "masterid", "location id", "location_id", "locationid")
    if id_col is None:
        raise ValueError("Station-list format requires masterid (or location_id) column")

    rename = {id_col: "station_id"}
    for raw_name, unified in STATION_LIST_COLUMN_MAP.items():
        col = _find_column(df, raw_name)
        if col and col != id_col:
            rename[col] = unified

    filtered = _filter_non_probabilistic(df, prob_col)
    print(f"  After probabilistic == False: {len(filtered):,} rows (from {len(df):,})")

    stations = filtered.rename(columns=rename)
    if "station_name" not in stations.columns:
        stations["station_name"] = ""
    return stations, "station-list"


def _load_cd3(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    missing = [c for c in CD3_COLUMN_MAP if c not in df.columns]
    if missing:
        raise ValueError(f"CD3 format missing expected columns: {missing}")

    derived_prob = df["STATIONNAME"].astype(str).str.contains("Random", case=False, na=False)
    filtered = df.loc[~derived_prob].copy()
    print(
        "  Note: no probabilistic column; treating STATIONNAME contains 'Random' "
        "as probabilistic=True (SMC CD3 naming convention)"
    )
    print(f"  After probabilistic == False: {len(filtered):,} rows (from {len(df):,})")

    stations = filtered[list(CD3_COLUMN_MAP.keys())].rename(columns=CD3_COLUMN_MAP)
    return stations, "cd3-analyte"


def main() -> None:
    if not RAW.exists():
        raise FileNotFoundError(f"Place SMC raw export at {RAW.relative_to(ROOT)}")

    df = pd.read_csv(RAW, sep="\t", low_memory=False)
    print(f"SMC: loaded {len(df):,} raw rows")

    prob_col = _find_column(df, "probabilistic", "probablistic")
    if prob_col is not None:
        stations, source = _load_station_list(df)
    elif "STATIONCODE" in df.columns and "LATITUDE" in df.columns:
        stations, source = _load_cd3(df)
    else:
        raise ValueError(
            "Unrecognized smc_raw.tsv format. Expected either:\n"
            "  • station-list columns: probabilistic, masterid, stationname, latitude, longitude\n"
            "  • CD3 analyte columns: STATIONCODE, STATIONNAME, LATITUDE, LONGITUDE, …"
        )

    stations = stations.drop_duplicates(subset=["station_id"])
    print(f"  Unique location IDs ({source}): {len(stations):,}")

    stations = stations.dropna(subset=["lat", "lon"])
    stations["lat"] = pd.to_numeric(stations["lat"], errors="coerce")
    stations["lon"] = pd.to_numeric(stations["lon"], errors="coerce")
    stations = stations.dropna(subset=["lat", "lon"])
    stations = stations[(stations["lat"] != 0) | (stations["lon"] != 0)]

    out_cols = [c for c in OUTPUT_COLUMNS if c in stations.columns]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    stations[out_cols].to_csv(OUTPUT, index=False)
    print(f"SMC: {len(stations)} stations -> {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
