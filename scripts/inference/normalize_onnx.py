#!/usr/bin/env python3
"""
Normalize ONNX models for CI:
- Keep IR version >= 10
- Choose opset:
    * If any Reduce* op uses "axes as input" (i.e., node has >=2 inputs), require opset >= 18
    * Otherwise normalize to opset 13 for maximum compatibility
This makes pre-commit robust for both legacy and newer models.
"""
from __future__ import annotations
import sys, glob, pathlib
import onnx
from onnx import helper

REDUCE_OPS = {
    "ReduceMean", "ReduceSum", "ReduceMax", "ReduceMin",
    "ReduceProd", "ReduceL1", "ReduceL2", "ReduceLogSum", "ReduceLogSumExp"
}
IR_TARGET = 10
OPSET_BASELINE = 13
OPSET_WITH_AXES_INPUT = 18

def uses_axes_input(m: onnx.ModelProto) -> bool:
    for n in m.graph.node:
        if n.op_type in REDUCE_OPS and len(n.input) >= 2:
            return True
    return False

def get_ai_onnx_opset(m: onnx.ModelProto) -> int | None:
    for imp in m.opset_import:
        if imp.domain in ("", "ai.onnx"):
            return int(imp.version)
    return None

def set_ai_onnx_opset(m: onnx.ModelProto, version: int) -> None:
    for imp in m.opset_import:
        if imp.domain in ("", "ai.onnx"):
            imp.version = version
            return
    m.opset_import.extend([helper.make_operatorsetid("", version)])

def normalize_one(path: str) -> None:
    p = pathlib.Path(path)
    m = onnx.load(str(p))

    # Decide target opset based on Reduce* usage
    desired = OPSET_WITH_AXES_INPUT if uses_axes_input(m) else OPSET_BASELINE

    # Only bump; never downgrade a model already at a higher opset
    current = get_ai_onnx_opset(m)
    if current is None or current < desired:
        set_ai_onnx_opset(m, desired)

    # IR version
    if getattr(m, "ir_version", 0) < IR_TARGET:
        m.ir_version = IR_TARGET

    # Validate and save
    onnx.checker.check_model(m)
    onnx.save(m, str(p))
    print(f"[onnx-normalize] {p} opset={get_ai_onnx_opset(m)} ir={m.ir_version}")

def main():
    args = sys.argv[1:] or glob.glob("artifacts/onnx/*.onnx")
    if not args:
        print("[onnx-normalize] no models found")
        return
    for a in args:
        normalize_one(a)

if __name__ == "__main__":
    main()
