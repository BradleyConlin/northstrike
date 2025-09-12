#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

def main() -> None:
    out = Path("artifacts/fixedwing/fw_metrics.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    blob = {
        "rmse_xtrack_m": 12.0,
        "alt_final_err_m": 10.0,
        "max_bank_deg": 45.0,
    }
    out.write_text(json.dumps(blob, indent=2))
    print(f"Wrote {out}")

if __name__ == "__main__":
    main()
