#!/usr/bin/env python3
import argparse
import json
import pathlib
import sys

try:
    import yaml  # PyYAML
except Exception:
    print("Install PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    prof = yaml.safe_load(open(args.profile))
    if not isinstance(prof, dict) or "profile" not in prof:
        print("Invalid profile YAML (missing 'profile').", file=sys.stderr)
        sys.exit(1)

    # Minimal normalization: ensure expected sections exist
    for k in ("lighting", "environment", "textures", "sensors"):
        prof.setdefault(k, {})

    outp = {
        "name": prof.get("profile", "unnamed"),
        "lighting": prof["lighting"],
        "environment": prof["environment"],
        "textures": prof["textures"],
        "sensors": prof["sensors"],
    }
    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(outp, open(args.out, "w"), indent=2)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
