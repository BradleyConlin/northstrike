#!/usr/bin/env python3
import argparse
import glob
import json
import os
import pathlib

import numpy as np
import torch
import torch.nn as nn


# Optional deps: keep imports inside try so the script stays friendly
def _maybe_import_mlflow():
    try:
        import mlflow  # type: ignore

        return mlflow
    except Exception:
        return None


def _maybe_import_ort():
    try:
        import onnxruntime as ort  # type: ignore

        return ort
    except Exception:
        return None


def _find_jsonl_logs(root: str) -> list[str]:
    pats = [
        os.path.join(root, "**", "*.jsonl"),
        os.path.join(root, "*.jsonl"),
    ]
    files = []
    for p in pats:
        files.extend(glob.glob(p, recursive=True))
    return sorted(set(files))


def _extract_pair(d: dict, candidates: list[tuple[str, str]]) -> tuple[float, float] | None:
    """
    Try many common shapes:
    - separate keys: ('wind_x','wind_y')
    - nested dict: d['wind']={'x':..,'y':..}
    - 2-list: d['wind_xy']=[..,..] or d['wind']=[..,..]
    """
    # separate keys
    for kx, ky in candidates:
        if kx in d and ky in d:
            try:
                return float(d[kx]), float(d[ky])
            except Exception:
                pass
    # nested dicts
    for kx, ky in candidates:
        root = kx.split(".")[0]
        sub = d.get(root)
        if isinstance(sub, dict):
            x = sub.get(kx.split(".")[-1], sub.get("x"))
            y = sub.get(ky.split(".")[-1], sub.get("y"))
            if x is not None and y is not None:
                try:
                    return float(x), float(y)
                except Exception:
                    pass
    # 2-lists
    for name in {k for pair in candidates for k in pair} | {
        "wind",
        "bias",
        "gnss_bias",
        "gnssBias",
        "bias_xy",
        "wind_xy",
    }:
        v = d.get(name)
        if isinstance(v, (list, tuple)) and len(v) >= 2:
            try:
                return float(v[0]), float(v[1])
            except Exception:
                pass
    return None


def _collect_numeric_features(d: dict, drop_keys: set, limit: int = 64) -> list[float]:
    """Collect scalar numeric fields.

    Flattens tiny lists/tuples; keeps key-sorted order for stability.
    """
    feats = []
    for k in sorted(d.keys()):
        if k in drop_keys:
            continue
        v = d[k]
        try:
            if isinstance(v, (int, float)) and np.isfinite(v):
                feats.append(float(v))
            elif isinstance(v, (list, tuple)) and 1 <= len(v) <= 4:
                vals = [float(x) for x in v if isinstance(x, (int, float)) and np.isfinite(x)]
                feats.extend(vals[:4])
            elif isinstance(v, dict):
                # pick common scalar-ish subkeys
                for sk in ("mean", "std", "rms", "var", "mag", "count", "duration_s"):
                    if sk in v and isinstance(v[sk], (int, float)) and np.isfinite(v[sk]):
                        feats.append(float(v[sk]))
        except Exception:
            continue
        if len(feats) >= limit:
            break
    return feats


class MLP(nn.Module):
    def __init__(self, in_dim: int, hidden: int = 64, out_dim: int = 4):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden),
            nn.ReLU(inplace=True),
            nn.Linear(hidden, hidden),
            nn.ReLU(inplace=True),
            nn.Linear(hidden, out_dim),
        )

    def forward(self, x):
        return self.net(x)


def _make_synth(n: int, fdim: int = 32, seed: int = 42):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, fdim)).astype(np.float32)
    W = rng.normal(scale=0.5, size=(4, fdim)).astype(np.float32)
    y = (X @ W.T) + rng.normal(scale=0.1, size=(n, 4)).astype(np.float32)
    return X, y


