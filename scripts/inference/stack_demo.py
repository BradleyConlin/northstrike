#!/usr/bin/env python3
import argparse
import json
import time

import numpy as np
import onnxruntime as ort

DEF_MAN = "deploy/models/manifest.json"


def load_manifest(p):
    m = json.load(open(p))
    return m if isinstance(m, dict) else {k["name"]: k for k in m}


def get_path(entry):
    return entry.get("dst") or entry.get("path")


def run_model(path, shape):
    sess = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
    x = np.random.rand(*shape).astype(np.float32)
    name = sess.get_inputs()[0].name
    t0 = time.time()
    y = sess.run(None, {name: x})[0]
    dt = (time.time() - t0) * 1000.0
    return y.shape, dt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=DEF_MAN)
    args = ap.parse_args()

    man = load_manifest(args.manifest)
    d = man["perception.depth"]
    p = man["control.policy"]
    depth_path, policy_path = get_path(d), get_path(p)

    depth_shape = d.get("shape", [1, 3, 384, 640])
    policy_shape = p.get("shape", [1, 64])

    ds, dt_ms = run_model(depth_path, depth_shape)
    ps, pt_ms = run_model(policy_path, policy_shape)

    print(f"[stack] depth  in={tuple(depth_shape)} out={tuple(ds)}  {dt_ms:.3f} ms")
    print(f"[stack] policy in={tuple(policy_shape)} out={tuple(ps)}  {pt_ms:.3f} ms")


if __name__ == "__main__":
    main()
