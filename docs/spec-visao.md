# ATLAS — Especificação para Agente de Visão Computacional

## Objetivo

Implementar o processo que recebe um vídeo ou câmera, detecta pessoas, verifica em quais ROIs elas estão, estabiliza a contagem e envia os resultados para a API do ATLAS.

A visão conversa com o resto do sistema **somente** por `POST /ingest` e pela leitura do `seed.json`.

## Stack

- Python
- OpenCV
- Ultralytics YOLO
- `requests` (ou `httpx`) para o envio

## Fluxo

```
VÍDEO/CÂMERA
→ OpenCV
→ amostragem de frames (2–5 fps)
→ YOLO (somente pessoa)
→ ponto dos pés
→ ROI
→ contagem por ROI
→ suavização (mediana da janela)
→ POST /ingest a cada 5 s
```

## Contrato compartilhado (idêntico nas três specs)

> Este bloco é a fonte de verdade da integração. Ele é copiado sem alterações nas specs de API, Visão e Frontend. Se algo precisar mudar, muda nas três.

### Convenções gerais

- Base URL da API: `http://localhost:8000` (configurável).
- JSON com chaves em `snake_case`.
- **IDs são strings definidas no seed**, nunca inteiros autoincrementais. Exemplos: `unifei-itabira`, `bld-1`, `bld-1-f2`, `room-102`, `CAM-01`, `ROI-01`.
- **Timestamps em ISO 8601, UTC, com sufixo `Z`.** Exemplo: `"2026-09-20T17:30:10Z"`.
- **A API usa sempre o horário do próprio servidor** para `last_seen_at` e para o `captured_at` dos snapshots. O `captured_at` enviado pela visão é opcional e serve só para log. Isso elimina problemas de fuso e de relógio entre máquinas.
- `effective_limit = operational_limit` se não for nulo; senão, `capacity`.
- `occupancy_rate = person_count / capacity`, na escala **0 a 1** (ex.: `0.9`). O frontend multiplica por 100 para exibir.
- **No MVP, cada space tem exatamente uma ROI.** (Regra futura para várias ROIs: ocupação = máximo entre elas, nunca a soma.)

### Status de ocupação

Códigos exatos, em inglês. **Calculados pela API no momento da leitura** (nos GETs), nunca no ingest e nunca no frontend.

| Código | Regra (avaliada nesta ordem) |
|---|---|
| `no_data` | câmera da ROI do space com `last_seen_at` nulo ou há mais de 30 s (horário do servidor), ou space sem nenhum snapshot |
| `empty` | `person_count == 0` |
| `normal` | `person_count < 0.7 × effective_limit` |
| `high` | `0.7 × effective_limit ≤ person_count ≤ effective_limit` |
| `over_limit` | `person_count > effective_limit` |

Quando o status é `no_data`, a API retorna `person_count: null` e `occupancy_rate: null`, para que ninguém exiba um número antigo como se fosse atual. O campo `captured_at` continua trazendo o horário do último snapshot conhecido (ou `null`).

Mapeamento visual (usado pelo frontend):

| Código | Rótulo | Cor | Token CSS | Hex |
|---|---|---|---|---|
| `empty` | Vazio | ciano | `--status-empty` | `#22D3EE` |
| `normal` | Normal | verde | `--status-normal` | `#22C55E` |
| `high` | Alta ocupação | âmbar | `--status-high` | `#F5A524` |
| `over_limit` | Acima do limite | vermelho | `--status-over` | `#F04438` |
| `no_data` | Sem dados | cinza | `--status-nodata` | `#64748B` |

Paleta completa, tokens e regras de uso: spec do Frontend, seção "Identidade visual e paleta".
O azul da marca (`#1E90FF`) é reservado a elementos interativos e NUNCA é usado como cor de status.

### Endpoints

#### `GET /health`

```json
{ "status": "ok" }
```

#### `GET /structure`

Árvore do campus para a navegação do frontend.

