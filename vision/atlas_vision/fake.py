from __future__ import annotations

import random


class FakeCounter:
    def __init__(self, capacities: dict[str, int], seed: int = 42):
        self.rng = random.Random(seed)
        self.values = {rid: min(max(0, capacity // 3), capacity) for rid, capacity in capacities.items()}
        self.capacities = capacities

    def next(self) -> dict[str, int]:
        for rid, cap in self.capacities.items():
            step = self.rng.randint(-2, 2)
            self.values[rid] = max(0, min(cap, self.values[rid] + step))
        return dict(self.values)
