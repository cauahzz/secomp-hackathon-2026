from __future__ import annotations

import cv2

from .roi import ScaledROI

WINDOW_NAME = "ATLAS Vision"
ROI_COLOR = (0, 200, 255)
BOX_COLOR = (0, 255, 0)
FEET_COLOR = (0, 0, 255)


def draw_frame(frame, scaled_rois: list[ScaledROI], detections, smooth_values: dict[str, int]) -> None:
    out = frame.copy()
    for roi in scaled_rois:
        p1 = (int(round(roi.x)), int(round(roi.y)))
        p2 = (int(round(roi.x2)), int(round(roi.y2)))
        cv2.rectangle(out, p1, p2, ROI_COLOR, 2)
        value = smooth_values.get(roi.roi.id)
        text = str(value) if value is not None else "-"
        origin = (p1[0] + 8, max(24, p1[1] + 26))
        cv2.putText(out, roi.roi.name, origin, cv2.FONT_HERSHEY_SIMPLEX, 0.6, ROI_COLOR, 2, cv2.LINE_AA)
        # A contagem é o número que a plateia lê de longe no pitch: fonte grande
        # e contorno escuro para não sumir em cima do vídeo.
        count_origin = (origin[0], origin[1] + 54)
        cv2.putText(out, text, count_origin, cv2.FONT_HERSHEY_SIMPLEX, 1.7, (0, 0, 0), 7, cv2.LINE_AA)
        cv2.putText(out, text, count_origin, cv2.FONT_HERSHEY_SIMPLEX, 1.7, ROI_COLOR, 3, cv2.LINE_AA)

    for det in detections:
        x1, y1, x2, y2 = map(int, det.box)
        cv2.rectangle(out, (x1, y1), (x2, y2), BOX_COLOR, 2)
        cv2.circle(out, (int((x1 + x2) / 2), y2), 5, FEET_COLOR, -1)
        cv2.putText(out, f"person {det.confidence:.2f}", (x1, max(18, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, BOX_COLOR, 1, cv2.LINE_AA)

    cv2.imshow(WINDOW_NAME, out)


def poll_quit_key(wait_ms: int = 1) -> bool:
    return (cv2.waitKey(wait_ms) & 0xFF) == ord("q")
