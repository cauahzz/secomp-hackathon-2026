from __future__ import annotations

import argparse
import json
import logging
import time
from typing import Any

import cv2

from .api_client import AsyncIngest, AtlasClient
from .detector import DEFAULT_CONF, DEFAULT_MODEL, Detection, PersonDetector
from .fake import FakeCounter
from .models import Camera, SeedError, load_seed, resolve_source
from .roi import assign_detections_to_rois, scale_roi
from .smoothing import MedianSmoother
from .source import OpenCVSource, frame_sampling_step
from .visualization import draw_frame, poll_quit_key

LOGGER = logging.getLogger("atlas_vision")

INGEST_TIMEOUT = 2.0
SOURCE_WARNING_INTERVAL = 2.0
FALLBACK_FPS = 30.0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="ATLAS — agente de visão computacional")
    p.add_argument("--api-url", default="http://localhost:8000")
    p.add_argument("--seed", default="../api/seed.json")
    p.add_argument("--camera-id", default="CAM-01")
    p.add_argument("--source", default=None, help="arquivo, índice de webcam ou URL de stream")
    p.add_argument("--process-fps", type=float, default=3.0)
    p.add_argument("--window", type=float, default=7.0)
    p.add_argument("--send-interval", type=float, default=5.0)
    p.add_argument("--conf", type=float, default=DEFAULT_CONF)
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--no-window", action="store_true")
    p.add_argument("--fake", action="store_true")
    p.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    p.add_argument("--fake-seed", type=int, default=42)
    return p


def _capacity_map(spaces: dict[str, Any], camera: Camera) -> dict[str, int]:
    return {roi.id: int(spaces[roi.space_id].get("capacity") or 0) for roi in camera.regions}


def _regions_payload(camera: Camera, counts: dict[str, int]) -> list[dict[str, Any]]:
    return [
        {"region_id": roi.id, "person_count": max(0, int(counts.get(roi.id, 0)))}
        for roi in camera.regions
    ]


def _pump_window(frame, scaled_rois, detections, smoothed) -> tuple[bool, bool]:
    """Devolve (usuário pediu para sair, janela ainda disponível).

    Com frame None só lê o teclado: mesmo sem frame a tecla de saída precisa
    responder, senão a janela trava enquanto a fonte estiver fora.
    """
    try:
        if frame is not None:
            draw_frame(frame, scaled_rois, detections, smoothed)
        return poll_quit_key(), True
    except cv2.error as exc:
        LOGGER.warning("Janela OpenCV indisponível; seguindo sem visualização: %s", exc)
        return False, False


def _run_fake(
    args: argparse.Namespace, camera: Camera, spaces: dict[str, Any], sender: AsyncIngest
) -> None:
    fake = FakeCounter(_capacity_map(spaces, camera), seed=args.fake_seed)
    LOGGER.info("Modo --fake ativo")
    last_send = 0.0
    while True:
        now = time.monotonic()
        if now - last_send >= args.send_interval:
            # A caminhada do fake já é suave por construção. Passá-la pelo
            # suavizador só achataria a variação que a demo precisa mostrar.
            sender.send(camera.id, _regions_payload(camera, fake.next()))
            last_send = now
        time.sleep(min(0.1, args.send_interval / 10))


