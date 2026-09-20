from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any

import requests

LOGGER = logging.getLogger(__name__)


def utc_now_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class AtlasClient:
    def __init__(self, api_url: str, timeout: float = 2.0):
        self.base_url = api_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def ingest(
        self, camera_id: str, regions: list[dict[str, Any]], captured_at: str | None = None
    ) -> bool:
        payload = {
            "camera_id": camera_id,
            "captured_at": captured_at or utc_now_z(),
            "regions": regions,
        }
        try:
            response = self.session.post(f"{self.base_url}/ingest", json=payload, timeout=self.timeout)
        except requests.RequestException as exc:
            LOGGER.warning("Falha no POST /ingest: %s", exc)
            return False
        if response.status_code != 200:
            LOGGER.warning("POST /ingest retornou HTTP %s: %s", response.status_code, response.text[:500])
            return False
        try:
            body = response.json()
        except ValueError:
            LOGGER.warning("POST /ingest retornou 200 mas corpo não é JSON")
            return False
        ignored = body.get("ignored", []) if isinstance(body, dict) else []
        if ignored:
            LOGGER.warning("API ignorou ROIs: %s", ignored)
        LOGGER.info("Enviado: %s", {r["region_id"]: r["person_count"] for r in regions})
        return True


class AsyncIngest:
    """Envia em thread e descarta a contagem se o envio anterior ainda está em voo.

    O loop de vídeo não pode esperar pela rede: com a API pendurada, um POST de
    2 s de timeout congelaria a janela 2 s a cada intervalo de envio. Descartar
    em vez de enfileirar também é o que a spec pede, porque o próximo envio já
    leva a contagem atual. Só há uma requisição por vez, então a Session basta.
    """

    def __init__(self, client: AtlasClient):
        self.client = client
        self._thread: threading.Thread | None = None

    def send(self, camera_id: str, regions: list[dict[str, Any]]) -> bool:
        if self._thread is not None and self._thread.is_alive():
            LOGGER.warning("Envio anterior ainda em voo; descartando esta contagem")
            return False
        # captured_at é o instante da contagem, não o da thread.
        self._thread = threading.Thread(
            target=self.client.ingest,
            args=(camera_id, regions, utc_now_z()),
            name="atlas-ingest",
            daemon=True,
        )
        self._thread.start()
        return True

    def close(self, timeout: float = 2.5) -> None:
        if self._thread is not None:
            self._thread.join(timeout)
