# Maps & Costmaps — Attributions & Notes

**AOIs built:** Toronto (UTM17N), Rural Missouri (UTM15N).
**Artifacts:** Float32 cost COGs (planner truth) + color PNG MBTiles (EPSG:3857, XYZ).

**Attribution (required when publishing anything derived):**
- DEM (Canada): Contains information licensed under the Open Government Licence – Canada. Source: NRCan CanElevation HRDEM (1 m).
- DEM (Global): Contains modified Copernicus DEM data [Copernicus Programme].
- OSM: © OpenStreetMap contributors (ODbL). Our raster masks are a “Produced Work.”

**Viewer:** local only, `viewer/mbtiles_overlay.html?svc=<service>`, served at 127.0.0.1.
**Tile scheme:** XYZ `{z}/{x}/{y}.png` (not TMS).
**Masks:** Strict 0/1 Byte, no NoData.
**Planner raster:** Float32 with NoData = −9999 outside AOI.
