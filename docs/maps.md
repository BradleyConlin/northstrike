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

### Visualization scale
- Cost viz is scaled **0 → 1500 ⇒ 1 → 255** before color-relief (planner raster remains Float32).
- Typical browse zooms: **z11–z17** for `yyz_downtown_cost8.mbtiles`.

## Implementation notes & troubleshooting

- **Temp file overwrite (GeoJSON)**: On Jammy, `ogr2ogr`’s GeoJSON driver won’t overwrite an existing file.
  We create temp names that **don’t pre-exist** (`mktemp -u --suffix=.geojson`) so `ogr2ogr` can write them.

- **GDAL options (Jammy-safe)**: Avoid `gdalinfo -ovr`, `gdal_translate -srcnodata/-dstnodata` (not available).
  We recompute stats with `-stats` and unset NoData on the 8-bit VRT before color-relief.

- **Cost viz scale**: Tiles are from an 8-bit VRT scaled **0→1500 ⇒ 1→255**. The Float32 COG remains the planner truth.
  Typical browse zooms: **z11–z17** for `yyz_downtown`.

- **Masks**: strict **0/1 Byte**, `NoData=0`, NEAREST overviews only.
  Quick sanity: `gdalinfo -stats maps/build/<AREA>_{roads,water,parks}_mask.tif` → Min=0, Max=1, non-zero mean if present.

- **OSM water filter**: Some extracts don’t expose a `water` column; use `natural='water'`
  (and optionally `landuse IN ('reservoir','basin')`, `waterway='riverbank'`) to catch common cases.

- **Viewer**:
  - Serve the repo root: `python -m http.server 8080` and open `http://localhost:8080/viewer/view.html`.
  - The viewer requests `/tiles/{z}/{x}/{y}.png?v=N` (absolute path + cache-buster).
    Make sure tiles live under `tiles/` at repo root, and you generated **XYZ** (not TMS).

- **Parity smoke**: `tiles-parity` samples MBTiles pixels and compares to the Float32 raster (±5 DN, 0↔1 allowed).
  A zero tile with Float32 NaN is treated as OK (outside AOI).

- **Road preference**: To prefer roads, set a **negative** `road_penalty` in `scripts/maps/cost_recipe.yaml`
  (example: `road_penalty: -40.0`).

- **Publishing**: `make maps-publish AREA=<aoi>` writes `artifacts/maps/<AREA>_tiles_cost8.zip` and a `.sha256`.
