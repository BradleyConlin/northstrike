#!/usr/bin/env python3
import numpy as np
import onnx
from onnx import TensorProto, helper

# Build a tiny linear+ReLU policy: obs(1x64) -> MatMul(64x4) -> Add(bias) -> Relu -> act(1x4)
obs = helper.make_tensor_value_info("obs", TensorProto.FLOAT, [1, 64])
act = helper.make_tensor_value_info("act", TensorProto.FLOAT, [1, 4])

W = np.eye(64, 4, dtype=np.float32)  # shape (64,4) with 1s along first 4 rows
b = np.zeros((4,), dtype=np.float32)

W_init = helper.make_tensor("W", TensorProto.FLOAT, [64, 4], W.flatten().tolist())
b_init = helper.make_tensor("b", TensorProto.FLOAT, [4], b.tolist())

mm = helper.make_node("MatMul", ["obs", "W"], ["mm"])
add = helper.make_node("Add", ["mm", "b"], ["pre"])
relu = helper.make_node("Relu", ["pre"], ["act"])

graph = helper.make_graph([mm, add, relu], "policy_dummy", [obs], [act], [W_init, b_init])
model = helper.make_model(graph, opset_imports=[helper.make_operatorsetid("", 13)])

# Let our normalizer hook upgrade IR/version as needed
onnx.checker.check_model(model)
onnx.save(model, "artifacts/onnx/policy_dummy.onnx")
print("Wrote artifacts/onnx/policy_dummy.onnx")
