#!/usr/bin/env python3
import argparse, json, os, hashlib, sys
def sha(p): 
    with open(p,"rb") as f: return hashlib.sha256(f.read()).hexdigest()
def flatten(man):
    out=[]
    if isinstance(man,list):
        for e in man:
            name=e.get("name")
            path=e.get("path") or e.get("dst") or e.get("src")
            h=e.get("sha256") or e.get("sha")
            out.append((name,path,h))
    elif isinstance(man,dict):
        # dotted-keys dict (preferred by tests): {"a.b":{"path":...,"sha256":...}}
        leaf_like=True
        for k,v in man.items():
            if isinstance(v,dict) and not {"path","dst","src"} & set(v.keys()):
                leaf_like=False; break
        if leaf_like:
            for name,v in man.items():
                path=v.get("path") or v.get("dst") or v.get("src")
                h=v.get("sha256") or v.get("sha")
                out.append((name,path,h))
        else:
            # nested dict -> recurse to dotted names
            def walk(prefix,d):
                if any(x in d for x in("path","dst","src")):
                    path=d.get("path") or d.get("dst") or d.get("src")
                    h=d.get("sha256") or d.get("sha"); out.append((prefix,path,h)); return
                for kk,vv in d.items():
                    if isinstance(vv,dict):
                        walk(kk if not prefix else f"{prefix}.{kk}", vv)
            walk("",man)
    else:
        raise SystemExit("[ERR] unsupported manifest format")
    return out
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",required=True)
    ap.add_argument("--check",action="store_true")
    args=ap.parse_args()
    man=json.load(open(args.manifest))
    entries=flatten(man)
    ok=True
    for name,path,expected in entries:
        if not path:
            print(f"[verify] {name}: MISSING 'path'"); ok=False; continue
        if not os.path.exists(path):
            print(f"[verify] {name}: MISSING file {path}"); ok=False; continue
        got=sha(path)
        if expected and got.lower()==expected.lower():
            print(f"[verify] {name}: OK {got[:8]}…")
        else:
            print(f"[verify] {name}: MISMATCH expected {str(expected)[:8]}… got {got[:8]}…")
            ok=False
    if args.check and not ok: sys.exit(1)
if __name__=="__main__": main()
