#!/usr/bin/env python3
import onnx
from onnx import helper, TensorProto

def main(out_path="artifacts/onnx/depth_e24.onnx"):
    X = helper.make_tensor_value_info("input", TensorProto.FLOAT, [1,3,384,640])
    Y = helper.make_tensor_value_info("output", TensorProto.FLOAT, [1,1,384,640])
    axes = helper.make_tensor("axes", TensorProto.INT64, [1], [1])  # channel axis
    node = helper.make_node("ReduceMean", ["input","axes"], ["output"], keepdims=1)
    g = helper.make_graph([node], "depth_dummy_reduce", [X], [Y], initializer=[axes])
    m = helper.make_model(g, opset_imports=[helper.make_operatorsetid("", 13)])
    m.ir_version = 10
    onnx.save(m, out_path)
    print(f"[ok] wrote {out_path}")

if __name__ == "__main__":
    main()
