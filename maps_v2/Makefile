.RECIPEPREFIX := >
.PHONY: toronto rural weminuche aoi-all publish verify

toronto:
> bin/build_aoi.sh toronto 43.6283082 -79.4218346 43.7015733 -79.3081948

rural:
> bin/build_aoi.sh rural_mo 37.6593 -91.1989 37.7674 -91.0621

weminuche:
> bin/build_aoi.sh weminuche_co 37.20 -107.70 37.50 -107.20

aoi-all: toronto rural weminuche

publish:
> bin/publish.sh toronto || true
> bin/publish.sh rural_mo || true
> bin/publish.sh weminuche_co || true

verify:
> gdalinfo ../artifacts/maps/mbtiles/toronto_cost_color.mbtiles      | sed -n '1,20p' || true
> gdalinfo ../artifacts/maps/mbtiles/rural_mo_cost_color.mbtiles     | sed -n '1,20p' || true
> gdalinfo ../artifacts/maps/mbtiles/weminuche_co_cost_color.mbtiles | sed -n '1,20p' || true
