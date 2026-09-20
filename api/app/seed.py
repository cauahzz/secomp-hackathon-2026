"""Carga do seed.json.

O mesmo arquivo é lido pela API (para popular o banco) e pela visão (para obter
as ROIs). Por isso a validação aborta com mensagem clara em vez de "corrigir"
silenciosamente: um seed inconsistente quebraria os dois lados.

Uso: python -m app.seed [--reset]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import Building, Camera, CameraRegion, Campus, Floor, Space


class SeedError(RuntimeError):
    """Seed inválido ou ausente."""


def load_seed_file(path: Path | None = None) -> dict[str, Any]:
    path = path or settings.seed_path
    if not path.exists():
        raise SeedError(f"seed não encontrado em {path} (ajuste ATLAS_SEED_PATH)")
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise SeedError(f"seed inválido em {path}: {exc}") from exc
    validate_seed(data, path)
    return data


def validate_seed(data: dict[str, Any], path: Path) -> None:
    where = f"seed {path}"

    campus = data.get("campus")
    if not isinstance(campus, dict) or not campus.get("id"):
        raise SeedError(f"{where}: bloco 'campus' ausente ou sem 'id'")

    space_ids: set[str] = set()
    for building in data.get("buildings", []):
        _require_id(building, "building", where)
        for floor in building.get("floors", []):
            _require_id(floor, "floor", where)
            if floor.get("level") is None:
                raise SeedError(f"{where}: andar {floor['id']} sem 'level'")
            for space in floor.get("spaces", []):
                _require_id(space, "space", where)
                if space["id"] in space_ids:
                    raise SeedError(f"{where}: space {space['id']} declarado mais de uma vez")
                if space.get("capacity") is None:
                    raise SeedError(f"{where}: space {space['id']} sem 'capacity'")
                space_ids.add(space["id"])

    if not space_ids:
        raise SeedError(f"{where}: nenhum ambiente declarado")

    # Regras do contrato: toda ROI aponta para um space existente e cada space
    # aparece em no máximo uma ROI.
    space_to_region: dict[str, str] = {}
    camera_ids: set[str] = set()
    region_ids: set[str] = set()
    for camera in data.get("cameras", []):
        _require_id(camera, "camera", where)
        if camera["id"] in camera_ids:
            raise SeedError(f"{where}: câmera {camera['id']} declarada mais de uma vez")
        camera_ids.add(camera["id"])
        for region in camera.get("regions", []):
            _require_id(region, "region", where)
            if region["id"] in region_ids:
                raise SeedError(f"{where}: ROI {region['id']} declarada mais de uma vez")
            region_ids.add(region["id"])

            space_id = region.get("space_id")
            if space_id not in space_ids:
                raise SeedError(
                    f"{where}: ROI {region['id']} aponta para space inexistente {space_id!r}"
                )
            if space_id in space_to_region:
                raise SeedError(
                    f"{where}: space {space_id} está em duas ROIs "
                    f"({space_to_region[space_id]} e {region['id']}); o MVP permite uma só"
                )
            space_to_region[space_id] = region["id"]

            if not isinstance(region.get("geometry"), dict):
                raise SeedError(f"{where}: ROI {region['id']} sem 'geometry'")


def _require_id(item: Any, kind: str, where: str) -> None:
    if not isinstance(item, dict) or not item.get("id"):
        raise SeedError(f"{where}: {kind} sem 'id'")


def is_database_empty(session: Session) -> bool:
    return session.scalars(select(Campus.id).limit(1)).first() is None


def populate(session: Session, data: dict[str, Any]) -> None:
    """Insere a estrutura do seed em um banco vazio."""
    campus_data = data["campus"]
    campus = Campus(id=campus_data["id"], name=campus_data["name"], code=campus_data.get("code"))
    session.add(campus)

    for building_data in data.get("buildings", []):
        building = Building(
            id=building_data["id"],
            campus_id=campus.id,
            name=building_data["name"],
            code=building_data.get("code"),
        )
        session.add(building)
        for floor_data in building_data.get("floors", []):
            floor = Floor(
                id=floor_data["id"],
                building_id=building.id,
                name=floor_data["name"],
                level=floor_data["level"],
            )
            session.add(floor)
            for space_data in floor_data.get("spaces", []):
                session.add(
                    Space(
                        id=space_data["id"],
                        floor_id=floor.id,
                        name=space_data["name"],
                        code=space_data.get("code"),
                        type=space_data.get("type"),
                        capacity=space_data["capacity"],
                        operational_limit=space_data.get("operational_limit"),
                        map_geometry=space_data.get("map_geometry"),
                    )
                )

    # Os spaces precisam existir antes das ROIs que os referenciam.
    session.flush()

    for camera_data in data.get("cameras", []):
        camera = Camera(
            id=camera_data["id"],
            campus_id=campus.id,
            name=camera_data["name"],
            source_type=camera_data.get("source_type"),
            source_uri=camera_data.get("source_uri"),
            width=camera_data.get("width"),
            height=camera_data.get("height"),
            fps=camera_data.get("fps"),
            enabled=camera_data.get("enabled", True),
        )
        session.add(camera)
        for region_data in camera_data.get("regions", []):
            session.add(
                CameraRegion(
                    id=region_data["id"],
                    camera_id=camera.id,
                    space_id=region_data["space_id"],
                    name=region_data.get("name"),
                    type=region_data.get("type", "occupancy"),
                    shape=region_data.get("shape", "rectangle"),
                    geometry=region_data["geometry"],
                    enabled=region_data.get("enabled", True),
                )
            )

    session.commit()


def seed_if_empty(session: Session) -> bool:
    """Chamado na inicialização da API. Devolve True se carregou."""
    if not is_database_empty(session):
        return False
    populate(session, load_seed_file())
    return True


def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.seed", description="Carrega o seed do ATLAS."
    )
    parser.add_argument(
        "--reset", action="store_true", help="apaga o banco e recria tudo a partir do seed"
    )
    args = parser.parse_args(argv)

    try:
        data = load_seed_file()
    except SeedError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1

    if args.reset:
        reset_database()
    else:
        Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        if not is_database_empty(session):
            print("banco já populado; use --reset para recriar do zero")
            return 0
        populate(session, data)

    print(f"seed carregado de {settings.seed_path} em {settings.db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
