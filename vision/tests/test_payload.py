from atlas_vision.app import _capacity_map, _regions_payload
from atlas_vision.models import ROI, Camera

CAMERA = Camera(
    "CAM-01", "Câmera 1", "file", "data/demo.mp4", 1280, 720, 30, True,
    (
        ROI("ROI-01", "room-101", "Sala 101", {"x": 0, "y": 0, "width": 640, "height": 720}),
        ROI("ROI-02", "room-102", "Sala 102", {"x": 640, "y": 0, "width": 640, "height": 720}),
    ),
)


def test_payload_no_formato_do_contrato():
    assert _regions_payload(CAMERA, {"ROI-01": 12, "ROI-02": 3}) == [
        {"region_id": "ROI-01", "person_count": 12},
        {"region_id": "ROI-02", "person_count": 3},
    ]


def test_toda_roi_da_camera_entra_na_requisicao():
    """Uma requisição por câmera contendo todas as ROIs dela."""
    payload = _regions_payload(CAMERA, {"ROI-01": 5})
    assert [r["region_id"] for r in payload] == ["ROI-01", "ROI-02"]
    assert payload[1]["person_count"] == 0


def test_contagem_negativa_nunca_sai():
    """person_count negativo é 422 na API."""
    assert _regions_payload(CAMERA, {"ROI-01": -3})[0]["person_count"] == 0


def test_capacidade_por_roi():
    spaces = {"room-101": {"capacity": 40}, "room-102": {}}
    assert _capacity_map(spaces, CAMERA) == {"ROI-01": 40, "ROI-02": 0}