```json
{
  "campus": { "id": "unifei-itabira", "name": "UNIFEI — Campus Itabira" },
  "buildings": [
    {
      "id": "bld-1",
      "name": "Prédio 1",
      "code": "P1",
      "floors": [
        {
          "id": "bld-1-f2",
          "name": "2º andar",
          "level": 2,
          "spaces": [
            { "id": "room-102", "name": "Sala 102", "code": "102", "type": "classroom" }
          ]
        }
      ]
    }
  ]
}
```

#### `GET /spaces`

Lista de todos os ambientes com ocupação atual.

```json
[
  {
    "id": "room-102",
    "name": "Sala 102",
    "code": "102",
    "type": "classroom",
    "building": { "id": "bld-1", "name": "Prédio 1" },
    "floor": { "id": "bld-1-f2", "name": "2º andar", "level": 2 },
    "capacity": 40,
    "operational_limit": 35,
    "person_count": 36,
    "occupancy_rate": 0.9,
    "status": "over_limit",
    "captured_at": "2026-09-20T17:30:10Z"
  }
]
```

#### `GET /spaces/{id}`

Mesmo objeto de `GET /spaces`, acrescido da fonte:

```json
{
  "...": "todos os campos de GET /spaces",
  "source": {
    "camera_id": "CAM-01",
    "camera_name": "Câmera 1",
    "region_id": "ROI-01",
    "online": true,
    "last_seen_at": "2026-09-20T17:30:12Z"
  }
}
```

Ambiente inexistente: `404` com `{ "detail": "space not found" }`.

#### `GET /spaces/{id}/occupancy`

```json
{
  "space_id": "room-102",
  "person_count": 36,
  "occupancy_rate": 0.9,
  "status": "over_limit",
  "captured_at": "2026-09-20T17:30:10Z",
  "source": { "camera_id": "CAM-01", "online": true, "last_seen_at": "2026-09-20T17:30:12Z" }
}
```

#### `GET /spaces/{id}/history?minutes=30`

Snapshots em ordem crescente de tempo. `minutes` padrão 30; no máximo 500 pontos (se houver mais, a API retorna os mais recentes).

```json
{
  "space_id": "room-102",
  "points": [
    { "captured_at": "2026-09-20T17:29:00Z", "person_count": 30, "occupancy_rate": 0.75 },
    { "captured_at": "2026-09-20T17:29:05Z", "person_count": 31, "occupancy_rate": 0.775 }
  ]
}
```

#### `GET /summary`

```json
{
  "total_people": 123,
  "spaces_total": 8,
  "empty": 2,
  "normal": 3,
  "high": 1,
  "over_limit": 1,
  "no_data": 1,
  "cameras_online": 1,
  "cameras_total": 1,
  "generated_at": "2026-09-20T17:30:12Z"
}
```

`total_people` soma apenas os ambientes que não estão em `no_data`.

#### `POST /ingest`

Usado somente pelo módulo de visão.

Requisição:

```json
{
  "camera_id": "CAM-01",
  "captured_at": "2026-09-20T17:30:10Z",
  "regions": [
    { "region_id": "ROI-01", "person_count": 12 },
    { "region_id": "ROI-02", "person_count": 3 }
  ]
}
```

Resposta `200`:

```json
{ "accepted": 2, "ignored": [] }
```

- Câmera desconhecida: `404` com `{ "detail": "camera not found" }`.
- ROI desconhecida ou que não pertence à câmera: não gera erro; vai para a lista `ignored`.
- `person_count` negativo: `422`.

### Seed (`apps/api/seed.json`)

Arquivo único, lido pela API (para popular o banco) **e pela visão** (para obter as ROIs). Não existe endpoint de ROIs.

