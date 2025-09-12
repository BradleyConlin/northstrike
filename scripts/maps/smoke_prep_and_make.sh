# --- smoke symlink guard (CI) ---
AOI="${1:-toronto_downtown}"
BUILD="maps/build/${AOI}_dtm1m.tif"
SRC="maps/src/${AOI}_dem.tif"
if [[ -f "$BUILD" && ! -f "$SRC" ]]; then
  mkdir -p "$(dirname "$SRC")"
  ln -sf "../build/${AOI}_dtm1m.tif" "$SRC"
  echo "[smoke-dem] linked $SRC -> ../build/${AOI}_dtm1m.tif"
fi
# --- end guard ---
