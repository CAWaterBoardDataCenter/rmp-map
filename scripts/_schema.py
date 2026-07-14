"""
Unified station schema for the regional monitoring map pipeline.

Every cleaned CSV in data/cleaned/ must use these exact column names.
"""

from __future__ import annotations

# Required — map will not build without these
REQUIRED_COLUMNS = ("station_id", "station_name", "lat", "lon")

# Recommended — shown in hex click panel when present
OPTIONAL_COLUMNS = ("county", "waterbody", "subbasin", "huc8", "organization")

# Full column order when writing cleaned files
OUTPUT_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS
