"""Configuração por variáveis de ambiente (ver README)."""

from __future__ import annotations

import os
from pathlib import Path

# Raiz do módulo de API. A spec chama esta pasta de `apps/api`; neste
# repositório ela é `api/`, e é aqui que mora o seed.json lido também pela visão.
BASE_DIR = Path(__file__).resolve().parent.parent


def _path_from_env(name: str, default: Path) -> Path:
    raw = os.getenv(name)
    if not raw:
        return default
    # Caminho relativo é resolvido a partir da raiz da API, não do cwd, para que
    # `uvicorn` e `python -m app.seed` apontem sempre para o mesmo arquivo.
    candidate = Path(raw).expanduser()
    return candidate if candidate.is_absolute() else (BASE_DIR / candidate).resolve()


class Settings:
    def __init__(self) -> None:
        self.db_path = _path_from_env("ATLAS_DB_PATH", BASE_DIR / "atlas.db")
        self.seed_path = _path_from_env("ATLAS_SEED_PATH", BASE_DIR / "seed.json")
        self.no_data_seconds = int(os.getenv("ATLAS_NO_DATA_SECONDS", "30"))
        self.cors_origins = [
            origin.strip()
            for origin in os.getenv("ATLAS_CORS_ORIGINS", "http://localhost:3000").split(",")
            if origin.strip()
        ]

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.db_path}"


settings = Settings()
