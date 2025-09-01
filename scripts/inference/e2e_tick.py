#!/usr/bin/env python3
import argparse
import json
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort


def _now_ms():
    return time.perf_counter() * 1000.0


def _mk_image(shape):
    # shape: [1,3,384,640]; simple deterministic ramp
    b, c, h, w = shape
    x = np.linspace(0, 1, num=h * w, dtype=np.float32).reshape(h, w)
    img = np.stack([x, 1.0 - x, 0.5 * np.ones_like(x)], axis=0)  # [3,H,W]
    return img[None, ...]  # [1,3,H,W]


def _depth_to_features(depth, n_feats=64):
    # depth: [1,1,H,W] -> 64 features by per-column-bin averages
    _, _, h, w = depth.shape
    d = depth.reshape(h, w).astype(np.float32)
    # split width into n bins; take mean per bin for stability
    edges = np.linspace(0, w, n_feats + 1, dtype=int)
    feats = []
    for i in range(n_feats):
        a, b = edges[i], edges[i + 1]
        if b <= a:
            feats.append(0.0)
        else:
            feats.append(float(d[:, a:b].mean()))
    return np.asarray(feats, dtype=np.float32)[None, :]  # [1,64]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--depth", default="artifacts/onnx/depth_e24.onnx")
    ap.add_argument("--policy", default="artifacts/onnx/policy_dummy.onnx")
    ap.add_argument("--iters", type=int, default=3)
    ap.add_argument("--out", default="artifacts/perf/e2e_tick.json")
    ap.add_argument("--provider", default="CPUExecutionProvider")
    args = ap.parse_args()

    Path(Path(args.out).parent).mkdir(parents=True, exist_ok=True)

    depth_sess = ort.InferenceSession(args.depth, providers=[args.provider])
    pol_sess = ort.InferenceSession(args.policy, providers=[args.provider])

    # infer IO names
    d_in = depth_sess.get_inputs()[0].name
    d_out = depth_sess.get_outputs()[0].name
    p_in = pol_sess.get_inputs()[0].name
    p_out = pol_sess.get_outputs()[0].name

    # expected shapes
    d_in_shape = [int(x) for x in depth_sess.get_inputs()[0].shape]
    p_in_shape = [int(x) for x in pol_sess.get_inputs()[0].shape]

    # warmup
    img = _mk_image(d_in_shape)
    depth_sess.run([d_out], {d_in: img})
    feats = _depth_to_features(np.zeros((1, 1, d_in_shape[2], d_in_shape[3]), dtype=np.float32))
    pol_sess.run([p_out], {p_in: feats})

    times = {"depth_ms": [], "policy_ms": []}
    last_u = None

    for _ in range(args.iters):
        t0 = _now_ms()
        D = depth_sess.run([d_out], {d_in: img})[0]  # [1,1,H,W]
        t1 = _now_ms()
        X = _depth_to_features(D, n_feats=p_in_shape[1])
        U = pol_sess.run([p_out], {p_in: X})[0]  # [1,4] typically
        t2 = _now_ms()
        times["depth_ms"].append(t1 - t0)
        times["policy_ms"].append(t2 - t1)
        last_u = U

    report = {
        "depth_input_shape": d_in_shape,
        "depth_output_shape": list(D.shape),
        "policy_input_shape": list(X.shape),
        "policy_output_shape": list(last_u.shape),
        "p50_depth_ms": float(np.median(times["depth_ms"])),
        "p50_policy_ms": float(np.median(times["policy_ms"])),
        "iters": args.iters,
    }
    Path(args.out).write_text(json.dumps(report, indent=2))
    print(
        f"[e2e] wrote {args.out}  p50: depth={report['p50_depth_ms']:.3f}ms policy={report['p50_policy_ms']:.3f}ms  OK"
    )


if __name__ == "__main__":
    main()