```json
{
  "campus": { "id": "unifei-itabira", "name": "UNIFEI — Campus Itabira", "code": "ITA" },
  "buildings": [
    {
      "id": "bld-1",
      "name": "Prédio 1",
      "code": "P1",
      "floors": [
        {
          "id": "bld-1-f2",
          "name": "2º andar",
          "level": 2,
          "spaces": [
            { "id": "room-101", "name": "Sala 101", "code": "101", "type": "classroom", "capacity": 40, "operational_limit": 35 },
            { "id": "room-102", "name": "Sala 102", "code": "102", "type": "classroom", "capacity": 40, "operational_limit": 35 }
          ]
        }
      ]
    }
  ],
  "cameras": [
    {
      "id": "CAM-01",
      "name": "Câmera 1",
      "source_type": "file",
      "source_uri": "data/demo.mp4",
      "width": 1280,
      "height": 720,
      "fps": 30,
      "enabled": true,
      "regions": [
        {
          "id": "ROI-01",
          "space_id": "room-101",
          "name": "Sala 101",
          "type": "occupancy",
          "shape": "rectangle",
          "geometry": { "x": 0, "y": 0, "width": 640, "height": 720 },
          "enabled": true
        },
        {
          "id": "ROI-02",
          "space_id": "room-102",
          "name": "Sala 102",
          "type": "occupancy",
          "shape": "rectangle",
          "geometry": { "x": 640, "y": 0, "width": 640, "height": 720 },
          "enabled": true
        }
      ]
    }
  ]
}
```

Regras do seed:

- A `geometry` das ROIs está **em pixels da resolução declarada da câmera** (`width` × `height`). Se o frame real tiver outra resolução, a visão escala as coordenadas proporcionalmente.
- Os IDs de campus, prédios, andares e ambientes são os mesmos usados nos SVGs do frontend.
- Cada `space_id` aparece em no máximo uma ROI.

### Convenção dos SVGs (`apps/web/public/maps/`)

- Nome do arquivo = ID do nível: `unifei-itabira.svg`, `bld-1-f2.svg` etc.
- No SVG do campus, cada prédio clicável tem `id` igual ao ID do prédio (`bld-1`).
- No SVG de um andar, cada ambiente clicável tem `id` igual ao ID do space (`room-102`).
- O nível de prédio não precisa de SVG: pode ser uma lista simples de andares.

### Portas e CORS

- API: porta `8000`. Frontend: porta `3000`.
- A API habilita CORS para `http://localhost:3000`.

## Configuração

Tudo configurável por linha de comando (ou variáveis de ambiente equivalentes). Nada de IDs ou caminhos hard-coded no algoritmo.

| Parâmetro | Padrão | Descrição |
|---|---|---|
| `--api-url` | `http://localhost:8000` | base da API |
| `--seed` | `../api/seed.json` | caminho do seed |
| `--camera-id` | `CAM-01` | câmera do seed a usar |
| `--source` | `source_uri` do seed | sobrescreve a fonte (arquivo, índice de webcam `0`, URL de stream) |
| `--process-fps` | `3` | frames processados por segundo |
| `--window` | `7` | tamanho da janela de suavização, em segundos |
| `--send-interval` | `5` | intervalo entre envios, em segundos |
| `--conf` | `0.4` | limiar de confiança do YOLO |
| `--model` | `yolo11n.pt` | modelo (usar `yolov8n.pt` se houver incompatibilidade) |
| `--no-window` | desligado | não abre a janela do OpenCV |
| `--fake` | desligado | modo de dados falsos (ver abaixo) |

As ROIs da câmera são lidas do `seed.json` (`cameras[].regions[]`, somente as com `enabled: true`).

## Detecção

- Modelo leve (`yolo11n` ou `yolov8n`), pré-treinado. Não treinar modelo.
- Filtrar somente a classe `person` (`classes=[0]`).
- Processar cerca de 2–5 fps. Ocupação não precisa de 30 fps.
- Não usar tracking. Não implementar reconhecimento facial.

### Amostragem de frames

Para vídeo gravado, amostrar pelo **tempo do vídeo**, não por frames consecutivos: processar um frame a cada `video_fps / process_fps` frames e descartar os intermediários. Assim o vídeo avança em velocidade real e a contagem acompanha o que aparece na tela.

## ROI

### Escala das coordenadas

A `geometry` de cada ROI está em pixels da resolução declarada da câmera no seed (`width` × `height`). Se o frame real tiver outra resolução, escalar:

```python
sx = frame_w / camera["width"]
sy = frame_h / camera["height"]
x, y = g["x"] * sx, g["y"] * sy
w, h = g["width"] * sx, g["height"] * sy
```

### Regra de pertencimento

Não usar o centro da bounding box. Usar o ponto inferior central (os pés):

```python
point = ((x1 + x2) / 2, y2)
```

