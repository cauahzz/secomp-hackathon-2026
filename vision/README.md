# ATLAS — Vision Agent

Implementação do módulo de visão descrito em [`docs/spec-visao.md`](../docs/spec-visao.md). O agente
só conversa com o resto do sistema por `POST /ingest` e pela leitura do
`seed.json`.

## O que está implementado

- Python + OpenCV + Ultralytics YOLO + `requests`.
- Leitura do `seed.json` para câmera e ROIs habilitadas, com validação no load.
- `POST /ingest` único por câmera, timeout de 2 s, enviado fora da thread do
  vídeo para que a API nunca congele a janela.
- Resiliência: falha de API só gera warning; nada de fila de envios pendentes.
- Detecção exclusiva de `person` (`classes=[0]`), sem tracking.
- Ponto dos pés: centro inferior da bounding box.
- Escala proporcional das ROIs quando a resolução do frame difere da declarada.
- Amostragem pelo fps real do vídeo aberto, não pelo declarado no seed.
- Janela deslizante de mediana em segundos.
- Vídeo de arquivo em loop; webcam/stream reabre a cada 2 s após falha.
- Janela OpenCV com ROI, bounding boxes, ponto dos pés e contagem em fonte grande.
- `--fake` sem vídeo/modelo para teste ponta a ponta.
- `evaluate.py` para extrair frames, comparar com o CSV manual e imprimir o MAE.
- Parâmetros configuráveis pela CLI.

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

## Execução real

A partir da raiz do projeto, usando o seed da especificação:

```bash
python run.py --seed ../api/seed.json --camera-id CAM-01 --api-url http://localhost:8000
```

Sobrescrevendo a fonte (arquivo, índice de webcam ou URL de stream):

```bash
python run.py --seed ../api/seed.json --camera-id CAM-01 --source data/demo.mp4
python run.py --seed ../api/seed.json --camera-id CAM-01 --source 0
python run.py --seed ../api/seed.json --camera-id CAM-01 --source rtsp://usuario:senha@host/stream
```

Caminho relativo em `--source` é resolvido a partir do diretório atual; o
`source_uri` do seed também aceita caminho relativo à pasta do próprio seed.

Sem janela, ou com modelo alternativo:

```bash
python run.py --seed ../api/seed.json --camera-id CAM-01 --no-window
python run.py --seed ../api/seed.json --camera-id CAM-01 --model yolov8n.pt
```

Tecla `q` na janela encerra o processo; `Ctrl+C` também.

## Modo fake

Não abre vídeo nem carrega YOLO. Gera uma caminhada aleatória suave de
contagens, limitada entre 0 e a `capacity` do space, e usa o mesmo cliente de
ingestão do modo real:

```bash
python run.py --seed ../api/seed.json --camera-id CAM-01 --fake
```

## Avaliação

O fluxo tem três passos, porque a anotação é manual.

1. Extrair ~20 frames espaçados:

```bash
python evaluate.py --seed ../api/seed.json --camera-id CAM-01 --video data/demo.mp4 \
  --frames-dir data/eval_frames --extract 20
```

2. A equipe anota um CSV com o cabeçalho abaixo. A coluna `frame` aceita
   `frame_000.jpg`, `frame_000`, `000` ou `0`.

```csv
frame,region_id,manual_count
frame_000.jpg,ROI-01,4
frame_000.jpg,ROI-02,2
```

3. Calcular o MAE por ROI e o geral, com o mesmo modelo e o mesmo limiar do
   agente e sem suavização:

```bash
python evaluate.py --seed ../api/seed.json --camera-id CAM-01 \
  --frames-dir data/eval_frames --csv data/manual.csv
```

## Testes

```bash
make test           # ou: python -m pytest tests -q
```

## Smoke test ponta a ponta

Terminal 1:

```bash
python tools/mock_api.py
```

Terminal 2:

```bash
python run.py --seed config/seed.example.json --camera-id CAM-01 \
  --api-url http://localhost:8000 --fake --send-interval 2
```

O mock imprime cada payload recebido. O modo fake não carrega o modelo YOLO.
