#!/usr/bin/env python3
import argparse, os, sys, glob, csv, hashlib, time
from pathlib import Path
import numpy as np
import cv2
import onnxruntime as ort

def read_depth(path, scale):
    ext = Path(path).suffix.lower()
    if ext == ".npy":
        d = np.load(path).astype(np.float32)
    else:
        raw = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if raw is None:
            raise RuntimeError(f"Failed to read depth: {path}")
        if raw.dtype == np.uint16:
            d = raw.astype(np.float32) * scale  # e.g., mm→m with scale 0.001
        else:
            d = raw.astype(np.float32) * scale
    return d

def read_mask(mask_path):
    ext = Path(mask_path).suffix.lower()
    if ext == ".npy":
        m = np.load(mask_path)
        return (m > 0).astype(bool)
    img = cv2.imread(mask_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        return None
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return (img > 0)

def colorize_depth(d, max_depth):
    d = np.clip(d, 0, max_depth) / max_depth
    d8 = (d * 255.0).astype(np.uint8)
    return cv2.applyColorMap(d8, cv2.COLORMAP_INFERNO)

def main():
    ap = argparse.ArgumentParser(description="ONNX depth smoke test")
    ap.add_argument("--model", required=True, help="path to .onnx model")
    ap.add_argument("--rgb", required=True, help="dir with RGB images")
    ap.add_argument("--gt", required=True, help="dir with GT depth (png/npy)")
    ap.add_argument("--out", required=True, help="output dir")
    ap.add_argument("--width", type=int, default=320)
    ap.add_argument("--height", type=int, default=240)
    ap.add_argument("--max-images", type=int, default=30)
    ap.add_argument("--max-depth-m", type=float, default=20.0)
    ap.add_argument("--gt-scale", type=float, default=0.001, help="0.001 if gt png is mm")
    ap.add_argument("--pred-scale", type=float, default=1.0, help="multiply raw pred to meters")
    ap.add_argument("--mask-dir", default="", help="optional dir with masks (png/npy)")
    ap.add_argument("--rgb-exts", default=".png,.jpg,.jpeg,.PNG,.JPG,.JPEG", help="comma list")
    args = ap.parse_args()

    # Early model existence check
    if not Path(args.model).exists():
        print(f"ERROR: model not found → {args.model}", file=sys.stderr)
        sys.exit(2)

    out_dir = Path(args.out)
    (out_dir / "pred").mkdir(parents=True, exist_ok=True)
    (out_dir / "overlay").mkdir(parents=True, exist_ok=True)

    # Stable model hash for traceability
    mh = hashlib.sha256(Path(args.model).read_bytes()).hexdigest()[:16]

    providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    sess = ort.InferenceSession(args.model, providers=providers)
    inp = sess.get_inputs()[0].name
    out = sess.get_outputs()[0].name

    rgb_paths = []
    for ext in args.rgb_exts.split(","):
        rgb_paths += glob.glob(str(Path(args.rgb) / f"*{ext.strip()}"))
    rgb_paths = sorted(rgb_paths)[: args.max_images]
    if not rgb_paths:
        print("No RGB files found.", file=sys.stderr)
        sys.exit(2)

    gt_candidates = [".png", ".npy", ".tiff", ".tif"]
    rows, used = [], 0
    t0 = time.time()

    for p in rgb_paths:
        stem = Path(p).stem
        # match GT by basename
        gt_path = None
        for ext in gt_candidates:
            c = Path(args.gt) / f"{stem}{ext}"
            if c.exists():
                gt_path = str(c)
                break
        if gt_path is None:
            print(f"[warn] GT missing for {stem}, skipping")
            continue

        img_bgr = cv2.imread(p, cv2.IMREAD_COLOR)
        if img_bgr is None:
            print(f"[warn] bad image {p}")
            continue
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        ih, iw = args.height, args.width
        img_rs = cv2.resize(img_rgb, (iw, ih), interpolation=cv2.INTER_AREA)
        x = (img_rs.astype(np.float32) / 255.0).transpose(2,0,1)[None, ...]  # 1x3xH×W

        pred = sess.run([out], {inp: x})[0]
        pred = np.squeeze(pred).astype(np.float32)
        if pred.ndim == 3:
            pred = pred[0]
        pred = np.clip(pred * args.pred_scale, 0, args.max_depth_m)

        gt = read_depth(gt_path, args.gt_scale)
        if gt.shape != pred.shape:
            gt = cv2.resize(gt, (pred.shape[1], pred.shape[0]), interpolation=cv2.INTER_NEAREST)

        # Valid GT mask
        mask = (gt > 0) & np.isfinite(gt)

        # Optional external mask gating
        if args.mask_dir:
            mpath = None
            for ext in gt_candidates + [".jpg", ".jpeg", ".JPG", ".JPEG", ".PNG"]:
                c = Path(args.mask_dir) / f"{stem}{ext}"
                if c.exists():
                    mpath = str(c)
                    break
            if mpath:
                mext = Path(mpath).suffix.lower()
                m = read_mask(mpath)
                if m is not None:
                    if m.shape != pred.shape:
                        m = cv2.resize(m.astype(np.uint8), (pred.shape[1], pred.shape[0]), interpolation=cv2.INTER_NEAREST).astype(bool)
                    mask = mask & m
            else:
                print(f"[warn] mask missing for {stem}, continuing without external mask")

        if mask.sum() == 0:
            print(f"[warn] empty valid mask for {stem}, skipping metrics")
            continue

        diff = np.abs(pred - gt)[mask]
        mae = float(np.mean(diff))
        rmse = float(np.sqrt(np.mean((pred[mask]-gt[mask])**2)))

        # save artifacts
        np.save(out_dir / "pred" / f"{stem}.npy", pred.astype(np.float32))

        ov = colorize_depth(pred, args.max_depth_m)
        blend = cv2.addWeighted(cv2.cvtColor(img_rs, cv2.COLOR_RGB2BGR), 0.5, ov, 0.5, 0)
        cv2.imwrite(str(out_dir / "overlay" / f"{stem}.png"), blend)

        rows.append([stem, mae, rmse, int(mask.sum())])
        used += 1

    # Write metrics
    csv_path = out_dir / "metrics.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["stem", "mae_m", "rmse_m", "valid_px"])
        w.writerows(rows)

    m_mae = float(np.mean([r[1] for r in rows])) if rows else float("nan")
    m_rmse = float(np.mean([r[2] for r in rows])) if rows else float("nan")

    # Summary
    (out_dir / "SUMMARY.txt").write_text(
        f"model: {args.model}\n"
        f"model_sha256_16: {mh}\n"
        f"images: {used}\n"
        f"mean_mae_m: {m_mae:.4f}\n"
        f"mean_rmse_m: {m_rmse:.4f}\n"
        f"max_depth_m: {args.max_depth_m}\n"
        f"gt_scale: {args.gt_scale}\n"
        f"pred_scale: {args.pred_scale}\n"
        f"mask_dir: {args.mask_dir}\n"
        f"elapsed_s: {time.time()-t0:.1f}\n"
    )
    print(f"Done. rows={used}  MAE={m_mae:.4f} m  RMSE={m_rmse:.4f} m  → {out_dir}")

if __name__ == "__main__":
    main()
