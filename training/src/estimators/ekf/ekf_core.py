from __future__ import annotations

from typing import Any


class EKF:
    """Minimal EKF stub."""

    def step(self, meas: dict[str, Any]) -> dict[str, Any]:
        # Replace with real predict/update
        return {"state": [0.0, 0.0, 0.0], "cov": [[1.0, 0.0, 0.0]]}
