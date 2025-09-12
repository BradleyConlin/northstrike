#!/usr/bin/env python3
import glob
import json
import os
import sqlite3

MB_DIR = os.path.join("artifacts", "maps", "mbtiles")
OUT_JS = os.path.join("viewer", "mbtiles_bounds.js")


def read_bounds(fp):
    try:
        with sqlite3.connect(fp) as db:
            row = db.execute("SELECT value FROM metadata WHERE name='bounds'").fetchone()
            if row and row[0]:
                vals = [float(x) for x in row[0].split(",")]
                if len(vals) == 4:
                    return vals
    except Exception:
        pass
    return None


best = {}  # prefer 'color' bounds if both exist
for path in sorted(glob.glob(os.path.join(MB_DIR, "*_cost_*.mbtiles"))):
    base = os.path.basename(path)
    name = base[:-8]  # strip .mbtiles
    aoi, flavor = name.split("_cost_")  # e.g., toronto_downtown, color/gray
    b = read_bounds(path)
    if not b:
        continue
    if aoi not in best or flavor == "color":
        best[aoi] = b

os.makedirs(os.path.dirname(OUT_JS), exist_ok=True)
with open(OUT_JS, "w") as f:
    f.write("// generated from MBTiles metadata\n")
    f.write("window.NS_BOUNDS = ")
    json.dump(best, f, indent=2)
    f.write(";\n")

print(f"Wrote {OUT_JS} with {len(best)} entries")
