#!/usr/bin/env bash
set -euo pipefail
# Usage: osm_masks_from_pbf.sh <AREA> <AOI.osm.pbf> <DEM_UTM.tif>
AREA="${1:?area}"; PBF="${2:?aoi.osm.pbf}"; DEM="${3:?utm_dem_tif}"
OUT="maps_v2/build/${AREA}"; mkdir -p "$OUT"
GPKG="${OUT}/${AREA}_features.gpkg"; rm -f "$GPKG"

# 0) Seed DEM-aligned Byte masks (0/1, NoData=0) so downstream can’t break
seed(){ gdal_calc.py -A "$DEM" --A_band=1 --calc="0" --NoDataValue=0 --type=Byte \
  --co=TILED=YES --co=COMPRESS=DEFLATE --co=BIGTIFF=IF_NEEDED --overwrite --outfile "$1" >/dev/null; }
M_ROADS="$OUT/${AREA}_roads_mask.tif";    seed "$M_ROADS"
M_WATER="$OUT/${AREA}_water_mask.tif";    seed "$M_WATER"
M_PARKS="$OUT/${AREA}_parks_mask.tif";    seed "$M_PARKS"
M_BLDG="$OUT/${AREA}_buildings_mask.tif"; seed "$M_BLDG"

# 1) PBF → GPKG layers using tag-safe SQL (hstore_get_value on other_tags)
to_gpkg(){ local name="$1" sql="$2"
  ogr2ogr -f GPKG -append -nln "$name" "$GPKG" "$PBF" -dialect SQLITE -sql "$sql" || true; }
to_gpkg roads     "SELECT * FROM lines WHERE hstore_get_value(other_tags,'highway') IS NOT NULL"
to_gpkg water     "SELECT * FROM multipolygons WHERE hstore_get_value(other_tags,'natural')='water'
                   OR hstore_get_value(other_tags,'waterway') IS NOT NULL
                   OR hstore_get_value(other_tags,'landuse')='reservoir'"
to_gpkg parks     "SELECT * FROM multipolygons WHERE hstore_get_value(other_tags,'leisure')='park'
                   OR hstore_get_value(other_tags,'landuse') IN ('recreation_ground','grass')"
to_gpkg buildings "SELECT * FROM multipolygons WHERE hstore_get_value(other_tags,'building') IS NOT NULL"

# 2) Burn layers if present (-at = all-touched)
burn(){ local L="$1" M="$2"
  if ogrinfo -so "$GPKG" "$L" >/dev/null 2>&1; then gdal_rasterize -burn 1 -at -l "$L" "$GPKG" "$M" >/dev/null; fi; }
burn roads "$M_ROADS"; burn water "$M_WATER"; burn parks "$M_PARKS"; burn buildings "$M_BLDG"

echo "[*] Masks ready:"; printf "    %s\n" "$M_BLDG" "$M_ROADS" "$M_WATER" "$M_PARKS"
