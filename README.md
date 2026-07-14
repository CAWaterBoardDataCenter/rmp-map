# Regional Monitoring Programs — Station Footprint Map

Interactive map of California regional water monitoring programs. Station locations (and wetland area coverage) are aggregated into **H3 hex grids** at three resolutions (≈5 km, 3 km, 1 km). The map shows **where** programs monitor — not analyte results or sample counts over time.

**Live map:** [https://isamuthung.github.io/regional_monitering_programs/](https://isamuthung.github.io/regional_monitering_programs/)

---

## Programs

| Program | What the hexes represent |
|---------|--------------------------|
| Delta | Monitoring stations |
| SF Bay | Monitoring stations |
| Klamath Basin | Monitoring stations |
| SMC | Stormwater Monitoring Coalition fixed sites |
| Southern California Bight | Survey stations across Bight batches |
| Russian River | Wetland **area coverage** (RRARI polygons), not point stations |

---

## Repo layout

```
├── index.html                 # Map UI (GitHub Pages entry point)
├── .nojekyll                  # Required so Pages serves data/ paths as-is
├── data/
│   ├── geojson/               # Built hex layers + manifest.json (served by the map)
│   ├── cleaned/               # Unified station CSVs (pipeline inputs)
│   ├── ca_counties.geojson    # Optional overlay
│   ├── ca_regional_boards.geojson
│   └── raw/                   # Local only — not in git (too large)
├── scripts/                   # clean_*.py per program
└── map/                       # build_h3_geojson.py + helpers
```

The browser only reads `index.html` and files under `data/` (geojson + overlays). Raw downloads stay on your machine.

---

## Local preview

```powershell
python -m http.server 8000
# Open http://localhost:8000
```

Do not open `index.html` via `file://` — `fetch` of GeoJSON will fail.

---

## Rebuild the map (developers)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Clean sources (see each scripts/clean_*.py for expected raw filenames)
python scripts/clean_delta.py
python scripts/clean_sf.py
python scripts/clean_klamath.py
python scripts/clean_smc.py
python scripts/clean_russian_river_wetlands.py
python scripts/clean_bight.py

# Build hex layers → data/geojson/
python map/build_h3_geojson.py
```

### Cleaned station CSV schema

Files in `data/cleaned/` are named `{program_id}.csv` with columns:

| Column | Required | Notes |
|--------|----------|-------|
| `station_id` | yes | Unique within the program |
| `station_name` | yes | Can be empty |
| `lat` / `lon` | yes | WGS84 |

Optional columns (`county`, `waterbody`, `batch_year`, etc.) show up in the hex click panel.

Russian River uses a GeoPackage of wetland polygons instead of a station CSV (`source: "polygons"` in `map/build_h3_geojson.py`). The older CEDEN station export is paused under `data/cleaned/_paused/`.

---

## GitHub Pages

This site is served from the `main` branch root.

1. Push updates to `main`
2. Repo **Settings → Pages → Deploy from branch → `main` / `/ (root)`**
3. Wait a minute, then open the live URL above

After rebuilding GeoJSON locally:

```powershell
git add data/geojson
git commit -m "Rebuild hex layers"
git push
```
