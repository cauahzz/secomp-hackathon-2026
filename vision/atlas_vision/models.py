from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

STREAM_SCHEMES = ("rtsp://", "rtmp://", "tcp://", "udp://")
HTTP_SCHEMES = ("http://", "https://")


@dataclass(frozen=True)
class ROI:
    id: str
    space_id: str
    name: str
    geometry: dict[str, float]
    enabled: bool = True


@dataclass(frozen=True)
class Camera:
    id: str
    name: str
    source_type: str
    source_uri: str | int
    width: int
    height: int
    fps: float
    enabled: bool
    regions: tuple[ROI, ...]


class SeedError(ValueError):
    pass


def _require_str(obj: dict[str, Any], key: str, where: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value:
        raise SeedError(f"{where}: '{key}' deve ser uma string não vazia")
    return value


def _require_number(obj: dict[str, Any], key: str, where: str) -> float:
    value = obj.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SeedError(f"{where}: '{key}' deve ser numérico")
    return float(value)


def _require_positive_int(obj: dict[str, Any], key: str, where: str) -> int:
    value = _require_number(obj, key, where)
    if value <= 0:
        raise SeedError(f"{where}: '{key}' deve ser > 0")
    return int(value)


def load_seed(path: str) -> tuple[dict[str, dict[str, Any]], dict[str, Camera]]:
    seed_path = Path(path).expanduser().resolve()
    if not seed_path.exists():
        raise FileNotFoundError(f"Seed não encontrado: {seed_path}")
    data = json.loads(seed_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SeedError("seed.json deve conter um objeto JSON")

    spaces: dict[str, dict[str, Any]] = {}
    for building in data.get("buildings", []):
        for floor in building.get("floors", []):
            for space in floor.get("spaces", []):
                spaces[_require_str(space, "id", "ambiente")] = space

    cameras: dict[str, Camera] = {}
    # Só ROI habilitada reserva o space: se uma desligada também reservasse,
    # reenquadrar um ambiente exigiria apagar a ROI antiga em vez de desligá-la.
    claimed_spaces: dict[str, str] = {}
    seen_rois: set[str] = set()

    for raw in data.get("cameras", []):
        cid = _require_str(raw, "id", "câmera")
        if cid in cameras:
            raise SeedError(f"id de câmera repetido: {cid}")
        where = f"câmera {cid}"

        regions: list[ROI] = []
        for region in raw.get("regions", []):
            rid = _require_str(region, "id", f"{where}: região")
            if rid in seen_rois:
                raise SeedError(f"id de ROI repetido: {rid}")
            seen_rois.add(rid)
            sid = _require_str(region, "space_id", f"ROI {rid}")
            if sid not in spaces:
                raise SeedError(f"ROI {rid}: space_id desconhecido: {sid}")
            geometry = region.get("geometry")
            if not isinstance(geometry, dict):
                raise SeedError(f"ROI {rid}: geometry inválida")
            for gkey in ("x", "y", "width", "height"):
                _require_number(geometry, gkey, f"ROI {rid} geometry")
            enabled = bool(region.get("enabled", True))
            if enabled:
                previous = claimed_spaces.get(sid)
                if previous is not None:
                    raise SeedError(
                        f"space_id {sid} aparece em duas ROIs habilitadas: {previous} e {rid}"
                    )
                claimed_spaces[sid] = rid
            regions.append(
                ROI(
                    id=rid,
                    space_id=sid,
                    name=str(region.get("name", sid)),
                    geometry={k: float(geometry[k]) for k in ("x", "y", "width", "height")},
                    enabled=enabled,
                )
            )

        enabled_regions = tuple(r for r in regions if r.enabled)
        if enabled_regions:
            # width/height são a escala da geometry das ROIs. Sem eles não há
            # como converter para a resolução real do frame, e o erro precisa
            # aparecer aqui, não no primeiro frame processado.
            width = _require_positive_int(raw, "width", where)
            height = _require_positive_int(raw, "height", where)
        else:
            width = int(raw.get("width", 0) or 0)
            height = int(raw.get("height", 0) or 0)

        source_uri = raw.get("source_uri", "")
        if isinstance(source_uri, bool) or not isinstance(source_uri, (str, int)):
            raise SeedError(f"{where}: 'source_uri' deve ser string ou inteiro")

        cameras[cid] = Camera(
            id=cid,
            name=str(raw.get("name", cid)),
            source_type=str(raw.get("source_type", "file")),
            source_uri=source_uri,
            width=width,
            height=height,
            fps=float(raw.get("fps", 0) or 0),
            enabled=bool(raw.get("enabled", True)),
            regions=enabled_regions,
        )

    return spaces, cameras


def resolve_source(source: str | int, seed_path: str) -> str | int:
    if isinstance(source, int):
        return source
    value = str(source).strip()
    # Índice de webcam, e não um arquivo de nome numérico.
    if value.isdigit() and len(value) <= 2 and not Path(value).exists():
        return int(value)
    if value.lower().startswith(STREAM_SCHEMES + HTTP_SCHEMES):
        return value
    p = Path(value).expanduser()
    if p.is_absolute():
        return str(p)
    # Relativo: o cwd vem primeiro porque é o que o usuário digitou em --source;
    # a pasta do seed é o fallback para o source_uri declarado no próprio seed.
    if p.exists():
        return str(p.resolve())
    candidate = (Path(seed_path).expanduser().resolve().parent / p).resolve()
    if candidate.exists():
        return str(candidate)
    return str(p.resolve())
