"""Fixtures dos testes.

As variáveis de ambiente são definidas antes de importar `app`: a engine é
criada na importação de `app.database`, então configurar depois não teria efeito.
"""

from __future__ import annotations

import os
import tempfile
from datetime import timedelta
from pathlib import Path

import pytest

API_DIR = Path(__file__).resolve().parent.parent
TEST_DB = Path(tempfile.gettempdir()) / "atlas-test.db"

os.environ["ATLAS_DB_PATH"] = str(TEST_DB)
os.environ["ATLAS_SEED_PATH"] = str(API_DIR / "seed.json")
os.environ["ATLAS_NO_DATA_SECONDS"] = "30"
os.environ["ATLAS_CORS_ORIGINS"] = "http://localhost:3000"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Camera  # noqa: E402
from app.seed import load_seed_file, populate  # noqa: E402
from app.timeutil import utcnow  # noqa: E402


@pytest.fixture
def client():
    """Banco limpo e populado pelo seed a cada teste."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        populate(session, load_seed_file())
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def age_camera():
    """Envelhece o `last_seen_at` de uma câmera, simulando ingest que parou."""

    def _age(camera_id: str, seconds: int) -> None:
        with SessionLocal() as db_session:
            camera = db_session.get(Camera, camera_id)
            camera.last_seen_at = utcnow() - timedelta(seconds=seconds)
            db_session.commit()

    return _age
