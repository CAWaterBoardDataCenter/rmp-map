# Paused / inactive cleaned outputs

Files here are **not** picked up by `map/build_h3_geojson.py`.

| File | Program | Why paused |
|------|---------|------------|
| `russian_river_ceden.csv` | Russian River (CEDEN MS4) | Only 8 sparse point stations; replaced by RRARI wetland polygon coverage |

To regenerate (optional):

```powershell
python scripts/clean_russian_river.py
```

Active Russian River map layer uses `data/cleaned/russian_river_wetlands.gpkg` via `scripts/clean_russian_river_wetlands.py`.
