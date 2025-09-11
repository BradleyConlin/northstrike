import pathlib, sys
try:
    import yaml
except Exception as e:
    print("FATAL: PyYAML is required (pip install pyyaml).", file=sys.stderr)
    raise

def patch_steps(steps):
    changed = False
    for s in steps or []:
        if isinstance(s, dict) and "steps" in s:  # recurse into composite steps
            if patch_steps(s["steps"]):
                changed = True
        if not isinstance(s, dict):
            continue
        uses = s.get("uses", "")
        if isinstance(uses, str) and uses.startswith("actions/checkout@"):
            w = s.setdefault("with", {})
            if w.get("lfs") is not True:
                w["lfs"] = True
                changed = True
            if w.get("fetch-depth") != 0:
                w["fetch-depth"] = 0
                changed = True
    return changed

def patch_workflow(path: pathlib.Path):
    data = yaml.safe_load(path.read_text())
    changed = False
    jobs = (data or {}).get("jobs", {})
    for _, job in (jobs or {}).items():
        if isinstance(job, dict) and isinstance(job.get("steps"), list):
            if patch_steps(job["steps"]):
                changed = True
    if changed:
        path.write_text(yaml.safe_dump(data, sort_keys=False))
        print(f"[patched] {path}")
    else:
        print(f"[skip]    {path}")

root = pathlib.Path(".github/workflows")
files = sorted(list(root.glob("*.yml")) + list(root.glob("*.yaml")))
if not files:
    print("[info] no workflow files found under .github/workflows")
    sys.exit(0)

for f in files:
    patch_workflow(f)
