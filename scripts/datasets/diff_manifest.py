#!/usr/bin/env python3
import argparse, json, sys
def load(p): return json.load(open(p))
def idx(m): return {f["relpath"]: f.get("sha256") for f in m.get("files", [])}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--fail-on-change", action="store_true")
    a, b = idx(load(ap.parse_args().old)), idx(load(ap.parse_args().new))
    added    = sorted(set(b) - set(a))
    removed  = sorted(set(a) - set(b))
    modified = sorted(x for x in set(a)&set(b) if a[x] != b[x])
    for x in added:    print(f"[diff] ADDED    {x}")
    for x in removed:  print(f"[diff] REMOVED  {x}")
    for x in modified: print(f"[diff] MOD      {x}")
    if not (added or removed or modified): print("[diff] no changes")
    if (added or removed or modified) and ap.parse_args().fail_on_change: sys.exit(3)
if __name__ == "__main__": main()
