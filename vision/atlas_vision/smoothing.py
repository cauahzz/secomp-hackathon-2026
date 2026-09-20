from __future__ import annotations

from collections import defaultdict, deque
from statistics import median
from time import monotonic


class MedianSmoother:
    def __init__(self, window_seconds: float, clock=monotonic):
        if window_seconds <= 0:
            raise ValueError("window_seconds deve ser > 0")
        self.window_seconds = float(window_seconds)
        self.clock = clock
        self.samples: dict[str, deque[tuple[float, int]]] = defaultdict(deque)

    def add(self, region_id: str, count: int, timestamp: float | None = None) -> None:
        now = self.clock() if timestamp is None else timestamp
        q = self.samples[region_id]
        q.append((now, int(count)))
        self._trim(region_id, now)

    def _trim(self, region_id: str, now: float) -> None:
        q = self.samples[region_id]
        cutoff = now - self.window_seconds
        while q and q[0][0] < cutoff:
            q.popleft()

    def value(self, region_id: str, timestamp: float | None = None) -> int | None:
        now = self.clock() if timestamp is None else timestamp
        if region_id not in self.samples:
            return None
        self._trim(region_id, now)
        q = self.samples[region_id]
        if not q:
            return None
        return int(round(median(v for _, v in q)))

    def values(self, timestamp: float | None = None) -> dict[str, int]:
        now = self.clock() if timestamp is None else timestamp
        result = {}
        for rid in list(self.samples):
            value = self.value(rid, now)
            if value is not None:
                result[rid] = value
        return result
