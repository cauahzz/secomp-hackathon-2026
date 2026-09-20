"""Testes da carga e da validação do seed."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import Camera, CameraRegion, Campus, Space
from app.seed import SeedError, is_database_empty, load_seed_file, main, seed_if_empty, validate_seed


@pytest.fixture
def seed_data() -> dict:
    return copy.deepcopy(load_seed_file())


def write_seed(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "seed.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def test_seed_file_is_valid():
    data = load_seed_file()
    assert data["campus"]["id"] == "unifei-itabira"


def test_seed_populates_structure():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        assert is_database_empty(session) is True
        assert seed_if_empty(session) is True

    with SessionLocal() as session:
        assert session.get(Campus, "unifei-itabira") is not None
        assert session.get(Space, "room-101").capacity == 40
        assert session.get(Space, "room-101").operational_limit == 35
        assert session.get(Camera, "CAM-01").last_seen_at is None
        region = session.get(CameraRegion, "ROI-02")
        assert region.space_id == "room-102"
        assert region.geometry == {"x": 640, "y": 0, "width": 640, "height": 720}


def test_seed_is_not_reapplied_to_a_populated_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        assert seed_if_empty(session) is True
    with SessionLocal() as session:
        assert seed_if_empty(session) is False


def test_missing_seed_file_has_a_clear_message(tmp_path):
    with pytest.raises(SeedError, match="seed não encontrado"):
        load_seed_file(tmp_path / "ausente.json")


def test_invalid_json_has_a_clear_message(tmp_path):
    path = tmp_path / "seed.json"
    path.write_text("{nao é json}", encoding="utf-8")
    with pytest.raises(SeedError, match="seed inválido"):
        load_seed_file(path)


def test_roi_pointing_to_unknown_space_is_rejected(tmp_path, seed_data):
    seed_data["cameras"][0]["regions"][0]["space_id"] = "room-999"
    with pytest.raises(SeedError, match="space inexistente"):
        validate_seed(seed_data, write_seed(tmp_path, seed_data))


def test_space_in_two_rois_is_rejected(tmp_path, seed_data):
    seed_data["cameras"][0]["regions"][1]["space_id"] = "room-101"
    with pytest.raises(SeedError, match="duas ROIs"):
        validate_seed(seed_data, write_seed(tmp_path, seed_data))


def test_duplicate_space_id_is_rejected(tmp_path, seed_data):
    spaces = seed_data["buildings"][0]["floors"][0]["spaces"]
    spaces.append(copy.deepcopy(spaces[0]))
    with pytest.raises(SeedError, match="mais de uma vez"):
        validate_seed(seed_data, write_seed(tmp_path, seed_data))


def test_space_without_capacity_is_rejected(tmp_path, seed_data):
    del seed_data["buildings"][0]["floors"][0]["spaces"][0]["capacity"]
    with pytest.raises(SeedError, match="sem 'capacity'"):
        validate_seed(seed_data, write_seed(tmp_path, seed_data))


def test_seed_cli_reset_recreates_the_database(capsys):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        seed_if_empty(session)

    # Sujeira que o --reset precisa apagar.
    with SessionLocal() as session:
        session.get(Camera, "CAM-01").name = "renomeada"
        session.commit()

    assert main(["--reset"]) == 0
    assert "seed carregado" in capsys.readouterr().out

    with SessionLocal() as session:
        assert session.get(Camera, "CAM-01").name == "Câmera 1"


def test_seed_cli_without_reset_keeps_existing_data(capsys):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        seed_if_empty(session)

    assert main([]) == 0
    assert "já populado" in capsys.readouterr().out


def test_seed_cli_reports_a_broken_seed(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(settings, "seed_path", tmp_path / "ausente.json")
    assert main([]) == 1
    assert "erro:" in capsys.readouterr().err