Se esse ponto estiver dentro do retângulo da ROI, a pessoa conta para aquela região. Motivo: com câmera em ângulo, o centro da pessoa pode cair na região errada.

## Suavização

A contagem oscila por oclusão (13, 11, 14, 12…).

- Manter, para cada ROI, as contagens dos últimos `--window` segundos.
- A cada `--send-interval` segundos, enviar a **mediana** da janela como `person_count` (arredondada para inteiro).
- A janela é deslizante: não é zerada após o envio.

## Envio para a API

- Não escrever no SQLite.
- Enviar `POST /ingest` no formato do contrato, com `captured_at` em UTC e sufixo `Z`.
- Uma requisição por câmera contendo todas as ROIs dela.
- Timeout curto (2 s).

### Resiliência

A visão **nunca pode travar** por causa da API:

- se a requisição falhar (conexão recusada, timeout, status diferente de 200), registrar um aviso no log e seguir processando;
- se a resposta vier com itens em `ignored`, registrar no log (indica ROI mal configurada);
- não acumular fila de envios pendentes: o próximo envio simplesmente leva a contagem atual.

## Vídeo em loop

Com fonte de arquivo, **ao chegar ao fim do vídeo, voltar ao início** (`cap.set(cv2.CAP_PROP_POS_FRAMES, 0)`).

Sem isso, o vídeo termina, os envios param e, 30 s depois, todos os ambientes viram `no_data` no meio do pitch.

Com webcam ou stream: se a leitura falhar, tentar reabrir a fonte a cada 2 s, sem encerrar o processo.

## Janela de visualização (usada no pitch)

A janela do OpenCV **é o vídeo mostrado na demo**, lado a lado com o navegador. O frontend não exibe vídeo.

Desenhar no frame:

- o retângulo de cada ROI, com o nome do ambiente;
- as bounding boxes das pessoas detectadas;
- o ponto dos pés de cada pessoa;
- a contagem suavizada atual de cada ROI, em fonte grande.

Tecla `q` encerra o processo.

## Modo `--fake` (esqueleto andante)

Na FASE 0, antes do YOLO funcionar:

- não abre vídeo nem carrega modelo;
- a cada `--send-interval` segundos, envia para cada ROI da câmera uma contagem que varia suavemente (por exemplo, valor anterior ± 0–2, limitado entre 0 e a capacidade do space);
- usa exatamente o mesmo código de envio do modo real.

Isso permite que API e frontend sejam testados de ponta a ponta desde o início. O modo `--fake` continua disponível como plano B da demo.

## Demo

Escolher vídeo com:

- boa iluminação;
- câmera em ângulo alto, quando possível;
- pessoas visíveis de corpo inteiro ou quase;
- pouca oclusão;
- movimento suficiente para a contagem variar.

Se uma única câmera for usada para simular vários ambientes com várias ROIs, deixar isso claro na apresentação.

## Avaliação mínima

Criar um script `evaluate.py`:

1. extrair cerca de 20 frames espaçados do vídeo da demo para uma pasta;
2. a equipe anota manualmente, em um CSV (`frame,region_id,manual_count`), quantas pessoas há em cada ROI;
3. o script roda a detecção (sem suavização) nesses frames, com as mesmas ROIs e o mesmo limiar;
4. calcula e imprime o erro médio absoluto por ROI e o geral.

Resultado para o pitch: "Erro médio de ±X pessoa por ambiente no vídeo de teste."

## Fora do escopo

Não implementar: tracking, entry/exit, reconhecimento facial, identificação de pessoas, treinamento, múltiplos tipos de ROI, eventos, banco local, streaming de vídeo para o navegador.

## Definition of Done

O módulo está pronto quando:

- `--fake` envia contagens que aparecem na API;
- lê o vídeo e volta ao início quando termina;
- detecta somente pessoas;
- desenha ROIs, bounding boxes, ponto dos pés e contagem;
- conta pessoas por ROI usando o ponto dos pés;
- estabiliza a contagem com a mediana da janela;
- envia `POST /ingest` a cada ~5 s no formato do contrato;
- continua rodando se a API cair e volta a enviar quando ela voltar;
- `evaluate.py` produz o erro médio absoluto.
