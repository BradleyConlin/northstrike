#!/usr/bin/env python3
import argparse, json, pathlib, sys, hashlib
def sha256(p, buf=1024*1024):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for chunk in iter(lambda: f.read(buf), b""): h.update(chunk)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root", default="datasets")
    ap.add_argument("--manifest", default="datasets/manifest.json")
    args=ap.parse_args()
    m=json.load(open(args.manifest))
    root=pathlib.Path(args.root)
    bad=[]
    for rec in m.get("files",[]):
        if rec.get("sha256") is None: continue
        p=root/rec["relpath"]
        if not p.is_file():
            print(f"[verify] MISSING {rec['relpath']}")
            bad.append(rec["relpath"]); continue
        s=sha256(p)
        if s!=rec["sha256"]:
            print(f"[verify] SHA MISMATCH {rec['relpath']} {s} != {rec['sha256']}")
            bad.append(rec["relpath"])
    if bad:
        print(f"[verify] FAILED ({len(bad)} files)"); sys.exit(2)
    print("[verify] OK")
if __name__=="__main__": main()
