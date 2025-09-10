# Maps v2 — Local overlays

- Float32 “planner truth”: `maps_v2/build/<area>/<area>_cost_f32.tif` (COG).
- Color MBTiles overlays: `artifacts/maps/mbtiles/<area>_cost_color.mbtiles` (EPSG:3857 / XYZ).
- View locally:
  - Static server (from repo root): `python3 -m http.server 8000 --bind 127.0.0.1`
  - MBTiles server: see `scripts/maps/serve_mbtiles.sh`
  - Open: `http://127.0.0.1:8000/viewer/mbtiles_overlay.html?svc=<area>_cost_color`
- Notes:
  - Overlay URL pattern is XYZ `{z}/{x}/{y}.png` (Leaflet).
  - `mbtileserver` exposes `/services/<id>` (TileJSON) and `/services/<id>/tiles/{z}/{x}/{y}.png`.
- Attribution: © OpenStreetMap contributors; DEM: NRCan HRDEM (OGL-Canada).
