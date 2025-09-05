#!/usr/bin/env python3
import argparse, io, json, math, os, sqlite3, subprocess, random, csv
from PIL import Image

def xyz_from_lonlat(lon, lat, z):
    lat_rad = math.radians(lat)
    n = 2.0 ** z
    xtile = (lon + 180.0) / 360.0 * n
    ytile = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    return xtile, ytile

def lonlat_from_xyz_pixel(x, y_xyz, z, px, py, tilesize=256):
    # Convert XYZ indices + pixel coords (0..255) to lon/lat at pixel center in WebMercator
    # px,py can be float; we sample at the center of the pixel footprint
    n = 2.0 ** z
    # normalize to [0,1]
    u = (x + (px + 0.5) / tilesize) / n
    v = (y_xyz + (py + 0.5) / tilesize) / n
    lon = u * 360.0 - 180.0
    # inverse mercator
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * v)))
    lat = math.degrees(lat_rad)
    return lon, lat

def read_mbtiles_bounds(cur):
    cur.execute("SELECT value FROM metadata WHERE name='bounds'")
    row = cur.fetchone()
    if not row: raise RuntimeError("bounds not found in metadata")
    b = [float(x) for x in row[0].split(',')]
    return b[0], b[1], b[2], b[3]  # minlon,minlat,maxlon,maxlat

def read_png_pixel_from_mbtiles(cur, z, x_xyz, y_xyz, px, py):
    # MBTiles stores TMS row index
    y_tms = (2**z - 1) - y_xyz
    cur.execute(
        "SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?",
        (z, x_xyz, y_tms),
    )
    row = cur.fetchone()
    if not row: return None
    img = Image.open(io.BytesIO(row[0])).convert("L")
    w, h = img.size
    px = max(0, min(w - 1, int(px)))
    py = max(0, min(h - 1, int(py)))
    return img.getpixel((px, py))

def sample_cost(cost_path, lon, lat):
    cmd = ["gdallocationinfo", "-valonly", "-wgs84", cost_path, str(lon), str(lat)]
    out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode("utf-8").strip()
    try:
        return float(out)
    except ValueError:
        return float("nan")

def scale_cost_to_byte(v, vmin=0.0, vmax=1500.0):
    if math.isnan(v): return math.nan
    if v <= vmin: return 1     # matches VRT mapping 0->1
    if v >= vmax: return 255
    return int(round(1 + (v - vmin) * (254.0 / (vmax - vmin))))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mbtiles", required=True)
    ap.add_argument("--cost", required=True)
    ap.add_argument("--zoom", type=int, default=14)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    conn = sqlite3.connect(args.mbtiles)
    cur = conn.cursor()
    minlon, minlat, maxlon, maxlat = read_mbtiles_bounds(cur)

    rows = []
    mismatches = 0
    for i in range(args.n):
        # choose a random xyz tile fully inside bounds
        # compute tile index range from bounds
        xmin_f, ymin_f = xyz_from_lonlat(minlon, minlat, args.zoom)
        xmax_f, ymax_f = xyz_from_lonlat(maxlon, maxlat, args.zoom)
        x_lo = int(math.floor(min(xmin_f, xmax_f)))
        x_hi = int(math.floor(max(xmin_f, xmax_f)))
        y_lo = int(math.floor(min(ymin_f, ymax_f)))
        y_hi = int(math.floor(max(ymin_f, ymax_f)))

        x_idx = random.randint(x_lo, x_hi)
        y_idx = random.randint(y_lo, y_hi)


        # pad away from edges by 1 tile when possible
        if x_hi - x_lo >= 2:
            x_lo += 1
            x_hi -= 1
        if y_hi - y_lo >= 2:
            y_lo += 1
            y_hi -= 1


        # random pixel within the tile
        px = random.uniform(0, 255)
        py = random.uniform(0, 255)

        # compute lon/lat of the pixel center
        lon, lat = lonlat_from_xyz_pixel(x_idx, y_idx, args.zoom, px, py)

        pix = read_png_pixel_from_mbtiles(cur, args.zoom, x_idx, y_idx, px, py)
        if pix is None:
            rows.append((i, lon, lat, "tile_missing", "tile_missing", "FAIL"))
            mismatches += 1
            continue

        v = sample_cost(args.cost, lon, lat)
        s = scale_cost_to_byte(v)

        tol = 5

        # Accept outside-AOI pixels: PNG=0 (nodata) while Float32 returns NaN
        if math.isnan(s) and int(pix) == 0:
            ok = True

        # Accept our 0→1 mapping quirk
        elif not math.isnan(s) and int(pix) == 0 and int(s) == 1:
            ok = True

        else:
            ok = (not math.isnan(s)) and (abs(int(pix) - int(s)) <= tol)



        rows.append((i, lon, lat, pix, s, "OK" if ok else "FAIL"))
        if not ok: mismatches += 1

    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["i","lon","lat","tile_gray","scaled_cost","status"])
        w.writerows(rows)

    summary = {
        "samples": args.n,
        "zoom": args.zoom,
        "bounds": [minlon, minlat, maxlon, maxlat],
        "mismatches": mismatches,
        "pass": mismatches == 0,
        "csv": args.out,
    }
    summ_path = os.path.splitext(args.out)[0] + "_summary.json"
    with open(summ_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Wrote {args.out}")
    print(f"Summary: {summ_path}")

if __name__ == "__main__":
    main()
