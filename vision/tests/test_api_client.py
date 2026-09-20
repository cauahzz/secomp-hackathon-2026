import json
import re
import threading

import requests

from atlas_vision.api_client import AsyncIngest, AtlasClient, utc_now_z

REGIONS = [{"region_id": "ROI-01", "person_count": 12}]


class FakeResponse:
    def __init__(self, status_code, body="{}"):
        self.status_code = status_code
        self.text = body

    def json(self):
        return json.loads(self.text)


class FakeSession:
    def __init__(self, result):
        self.result = result
        self.calls = []
        self.started = threading.Event()
        self.release = threading.Event()

    def post(self, url, json=None, timeout=None):
        self.calls.append({"url": url, "payload": json, "timeout": timeout})
        self.started.set()
        self.release.wait(5)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def make_client(result, timeout=2.0):
    client = AtlasClient("http://localhost:8000/", timeout=timeout)
    session = FakeSession(result)
    session.release.set()
    client.session = session
    return client, session


def test_captured_at_em_utc_com_z():
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", utc_now_z())


def test_payload_no_formato_do_contrato():
    client, session = make_client(FakeResponse(200, '{"accepted": 1, "ignored": []}'))
    assert client.ingest("CAM-01", REGIONS, captured_at="2026-09-20T17:30:10Z") is True
    call = session.calls[0]
    assert call["url"] == "http://localhost:8000/ingest"
    assert call["timeout"] == 2.0
    assert call["payload"] == {
        "camera_id": "CAM-01",
        "captured_at": "2026-09-20T17:30:10Z",
        "regions": REGIONS,
    }


def test_falha_de_conexao_nao_propaga():
    client, _ = make_client(requests.RequestException("conexão recusada"))
    assert client.ingest("CAM-01", REGIONS) is False


def test_status_diferente_de_200_nao_propaga():
    client, _ = make_client(FakeResponse(404, '{"detail": "camera not found"}'))
    assert client.ingest("CAM-01", REGIONS) is False


def test_corpo_nao_json_nao_propaga():
    client, _ = make_client(FakeResponse(200, "<html>"))
    assert client.ingest("CAM-01", REGIONS) is False


def test_rois_ignoradas_geram_aviso(caplog):
    client, _ = make_client(FakeResponse(200, '{"accepted": 0, "ignored": ["ROI-09"]}'))
    with caplog.at_level("WARNING"):
        assert client.ingest("CAM-01", REGIONS) is True
    assert "ROI-09" in caplog.text


def test_envio_em_voo_descarta_a_contagem_nova():
    """Não acumular fila: o próximo envio já leva a contagem atual."""
    client, session = make_client(FakeResponse(200, '{"accepted": 1, "ignored": []}'))
    session.release.clear()
    sender = AsyncIngest(client)
    try:
        assert sender.send("CAM-01", REGIONS) is True
        assert session.started.wait(5)
        assert sender.send("CAM-01", REGIONS) is False
    finally:
        session.release.set()
        sender.close()
    assert len(session.calls) == 1


def test_envio_seguinte_passa_depois_de_terminar():
    client, session = make_client(FakeResponse(200, '{"accepted": 1, "ignored": []}'))
    sender = AsyncIngest(client)
    assert sender.send("CAM-01", REGIONS) is True
    sender.close()
    assert sender.send("CAM-01", REGIONS) is True
    sender.close()
    assert len(session.calls) == 2