def _run_real(args: argparse.Namespace, camera: Camera, sender: AsyncIngest) -> None:
    detector = PersonDetector(args.model, args.conf)
    source = resolve_source(args.source if args.source is not None else camera.source_uri, args.seed)
    cap = OpenCVSource(source, camera.source_type)
    LOGGER.info("Fonte: %s | tipo=%s | live=%s", source, camera.source_type, cap.live)

    smoother = MedianSmoother(args.window)
    latest_smoothed: dict[str, int] = {}
    # Mantidas entre frames processados: sem isso as caixas apareceriam em 1 de
    # cada sample_every frames exibidos e piscariam na janela do pitch.
    drawn_detections: list[Detection] = []
    window_enabled = not args.no_window
    process_period = 1.0 / args.process_fps
    next_process = 0.0
    video_fps: float | None = None
    sample_every = 1
    frame_period = 0.0
    next_frame_deadline = time.monotonic()
    frame_number = 0
    last_warning = 0.0
    last_send = 0.0

    try:
        while True:
            frame_started = time.monotonic()
            ok, frame = cap.read()
            if not ok:
                if frame_started - last_warning > SOURCE_WARNING_INTERVAL:
                    LOGGER.warning("Sem frame disponível; processo continua")
                    last_warning = frame_started
                if window_enabled:
                    quit_requested, window_enabled = _pump_window(None, [], [], {})
                    if quit_requested:
                        break
                continue

            if video_fps is None:
                # O fps do seed é o declarado; o que importa para a amostragem e
                # para o ritmo é o do arquivo que o OpenCV realmente abriu.
                video_fps = cap.fps(fallback=float(camera.fps or FALLBACK_FPS))
                sample_every = 1 if cap.live else frame_sampling_step(video_fps, args.process_fps)
                frame_period = 0.0 if cap.live else 1.0 / video_fps
                next_frame_deadline = time.monotonic()
                LOGGER.info(
                    "fps da fonte: %.2f | processando 1 a cada %d frame(s)", video_fps, sample_every
                )

            frame_number += 1
            now = time.monotonic()
            if cap.live:
                should_process = now >= next_process
            else:
                should_process = (frame_number - 1) % sample_every == 0
            scaled_rois = [
                scale_roi(r, frame.shape[1], frame.shape[0], camera.width, camera.height)
                for r in camera.regions
            ]

            if should_process:
                if cap.live:
                    next_process = now + process_period
                detections = detector.detect(frame)
                counts = assign_detections_to_rois([d.box for d in detections], scaled_rois)
                for rid, count in counts.items():
                    smoother.add(rid, count, now)
                latest_smoothed = smoother.values(now)
                drawn_detections = detections

            if now - last_send >= args.send_interval and latest_smoothed:
                sender.send(camera.id, _regions_payload(camera, latest_smoothed))
                last_send = now

            if window_enabled:
                quit_requested, window_enabled = _pump_window(
                    frame, scaled_rois, drawn_detections, latest_smoothed
                )
                if quit_requested:
                    break

            # Para arquivos, o vídeo tem de avançar em velocidade real: adiantado,
            # espera; atrasado, descarta frames sem decodificar. Sem o descarte a
            # reprodução vira slow motion assim que a máquina não acompanha, e a
            # contagem deixa de corresponder ao que está na tela.
            if frame_period > 0:
                next_frame_deadline += frame_period
                now = time.monotonic()
                late = now - next_frame_deadline
                if late <= 0:
                    time.sleep(-late)
                elif late > frame_period:
                    skipped = cap.skip(min(int(late / frame_period), sample_every))
                    frame_number += skipped
                    next_frame_deadline = max(
                        next_frame_deadline + skipped * frame_period, now
                    )
    finally:
        cap.release()
        try:
            cv2.destroyAllWindows()
        except cv2.error:
            pass


def run(args: argparse.Namespace) -> int:
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if args.process_fps <= 0 or args.send_interval <= 0 or args.window <= 0:
        raise SystemExit("--process-fps, --send-interval e --window devem ser > 0")

    try:
        spaces, cameras = load_seed(args.seed)
    except (SeedError, FileNotFoundError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Seed inválido: {exc}") from None
    if args.camera_id not in cameras:
        disponiveis = ", ".join(sorted(cameras)) or "nenhuma"
        raise SystemExit(
            f"Câmera não encontrada no seed: {args.camera_id} (disponíveis: {disponiveis})"
        )
    camera = cameras[args.camera_id]
    if not camera.enabled:
        raise SystemExit(f"Câmera desabilitada: {camera.id}")
    if not camera.regions:
        raise SystemExit(f"Câmera sem ROIs habilitadas: {camera.id}")

    sender = AsyncIngest(AtlasClient(args.api_url, timeout=INGEST_TIMEOUT))
    try:
        if args.fake:
            _run_fake(args, camera, spaces, sender)
        else:
            _run_real(args, camera, sender)
    except KeyboardInterrupt:
        LOGGER.info("Encerrando")
    finally:
        sender.close()
    return 0


def main() -> None:
    raise SystemExit(run(build_parser().parse_args()))
