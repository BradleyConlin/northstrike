#!/usr/bin/env python3
import argparse

import numpy as np
import onnx
from onnx import TensorProto, helper

ap = argparse.ArgumentParser()
ap.add_argument("--in-dim", type=int, default=64)
ap.add_argument("--hidden", type=int, default=32)
ap.add_argument("--out-dim", type=int, default=4)
ap.add_argument("--out", type=str, required=True)
args = ap.parse_args()


def const(name, arr):
    return helper.make_tensor(name, TensorProto.FLOAT, arr.shape, arr.flatten().tolist())


X = helper.make_tensor_value_info("input", TensorProto.FLOAT, [1, args.in_dim])
Y = helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, args.out_dim])

W1 = np.random.randn(args.in_dim, args.hidden).astype("float32") * 0.1
b1 = np.zeros((args.hidden,), "float32")
W2 = np.random.randn(args.hidden, args.out_dim).astype("float32") * 0.1
b2 = np.zeros((args.out_dim,), "float32")

n1 = helper.make_node("Gemm", ["input", "W1", "b1"], ["h"], alpha=1.0, beta=1.0, transB=0)
n2 = helper.make_node("Relu", ["h"], ["h2"])
n3 = helper.make_node("Gemm", ["h2", "W2", "b2"], ["output"], alpha=1.0, beta=1.0, transB=0)

graph = helper.make_graph(
    [n1, n2, n3],
    "mlp",
    [X],
    [Y],
    initializer=[const("W1", W1), const("b1", b1), const("W2", W2), const("b2", b2)],
)
onnx.save(helper.make_model(graph, producer_name="dummy_policy"), args.out)
print(f"wrote {args.out}")
