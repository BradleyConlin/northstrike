#!/usr/bin/env python3
import argparse
import csv
import os

import numpy as np
import onnxruntime as ort


def _get_io(model_path: str) -> tuple[tuple[str, tuple[int, ...]], tuple[str, tuple[int, ...]]]:
    """Return ((in_name, in_shape), (out_name, out_shape)) from ONNX metadata."""
    sess = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
    iv = sess.get_inputs()[0]
    ov = sess.get_outputs()[0]

    def _shape(s):
        out = []
        for d in s:
            if isinstance(d, int):
                out.append(d)
            elif d in (None, "None"):
                out.append(-1)
            else:
                # symbolic -> treat as dynamic
                out.append(-1)
        return tuple(out)

    return (iv.name, tuple(iv.shape)), (ov.name, _shape(ov.shape))


def _make_input(shape_1x3xHxW: tuple[int, ...], mode: str, npy: str | None) -> np.ndarray:
    """Create or load input tensor shaped (1,3,H,W) float32, normalized 0..1."""
    b, c, h, w = shape_1x3xHxW
    c = 3 if c in (-1, None) else c
    h = 384 if h in (-1, None) else h
    w = 640 if w in (-1, None) else w
    if mode == "rand":
        x = np.random.RandomState(123).randn(1, c, h, w).astype(np.float32)
        # normalize to 0..1
        x = (x - x.min()) / max(1e-6, (x.max() - x.min()))
        return x.astype(np.float32)
    assert npy, "--npy is required for mode=npy"
    arr = np.load(npy)
    # Accept CHW or HWC or BCHW; coerce to (1,3,H,W)
    if arr.ndim == 2:
        arr = np.stack([arr] * 3, axis=0)  # H,W -> 3,H,W
    if arr.ndim == 3:
        if arr.shape[0] in (1, 3):  # CHW
            chw = arr
        else:  # HWC
            chw = np.transpose(arr, (2, 0, 1))
        arr = chw[None, ...]
    if arr.ndim != 4:
        raise ValueError(f"expected 2D/3D/4D image, got shape {arr.shape}")
    # Resize/pad/crop to (1,3,h,w) if necessary (simple center crop/pad)
    b0, c0, h0, w0 = arr.shape
    if c0 != 3:
        if c0 == 1:
            arr = np.repeat(arr, 3, axis=1)
        else:
            arr = arr[:, :3, :, :]
    out = np.zeros((1, 3, h, w), dtype=np.float32)
    hs = min(h, h0)
    ws = min(w, w0)
    y0 = (h - hs) // 2
    x0 = (w - ws) // 2
    y1 = (h0 - hs) // 2
    x1 = (w0 - ws) // 2
    out[:, :, y0 : y0 + hs, x0 : x0 + ws] = arr[:, :, y1 : y1 + hs, x1 : x1 + ws]
    # normalize 0..1 if not already
    if out.max() > 1.0:
        out = out / 255.0
    return out.astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="ONNX depth model (expects 1x3xHxW input)")
    ap.add_argument(
        "--mode", choices=["rand", "npy"], default="rand", help="random input or load .npy"
    )
    ap.add_argument("--npy", default=None, help="path to .npy if --mode npy")
    ap.add_argument("--out-npz", required=True, help="npz to save raw output and stats")
    ap.add_argument("--out-csv", required=True, help="csv to save summary stats")
    args = ap.parse_args()

    (in_name, in_shape), (out_name, out_shape) = _get_io(args.model)
    # coerce input shape to (1,3,H,W) for generation
    in_shape_sane = (
        1 if in_shape[0] in (-1, None) else in_shape[0],
        3 if in_shape[1] in (-1, None) else in_shape[1],
        384 if in_shape[2] in (-1, None) else in_shape[2],
        640 if in_shape[3] in (-1, None) else in_shape[3],
    )
    X = _make_input(in_shape_sane, args.mode, args.npy)

    sess = ort.InferenceSession(args.model, providers=["CPUExecutionProvider"])
    Y = sess.run(None, {in_name: X})[0]
    Y = np.asarray(Y)

    # write artifacts
    os.makedirs(os.path.dirname(args.out_npz) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(args.out_csv) or ".", exist_ok=True)

    stats = {
        "in_shape": list(X.shape),
        "out_shape": list(Y.shape),
        "min": float(np.min(Y)),
        "max": float(np.max(Y)),
        "mean": float(np.mean(Y)),
        "std": float(np.std(Y)),
    }
    np.savez(args.out_npz, output=Y, **stats)
    with open(args.out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["key", "value"])
        for k, v in stats.items():
            w.writerow([k, v])

    print(
        f"[depth-offline] wrote {args.out_npz} & {args.out_csv}  "
        f"in={stats['in_shape']} out={stats['out_shape']}  "
        f"mean={stats['mean']:.6f} std={stats['std']:.6f}"
    )


if __name__ == "__main__":
    main()
