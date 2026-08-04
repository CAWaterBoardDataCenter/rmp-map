# Regional Monitoring Programs Station Footprint Map

Interactive map of six California regional water monitoring programs (RMPs). Station locations (and, for Russian River, wetland inventory polygons) are aggregated into **H3 hex grids** at about 5 km, 3 km, and 1 km. The map shows **where** programs observe the landscape — not lab results over time.

Live map: https://isamuthung.github.io/regional_monitering_programs/

Local preview:

```powershell
python -m http.server 3000
# open http://localhost:3000
```

---

## What the map is for

Programs differ in design and data systems, but each layer answers the same spatial question: where does this program observe? Hex grids put those footprints on a common grid so overlaps and gaps are easier to see.

Most CEDEN-based layers come from **Water Quality (Chemistry)** downloads used to locate stations. Separate CEDEN categories (toxicity, tissue, benthic, habitat) were not pulled into this build. Klamath Basin uses KBMP’s station metadata spreadsheet. Russian River uses RRARI wetland inventory polygons, not sample stations.

---

## Programs

| Program | What the hexes represent |
| --- | --- |
| Delta | Monitoring stations |
| SF Bay | Monitoring stations |
| Klamath Basin | Monitoring stations |
| SMC | Stormwater Monitoring Coalition fixed sites |
| Southern California Bight | Survey stations across Bight batches |
| Russian River | Wetland area coverage (RRARI polygons), not point stations |

### Russian River wetland hexes

Each Russian River hex counts how many **RRARI wetland inventory polygons** intersect that cell. Those are delineated habitat features from the source GIS — not “N wetlands that are each monitored with water samples” inside the hex. Monitoring results, if any, must be sought from R3MP / SFEI sources or CEDEN separately.

Program blurbs, themes, freshness, and find-data links for the UI live in [`data/program_profiles.json`](data/program_profiles.json).

---

## Map UI (local / Pages)

- **About** — welcome pane (overview, program browser, find-data help)
- **Summary** — half-screen drawer; solo-focuses one RMP on the map and flies to its bounds
- **Programs / Hex / Map / Overlays / Filter** — layer and view controls
- **Filter** — regional water board filter; non-matching hexes are grayed on the map
- Defaults: light-grey basemap, 5 km hexes, three lighter programs (Delta, SF Bay, SMC)

---

## Finding data (CEDEN / data.ca.gov)

Yes — several programs appear in the CEDEN Query Tool under the **Program** filter (exact names are in `program_profiles.json`).

### CEDEN Query Tool (best for program-specific pulls)

1. Open https://ceden.waterboards.ca.gov/CQT/Home/AqtTool  
2. Process: Download Results as TSV  
3. Category: Water Quality (Chemistry)  
4. Program: use the exact CEDEN program name for that RMP  
5. IncludeQCData: NoQCData → Submit  

### data.ca.gov

https://data.ca.gov/dataset/?q=CEDEN hosts yearly bulk files and portal APIs by **data category** (chemistry, toxicity, etc.). Those dumps do **not** filter cleanly by Program the way the CEDEN Query Tool does. Prefer CEDEN for program-scoped downloads; use Open Data for category-wide bulk access.

### Example web-service query URLs

`program_profiles.json` includes example CEDEN web-service URLs shaped like:

```text
https://cedenwebservices.waterboards.ca.gov:9267/cedenwaterqualityresultslist/?queryParams={"filter":[{"program":"PROGRAM_NAME_HERE"}],"top":1000}
```

These are **starting points for developers**, not a guarantee that every environment returns a full extract. See **Testing the example API URLs** below.

---

## Sources (how this map’s raw files were obtained)

### Delta Regional Monitoring Program

Website: https://deltarmp.org/

1. https://ceden.waterboards.ca.gov/CQT/Home/AqtTool  
2. Download Results as TSV → Category: Water Quality (Chemistry) → Program: **Delta Regional Monitoring Program** → NoQCData → Submit  

### San Francisco Bay

Website: https://www.sfei.org/programs/rmp

1. CEDEN Query Tool → Chemistry → Program: **SF Bay Regional Monitoring for Water Quality** → NoQCData  

### Klamath Basin

