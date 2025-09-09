#!/usr/bin/env bash
set -euo pipefail
# Usage: osm_masks_from_pbf.sh <AREA> <AOI.osm.pbf> <DEM_UTM.tif>
AREA="${1:?area}"; PBF="${2:?aoi.osm.pbf}"; DEM="${3:?utm_dem_tif}"
OUT="maps_v2/build/${AREA}"; mkdir -p "$OUT"
GPKG="${OUT}/${AREA}_features.gpkg"; rm -f "$GPKG"
# seed: always recreate mask TIFFs (rm + --overwrite), unset NoData
seed(){ rm -f "$1"; gdal_calc.py -A "$DEM" --A_band=1 --calc="0" --NoDataValue=0 \
  --type=Byte --overwrite --co=TILED=YES --co=COMPRESS=DEFLATE --outfile "$1" >/dev/null
  gdal_edit.py -unsetnodata "$1" >/dev/null; }
seed "$OUT/${AREA}_roads_mask.tif"; seed "$OUT/${AREA}_water_mask.tif"
seed "$OUT/${AREA}_parks_mask.tif"; seed "$OUT/${AREA}_buildings_mask.tif"
# Use SQLite dialect + hstore_get_value() for OSM other_tags
ogr2ogr -f GPKG "$GPKG" "$PBF" -dialect SQLite -sql \
"SELECT * FROM lines WHERE hstore_get_value(other_tags,'highway') IS NOT NULL" -nln lines >/dev/null
ogr2ogr -f GPKG -append "$GPKG" "$PBF" -dialect SQLite -sql \
"SELECT * FROM multipolygons WHERE (hstore_get_value(other_tags,'natural')='water' OR
 hstore_get_value(other_tags,'waterway') IS NOT NULL OR hstore_get_value(other_tags,'landuse')='reservoir')" -nln water >/dev/null
ogr2ogr -f GPKG -append "$GPKG" "$PBF" -dialect SQLite -sql \
"SELECT * FROM multipolygons WHERE (hstore_get_value(other_tags,'leisure')='park' OR
 hstore_get_value(other_tags,'landuse') IN ('recreation_ground','grass'))" -nln parks >/dev/null
ogr2ogr -f GPKG -append "$GPKG" "$PBF" -dialect SQLite -sql \
"SELECT * FROM multipolygons WHERE hstore_get_value(other_tags,'building') IS NOT NULL" -nln buildings >/dev/null
gdal_rasterize -burn 1 -at "$GPKG" "$OUT/${AREA}_roads_mask.tif"     -l lines >/dev/null || true
gdal_rasterize -burn 1 -at "$GPKG" "$OUT/${AREA}_water_mask.tif"     -l water >/dev/null || true
gdal_rasterize -burn 1 -at "$GPKG" "$OUT/${AREA}_parks_mask.tif"     -l parks >/dev/null || true
gdal_rasterize -burn 1 -at "$GPKG" "$OUT/${AREA}_buildings_mask.tif" -l buildings >/dev/null || true
for m in roads water parks buildings; do gdal_edit.py -unsetnodata "$OUT/${AREA}_${m}_mask.tif" >/dev/null; done
