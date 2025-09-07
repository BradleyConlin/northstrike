#!/usr/bin/env python3
import argparse
import json
import os
import pathlib
import time

import numpy as np
import onnxruntime as ort


def parse_shape(txt):
    # "1x3x384x640" → [1,3,384,640]
    return [int(x) for x in txt.lower().replace(" ", "").split("x")]


def p50_p90(vals):
    a = np.array(vals, dtype=np.float64)
    return float(np.percentile(a, 50)), float(np.percentile(a, 90))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--provider", default="cpu", choices=["cpu", "cuda", "tensorrt"])
    ap.add_argument("--shape", default=None, help="Override input shape like 1x3x384x640")
    ap.add_argument("--iters", type=int, default=50)
    ap.add_argument("--warmup", type=int, default=10)
    ap.add_argument("--outdir", default="artifacts/perf")
    args = ap.parse_args()

    providers = {
        "cpu": "CPUExecutionProvider",
        "cuda": "CUDAExecutionProvider",
        "tensorrt": "TensorrtExecutionProvider",
    }
    so = ort.SessionOptions()
    so.enable_profiling = True
    sess = ort.InferenceSession(args.model, sess_options=so, providers=[providers[args.provider]])

    # Infer input shape (or override)
    i0 = sess.get_inputs()[0]
    if args.shape:
        shape = parse_shape(args.shape)
    else:
        shape = [d if isinstance(d, int) else 1 for d in i0.shape]  # fill dynamic dims with 1

    # Make deterministic random to ease comparisons
    rng = np.random.default_rng(1234)
    feed = {i0.name: rng.random(shape, dtype=np.float32)}

    # Warmup
    for _ in range(args.warmup):
        _ = sess.run(None, feed)

    # Timed runs
    times = []
    for _ in range(args.iters):
        t0 = time.perf_counter()
        _ = sess.run(None, feed)
        times.append((time.perf_counter() - t0) * 1000.0)  # ms

    p50, p90 = p50_p90(times)
    prof_file = sess.end_profiling()  # ORT writes a JSON trace file

    pathlib.Path(args.outdir).mkdir(parents=True, exist_ok=True)
    out = {
        "model": args.model,
        "provider": args.provider,
        "shape": shape,
        "iters": args.iters,
        "warmup": args.warmup,
        "p50_ms": round(p50, 3),
        "p90_ms": round(p90, 3),
        "profile_trace": prof_file,
    }
    ofn = os.path.join(args.outdir, f"ort_{pathlib.Path(args.model).stem}_{args.provider}.json")
    with open(ofn, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {ofn}")


if __name__ == "__main__":
    main()
