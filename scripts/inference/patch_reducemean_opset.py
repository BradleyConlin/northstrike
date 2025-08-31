#!/usr/bin/env python3
import sys, onnx
from onnx import helper

def patch(path):
    m = onnx.load(path)
    # If any ReduceMean uses a second input (axes), we need opset >= 18
    need18 = any(n.op_type == "ReduceMean" and len(n.input) >= 2 for n in m.graph.node)
    if not need18:
        print(f"[patch] {path}: no 2-input ReduceMean found; nothing to do")
        return
    bumped = False
    for imp in m.opset_import:
        if imp.domain == "" and imp.version < 18:
            imp.version = 18
            bumped = True
    if not bumped and not any(imp.domain == "" for imp in m.opset_import):
        m.opset_import.extend([helper.make_operatorsetid("", 18)])
    onnx.checker.check_model(m)
    onnx.save(m, path)
    print(f"[patch] bumped main opset to 18 for {path}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: patch_reducemean_opset.py <model.onnx>")
        sys.exit(2)
    patch(sys.argv[1])
