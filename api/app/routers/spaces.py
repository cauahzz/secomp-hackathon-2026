"""GET /spaces, /spaces/{id}, /spaces/{id}/occupancy, /spaces/{id}/history."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.database import get_session
from app.models import CameraRegion, Floor, OccupancySnapshot, Space
from app.schemas import (
    BuildingRef,
    FloorRef,
    History,
    HistoryPoint,
    Occupancy,
    OccupancySource,
    SpaceDetail,
    SpaceOut,
    SpaceSource,
)
from app.services.occupancy import OccupancyState, current_state, current_states
from app.timeutil import utcnow

router = APIRouter(tags=["spaces"])

HISTORY_MAX_POINTS = 500

# Andar/prédio e ROI/câmera vêm junto: sem isso cada space dispararia consultas
# extras ao montar a resposta.
SPACE_LOADERS = (
    joinedload(Space.floor).joinedload(Floor.building),
    selectinload(Space.regions).joinedload(CameraRegion.camera),
)


def load_space(session: Session, space_id: str) -> Space:
    space = session.scalars(
        select(Space).where(Space.id == space_id).options(*SPACE_LOADERS)
    ).first()
    if space is None:
        raise HTTPException(status_code=404, detail="space not found")
    return space


def space_fields(space: Space, state: OccupancyState) -> dict:
    return {
        "id": space.id,
        "name": space.name,
        "code": space.code,
        "type": space.type,
        "building": BuildingRef(id=space.floor.building.id, name=space.floor.building.name),
        "floor": FloorRef(id=space.floor.id, name=space.floor.name, level=space.floor.level),
        "capacity": space.capacity,
        "operational_limit": space.operational_limit,
        "person_count": state.person_count,
        "occupancy_rate": state.occupancy_rate,
        "status": state.status,
        "captured_at": state.captured_at,
    }


def space_source(state: OccupancyState) -> SpaceSource | None:
    if state.region is None or state.camera is None:
        return None
    return SpaceSource(
        camera_id=state.camera.id,
        camera_name=state.camera.name,
        region_id=state.region.id,
        online=state.camera_online,
        last_seen_at=state.camera.last_seen_at,
    )


@router.get("/spaces", response_model=list[SpaceOut])
def list_spaces(session: Session = Depends(get_session)) -> list[SpaceOut]:
    spaces = list(session.scalars(select(Space).options(*SPACE_LOADERS).order_by(Space.id)))
    states = current_states(session, spaces)
    return [SpaceOut(**space_fields(space, states[space.id])) for space in spaces]


@router.get("/spaces/{space_id}", response_model=SpaceDetail)
def get_space(space_id: str, session: Session = Depends(get_session)) -> SpaceDetail:
    space = load_space(session, space_id)
    state = current_state(session, space)
    return SpaceDetail(**space_fields(space, state), source=space_source(state))


@router.get("/spaces/{space_id}/occupancy", response_model=Occupancy)
def get_space_occupancy(space_id: str, session: Session = Depends(get_session)) -> Occupancy:
    space = load_space(session, space_id)
    state = current_state(session, space)
    source = None
    if state.camera is not None:
        source = OccupancySource(
            camera_id=state.camera.id,
            online=state.camera_online,
            last_seen_at=state.camera.last_seen_at,
        )
    return Occupancy(
        space_id=space.id,
        person_count=state.person_count,
        occupancy_rate=state.occupancy_rate,
        status=state.status,
        captured_at=state.captured_at,
        source=source,
    )


@router.get("/spaces/{space_id}/history", response_model=History)
def get_space_history(
    space_id: str,
    minutes: int = Query(default=30, ge=1),
    session: Session = Depends(get_session),
) -> History:
    space = load_space(session, space_id)
    since = utcnow() - timedelta(minutes=minutes)

    # Busca os mais recentes e inverte: havendo mais de 500 pontos na janela, o
    # contrato manda devolver os últimos, não os primeiros.
    recent = list(
        session.scalars(
            select(OccupancySnapshot)
            .where(OccupancySnapshot.space_id == space.id, OccupancySnapshot.captured_at >= since)
            .order_by(OccupancySnapshot.captured_at.desc(), OccupancySnapshot.id.desc())
            .limit(HISTORY_MAX_POINTS)
        )
    )
    points = [
        HistoryPoint(
            captured_at=snapshot.captured_at,
            person_count=snapshot.person_count,
            occupancy_rate=snapshot.occupancy_rate,
        )
        for snapshot in reversed(recent)
    ]
    return History(space_id=space.id, points=points)
