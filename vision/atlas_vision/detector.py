from __future__ import annotations

import logging
from dataclasses import dataclass

LOGGER = logging.getLogger(__name__)

# Compartilhados entre o agente e o evaluate.py: a spec pede o mesmo limiar nos
# dois, senão o MAE medido não corresponde ao que roda na demo.
DEFAULT_MODEL = "yolo11n.pt"
DEFAULT_CONF = 0.4


@dataclass(frozen=True)
class Detection:
    box: tuple[float, float, float, float]
    confidence: float
    class_id: int


class PersonDetector:
    def __init__(self, model_name: str, conf: float):
        self.model_name = model_name
        self.conf = conf
        self._model = None

    def load(self) -> None:
        if self._model is not None:
            return
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError("Ultralytics não instalado. Execute: pip install -r requirements.txt") from exc
        LOGGER.info("Carregando modelo YOLO: %s", self.model_name)
        self._model = YOLO(self.model_name)

    def detect(self, frame) -> list[Detection]:
        self.load()
        results = self._model.predict(source=frame, conf=self.conf, classes=[0], verbose=False)
        if not results:
            return []
        result = results[0]
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            return []
        xyxy = boxes.xyxy.cpu().numpy()
        conf = boxes.conf.cpu().numpy()
        cls = boxes.cls.cpu().numpy().astype(int)
        return [Detection(tuple(map(float, box)), float(score), int(cid)) for box, score, cid in zip(xyxy, conf, cls)]
