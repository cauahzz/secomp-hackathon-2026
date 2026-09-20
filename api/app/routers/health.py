"""GET /health."""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas import Health

router = APIRouter(tags=["health"])


@router.get("/health", response_model=Health)
def health() -> Health:
    return Health(status="ok")
