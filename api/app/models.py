"""Modelos do banco.

Chaves primárias de campus, prédios, andares, ambientes, câmeras e ROIs são
strings vindas do seed — os mesmos IDs usados nos SVGs do frontend e nas ROIs da
visão. Só `occupancy_snapshots` usa inteiro autoincremental.

`occupancy_snapshots` não tem coluna de status: status é calculado na leitura
(ver `app/services/occupancy.py`).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.timeutil import utcnow


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )


class Campus(TimestampMixin, Base):
    __tablename__ = "campuses"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str | None] = mapped_column(String)

    buildings: Mapped[list["Building"]] = relationship(
        back_populates="campus", cascade="all, delete-orphan", order_by="Building.id"
    )
    cameras: Mapped[list["Camera"]] = relationship(
        back_populates="campus", cascade="all, delete-orphan", order_by="Camera.id"
    )


class Building(TimestampMixin, Base):
    __tablename__ = "buildings"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    campus_id: Mapped[str] = mapped_column(ForeignKey("campuses.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str | None] = mapped_column(String)

    campus: Mapped[Campus] = relationship(back_populates="buildings")
    floors: Mapped[list["Floor"]] = relationship(
        back_populates="building", cascade="all, delete-orphan", order_by="Floor.level"
    )


class Floor(TimestampMixin, Base):
    __tablename__ = "floors"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)

    building: Mapped[Building] = relationship(back_populates="floors")
    spaces: Mapped[list["Space"]] = relationship(
        back_populates="floor", cascade="all, delete-orphan", order_by="Space.id"
    )


class Space(TimestampMixin, Base):
    __tablename__ = "spaces"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    floor_id: Mapped[str] = mapped_column(ForeignKey("floors.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str | None] = mapped_column(String)
    type: Mapped[str | None] = mapped_column(String)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    operational_limit: Mapped[int | None] = mapped_column(Integer)
    # Reservado: no MVP o frontend usa os SVGs em public/maps/, não este campo.
    map_geometry: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    floor: Mapped[Floor] = relationship(back_populates="spaces")
    regions: Mapped[list["CameraRegion"]] = relationship(
        back_populates="space", cascade="all, delete-orphan", order_by="CameraRegion.id"
    )
    snapshots: Mapped[list["OccupancySnapshot"]] = relationship(
        back_populates="space", cascade="all, delete-orphan"
    )

    @property
    def effective_limit(self) -> int:
        return self.operational_limit if self.operational_limit is not None else self.capacity


class Camera(TimestampMixin, Base):
    __tablename__ = "cameras"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    campus_id: Mapped[str] = mapped_column(ForeignKey("campuses.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    source_type: Mapped[str | None] = mapped_column(String)
    source_uri: Mapped[str | None] = mapped_column(String)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    fps: Mapped[int | None] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Nulo até o primeiro ingest.
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime)

    campus: Mapped[Campus] = relationship(back_populates="cameras")
    regions: Mapped[list["CameraRegion"]] = relationship(
        back_populates="camera", cascade="all, delete-orphan", order_by="CameraRegion.id"
    )


class CameraRegion(TimestampMixin, Base):
    __tablename__ = "camera_regions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    camera_id: Mapped[str] = mapped_column(ForeignKey("cameras.id"), nullable=False)
    space_id: Mapped[str] = mapped_column(ForeignKey("spaces.id"), nullable=False)
    name: Mapped[str | None] = mapped_column(String)
    type: Mapped[str] = mapped_column(String, default="occupancy", nullable=False)
    shape: Mapped[str] = mapped_column(String, default="rectangle", nullable=False)
    geometry: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    camera: Mapped[Camera] = relationship(back_populates="regions")
    space: Mapped[Space] = relationship(back_populates="regions")


class OccupancySnapshot(Base):
    __tablename__ = "occupancy_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    space_id: Mapped[str] = mapped_column(ForeignKey("spaces.id"), nullable=False, index=True)
    camera_region_id: Mapped[str] = mapped_column(ForeignKey("camera_regions.id"), nullable=False)
    person_count: Mapped[int] = mapped_column(Integer, nullable=False)
    occupancy_rate: Mapped[float | None] = mapped_column(Float)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False, index=True)

    space: Mapped[Space] = relationship(back_populates="snapshots")
