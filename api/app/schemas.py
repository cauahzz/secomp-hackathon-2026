"""Schemas de request/response — espelham exatamente os exemplos do contrato."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, PlainSerializer

from app.timeutil import to_iso_z

Timestamp = Annotated[datetime, PlainSerializer(to_iso_z, return_type=str)]
OptionalTimestamp = Annotated[
    datetime | None,
    PlainSerializer(lambda v: to_iso_z(v) if v is not None else None, return_type=str | None),
]


class Health(BaseModel):
    status: str


# --- GET /structure ---------------------------------------------------------


class CampusRef(BaseModel):
    id: str
    name: str


class StructureSpace(BaseModel):
    id: str
    name: str
    code: str | None
    type: str | None


class StructureFloor(BaseModel):
    id: str
    name: str
    level: int
    spaces: list[StructureSpace]


class StructureBuilding(BaseModel):
    id: str
    name: str
    code: str | None
    floors: list[StructureFloor]


class Structure(BaseModel):
    campus: CampusRef
    buildings: list[StructureBuilding]


# --- GET /spaces ------------------------------------------------------------


class BuildingRef(BaseModel):
    id: str
    name: str


class FloorRef(BaseModel):
    id: str
    name: str
    level: int


class SpaceSource(BaseModel):
    camera_id: str
    camera_name: str
    region_id: str
    online: bool
    last_seen_at: OptionalTimestamp


class SpaceOut(BaseModel):
    id: str
    name: str
    code: str | None
    type: str | None
    building: BuildingRef
    floor: FloorRef
    capacity: int
    operational_limit: int | None
    person_count: int | None
    occupancy_rate: float | None
    status: str
    captured_at: OptionalTimestamp


class SpaceDetail(SpaceOut):
    source: SpaceSource | None


# --- GET /spaces/{id}/occupancy ---------------------------------------------


class OccupancySource(BaseModel):
    camera_id: str
    online: bool
    last_seen_at: OptionalTimestamp


class Occupancy(BaseModel):
    space_id: str
    person_count: int | None
    occupancy_rate: float | None
    status: str
    captured_at: OptionalTimestamp
    source: OccupancySource | None


# --- GET /spaces/{id}/history -----------------------------------------------


class HistoryPoint(BaseModel):
    captured_at: Timestamp
    person_count: int
    occupancy_rate: float | None


class History(BaseModel):
    space_id: str
    points: list[HistoryPoint]


# --- GET /summary -----------------------------------------------------------


class Summary(BaseModel):
    total_people: int
    spaces_total: int
    empty: int
    normal: int
    high: int
    over_limit: int
    no_data: int
    cameras_online: int
    cameras_total: int
    generated_at: Timestamp


# --- POST /ingest -----------------------------------------------------------


class IngestRegion(BaseModel):
    region_id: str
    person_count: int = Field(ge=0)


class IngestRequest(BaseModel):
    camera_id: str
    # Só para log: a API usa sempre o horário do próprio servidor.
    captured_at: datetime | None = None
    regions: list[IngestRegion]


class IngestResponse(BaseModel):
    accepted: int
    ignored: list[str]