def _load_from_logs(log_root: str, min_rows: int = 16):
    files = _find_jsonl_logs(log_root)
    X, Y = [], []
    for fp in files:
        with open(fp) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                wind = _extract_pair(
                    d,
                    candidates=[
                        ("wind_x", "wind_y"),
                        ("wind.x", "wind.y"),
                        ("wind", "wind"),
                        ("wind_xy", "wind_xy"),
                    ],
                )
                bias = _extract_pair(
                    d,
                    candidates=[
                        ("gnss_bias_x", "gnss_bias_y"),
                        ("bias_x", "bias_y"),
                        ("gnss_bias.x", "gnss_bias.y"),
                        ("gnss_bias", "gnss_bias"),
                        ("bias_xy", "bias_xy"),
                    ],
                )
                if not (wind and bias):
                    continue
                drop = {
                    "wind_x",
                    "wind_y",
                    "bias_x",
                    "bias_y",
                    "gnss_bias_x",
                    "gnss_bias_y",
                    "wind",
                    "wind_xy",
                    "gnss_bias",
                    "bias_xy",
                }
                feats = _collect_numeric_features(d, drop_keys=drop, limit=64)
                if len(feats) == 0:
                    # minimal “bias-only” features to keep shapes valid
                    feats = [np.hypot(*wind), np.hypot(*bias)]
                X.append(np.asarray(feats, dtype=np.float32))
                Y.append(np.asarray([*wind, *bias], dtype=np.float32))
    if len(X) < min_rows:
        return None, None
    # pad/truncate to a consistent feature dimension
    fdim = max(len(x) for x in X)
    Xp = []
    for x in X:
        if len(x) < fdim:
            x = np.pad(x, (0, fdim - len(x)))
        Xp.append(x.astype(np.float32))
    return np.stack(Xp), np.stack(Y, dtype=np.float32)


def train(args):
    mlflow = _maybe_import_mlflow()
    ort = _maybe_import_ort()

    # 1) Build dataset
    X, Y = (None, None)
    if args.logs and os.path.isdir(args.logs):
        X, Y = _load_from_logs(args.logs)
    if X is None or Y is None:
        n = args.synthetic if args.synthetic > 0 else 512
        print(f"[info] falling back to synthetic dataset: N={n}")
        X, Y = _make_synth(n=n, fdim=args.fdim, seed=args.seed)

    X = torch.from_numpy(X)
    Y = torch.from_numpy(Y)
    n, fdim = X.shape
    idx = torch.randperm(n)
    tr, va = idx[: int(0.9 * n)], idx[int(0.9 * n) :]

    # 2) Model/optim
    model = MLP(in_dim=fdim, hidden=args.hidden, out_dim=4)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    loss_fn = nn.MSELoss()

    if mlflow and args.mlflow:
        mlflow.set_tracking_uri("file:artifacts/mlruns")
        mlflow.set_experiment("northstrike")
        mlflow.start_run()
        mlflow.log_params(
            {
                "task": 20,
                "fdim": fdim,
                "hidden": args.hidden,
                "lr": args.lr,
                "epochs": args.epochs,
                "seed": args.seed,
                "source": "logs" if args.logs else "synthetic",
            }
        )

    # 3) Train
    for ep in range(args.epochs):
        model.train()
        opt.zero_grad(set_to_none=True)
        pred = model(X[tr])
        loss = loss_fn(pred, Y[tr])
        loss.backward()
        opt.step()
        if ep % max(1, args.epochs // 10) == 0:
            with torch.no_grad():
                va_loss = loss_fn(model(X[va]), Y[va]).item()
            print(f"[ep {ep:03d}] train={loss.item():.4f}  val={va_loss:.4f}")
            if mlflow and args.mlflow:
                mlflow.log_metrics(
                    {"train_loss": float(loss.item()), "val_loss": float(va_loss)}, step=ep
                )

    # 4) Export ONNX
    out_path = pathlib.Path(args.out_onnx)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    model.eval()
    dummy = torch.randn(1, fdim)
    torch.onnx.export(
        model,
        dummy,
        out_path.as_posix(),
        input_names=["x"],
        output_names=["y"],
        dynamic_axes={"x": {0: "batch"}, "y": {0: "batch"}},
        opset_version=13,
    )
    print(f"[save] onnx -> {out_path}")

    # 5) Quick ORT smoke
    if ort:
        sess = ort.InferenceSession(out_path.as_posix(), providers=["CPUExecutionProvider"])
        y = sess.run(None, {"x": dummy.numpy()})[0]
        assert y.shape == (1, 4), f"bad ONNX output shape {y.shape}"
        print("[onnxruntime] inference OK")

    if mlflow and args.mlflow:
        mlflow.log_artifact(out_path.as_posix())
        mlflow.end_run()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", type=str, default="", help="Path to Task-19 logs root (jsonl)")
    ap.add_argument("--synthetic", type=int, default=0, help="If >0, generate N synthetic samples")
    ap.add_argument(
        "--fdim", type=int, default=32, help="Synthetic feature dim (when using --synthetic)"
    )
    ap.add_argument("--hidden", type=int, default=64)
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--seed", type=int, default=123)
    ap.add_argument("--mlflow", action="store_true")
    ap.add_argument("--out-onnx", type=str, default="artifacts/onnx/wind_bias_mlp.onnx")
    args = ap.parse_args()
    train(args)


if __name__ == "__main__":
    main()
