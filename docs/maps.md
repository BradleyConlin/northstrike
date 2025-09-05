# Maps & Costmaps

- **AOI**: `yyz_downtown` (EPSG:32617, 1 m)
- **Pipeline**: HRDEM → slope (percent) → OSM → masks (0/1 Byte) → cost Float32 (planner) → 8-bit VRT + color-relief → tiles/MBTiles (viewer)
- **Gates**:
  - `maps-readback`: sample Float32 at random points → CSV + JSON summary
  - `tiles-parity`: compare MBTiles grayscale vs scaled Float32 at pixel centers (±5 DN, 0↔1 allowed)

# Toronto — yyz_downtown AOI

- AOI bounds (WGS84):
  W: -79.4218346223, S: 43.6284246884, E: -79.3080338582, N: 43.7015732552
- DEM: HRDEM 1 m DTM (CanElevation), reprojected to **EPSG:32617 (WGS 84 / UTM 17N)**.
- Pixel size: **1.0 m**.
- Products:
  - Float32 planner raster: `maps/costmaps/yyz_downtown_cost.tif` (NoData = -9999, COG, AVERAGE overviews).
  - 8-bit visualization VRT (scaled 0→1500 ⇒ 1→255): `maps/costmaps/yyz_downtown_cost_8bit.vrt`.
  - MBTiles (XYZ): `maps/mbtiles/yyz_downtown_cost8.mbtiles` (minzoom=11, maxzoom=17, format=png).
- Masks: strict **0/1 Byte**, NoData=0, NEAREST overviews.
- Tile scheme: **XYZ** (no TMS), cache-busted when regenerating.

## Attribution
- Contains information licensed under the **Open Government Licence – Canada** (HRDEM / CanElevation).
- © **OpenStreetMap contributors** (ODbL). The rasterized building mask is a Produced Work.
