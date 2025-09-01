#!/usr/bin/env python3
import argparse
import csv
import os

import numpy as np
import onnxruntime as ort


def _read_features(csv_path: str) -> tuple[np.ndarray, list[float]]:
    rows, ts = [], []
    with open(csv_path, newline="") as f:
        r = csv.DictReader(f)
        headers = r.fieldnames or []
        feat_cols = [h for h in headers if h != "t"]
        for row in r:
            ts.append(float(row.get("t", 0.0)))
            rows.append([float(row.get(c, 0.0)) for c in feat_cols])
    X = np.asarray(rows, dtype=np.float32)
    return X, ts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--in-csv", required=True)
    ap.add_argument("--out-csv", required=True)
    args = ap.parse_args()

    sess = ort.InferenceSession(args.model, providers=["CPUExecutionProvider"])
    in_vi = sess.get_inputs()[0]
    in_name = in_vi.name
    in_shape = list(in_vi.shape)

    X_raw, ts = _read_features(args.in_csv)
    if X_raw.ndim == 1:
        X_raw = X_raw[None, :]

    feat_dim = in_shape[1] if len(in_shape) > 1 else None
    try:
        F = int(feat_dim) if feat_dim not in (None, "None") else 64
    except Exception:
        F = 64

    if X_raw.shape[1] < F:
        pad = np.zeros((X_raw.shape[0], F - X_raw.shape[1]), dtype=np.float32)
        X = np.concatenate([X_raw.astype(np.float32), pad], axis=1)
    else:
        X = X_raw[:, :F].astype(np.float32)

    bd = in_shape[0] if len(in_shape) > 0 else None
    dynamic_batch = (bd in (None, "None", -1)) or isinstance(bd, str)

    outs = []
    if dynamic_batch:
        Y = sess.run(None, {in_name: X})
        Y0 = np.array(Y[0])
        if Y0.ndim == 1:
            Y0 = Y0[:, None]
        outs.append(Y0)
    else:
        for i in range(X.shape[0]):
            Y = sess.run(None, {in_name: X[i : i + 1, :]})
            Y0 = np.array(Y[0])
            if Y0.ndim == 1:
                Y0 = Y0[:, None]
            outs.append(Y0)

    Y0 = np.vstack(outs)
    act_dim = int(Y0.shape[-1])

    os.makedirs(os.path.dirname(args.out_csv) or ".", exist_ok=True)
    with open(args.out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t"] + [f"u{k}" for k in range(act_dim)])
        for i, t in enumerate(ts[: Y0.shape[0]]):
            w.writerow([f"{t:.2f}"] + [f"{float(v):.6f}" for v in Y0[i].tolist()])

    print(
        f"[policy-offline] wrote {args.out_csv}  rows={Y0.shape[0]} dims={act_dim} "
        f"(csv_cols={X_raw.shape[1]} -> model_feats={F})"
    )


if __name__ == "__main__":
    main()
