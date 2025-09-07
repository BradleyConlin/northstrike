#!/usr/bin/env python3
import os, sys, json, argparse

parser = argparse.ArgumentParser()
parser.add_argument("--root", default="datasets/public")
parser.add_argument("--expect", nargs="*", default=["xview","dota","visdrone","semantic-drone","ddos"])
parser.add_argument("--json-out", default="artifacts/perf/datasets_verify.json")
args = parser.parse_args()

missing = [d for d in args.expect if not os.path.isdir(os.path.join(args.root, d))]
status = {"root": args.root, "expected": args.expect, "missing": missing, "ok": not missing}
os.makedirs(os.path.dirname(args.json_out), exist_ok=True)
with open(args.json_out, "w") as f: json.dump(status, f, indent=2)

print("OK: public datasets scaffold present" if not missing else f"Missing: {', '.join(missing)}")
sys.exit(0 if not missing else 1)
