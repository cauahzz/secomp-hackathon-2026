import copy
import json

import pytest

from atlas_vision.models import SeedError, load_seed, resolve_source

BASE = {
    "campus": {"id": "unifei-itabira", "name": "UNIFEI", "code": "ITA"},
    "buildings": [
        {
            "id": "bld-1",
            "name": "Prédio 1",
            "code": "P1",
            "floors": [
                {
                    "id": "bld-1-f2",
                    "name": "2º andar",
                    "level": 2,
                    "spaces": [
                        {"id": "room-101", "name": "Sala 101", "capacity": 40, "operational_limit": 35},
                        {"id": "room-102", "name": "Sala 102", "capacity": 40, "operational_limit": 35},
                    ],
                }
            ],
        }
    ],
    "cameras": [
        {
            "id": "CAM-01",
            "name": "Câmera 1",
            "source_type": "file",
            "source_uri": "data/demo.mp4",
            "width": 1280,
            "height": 720,
            "fps": 30,
            "enabled": True,
            "regions": [
                {
                    "id": "ROI-01",
                    "space_id": "room-101",
                    "name": "Sala 101",
                    "geometry": {"x": 0, "y": 0, "width": 640, "height": 720},
                    "enabled": True,
                }
            ],
        }
    ],
}


def write_seed(tmp_path, mutate=None):
    data = copy.deepcopy(BASE)
    if mutate is not None:
        mutate(data)
    path = tmp_path / "seed.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def test_carrega_seed_valido(tmp_path):
    spaces, cameras = load_seed(write_seed(tmp_path))
    assert set(spaces) == {"room-101", "room-102"}
    camera = cameras["CAM-01"]
    assert camera.width == 1280 and camera.height == 720
    assert [r.id for r in camera.regions] == ["ROI-01"]


def test_roi_desabilitada_fica_fora(tmp_path):
    def mutate(data):
        data["cameras"][0]["regions"][0]["enabled"] = False

    _, cameras = load_seed(write_seed(tmp_path, mutate))
    assert cameras["CAM-01"].regions == ()


def test_roi_desabilitada_nao_reserva_o_space(tmp_path):
    """Reenquadrar um ambiente é desligar a ROI antiga e criar outra."""

    def mutate(data):
        regions = data["cameras"][0]["regions"]
        regions[0]["enabled"] = False
        regions.append(dict(regions[0], id="ROI-03", enabled=True))

    _, cameras = load_seed(write_seed(tmp_path, mutate))
    assert [r.id for r in cameras["CAM-01"].regions] == ["ROI-03"]


def test_duas_rois_habilitadas_no_mesmo_space_falham(tmp_path):
    def mutate(data):
        regions = data["cameras"][0]["regions"]
        regions.append(dict(regions[0], id="ROI-03"))

    with pytest.raises(SeedError, match="duas ROIs habilitadas"):
        load_seed(write_seed(tmp_path, mutate))


def test_width_e_height_sao_obrigatorios(tmp_path):
    """A geometry está em pixels dessa resolução: o erro tem de sair no load."""

    def mutate(data):
        del data["cameras"][0]["width"]

    with pytest.raises(SeedError, match="'width'"):
        load_seed(write_seed(tmp_path, mutate))


def test_width_zero_falha(tmp_path):
    def mutate(data):
        data["cameras"][0]["width"] = 0

    with pytest.raises(SeedError, match="deve ser > 0"):
        load_seed(write_seed(tmp_path, mutate))


def test_camera_sem_roi_habilitada_dispensa_resolucao(tmp_path):
    def mutate(data):
        data["cameras"][0]["regions"] = []
        del data["cameras"][0]["width"]

    _, cameras = load_seed(write_seed(tmp_path, mutate))
    assert cameras["CAM-01"].regions == ()


def test_id_de_camera_repetido_falha(tmp_path):
    def mutate(data):
        clone = copy.deepcopy(data["cameras"][0])
        clone["regions"] = []
        data["cameras"].append(clone)

    with pytest.raises(SeedError, match="id de câmera repetido"):
        load_seed(write_seed(tmp_path, mutate))


def test_id_de_roi_repetido_falha(tmp_path):
    def mutate(data):
        clone = copy.deepcopy(data["cameras"][0])
        clone["id"] = "CAM-02"
        clone["regions"][0]["space_id"] = "room-102"
        data["cameras"].append(clone)

    with pytest.raises(SeedError, match="id de ROI repetido"):
        load_seed(write_seed(tmp_path, mutate))


def test_space_id_desconhecido_falha(tmp_path):
    def mutate(data):
        data["cameras"][0]["regions"][0]["space_id"] = "room-999"

    with pytest.raises(SeedError, match="space_id desconhecido"):
        load_seed(write_seed(tmp_path, mutate))


def test_seed_inexistente(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_seed(str(tmp_path / "nao-existe.json"))


def test_resolve_source_indice_de_webcam(tmp_path, monkeypatch):
    seed = write_seed(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert resolve_source("0", seed) == 0
    assert resolve_source(2, seed) == 2


def test_resolve_source_arquivo_de_nome_numerico_nao_e_webcam(tmp_path, monkeypatch):
    seed = write_seed(tmp_path)
    (tmp_path / "12").write_bytes(b"")
    monkeypatch.chdir(tmp_path)
    assert resolve_source("12", seed) == str((tmp_path / "12").resolve())


def test_resolve_source_stream(tmp_path):
    seed = write_seed(tmp_path)
    assert resolve_source("rtsp://host/stream", seed) == "rtsp://host/stream"
    assert resolve_source("http://host/video.mp4", seed) == "http://host/video.mp4"


def test_resolve_source_relativo_ao_seed(tmp_path, monkeypatch):
    """O source_uri do seed vale quando o cwd não tem o arquivo."""
    seed_dir = tmp_path / "api"
    seed_dir.mkdir()
    seed = write_seed(seed_dir)
    video = seed_dir / "data" / "demo.mp4"
    video.parent.mkdir()
    video.write_bytes(b"")
    cwd_vazio = tmp_path / "vision"
    cwd_vazio.mkdir()
    monkeypatch.chdir(cwd_vazio)
    assert resolve_source("data/demo.mp4", seed) == str(video.resolve())


def test_resolve_source_prefere_o_cwd(tmp_path, monkeypatch):
    """--source é digitado pelo usuário: vale o cwd antes da pasta do seed."""
    seed_dir = tmp_path / "api"
    seed_dir.mkdir()
    seed = write_seed(seed_dir)
    for base in (seed_dir, tmp_path):
        (base / "data").mkdir(exist_ok=True)
        (base / "data" / "demo.mp4").write_bytes(b"")
    monkeypatch.chdir(tmp_path)
    assert resolve_source("data/demo.mp4", seed) == str((tmp_path / "data" / "demo.mp4").resolve())
