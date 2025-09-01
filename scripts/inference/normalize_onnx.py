#!/usr/bin/env python
from __future__ import annotations

import sys
from pathlib import Path

import onnx

# Reduce ops that, at higher opsets, may accept "axes" as a second *input* tensor
REDUCE_OPS = {
    "ReduceMean",
    "ReduceSum",
    "ReduceProd",
    "ReduceMin",
    "ReduceMax",
    "ReduceL1",
    "ReduceL2",
    "ReduceLogSum",
    "ReduceLogSumExp",
    "ReduceSumSquare",
}


def needs_opset18_for_axes_input(model: onnx.ModelProto) -> bool:
    """Return True iff any Reduce* node supplies axes as a tensor input (input[1])."""
    for n in model.graph.node:
        if n.op_type in REDUCE_OPS and len(n.input) >= 2 and n.input[1]:
            return True
    return False


def current_ai_onnx_opset(model: onnx.ModelProto) -> int:
    """Get the numeric opset for the default (ai.onnx) domain."""
    cur = 0
    for imp in model.opset_import:
        if imp.domain in ("", "ai.onnx"):
            try:
                cur = max(cur, int(imp.version))
            except Exception:
                pass
    return cur


def set_ai_onnx_opset_at_least(model: onnx.ModelProto, minimum: int) -> bool:
    """
    Ensure the default (ai.onnx) opset is >= minimum.
    Preserve other domains. Return True if modified.
    """
    cur = current_ai_onnx_opset(model)
    target = max(cur, minimum)
    if target == cur:
        return False

    new_imports: list[onnx.OperatorSetIdProto] = []
    replaced_ai = False
    for imp in model.opset_import:
        if imp.domain in ("", "ai.onnx"):
            if not replaced_ai:
                new_imports.append(onnx.helper.make_operatorsetid("", target))
                replaced_ai = True
            # skip duplicate ai.onnx entries
        else:
            new_imports.append(imp)

    if not replaced_ai:
        new_imports.append(onnx.helper.make_operatorsetid("", target))

    del model.opset_import[:]
    model.opset_import.extend(new_imports)
    return True


def normalize_one(p: Path) -> None:
    # Skip scratch promotion files by convention
    if p.name.startswith("_promote_"):
        print(f"[skip] {p} (promotion scratch)")
        return

    m = onnx.load(p.as_posix())

    # Base requirement: opset >= 13 for broad ORT compatibility
    required = 13
    # If any Reduce* uses axes as an input tensor, require opset >= 18
    if needs_opset18_for_axes_input(m):
        required = 18

    changed = set_ai_onnx_opset_at_least(m, required)

    # Do NOT force IR downgrades; keep whatever IR the model already has.
    # Validate before saving so schema mismatches fail early.
    onnx.checker.check_model(m)

    if changed:
        onnx.save(m, p.as_posix())
        print(f"[normalized] {p} opset -> {required}")
    else:
        print(f"[ok] {p} opset={current_ai_onnx_opset(m)}")


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: normalize_onnx.py <model.onnx | directory>", file=sys.stderr)
        sys.exit(2)

    root = Path(sys.argv[1])
    if root.is_file():
        normalize_one(root)
    else:
        for f in sorted(root.rglob("*.onnx")):
            normalize_one(f)


if __name__ == "__main__":
    main()
