#!/usr/bin/env python3
import argparse, json, numpy as np, onnxruntime as ort, pathlib, sys, time

def run_once(model_path: str):
    sess = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
    inp = sess.get_inputs()[0]; out = sess.get_outputs()[0]
    # deterministic 1x64 ramp input
    x = np.arange(64, dtype=np.float32)[None, :]
    y = sess.run([out.name], {inp.name: x})[0].astype(np.float32).reshape(-1)
    return {"in_shape":[1,64], "out_shape":list(y.shape), "mean":float(y.mean()), "std":float(y.std())}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--check-against", default=None)
    ap.add_argument("--tol-mean", type=float, default=1e-4)
    ap.add_argument("--tol-std",  type=float, default=1e-4)
    args = ap.parse_args()

    t0=time.time(); res = run_once(args.model); dt=(time.time()-t0)*1000.0
    outp = {"model":args.model, "latency_ms":dt, **res}

    pathlib.Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    if args.check_against:
        base = json.load(open(args.check_against,"r"))
        dmean = abs(outp["mean"] - base["mean"])
        dstd  = abs(outp["std"]  - base["std"])
        ok = (dmean <= args.tol_mean) and (dstd <= args.tol_std)
        print(f"[policy-regress] mean={outp['mean']:.6f} (Δ={dmean:.6g}) "
              f"std={outp['std']:.6f} (Δ={dstd:.6g}) { 'OK' if ok else 'FAIL'}")
        json.dump(outp, open(args.out_json,"w"), indent=2)
        sys.exit(0 if ok else 2)
    else:
        json.dump(outp, open(args.out_json,"w"), indent=2)
        print(f"[policy-regress] wrote {args.out_json} "
              f"mean={outp['mean']:.6f} std={outp['std']:.6f} ({outp['latency_ms']:.3f}ms)")

if __name__ == "__main__":
    main()
