#!/usr/bin/env python3
import argparse
from pathlib import Path

import onnx
from onnx import TensorProto, helper


def build_model(in_dim: int, out_dim: int) -> onnx.ModelProto:
    x = helper.make_tensor_value_info("x", TensorProto.FLOAT, [1, in_dim])
    y = helper.make_tensor_value_info("y", TensorProto.FLOAT, [1, out_dim])

    W = helper.make_tensor("W", TensorProto.FLOAT, [in_dim, out_dim], [0.0] * (in_dim * out_dim))
    b = helper.make_tensor("b", TensorProto.FLOAT, [out_dim], [0.0] * out_dim)

    node = helper.make_node("Gemm", ["x", "W", "b"], ["y"], alpha=1.0, beta=1.0, transA=0, transB=0)
    graph = helper.make_graph([node], "policy_dummy_gemm", [x], [y], [W, b])

    # IR=10 and opset 13 to satisfy older ORT builds
    opset = helper.make_operatorsetid("", 13)
    return helper.make_model(graph, opset_imports=[opset], ir_version=10)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-dim", type=int, required=True)
    ap.add_argument("--out-dim", type=int, required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    model = build_model(args.in_dim, args.out_dim)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Important: if a dangling symlink exists at the target, unlink it first
    try:
        if out.is_symlink() or out.exists():
            out.unlink()
    except FileNotFoundError:
        pass

    onnx.save_model(model, str(out))
    print(f"wrote {out} (IR={model.ir_version}, opset=[{[i.version for i in model.opset_import]}])")


if __name__ == "__main__":
    main()