Website: https://kbmp.net/

Primary footprint: KBMP Monitoring Location Metadata spreadsheet  
https://kbmp.net/maps-and-data/monitoring-locations · https://kbmp.ecoatlas.org/map.php  

Note: CEDEN under “Klamath Basin Monitoring Program” has far fewer stations than KBMP’s spreadsheet.

### Stormwater Monitoring Coalition (SMC)

Website: https://socalsmc.org/

CEDEN Query Tool → Chemistry → Program: **Southern CA Stormwater Monitoring Coalition** → NoQCData  

(SMC public data links are often unreliable; CEDEN was the practical path used here.)

### Southern California Bight

Website: https://www.sccwrp.org/

CEDEN Query Tool → Chemistry → Program: **Southern California Bight Program** → NoQCData  

Stations carry a survey `batch_year` in cleaned data.

### Russian River

R3MP overview: https://www.russianriverconfluence.org/r3mp  

Primary footprint: RRARI v1.0 Wetland Polygons (geopackage)  
https://www.sfei.org/data/russian-river-aquatic-resource-inventory-rrari-version-10-gis-data  

CEDEN “Russian River MS4 Program” has very few unique stations and is not used for the primary hex footprint.

---

## Repo layout

```
├── index.html                 # Map UI
├── .nojekyll
├── data/
│   ├── program_profiles.json  # UI summaries, themes, find-data links
│   ├── geojson/               # Built hex layers + manifest.json
│   ├── cleaned/               # Unified station CSVs
│   ├── ca_counties.geojson
│   ├── ca_regional_boards.geojson
│   └── raw/                   # Local only (gitignored)
├── scripts/                   # clean_*.py per program
└── map/                       # build_h3_geojson.py and helpers
```

The browser only reads `index.html` and files under `data/` (geojson, overlays, profiles). Raw downloads stay local.

---

## For developers

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

python -m http.server 3000
```

### Cleaned station CSV schema

Files in `data/cleaned/` are named `{program_id}.csv` with columns:

| Column | Required | Notes |
| --- | --- | --- |
| `station_id` | yes | Unique within the program |
| `station_name` | yes | Can be empty |
| `lat` / `lon` | yes | WGS84 |

Optional columns (`county`, `waterbody`, `batch_year`, etc.) show up in the hex click panel.

Russian River uses a GeoPackage of wetland polygons instead of a station CSV (`source: "polygons"` in `map/build_h3_geojson.py`). The older CEDEN station export is paused under `data/cleaned/_paused/`.

---

## Testing the example API URLs

What they are: example GET requests against CEDEN’s web services (`cedenwaterqualityresultslist` and related endpoints), with a JSON-style `queryParams` filter that includes a **program** name. They are documented as developer examples in About → Find data and in `program_profiles.json`.

What they are **not**: a live guaranteed download of this map’s full chemistry extracts, and not the same as data.ca.gov’s yearly Open Data APIs.

### How to test

1. Copy an example URL from `data/program_profiles.json` → `programs.<id>.api.url` (Delta / SF Bay / SMC / Bight have examples).  
2. Paste into a browser address bar, or:

```powershell
Invoke-WebRequest -Uri 'PASTE_URL_HERE' -Headers @{ Accept = 'text/csv' } -OutFile ceden_sample.csv
```

3. Expect either CSV/text results, an auth/network error, or an empty/partial response depending on CEDEN service availability, network path, and query size (`top` caps the row count).  
4. For reliable program-scoped downloads for rebuilding this map, use the **CEDEN Query Tool** steps above instead of depending on the web-service URL alone.  
5. For category-wide bulk files, use https://data.ca.gov/dataset/surface-water-chemistry-results (and related CEDEN datasets) — those portal APIs do not replace Program filtering.

Klamath and Russian River do not have a dependable program-scoped chemistry web-service URL in this project; use KBMP / RRARI downloads.

---

## GitHub Pages

Served from the `main` branch root.

1. Push updates to `main`  
2. Repo **Settings → Pages → Deploy from branch → `main` / `/ (root)`**  
3. Open the live URL above  

After rebuilding GeoJSON locally:

```powershell
git add data/geojson
git commit -m "Rebuild hex layers"
git push
```
