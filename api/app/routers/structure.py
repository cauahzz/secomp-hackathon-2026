"""GET /structure — árvore do campus para a navegação do frontend."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_session
from app.models import Building, Campus, Floor
from app.schemas import (
    CampusRef,
    Structure,
    StructureBuilding,
    StructureFloor,
    StructureSpace,
)

router = APIRouter(tags=["structure"])


@router.get("/structure", response_model=Structure)
def get_structure(session: Session = Depends(get_session)) -> Structure:
    campus = session.scalars(
        select(Campus)
        .options(
            selectinload(Campus.buildings)
            .selectinload(Building.floors)
            .selectinload(Floor.spaces)
        )
        .order_by(Campus.id)
        .limit(1)
    ).first()
    if campus is None:
        raise HTTPException(status_code=404, detail="campus not found")

    return Structure(
        campus=CampusRef(id=campus.id, name=campus.name),
        buildings=[
            StructureBuilding(
                id=building.id,
                name=building.name,
                code=building.code,
                floors=[
                    StructureFloor(
                        id=floor.id,
                        name=floor.name,
                        level=floor.level,
                        spaces=[
                            StructureSpace(
                                id=space.id, name=space.name, code=space.code, type=space.type
                            )
                            for space in floor.spaces
                        ],
                    )
                    for floor in building.floors
                ],
            )
            for building in campus.buildings
        ],
    )
