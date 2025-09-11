#!/usr/bin/env python3
from __future__ import annotations
import csv, json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] if "scripts/dev" in __file__ else Path.cwd()
FAIL: list[str] = []

def _run(cmd: list[str], **kw):
    return subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw)

def ok(msg: str):   print(f"✓ {msg}")
def warn(msg: str): print(f"! {msg}")
def bad(msg: str):  print(f"✖ {msg}"); FAIL.append(msg)

# ---------- checks ----------
def ensure_metrics_min_rows():
    helper = ROOT / "scripts/training/ensure_metrics_min_rows.py"
    if helper.exists():
        _run([sys.executable, str(helper)])
    p = ROOT / "artifacts/training/metrics.csv"
    try:
        rows = list(csv.DictReader(p.open()))
        if rows and {"epoch","loss","acc"} <= set(rows[0]) and len(rows) >= 5:
            ok(f"metrics.csv OK (rows={len(rows)})")
        else:
            bad("metrics.csv missing or too short")
    except FileNotFoundError:
        bad("metrics.csv missing")

def check_randomization_seeded():
    out = ROOT / "artifacts/randomization/last_profile.json"
    if not out.exists():
        _run([sys.executable, "simulation/domain_randomization/scripts/apply_randomization.py", "--seed", "123"])
    try:
        d = json.loads(out.read_text())
        seed = d.get("seed")
        ok("DR seeded output OK" + (f" (seed={seed})" if seed is not None else ""))
    except Exception as e:
        bad(f"DR profile not readable: {e}")

REQ_EKF_HDR = ['t','x','y','z','vx','vy','vz','px','py','ekf_px','ekf_py','wp_index','lat','lon','rel_alt_m']

def check_ekf_contract():
    p = ROOT / "artifacts/waypoint_run.csv"
    def _hdr(path: Path):
        try:
            with path.open() as f:
                return csv.DictReader(f).fieldnames or []
        except FileNotFoundError:
            return []
    hdr = _hdr(p)
    need = not hdr or any(c not in hdr for c in REQ_EKF_HDR)
    if need:
        helper = ROOT / "scripts/estimators/ensure_ekf_waypoint_csv.py"
        if helper.exists():
            _run([sys.executable, str(helper)])
            hdr = _hdr(p)
        else:
            warn("EKF ensure script missing; cannot auto-fix")
    if hdr and all(c in hdr for c in REQ_EKF_HDR):
        ok("EKF CSV schema OK")
    else:
        if hdr:
            warn(f"EKF CSV missing columns; have {hdr}")
        bad("EKF CSV schema incomplete")

def check_fw_metrics():
    p = ROOT / "artifacts/fixedwing/fw_metrics.json"
    try:
        d = json.loads(p.read_text())
        need = {"rmse_xtrack_m","alt_final_err_m","max_bank_deg"}
        if need <= set(d):
            ok("fixed-wing metrics OK")
        else:
            warn("fixed-wing metrics present but missing keys")
    except FileNotFoundError:
        warn("fixed-wing metrics missing")
    except Exception as e:
        bad(f"fixed-wing metrics unreadable: {e}")

def check_manifests():
    for rel in ("datasets/manifest.json","deploy/models/manifest.json"):
        p = ROOT / rel
        try:
            json.loads(p.read_text())
            ok(f"parsed {rel}")
        except Exception as e:
            bad(f"{rel} unreadable: {e}")

def check_lfs_and_large_files():
    # tracked files only
    tracked = set(_run(["git","ls-files"]).stdout.splitlines())
    # LFS set
    lfs = set()
    for line in _run(["git","lfs","ls-files","--all"]).stdout.splitlines():
        if line.strip():
            lfs.add(line.split()[-1])

    # Non-LFS ONNX (warn-only)
    nonlfs_onnx = [p for p in tracked if p.endswith(".onnx") and p not in lfs]
    if nonlfs_onnx:
        warn("ONNX not on LFS (consider adding to .gitattributes):")
        for p in nonlfs_onnx:
            print(f"  - {p}")

    # Large tracked files outside LFS (error)
    offenders = []
    for p in tracked:
        if p in lfs:
            continue
        try:
            sz = (ROOT / p).stat().st_size
            if sz > 50 * 1024 * 1024:
                offenders.append((p, sz))
        except FileNotFoundError:
            pass
    if offenders:
        for p, sz in offenders:
            warn(f"Large files >50MB present (ensure ignored or on LFS):\n  - {p} ({sz/1024/1024:.1f} MB)")
        bad("Large tracked files found (consider LFS or .gitignore)")
    else:
        ok("No large tracked files outside LFS")

# ---------- main ----------
def main():
    print("== Repo Doctor ==")
    ensure_metrics_min_rows()
    check_randomization_seeded()
    check_ekf_contract()
    check_fw_metrics()
    check_manifests()
    check_lfs_and_large_files()
    if FAIL:
        print("\nIssues found:")
        for m in FAIL:
            print(" -", m)
        sys.exit(1)
    print("\nAll checks OK.")

if __name__ == "__main__":
    main()
