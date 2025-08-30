#!/usr/bin/env python
import sys, onnx
from pathlib import Path

def fix(p: Path):
    m = onnx.load(p.as_posix())
    m.ir_version = 10
    for imp in m.opset_import:
        if imp.domain in ("", "ai.onnx"):
            imp.version = 13
    onnx.checker.check_model(m)
    onnx.save(m, p.as_posix())
    print(f"[normalized] {p}")

paths = [Path(x) for x in sys.argv[1:]]
for p in paths:
    if p.is_file():
        fix(p)
