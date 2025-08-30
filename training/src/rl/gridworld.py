#!/usr/bin/env python3
from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass

Pos = tuple[int, int]


@dataclass
class GWCfg:
    w: int = 8
    h: int = 6
    start: Pos = (0, 0)
    goal: Pos = (7, 5)
    obstacles: set[Pos] = None  # type: ignore
    hazards: set[Pos] = None  # type: ignore
    step_cost: float = -0.01
    goal_reward: float = 1.0
    obstacle_penalty: float = -1.0
    hazard_penalty: float = -0.2


class GridWorld:
    """Tiny deterministic gridworld with obstacles and 'hazard' cells (safety)."""

    ACTIONS: list[Pos] = [(1, 0), (-1, 0), (0, 1), (0, -1)]  # E, W, S, N

    def __init__(self, cfg: GWCfg | None = None, seed: int = 7):
        self.cfg = cfg or GWCfg()
        self.rng = random.Random(seed)
        if self.cfg.obstacles is None:
            self.cfg.obstacles = set()
        if self.cfg.hazards is None:
            self.cfg.hazards = set()
        self.pos: Pos = self.cfg.start

    def reset(self, seed: int | None = None) -> Pos:
        if seed is not None:
            self.rng.seed(seed)
        self.pos = self.cfg.start
        return self.pos

    def step(self, a_idx: int) -> tuple[Pos, float, bool, dict]:
        dx, dy = self.ACTIONS[a_idx]
        nx, ny = self.pos[0] + dx, self.pos[1] + dy
        done = False
        info: dict = {"unsafe": False}

        # out of bounds => treat as obstacle (no move + penalty)
        if not (0 <= nx < self.cfg.w and 0 <= ny < self.cfg.h) or (nx, ny) in self.cfg.obstacles:
            reward = self.cfg.obstacle_penalty
            nxt = self.pos  # blocked; stay
        else:
            nxt = (nx, ny)
            reward = self.cfg.step_cost
            if nxt in self.cfg.hazards:
                reward += self.cfg.hazard_penalty
                info["unsafe"] = True
            if nxt == self.cfg.goal:
                reward += self.cfg.goal_reward
                done = True

        self.pos = nxt
        return nxt, float(reward), bool(done), info


def shortest_path_len(w: int, h: int, start: Pos, goal: Pos, obstacles: set[Pos]) -> int:
    """BFS on 4-connectivity (ignores hazards). Returns steps or large number if unreachable."""
    Q = deque([(start, 0)])
    seen = {start}
    moves = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    while Q:
        (x, y), d = Q.popleft()
        if (x, y) == goal:
            return d
        for dx, dy in moves:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < w and 0 <= ny < h):
                continue
            if (nx, ny) in obstacles:
                continue
            if (nx, ny) in seen:
                continue
            seen.add((nx, ny))
            Q.append(((nx, ny), d + 1))
    return 10**9
