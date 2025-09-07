#!/usr/bin/env bash
set -euo pipefail
REPO=${REPO:-$HOME/dev/northstrike}
cd "$REPO"

AREA=aoi_rural_mo
S=37.6593; W=-91.1989; N=37.7674; E=-91.0621   # WGS84 bbox
EPSG=32615                                      # UTM 15N

SRC="maps/src"; BUILD="maps/build"; MASKS="maps/masks"; COST="maps/costmaps"; TILES="tiles"
mkdir -p "$SRC" "$BUILD" "$MASKS" "$COST" "$TILES" viewer

# Copernicus DSM 30 m tile for N37 W092 (covers -92..-91)
DEM_TILE="$SRC/${AREA}_cop30_W092.tif"
if [ ! -f "$DEM_TILE" ]; then
  curl --fail --retry 3 -L -o "$DEM_TILE" \
  "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N37_00_W092_00_DEM/Copernicus_DSM_COG_10_N37_00_W092_00_DEM.tif"
fi

CLIP="$BUILD/${AREA}_dtm_wgs84_clip.tif"
DTM="$BUILD/${AREA}_dtm30m.tif"
rm -f "$CLIP" "$DTM"  # avoid 'exists' errors on reruns
gdal_translate -projwin_srs EPSG:4326 -projwin $W $N $E $S -a_nodata -9999 "$DEM_TILE" "$CLIP"
gdalwarp -t_srs "EPSG:${EPSG}" -r bilinear -tr 30 30 -dstnodata -9999 -of COG \
  -co COMPRESS=DEFLATE -co BIGTIFF=IF_NEEDED "$CLIP" "$DTM"

SLOPE="$BUILD/${AREA}_slope_pct.tif"
gdaldem slope -p "$DTM" "$SLOPE" -compute_edges

_overpass() {
  local Q=$1 OUT=$2
  curl --fail --retry 3 -G 'https://overpass-api.de/api/interpreter' \
    --data-urlencode "data=$Q" -o "$OUT" || \
  curl --fail --retry 3 -G 'https://overpass.kumi.systems/api/interpreter' \
    --data-urlencode "data=$Q" -o "$OUT"
}
_overpass "[out:xml][timeout:60];(way['building']($S,$W,$N,$E);rel['building']($S,$W,$N,$E););out body;>;out skel qt;" "$SRC/${AREA}_buildings.osm"
_overpass "[out:xml][timeout:60];(way['natural'='water']($S,$W,$N,$E);rel['natural'='water']($S,$W,$N,$E);way['waterway'='riverbank']($S,$W,$N,$E);rel['waterway'='riverbank']($S,$W,$N,$E););out body;>;out skel qt;" "$SRC/${AREA}_water.osm"
_overpass "[out:xml][timeout:60];(way['leisure'='park']($S,$W,$N,$E);rel['leisure'='park']($S,$W,$N,$E););out body;>;out skel qt;" "$SRC/${AREA}_parks.osm"
_overpass "[out:xml][timeout:60];(way['highway']($S,$W,$N,$E);>;);out body;>;out skel qt;" "$SRC/${AREA}_roads.osm"

OSM_USE_CUSTOM_INDEXING=NO ogr2ogr --config OSM_USE_CUSTOM_INDEXING NO -oo USE_CUSTOM_INDEXING=NO -f GPKG "$SRC/${AREA}_buildings.gpkg" "$SRC/${AREA}_buildings.osm" multipolygons -where "building IS NOT NULL"
OSM_USE_CUSTOM_INDEXING=NO ogr2ogr --config OSM_USE_CUSTOM_INDEXING NO -oo USE_CUSTOM_INDEXING=NO -f GPKG "$SRC/${AREA}_water.gpkg"     "$SRC/${AREA}_water.osm"     multipolygons
OSM_USE_CUSTOM_INDEXING=NO ogr2ogr --config OSM_USE_CUSTOM_INDEXING NO -oo USE_CUSTOM_INDEXING=NO -f GPKG "$SRC/${AREA}_parks.gpkg"     "$SRC/${AREA}_parks.osm"     multipolygons
OSM_USE_CUSTOM_INDEXING=NO ogr2ogr --config OSM_USE_CUSTOM_INDEXING NO -oo USE_CUSTOM_INDEXING=NO -f GPKG "$SRC/${AREA}_roads.gpkg"     "$SRC/${AREA}_roads.osm"     lines

