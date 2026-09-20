from __future__ import annotations

import logging
import time

import cv2

from .models import HTTP_SCHEMES, STREAM_SCHEMES

LOGGER = logging.getLogger(__name__)


def is_live_source(source: str | int, source_type: str) -> bool:
    if isinstance(source, int):
        return True
    value = str(source).lower()
    if value.startswith(STREAM_SCHEMES):
        return True
    kind = source_type.lower()
    if kind in {"camera", "webcam", "stream", "rtsp", "rtmp"}:
        return True
    if kind == "file":
        # Arquivo continua sendo arquivo mesmo servido por HTTP: precisa voltar
        # ao início no fim, senão a demo para e tudo vira no_data em 30 s.
        return False
    return value.startswith(HTTP_SCHEMES)


def frame_sampling_step(video_fps: float, process_fps: float) -> int:
    """Quantos frames avançar entre dois processamentos."""
    if video_fps <= 0 or process_fps <= 0:
        return 1
    return max(1, int(round(video_fps / process_fps)))


class OpenCVSource:
    def __init__(self, source: str | int, source_type: str, reconnect_seconds: float = 2.0):
        self.source = source
        self.source_type = source_type
        self.reconnect_seconds = reconnect_seconds
        self.live = is_live_source(source, source_type)
        self.cap = None
        self.last_attempt = 0.0

    def _open(self) -> bool:
        now = time.monotonic()
        if now - self.last_attempt < self.reconnect_seconds:
            return False
        self.last_attempt = now
        if self.cap is not None:
            self.cap.release()
        self.cap = cv2.VideoCapture(self.source)
        ok = self.cap.isOpened()
        if ok:
            LOGGER.info("Fonte aberta: %s", self.source)
        else:
            LOGGER.warning("Não foi possível abrir a fonte: %s", self.source)
            self.cap.release()
            self.cap = None
        return ok

    def read(self):
        while True:
            if self.cap is None and not self._open():
                time.sleep(0.1)
                return False, None
            ok, frame = self.cap.read()
            if ok:
                return True, frame
            if not self.live:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = self.cap.read()
                if ok:
                    LOGGER.info("Vídeo reiniciado no frame 0")
                    return True, frame
                self.cap.release()
                self.cap = None
                return False, None
            LOGGER.warning("Leitura da fonte falhou; tentando reabrir em %.1fs", self.reconnect_seconds)
            self.cap.release()
            self.cap = None
            time.sleep(self.reconnect_seconds)

    def skip(self, count: int) -> int:
        """Avança frames sem decodificar. Devolve quantos foram realmente pulados."""
        if self.cap is None or count <= 0:
            return 0
        skipped = 0
        while skipped < count and self.cap.grab():
            skipped += 1
        return skipped

    def fps(self, fallback: float = 30.0) -> float:
        if self.cap is None:
            return fallback
        fps = float(self.cap.get(cv2.CAP_PROP_FPS) or 0)
        return fps if fps > 0 else fallback

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
