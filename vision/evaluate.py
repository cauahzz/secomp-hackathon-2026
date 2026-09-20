from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import cv2

from atlas_vision.detector import DEFAULT_CONF, DEFAULT_MODEL, PersonDetector
from atlas_vision.models import SeedError, load_seed, resolve_source
from atlas_vision.roi import assign_detections_to_rois, scale_roi


def extract_frames(video_path: str, output_dir: str, count: int = 20) -> list[Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise SystemExit(f"Não abriu vídeo: {video_path}")
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if total <= 0:
        cap.release()
        raise SystemExit(f"Vídeo sem contagem de frames disponível: {video_path}")
    indices = [round(i * (total - 1) / max(1, count - 1)) for i in range(count)]
    paths = []
    for i, idx in enumerate(indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok:
            continue
        path = out / f"frame_{i:03d}.jpg"
        cv2.imwrite(str(path), frame)
        paths.append(path)
    cap.release()
    return paths


def load_manual(csv_path: str) -> dict[tuple[str, str], int]:
    # utf-8-sig porque o CSV é anotado à mão, normalmente em planilha, que grava BOM.
    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        missing = {"frame", "region_id", "manual_count"} - set(reader.fieldnames or ())
        if missing:
            raise SystemExit(
                f"{csv_path}: faltam as colunas {', '.join(sorted(missing))}; "
                "o cabeçalho precisa ser frame,region_id,manual_count"
            )
        result: dict[tuple[str, str], int] = {}
        for line, row in enumerate(reader, start=2):
            raw = (row.get("manual_count") or "").strip()
            try:
                count = int(raw)
            except ValueError:
                raise SystemExit(f"{csv_path}:{line}: manual_count não é inteiro: {raw!r}") from None
            key = ((row.get("frame") or "").strip(), (row.get("region_id") or "").strip())
            result[key] = count
    return result


def frame_keys(path: Path) -> list[str]:
    """Nomes que o CSV pode usar para o mesmo frame: frame_000.jpg, frame_000, 000 e 0."""
    numeric = path.stem.split("_")[-1]
    keys = [path.name, path.stem, numeric]
    if numeric.isdigit():
        keys.append(str(int(numeric)))
    return keys


def run(args: argparse.Namespace) -> None:
    try:
        _, cameras = load_seed(args.seed)
    except (SeedError, FileNotFoundError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Seed inválido: {exc}") from None
    if args.camera_id not in cameras:
        disponiveis = ", ".join(sorted(cameras)) or "nenhuma"
        raise SystemExit(
            f"Câmera não encontrada no seed: {args.camera_id} (disponíveis: {disponiveis})"
        )
    camera = cameras[args.camera_id]

    if args.extract:
        video = resolve_source(args.video or camera.source_uri, args.seed)
        if not isinstance(video, str):
            raise SystemExit("--extract requer vídeo em arquivo")
        paths = extract_frames(video, args.frames_dir, args.extract)
        print(f"{len(paths)} frames extraídos em {args.frames_dir}")
        if not args.csv:
            # O passo 2 da spec é manual: a equipe anota antes de haver MAE.
            print("Anote o CSV (frame,region_id,manual_count) e rode de novo com --csv.")
            return
    else:
        paths = sorted(Path(args.frames_dir).glob("frame_*.jpg"))

    if not args.csv:
        raise SystemExit("--csv é obrigatório para calcular o MAE (use --extract sozinho para só extrair)")
    if not paths:
        raise SystemExit(f"Nenhum frame em {args.frames_dir}; use --extract 20")

    manual = load_manual(args.csv)
    detector = PersonDetector(args.model, args.conf)
    abs_errors: dict[str, list[int]] = defaultdict(list)
    all_errors: list[int] = []

    for path in paths:
        frame = cv2.imread(str(path))
        if frame is None:
            print(f"aviso: não foi possível ler {path}")
            continue
        rois = [
            scale_roi(r, frame.shape[1], frame.shape[0], camera.width, camera.height)
            for r in camera.regions
        ]
        # Sem suavização: aqui se mede o detector, não a janela deslizante.
        counts = assign_detections_to_rois([d.box for d in detector.detect(frame)], rois)
        keys = frame_keys(path)
        for roi in camera.regions:
            expected = next((manual[(k, roi.id)] for k in keys if (k, roi.id) in manual), None)
            if expected is None:
                continue
            err = abs(counts.get(roi.id, 0) - expected)
            abs_errors[roi.id].append(err)
            all_errors.append(err)

    if not all_errors:
        raise SystemExit(
            "Nenhuma anotação do CSV correspondeu aos frames/ROIs; "
            f"confira a coluna frame (esperado algo como {paths[0].name}) e os region_id"
        )

    print(f"Frames lidos: {len(paths)} | anotações usadas: {len(all_errors)}")
    print("MAE por ROI")
    for rid, values in sorted(abs_errors.items()):
        print(f"  {rid}: {sum(values) / len(values):.3f}  ({len(values)} anotações)")
    print(f"Geral: {sum(all_errors) / len(all_errors):.3f}")


def main() -> None:
    p = argparse.ArgumentParser(description="Avalia o MAE do agente ATLAS")
    p.add_argument("--seed", default="../api/seed.json")
    p.add_argument("--camera-id", default="CAM-01")
    p.add_argument("--frames-dir", default="data/eval_frames")
    p.add_argument("--csv", default=None, help="anotação manual; dispensável com --extract sozinho")
    p.add_argument("--extract", type=int, default=0, help="extrai N frames espaçados")
    p.add_argument("--video", default=None)
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--conf", type=float, default=DEFAULT_CONF)
    run(p.parse_args())


if __name__ == "__main__":
    main()
