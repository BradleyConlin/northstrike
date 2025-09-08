.RECIPEPREFIX := >
.PHONY: yyz serve open publish verify readback clean

# Build YYZ tiles end-to-end (runs inside maps_v2/)
yyz:
> bin/build_aoi.sh yyz_downtown 43.6283082 -79.4218346 43.7015733 -79.3081948

# Serve local tiles and open the viewer
serve:
> bin/serve.sh
open:
> xdg-open ../viewer/yyz_cost.html 2>/dev/null || true

# Copy MBTiles to artifacts/ and print metadata summary
publish:
> bin/publish.sh yyz_downtown

# Light check: print top of gdalinfo for the MBTiles in artifacts/
verify:
> gdalinfo ../artifacts/maps/mbtiles/yyz_downtown_cost_color.mbtiles | sed -n '1,80p'

# Planner smoke: sample Float32 raster by lat/lon CSV
readback:
> bin/smoke_readback.py yyz_downtown /tmp/yyz_pts.csv

clean:
> rm -f mbtiles/*.mbtiles
> rm -f build/yyz_downtown/*_color_*.tif build/yyz_downtown/*_0_400_byte.tif
