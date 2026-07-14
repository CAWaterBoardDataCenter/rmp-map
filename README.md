# Regional Monitoring Programs Station Footprint Map

This is an interactive map of six California regional water monitoring programs (RMPs). Station locations (and wetland area coverage) are aggregated into **H3 hex grids** at three resolutions (≈5 km, 3 km, 1 km). The map shows where programs monitor and not results or sample counts over time. However, there is clear traceability from where the data was sourced and the method used to synthesize the data. 

The Live Map is available here: https://isamuthung.github.io/regional_monitering_programs/

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

---

## Sources

To find where the raw files come from, here’s the exact links and instructions for accessing the orignial downloads that have been used in this map for each program. 

### **Delta Regional Monitoring Program**

Here’s the main website: https://deltarmp.org/

1. https://ceden.waterboards.ca.gov/CQT/Home/AqtTool
2. Process: “Download Results as TSV”
    
    Category: “Water Quality (Chemistry)”
    
    **Program “Delta Regional Monitoring Program”**
    
    IncludeQCData: “NoQCData”
    
    Submit
    

### **San Francisco Bay**

Here’s the base website: https://www.sfei.org/programs/rmp

1. https://ceden.waterboards.ca.gov/CQT/Home/AqtTool
2. Process: “Download Results as TSV”
    
    Category: “Water Quality (Chemistry)”
    
    **Program “SF Bay Regional Monitoring for Water Quality”**
    
    IncludeQCData: “NoQCData”
    
    Submit
    

### **Klamath Basin**

Here is the base website: https://kbmp.net/ This program keeps a clean list of their stations separate from CEDEN like the others above, so it’s intutive to get their spatial footprint even though it’s not in an offical data portal. 

1. https://kbmp.net/maps-and-data/monitoring-locations
2. https://kbmp.ecoatlas.org/map.php - “Monitoring Location Metadata Spreadsheet” is the excel worksheet that’s directly in data/raw. One data gap is that there’s a disparity between the 2440 stations present on their website and what’s available in CEDEN under “Klamath Basin Monitoring Program” which displays only 173 stations.
    
    From their website, I’m able to download a xlsx (Microsoft Excel Workbook) therefore, the script ingests this as the raw data and then translates it into the cleaned csv directly. There’s no need for the user to convert to tsv if they run this again.
    

### **Stormwater Monitoring Coalition (SMC)**

Here’s their base website: https://socalsmc.org/. Antoher data gap, if you try finding data directly on their website, you will hit deadends. The links under https://socalsmc.org/data/ do not work. These also don’t work: https://smc.sccwrp.org/#dr and https://nexus.sccwrp.org/smcdataquery/ Instead, use CEDEN to access the data. 

1. https://ceden.waterboards.ca.gov/CQT/Home/AqtTool
2. Process: “Download Results as TSV”
    
    Category: “Water Quality (Chemistry)”
    
    **Program “Southern CA Stormwater Monitoring Coalition”**
    
    IncludeQCData: “NoQCData”
    
    Submit
    

### **Southern California Bight**

Here is their base website: https://www.sccwrp.org/.  Although they do have their own data portal, it was difficult to parse where to gather station footprint data: https://dataportal.sccwrp.org/ Therefore we use CEDEN. 

1. https://ceden.waterboards.ca.gov/CQT/Home/AqtTool
2. Process: “Download Results as TSV”
    
    Category: “Water Quality (Chemistry)”
    
    **Program “Southern California Bight Program”**
    
    IncludeQCData: “NoQCData”
    
    Submit
    

One thing to note, this dataset has batches of 5 years with various numbers of station locations. The script is designed to handle this, and adds an additional column indicating which batch year the unique station is from.

### **Russian River**

This program has multiple webites to which to find information, such as this: https://www.russianriverconfluence.org/r3mp and this:  [](https://www.russianriverconfluence.org/r3mp)https://sites.google.com/sfei.org/r3mp/ While they do have data published in CEDEN, it’s not substantive for our purposes and likely outdated, so this is the only program where I created the hexagons out of the raw river system geopackage file they had on their website. 

This is another link to find more on them: https://www.sfei.org/projects/russian-river-regional-monitoring-program-comprehensive-basemap-surface-waters-and#toc-associated-data

This is the link where I downloaded the datafile (RRARI v1.0 Wetland Polygons (561 MB) geopackage) directly from them: https://www.sfei.org/data/russian-river-aquatic-resource-inventory-rrari-version-10-gis-data Since this raw data differs from the others, the clean script is made specificly for this gpkg (geopackage) data. Thus, the hexagons on the map for this program is derived from polygons of the wetland habitat, not specific station data, but it should help get a sense of its rough footprint nonetheless. The steps below are the ways to get data from CEDEN, but it is likely incomplete for the reasons stated here. 

1. https://ceden.waterboards.ca.gov/CQT/Home/AqtTool
2. Process: “Download Results as TSV”
    
    Category: “Water Quality (Chemistry)”
    
    **Program “Russian River MS4 Program”**
    
    IncludeQCData: “NoQCData”
    
    Submit
    

One thing to note, there were only 8 unique stations through CEDEN. And the links through the official website do not yield directly to their data although they do state they want to improve data visualization and access.

---

## Repo layout

```
├── index.html                 # Map UI 
├── .nojekyll                  
├── data/
│   ├── geojson/               # Built hex layers and manifest.json 
│   ├── cleaned/               # Unified station CSVs
│   ├── ca_counties.geojson    # Optional overlay
│   ├── ca_regional_boards.geojson
│   └── raw/                   # Local only
├── scripts/                   # clean .py per program
└── map/                       # build_h3_geojson.py amd helpers
```

The browser only reads `index.html` and files under `data/` (geojson + overlays). Raw downloads stay on the machine, however you are able to find access to those raw files through the steps below.

---

## For Developers

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

# Open <http://localhost:8000>
python -m http.server 8000
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

## GitHub Pages

This site is served from the `main` branch root. These are the steps to re-upload this to Github Pages

1. Push updates to `main`
2. Repo **Settings → Pages → Deploy from branch → `main` / `/ (root)`**
3. Wait a minute, then open the live URL above and the map should render correctly.

If you decide to rebuild the GeoJSON file locally, then do this to update the map.

```powershell
git add data/geojson
git commit -m "Rebuild hex layers"
git push
```
