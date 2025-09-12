#!/usr/bin/env python
import sys

import onnx


def normalize(path: str):
    m = onnx.load(path)
    orig_ir = m.ir_version
    try:
        # Prefer IR=10 and default opset<=13 for stability, if safe
        if not orig_ir or orig_ir > 10:
            m.ir_version = 10
        for imp in m.opset_import:
            if imp.domain == "" and imp.version and imp.version > 13:
                imp.version = 13
        onnx.checker.check_model(m)
    except Exception:
        m = onnx.load(path)  # revert if lowering not safe
    onnx.save(m, path)


if __name__ == "__main__":
    for f in sys.argv[1:]:
        normalize(f)
