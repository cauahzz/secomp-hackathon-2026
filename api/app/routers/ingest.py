"""POST /ingest — única porta de entrada do módulo de visão."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_session
from app.models import Camera, CameraRegion, OccupancySnapshot, Space
from app.schemas import IngestRequest, IngestResponse
from app.services.occupancy import compute_occupancy_rate
from app.timeutil import utcnow

router = APIRouter(tags=["ingest"])

logger = logging.getLogger("atlas.ingest")


@router.post("/ingest", response_model=IngestResponse)
def ingest(payload: IngestRequest, session: Session = Depends(get_session)) -> IngestResponse:
    camera = session.scalars(
        select(Camera)
        .where(Camera.id == payload.camera_id)
        .options(selectinload(Camera.regions).joinedload(CameraRegion.space))
    ).first()
    if camera is None:
        raise HTTPException(status_code=404, detail="camera not found")

    # Horário do servidor, sempre. O captured_at do corpo serve só para log —
    # assim o relógio da máquina da visão não contamina o cálculo de no_data.
    now = utcnow()
    if payload.captured_at is not None:
        logger.debug(
            "ingest de %s: captured_at do cliente %s, gravando com %s",
            camera.id,
            payload.captured_at,
            now,
        )

    camera.last_seen_at = now

    regions_by_id = {region.id: region for region in camera.regions}
    accepted = 0
    ignored: list[str] = []

    for entry in payload.regions:
        region = regions_by_id.get(entry.region_id)
        # ROI desconhecida, de outra câmera ou desabilitada não é erro: a visão
        # pode estar com um seed mais novo que o da API.
        if region is None or not region.enabled:
            ignored.append(entry.region_id)
            continue

        space: Space = region.space
        session.add(
            OccupancySnapshot(
                space_id=space.id,
                camera_region_id=region.id,
                person_count=entry.person_count,
                occupancy_rate=compute_occupancy_rate(entry.person_count, space.capacity),
                captured_at=now,
            )
        )
        accepted += 1

    session.commit()
    return IngestResponse(accepted=accepted, ignored=ignored)
