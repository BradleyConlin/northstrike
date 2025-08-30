#!/usr/bin/env python3
import argparse, json, hashlib, numpy as np, onnxruntime as ort, os, sys, time
def _stats(a):
    return dict(mean=float(a.mean()), std=float(a.std()), min=float(a.min()), max=float(a.max()))
def _sha(b: bytes) -> str:
    h=hashlib.sha256(); h.update(b); return h.hexdigest()
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out-json")
    ap.add_argument("--check-against")
    ap.add_argument("--tol-mean", type=float, default=1e-4)
    ap.add_argument("--tol-std",  type=float, default=1e-4)
    ap.add_argument("--shape", default="1x3x384x640")
    args=ap.parse_args()

    n,c,h,w = [int(x) for x in args.shape.lower().split("x")]
    x = np.linspace(0.0, 1.0, num=n*c*h*w, dtype=np.float32).reshape(n,c,h,w)

    sess = ort.InferenceSession(args.model, providers=["CPUExecutionProvider"])
    in_name  = sess.get_inputs()[0].name
    out_name = sess.get_outputs()[0].name
    t0=time.perf_counter(); y = sess.run(None, {in_name: x})[0]; dt = (time.perf_counter()-t0)*1e3

    out = dict(
        model=args.model, input_shape=[n,c,h,w], output_shape=list(y.shape),
        stats=_stats(y), sha256=_sha(y.tobytes()), p50_ms=dt
    )

    if args.check-against:
        base=json.load(open(args.check-against))
        dm=abs(out["stats"]["mean"]-base["stats"]["mean"])
        ds=abs(out["stats"]["std"] -base["stats"]["std"])
        if dm>args.tol-mean or ds>args.tol-std:  # noqa
            print(f"[FAIL] drift mean={dm:.3e} std={ds:.3e} (tols {args.tol_mean:.1e}/{args.tol_std:.1e})")
            print(json.dumps({"current":out,"baseline":base}, indent=2))
            sys.exit(2)
        print(f"[ok] drift within tol mean={dm:.3e} std={ds:.3e}  p50={out['p50_ms']:.3f}ms")
        return

    if not args.out_json:
        print(json.dumps(out, indent=2)); return
    os.makedirs(os.path.dirname(args.out_json), exist_ok=True)
    json.dump(out, open(args.out_json,"w"), indent=2)
    print(f"[depth-regress] wrote {args.out_json} p50={out['p50_ms']:.3f}ms")
if __name__=="__main__": main()
