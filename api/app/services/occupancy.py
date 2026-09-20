"""Cálculo de ocupação e status.

Fonte única de verdade para status: todo endpoint que devolve `status` passa por
aqui. Status nunca é gravado no banco — um status gravado no ingest jamais
viraria `no_data`, porque `no_data` significa exatamente que o ingest parou.

Estado atual de um space = seu último snapshot. Não há tabela de estado atual.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.config import settings
from app.models import Camera, CameraRegion, OccupancySnapshot, Space
from app.timeutil import utcnow

HIGH_THRESHOLD = 0.7

STATUS_NO_DATA = "no_data"
STATUS_EMPTY = "empty"
STATUS_NORMAL = "normal"
STATUS_HIGH = "high"
STATUS_OVER_LIMIT = "over_limit"


@dataclass(frozen=True)
class OccupancyState:
    """Ocupação de um space no instante da leitura."""

    status: str
    person_count: int | None
    occupancy_rate: float | None
    captured_at: datetime | None
    region: CameraRegion | None
    camera: Camera | None

    @property
    def camera_online(self) -> bool:
        return is_camera_online(self.camera)


def compute_occupancy_rate(person_count: int, capacity: int | None) -> float | None:
    """Escala 0 a 1. Arredondado para manter o JSON legível (0.775, não 0.7750000001)."""
    if not capacity:
        return None
    return round(person_count / capacity, 4)


def is_camera_online(camera: Camera | None, now: datetime | None = None) -> bool:
    if camera is None or camera.last_seen_at is None:
        return False
    now = now or utcnow()
    return (now - camera.last_seen_at).total_seconds() <= settings.no_data_seconds


def latest_snapshots(session: Session, space_ids: list[str] | None = None) -> dict[str, OccupancySnapshot]:
    """Último snapshot de cada space, em uma única consulta.

    Último = maior `captured_at`, desempatando pelo maior `id` (inserções no
    mesmo segundo).
    """
    ranked = (
        select(
            OccupancySnapshot,
            func.row_number()
            .over(
                partition_by=OccupancySnapshot.space_id,
                order_by=(OccupancySnapshot.captured_at.desc(), OccupancySnapshot.id.desc()),
            )
            .label("rank"),
        )
        .subquery()
    )
    snapshot = aliased(OccupancySnapshot, ranked)
    query = select(snapshot).where(ranked.c.rank == 1)
    if space_ids is not None:
        if not space_ids:
            return {}
        query = query.where(ranked.c.space_id.in_(space_ids))
    return {row.space_id: row for row in session.scalars(query)}


def build_state(
    space: Space,
    snapshot: OccupancySnapshot | None,
    now: datetime | None = None,
) -> OccupancyState:
    """Aplica a tabela de status do contrato, na ordem."""
    now = now or utcnow()
    region = next((r for r in space.regions if r.enabled), None) or (
        space.regions[0] if space.regions else None
    )
    camera = region.camera if region is not None else None
    captured_at = snapshot.captured_at if snapshot is not None else None

    # ROI desabilitada deixa de alimentar o space, mas a câmera continua online
    # pelas outras ROIs. Sem esta condição o último número ficaria para sempre
    # como se fosse atual.
    feeding = region is not None and region.enabled

    if snapshot is None or not feeding or not is_camera_online(camera, now):
        # `captured_at` continua vindo, para o frontend saber de quando é o
        # silêncio; person_count e occupancy_rate somem para ninguém exibir
        # número velho como se fosse atual.
        return OccupancyState(STATUS_NO_DATA, None, None, captured_at, region, camera)

    person_count = snapshot.person_count
    if person_count == 0:
        status = STATUS_EMPTY
    else:
        effective_limit = space.effective_limit
        if person_count < HIGH_THRESHOLD * effective_limit:
            status = STATUS_NORMAL
        elif person_count <= effective_limit:
            status = STATUS_HIGH
        else:
            status = STATUS_OVER_LIMIT

    return OccupancyState(
        status, person_count, snapshot.occupancy_rate, captured_at, region, camera
    )


def current_state(session: Session, space: Space, now: datetime | None = None) -> OccupancyState:
    """Estado de um único space."""
    snapshot = session.scalars(
        select(OccupancySnapshot)
        .where(OccupancySnapshot.space_id == space.id)
        .order_by(OccupancySnapshot.captured_at.desc(), OccupancySnapshot.id.desc())
        .limit(1)
    ).first()
    return build_state(space, snapshot, now)


def current_states(session: Session, spaces: list[Space], now: datetime | None = None) -> dict[str, OccupancyState]:
    """Estado de vários spaces sem cair em N+1."""
    now = now or utcnow()
    snapshots = latest_snapshots(session, [space.id for space in spaces])
    return {space.id: build_state(space, snapshots.get(space.id), now) for space in spaces}
