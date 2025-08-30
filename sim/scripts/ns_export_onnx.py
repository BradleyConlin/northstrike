#!/usr/bin/env python3
import argparse, re, sys
import onnx
from onnx import helper, TensorProto

def _parse_shape(s):
    m = re.fullmatch(r"\s*(\d+)x(\d+)x(\d+)x(\d+)\s*", s)
    if not m: raise SystemExit(f"bad --input '{s}', want 1xCxHxW")
    n,c,h,w = map(int, m.groups())
    return [n,c,h,w]

def _export_depth_placeholder(shape, out):
    n,c,h,w = shape
    X = helper.make_tensor_value_info("input", TensorProto.FLOAT, [n,c,h,w])
    Y = helper.make_tensor_value_info("output", TensorProto.FLOAT, [n,1,h,w])
    node = helper.make_node("ReduceMean", ["input"], ["output"], keepdims=1, axes=[1])
    g = helper.make_graph([node], "depth_reduce_c_to_1", [X], [Y])
    m = helper.make_model(g, opset_imports=[helper.make_operatorsetid("",13)])
    m.ir_version = 10
    onnx.checker.check_model(m); onnx.save(m, out)
    print(f"[export] wrote {out} (ReduceMean over C)")

def _normalize(path):
    m = onnx.load(path); m.ir_version = 10
    for imp in m.opset_import:
        if imp.domain in ("","ai.onnx"): imp.version = 13
    onnx.checker.check_model(m); onnx.save(m, path)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--input", default="1x3x384x640")
    ap.add_argument("--task", choices=["depth"], default="depth")
    args = ap.parse_args()
    shape = _parse_shape(args.input)

    # try PyTorch export if available; otherwise fallback
    try:
        import torch, torch.nn as nn  # noqa
        class MeanC(nn.Module):
            def forward(self,x): return x.mean(dim=1, keepdim=True)
        model = MeanC().eval()
        dummy = torch.randn(*shape, dtype=torch.float32)
        torch.onnx.export(model, dummy, args.out, opset_version=13,
                          input_names=["input"], output_names=["output"],
                          dynamic_axes=None)
        _normalize(args.out)
        print(f"[export] torch->onnx wrote {args.out}")
    except Exception as e:
        print(f"[warn] torch export unavailable ({e}); using ONNX fallback")
        _export_depth_placeholder(shape, args.out)
        _normalize(args.out)

if __name__ == "__main__":
    main()
