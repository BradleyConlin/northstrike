from __future__ import annotations


class TECS:
    """Tiny placeholder for TECS controller interface."""

    def step(self, state: dict, refs: dict) -> dict:
        """Return placeholder pitch/throttle commands."""
        return {"pitch": 0.0, "throttle": 0.5}
