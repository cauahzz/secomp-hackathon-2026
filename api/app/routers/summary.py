"""GET /summary — números agregados do campus."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.database import get_session
from app.models import Camera, CameraRegion, Space
from app.schemas import Summary
from app.services.occupancy import STATUS_NO_DATA, current_states, is_camera_online
from app.timeutil import utcnow

router = APIRouter(tags=["summary"])


@router.get("/summary", response_model=Summary)
def get_summary(session: Session = Depends(get_session)) -> Summary:
    now = utcnow()

    spaces = list(
        session.scalars(
            select(Space).options(selectinload(Space.regions).joinedload(CameraRegion.camera))
        )
    )
    states = current_states(session, spaces, now)

    counts = {"empty": 0, "normal": 0, "high": 0, "over_limit": 0, "no_data": 0}
    total_people = 0
    for state in states.values():
        counts[state.status] += 1
        # `no_data` não entra na soma: o número que existia já não vale.
        if state.status != STATUS_NO_DATA and state.person_count is not None:
            total_people += state.person_count

    cameras = list(session.scalars(select(Camera)))

    return Summary(
        total_people=total_people,
        spaces_total=len(spaces),
        **counts,
        cameras_online=sum(1 for camera in cameras if is_camera_online(camera, now)),
        cameras_total=len(cameras),
        generated_at=now,
    )
