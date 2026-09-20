from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .models import ROI


@dataclass(frozen=True)
class ScaledROI:
    roi: ROI
    x: float
    y: float
    width: float
    height: float

    @property
    def x2(self) -> float:
        return self.x + self.width

    @property
    def y2(self) -> float:
        return self.y + self.height

    def contains(self, px: float, py: float) -> bool:
        return self.x <= px < self.x2 and self.y <= py < self.y2


def scale_roi(roi: ROI, frame_w: int, frame_h: int, camera_w: int, camera_h: int) -> ScaledROI:
    if camera_w <= 0 or camera_h <= 0:
        raise ValueError("dimensões da câmera no seed devem ser > 0")
    sx = frame_w / camera_w
    sy = frame_h / camera_h
    g = roi.geometry
    return ScaledROI(roi, g["x"] * sx, g["y"] * sy, g["width"] * sx, g["height"] * sy)


def feet_point(box: Iterable[float]) -> tuple[float, float]:
    x1, y1, x2, y2 = map(float, box)
    return ((x1 + x2) / 2.0, y2)


def assign_detections_to_rois(
    boxes: Iterable[Iterable[float]], rois: list[ScaledROI]
) -> dict[str, int]:
    counts = {r.roi.id: 0 for r in rois}
    for box in boxes:
        px, py = feet_point(box)
        for r in rois:
            if r.contains(px, py):
                counts[r.roi.id] += 1
                # Uma pessoa conta para uma ROI só: em ROIs sobrepostas a ordem
                # do seed decide, nunca a soma.
                break
    return counts
