.RECIPEPREFIX := >
.PHONY: yyz serve open clean

yyz:
> maps_v2/bin/build_aoi.sh yyz_downtown 43.6283082 -79.4218346 43.7015733 -79.3081948

serve:
> maps_v2/bin/serve.sh

open:
> xdg-open viewer/yyz_cost.html 2>/dev/null || true

clean:
> rm -f maps_v2/mbtiles/*.mbtiles
> rm -f maps_v2/build/yyz_downtown/*_color_*.tif maps_v2/build/yyz_downtown/*_0_400_byte.tif