BLD="$MASKS/${AREA}_buildings_mask.tif"
WAT="$MASKS/${AREA}_water_mask.tif"
PRK="$MASKS/${AREA}_parks_mask.tif"
RD="$MASKS/${AREA}_roads_mask.tif"
for M in "$BLD" "$WAT" "$PRK" "$RD"; do
  gdal_calc.py -A "$DTM" --calc="0*A" --type=Byte --co TILED=YES --co COMPRESS=DEFLATE --outfile "$M"
done

OSM_USE_CUSTOM_INDEXING=NO ogr2ogr --config OSM_USE_CUSTOM_INDEXING NO -oo USE_CUSTOM_INDEXING=NO -f GPKG "$SRC/${AREA}_buildings.gpkg" "$SRC/${AREA}_buildings.osm" multipolygons -where "building IS NOT NULL"
OSM_USE_CUSTOM_INDEXING=NO ogr2ogr --config OSM_USE_CUSTOM_INDEXING NO -oo USE_CUSTOM_INDEXING=NO -f GPKG "$SRC/${AREA}_water.gpkg"     "$SRC/${AREA}_water.osm"     multipolygons
OSM_USE_CUSTOM_INDEXING=NO ogr2ogr --config OSM_USE_CUSTOM_INDEXING NO -oo USE_CUSTOM_INDEXING=NO -f GPKG "$SRC/${AREA}_parks.gpkg"     "$SRC/${AREA}_parks.osm"     multipolygons
OSM_USE_CUSTOM_INDEXING=NO ogr2ogr --config OSM_USE_CUSTOM_INDEXING NO -oo USE_CUSTOM_INDEXING=NO -f GPKG "$SRC/${AREA}_roads.gpkg"     "$SRC/${AREA}_roads.osm"     lines

OUT="$COST/${AREA}_cost.tif"
SLOPE_W=2.0; BLD_W=200.0; WAT_W=500.0; PRK_W=20.0; RD_W=-80.0
gdal_calc.py -A "$SLOPE" -B "$DTM" -C "$BLD" -D "$WAT" -E "$PRK" -F "$RD" \
  --calc="(B!=-9999)*(${SLOPE_W}*A + ${BLD_W}*C + ${WAT_W}*D + ${PRK_W}*E + ${RD_W}*F) + (B==-9999)*(-9999)" \
  --type=Float32 --NoDataValue=-9999 --overwrite --co TILED=YES --co COMPRESS=DEFLATE --outfile "$OUT"

VIS="$COST/${AREA}_cost8.tif"
COL="$COST/${AREA}_cost_RGBA.tif"
rm -rf "$TILES/${AREA}_cost8" "$TILES/${AREA}_cost_color"
gdal_translate "$OUT" "$VIS" -ot Byte -scale 0 1000 1 255 -a_nodata 0

mkdir -p scripts/maps
cat > "scripts/maps/cost_ramp_${AREA}.txt" <<'TXT'
nv  0   0   0   0
0   0   0   0   0
5   37  52 148 160
20  65 182 196 190
50  123 204 196 210
100 255 255 128 230
200 254 178  76 240
400 240  59  32 255
TXT

gdaldem color-relief -alpha "$OUT" "scripts/maps/cost_ramp_${AREA}.txt" "$COL" -of GTiff -co TILED=YES -co COMPRESS=DEFLATE
gdal2tiles.py --xyz -r bilinear -z 11-16 "$VIS" "$TILES/${AREA}_cost8"
gdal2tiles.py --xyz -r bilinear -z 11-16 "$COL" "$TILES/${AREA}_cost_color"

test -f viewer/empty.png || printf 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQImWNgYGBgAAAABQABJzQnCgAAAABJRU5ErkJggg==' | base64 -d > viewer/empty.png
echo "AOI-A done → $OUT"
