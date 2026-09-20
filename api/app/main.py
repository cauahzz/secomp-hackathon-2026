"""Aplicação FastAPI do ATLAS.

Rodar com: uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.routers import health, ingest, spaces, structure, summary
from app.seed import seed_if_empty

logger = logging.getLogger("atlas")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        # Seed inválido derruba a API de propósito: subir com estrutura pela
        # metade esconderia o erro até a demo.
        if seed_if_empty(session):
            logger.info("banco vazio: seed carregado de %s", settings.seed_path)
    yield


app = FastAPI(title="ATLAS API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(structure.router)
app.include_router(spaces.router)
app.include_router(summary.router)
app.include_router(ingest.router)
