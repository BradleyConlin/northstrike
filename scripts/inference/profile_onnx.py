#!/usr/bin/env python3
import argparse
import json
import os
import pathlib
import statistics
import time

import numpy as np
import onnxruntime as ort
import yaml


def _parse_shape(s):
    return [int(x) for x in s.lower().replace("x", " ").split() if x.strip()]


def profile_one(name, path, shape, iters=200, warmup=30, provider="CPUExecutionProvider"):
    assert os.path.isfile(path), f"missing model: {path}"
    sess = ort.InferenceSession(path, providers=[provider])
    in0 = sess.get_inputs()[0]
    shp = _parse_shape(shape)
    assert all(isinstance(d, int) for d in shp), "shape must be concrete ints, e.g. 1x3x384x640"
    x = np.random.rand(*shp).astype(np.float32)  # default float32
    if in0.type == "tensor(int64)":
        x = x.astype(np.int64)
    feed = {in0.name: x}

    # warmup
    for _ in range(warmup):
        sess.run(None, feed)

    times = []
    t0 = time.perf_counter()
    for _ in range(iters):
        s = time.perf_counter()
        sess.run(None, feed)
        times.append((time.perf_counter() - s) * 1000.0)  # ms
    t1 = time.perf_counter()
    fps = iters / (t1 - t0)

    stats = {
        "name": name,
        "path": path,
        "provider": provider,
        "iters": iters,
        "warmup": warmup,
        "p50_ms": float(statistics.median(times)),
        "p90_ms": float(np.percentile(times, 90)),
        "p99_ms": float(np.percentile(times, 99)),
        "mean_ms": float(statistics.fmean(times)),
        "fps": float(fps),
    }
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=str, required=True, help="budgets.yaml")
    ap.add_argument("--outdir", type=str, default="artifacts/perf")
    ap.add_argument("--iters", type=int, default=200)
    ap.add_argument("--warmup", type=int, default=30)
    ap.add_argument("--provider", type=str, default="CPUExecutionProvider")
    ap.add_argument("--check", action="store_true", help="enforce budgets; nonzero exit on fail")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    cfg = yaml.safe_load(open(args.config, "r"))
    targets = cfg.get("targets", {})
    failed = []

    for name, t in targets.items():
        if "path" not in t or "shape" not in t:
            # skip non-model entries like 'full_loop'
            continue
        p = profile_one(name, t["path"], t["shape"], args.iters, args.warmup, args.provider)
        out_json = os.path.join(args.outdir, f"{name.replace('.','_')}.json")
        pathlib.Path(out_json).parent.mkdir(parents=True, exist_ok=True)
        json.dump(p, open(out_json, "w"), indent=2)

        budget = float(t.get("budget_ms", 0.0))
        verdict = "OK"
        if args.check and budget > 0 and p["p50_ms"] > budget:
            verdict = f"FAIL (p50 {p['p50_ms']:.2f}ms > budget {budget:.2f}ms)"
            failed.append(name)
        print(
            f"[perf] {name:18s} p50={p['p50_ms']:.2f}ms p90={p['p90_ms']:.2f}ms fps={p['fps']:.1f}  {verdict}"
        )

    if args.check and failed:
        print(f"[perf] Failed budgets: {', '.join(failed)}")
        raise SystemExit(2)


if __name__ == "__main__":
    main()
