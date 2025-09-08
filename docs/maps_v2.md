# Maps v2 — YYZ cost overlay (planner + tiles)

**AOI (YYZ downtown):** S 43.6283082, W −79.4218346, N 43.7015733, E −79.3081948
**CRS (canonical):** UTM zone 17N (EPSG:32617) at 1 m/px
**Processing:** Reproject DEM → UTM@1 m → `gdaldem slope -p` (percent) → OSM buildings mask (0/1, all-touched) → Float32 cost `2·slope + 200·buildings` → Byte clamp 0→400 → color relief (RGBA) → EPSG:3857 → MBTiles (`gdal_translate -of MBTILES` + `gdaladdo`).

**Reasoning:** Slope computed on metric DEMs uses `-p`; only geographic (degrees) DEMs require a scale (e.g., `-s 111120`).
**Viewer:** XYZ tiles via mbtileserver; Leaflet overlay on OSM.

## Data sources & attribution
- **OpenStreetMap** — © OpenStreetMap contributors. Data under the [ODbL]; attribution required and must be visible near the produced map. :contentReference[oaicite:7]{index=7}
- **HRDEM (CanElevation)** — High Resolution Digital Elevation Model (1 m/2 m). Licensed under the **Open Government Licence – Canada**. :contentReference[oaicite:8]{index=8}

[ODbL]: https://www.openstreetmap.org/copyright
