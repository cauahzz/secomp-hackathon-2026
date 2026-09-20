"""Tempo do servidor e serialização ISO 8601 UTC.

O banco guarda datetimes *naive* já em UTC: o SQLite descarta o fuso na
gravação, então normalizar na entrada evita comparar aware com naive na leitura.
"""

from __future__ import annotations

from datetime import datetime, timezone

ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def utcnow() -> datetime:
    """Horário atual do servidor, em UTC e naive."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def as_utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def to_iso_z(value: datetime) -> str:
    return as_utc_naive(value).strftime(ISO_FORMAT)
