#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from typing import Any, Dict, Iterable, List, Tuple

import onnx
import yaml


def _dims(vi) -> list[int]:
    t = vi.type.tensor_type
    out = []
    for d in t.shape.dim:
        out.append(d.dim_value if d.HasField("dim_value") else -1)
    return out


def _fmt_shape(xs: List[int]) -> str:
    def one(x):
        return "*" if x in (-1, None) else str(int(x))

    return "x".join(one(x) for x in xs)


def _parse_shape(obj) -> List[int]:
    # Accept [1,3,384,640] OR "1x3x384x640" OR "1,3,384,640"
    if isinstance(obj, list):
        return [int(x) if str(x).isdigit() else -1 for x in obj]
    if isinstance(obj, str):
        toks = re.split(r"[x,]", obj.strip().lower())
        out = []
        for t in toks:
            t = t.strip()
            if t in {"*", "?", "n", "none", "-1"}:
                out.append(-1)
            else:
                out.append(int(t))
        return out
    raise TypeError(f"Unsupported shape type: {type(obj)}")


def _iter_tasks(node: Any, prefix: str = "") -> Iterable[Tuple[str, Dict[str, Any]]]:
    if isinstance(node, dict):
        if "path" in node and "shape" in node:
            yield prefix or "model", node
        for k, v in node.items():
            child = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                yield from _iter_tasks(v, child)


def _ok_shape(expected: list[int], got: list[int]) -> bool:
    if len(expected) != len(got):
        return False
    for e, g in zip(expected, got):
        if e != -1 and e != g:
            return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    conf = yaml.safe_load(open(args.config))
    failures = 0

    for name, task in _iter_tasks(conf):
        path = task["path"]
        exp_list = _parse_shape(task["shape"])
        if not os.path.isfile(path):
            print(f"[FAIL] {name}: missing file {path}")
            failures += 1
            continue

        m = onnx.load(path)
        ins = m.graph.input
        outs = m.graph.output
        first_in = _dims(ins[0])
        dtype = ins[0].type.tensor_type.elem_type
        out_names = [o.name for o in outs]

        ok = _ok_shape(exp_list, first_in)
        report = {
            "name": name,
            "path": path,
            "expected_input_shape": exp_list,
            "input_shape": first_in,
            "input_dtype": int(dtype),
            "outputs": out_names,
            "pass": ok,
        }
        out_json = os.path.join(args.outdir, f"{name.replace('.', '_')}_contract.json")
        json.dump(report, open(out_json, "w"), indent=2)

        if ok:
            print(f"[contract] {name:20s} shape={_fmt_shape(first_in)}  OK")
        else:
            print(
                f"[contract] {name:20s} shape={_fmt_shape(first_in)}  EXPECTED={_fmt_shape(exp_list)}  FAIL"
            )
            failures += 1

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
