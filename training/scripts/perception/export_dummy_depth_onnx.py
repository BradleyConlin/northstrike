#!/usr/bin/env python3
import argparse
import os

import torch


class RGB2Depth(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = torch.nn.Conv2d(3, 1, kernel_size=1, bias=False)
        with torch.no_grad():
            w = torch.tensor([0.299, 0.587, 0.114]).view(1, 3, 1, 1)
            self.conv.weight.copy_(w)

    def forward(self, x):
        y = self.conv(x)  # (N,1,H,W), roughly 0..1
        return torch.clamp(y, 0.0, 1.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--height", type=int, default=240)
    ap.add_argument("--width", type=int, default=320)
    ap.add_argument("--opset", type=int, default=17)
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    m = RGB2Depth().eval()
    x = torch.randn(1, 3, args.height, args.width)
    torch.onnx.export(
        m,
        x,
        args.out,
        export_params=True,
        opset_version=args.opset,
        do_constant_folding=True,
        input_names=["images"],
        output_names=["depth"],
        dynamic_axes={"images": {0: "N", 2: "H", 3: "W"}, "depth": {0: "N", 2: "H", 3: "W"}},
    )
    print("Exported →", args.out)


if __name__ == "__main__":
    main()
