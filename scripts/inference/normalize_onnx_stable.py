#!/usr/bin/env python3
import argparse
import pathlib
import sys

import onnx
from onnx import checker, helper, numpy_helper

REDUCE_SET = {
    "ReduceMean",
    "ReduceSum",
    "ReduceProd",
    "ReduceMax",
    "ReduceMin",
    "ReduceL1",
    "ReduceL2",
    "ReduceLogSum",
    "ReduceLogSumExp",
    "ReduceSumSquare",
}


def _inits_by_name(graph):
    return {i.name: i for i in graph.initializer}


def fold_reduce_axes_to_attr(model):
    g = model.graph
    inits = _inits_by_name(g)
    removed, changed = set(), False
    for n in g.node:
        if n.op_type in REDUCE_SET and len(n.input) >= 2:
            axes = n.input[1]
            if axes in inits:
                vals = numpy_helper.to_array(inits[axes]).tolist()
                del n.input[1]
                kept = [a for a in n.attribute if a.name != "axes"]
                n.ClearField("attribute")
                n.attribute.extend(kept)
                n.attribute.extend([helper.make_attribute("axes", vals)])
                removed.add(axes)
                changed = True
    if removed:
        keep_inits = [i for i in g.initializer if i.name not in removed]
        g.ClearField("initializer")
        g.initializer.extend(keep_inits)
        keep_inputs = [vi for vi in g.input if vi.name not in removed]
        g.ClearField("input")
        g.input.extend(keep_inputs)
    return changed


def still_needs_opset18(model):
    return any(n.op_type in REDUCE_SET and len(n.input) >= 2 for n in model.graph.node)


def get_ai_onnx_opset(model):
    for o in model.opset_import:
        if o.domain in ("", "ai.onnx"):
            return o
    new = helper.make_operatorsetid("", 13)
    model.opset_import.extend([new])
    return new


def normalize_bytes(path: pathlib.Path) -> bytes:
    m = onnx.load(str(path))
    m.ir_version = 10
    fold_reduce_axes_to_attr(m)  # no unused variable
    oi = get_ai_onnx_opset(m)
    oi.version = 18 if still_needs_opset18(m) else 13
    checker.check_model(m)
    return m.SerializeToString()


def normalize_one(path: pathlib.Path):
    before = path.read_bytes()
    after = normalize_bytes(path)
    if after != before:
        path.write_bytes(after)
        print(f"[normalized] {path.name}: updated")
        return True
    else:
        print(f"[normalized] {path.name}: no-op")
        return False


def iter_targets(args_paths):
    targets = []
    if not args_paths:
        d = pathlib.Path("artifacts/onnx")
        if d.is_dir():
            targets = list(d.glob("*.onnx"))
    else:
        for p in args_paths:
            P = pathlib.Path(p)
            if P.is_dir():
                targets += list(P.glob("*.onnx"))
            elif P.suffix == ".onnx":
                targets.append(P)
    return targets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    a = ap.parse_args()
    tgts = iter_targets(a.paths)
    if not tgts:
        print("No ONNX files found.", file=sys.stderr)
        return 1
    changed = False
    for t in tgts:
        changed |= normalize_one(t)
    return 1 if changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
