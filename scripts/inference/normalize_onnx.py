#!/usr/bin/env python3
import glob
import sys

import onnx
from onnx import helper


def _default_domain_opset(model):
    v = 0
    for imp in model.opset_import:
        if imp.domain == "":
            v = max(v, imp.version)
    return v or 13


def _has_reduce_axes_input(model):
    for n in model.graph.node:
        if n.op_type.startswith("Reduce"):
            # axes-as-input (len >= 2) requires opset >= 18
            if len(n.input) >= 2 and n.input[1]:
                return True
    return False


def _set_default_opset(model, target):
    found = False
    for imp in model.opset_import:
        if imp.domain == "":
            if imp.version < target:
                imp.version = target
            found = True
    if not found:
        model.opset_import.extend([helper.make_opsetid("", target)])


def normalize_one(path):
    m = onnx.load(path)

    # Choose a safe target opset: 13 by default; if any Reduce* uses axes input, keep/bump to >=18
    cur_default = _default_domain_opset(m)
    target = 13
    if _has_reduce_axes_input(m):
        target = max(18, cur_default)

    _set_default_opset(m, target)
    if not getattr(m, "ir_version", None):
        m.ir_version = 7  # safe baseline

    onnx.checker.check_model(m)
    onnx.save(m, path)
    print(f"[normalized] {path} opset={target}")


def main():
    files = sys.argv[1:]
    if not files:
        files = glob.glob("artifacts/onnx/*.onnx")
    for p in files:
        normalize_one(p)


if __name__ == "__main__":
    main()
