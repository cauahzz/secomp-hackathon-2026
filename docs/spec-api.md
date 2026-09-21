# ATLAS — Especificação para Agente de API

## Objetivo

Implementar o backend mínimo do ATLAS para receber a ocupação calculada pelo módulo de Visão Computacional, persistir os dados e fornecer ao frontend tudo o que ele precisa.

O módulo de visão e o frontend conversam **somente** pelo contrato HTTP descrito abaixo.

## Stack

- Python
- FastAPI
- SQLAlchemy
- SQLite

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

## Escopo obrigatório

1. Banco e modelos: `campuses`, `buildings`, `floors`, `spaces`, `cameras`, `camera_regions`, `occupancy_snapshots`.
2. Carga do seed a partir de `apps/api/seed.json`.
3. Todos os endpoints do contrato: `GET /health`, `GET /structure`, `GET /spaces`, `GET /spaces/{id}`, `GET /spaces/{id}/occupancy`, `GET /spaces/{id}/history`, `GET /summary`, `POST /ingest`.
4. CORS habilitado para `http://localhost:3000`.

## Modelos

**Chaves primárias de `campuses`, `buildings`, `floors`, `spaces`, `cameras` e `camera_regions` são `String`**, com os valores vindos do seed. Não usar inteiro autoincremental nessas tabelas. `occupancy_snapshots.id` pode ser inteiro autoincremental.

### spaces

- `id`, `floor_id`, `name`, `code`, `type`, `capacity`, `operational_limit` (nulo permitido), `map_geometry` (nulo permitido; o frontend usa os SVGs, não este campo, no MVP), `created_at`, `updated_at`.

### cameras

- `id`, `campus_id`, `name`, `source_type`, `source_uri`, `width`, `height`, `fps`, `enabled`, `last_seen_at` (nulo até o primeiro ingest), `created_at`, `updated_at`.

### camera_regions

- `id`, `camera_id`, `space_id`, `name`, `type`, `shape`, `geometry` (JSON), `enabled`, `created_at`, `updated_at`.
- No MVP: `shape = rectangle`, `type = occupancy`, `geometry = {x, y, width, height}`.

### occupancy_snapshots

- `id`, `space_id`, `camera_region_id`, `person_count`, `occupancy_rate`, `captured_at`.
- **Não existe coluna de status.** O status é calculado na leitura.

## POST /ingest — comportamento

Ao receber uma requisição válida:

1. conferir se a câmera existe (senão, `404`);
2. atualizar `cameras.last_seen_at` com o **horário atual do servidor (UTC)**;
3. para cada região: conferir se pertence à câmera e está habilitada (senão, colocar em `ignored`);
4. resolver ROI → space;
5. calcular `occupancy_rate = person_count / capacity`;
6. gravar um `occupancy_snapshot` com `captured_at` = horário atual do servidor.

O `captured_at` do corpo da requisição não é usado para lógica, apenas para log.

**Não calcular status no ingest.** Um status gravado no ingest nunca poderia virar `no_data`, porque `no_data` significa justamente que o ingest parou de chegar.

## Leitura — cálculo de status

Em todo endpoint que retorna status (`/spaces`, `/spaces/{id}`, `/spaces/{id}/occupancy`, `/summary`):

1. buscar o último snapshot do space;
2. buscar a câmera da ROI do space;
3. aplicar a tabela de status do contrato, na ordem, usando o horário atual do servidor;
4. se o status for `no_data`, retornar `person_count` e `occupancy_rate` como `null`.

Centralizar essa lógica em uma única função (por exemplo `services/occupancy.py::current_state(space)`), usada por todos os endpoints.

**Estado atual = último snapshot de cada space.** Não criar tabela separada de estado atual.

## Seed

- Comando: `python -m app.seed --reset`, que apaga o banco e recria tudo a partir do `seed.json`.
- Na inicialização da API, se o banco estiver vazio, carregar o seed automaticamente.
- Validar ao carregar: cada `space_id` aparece em no máximo uma ROI; toda ROI aponta para um space existente. Se falhar, abortar com mensagem clara.
- O caminho do seed é configurável pela variável `ATLAS_SEED_PATH` (padrão `apps/api/seed.json`).

## Configuração

- `ATLAS_DB_PATH` (padrão `atlas.db`)
- `ATLAS_SEED_PATH` (padrão `apps/api/seed.json`)
- `ATLAS_CORS_ORIGINS` (padrão `http://localhost:3000`)
- `ATLAS_NO_DATA_SECONDS` (padrão `30`)

Rodar com: `uvicorn app.main:app --reload --port 8000`.

## Esqueleto andante

Na FASE 0, antes de qualquer lógica completa:

- `GET /health` funcionando;
- seed carregado;
- `POST /ingest` gravando snapshot;
- `GET /spaces` retornando os ambientes com a ocupação atual.

Isso já permite que o modo `--fake` da visão e o frontend funcionem de ponta a ponta. O restante é completado na FASE 2.

## Fora do escopo

Não implementar: autenticação/login, permissões reais, WebSocket, eventos, reconhecimento facial, filas/estacionamento, microserviços, cloud, endpoint de configuração de ROI, streaming de vídeo.

## Definition of Done

A API está pronta quando:

- o banco sobe vazio e o seed cria a estrutura da demo;
- `python -m app.seed --reset` recria o banco limpo;
- `POST /ingest` recebe uma contagem e a salva;
- `GET /spaces` mostra a ocupação atual com os status do contrato;
- parar de enviar ingest por mais de 30 s faz os ambientes da câmera virarem `no_data`, com `person_count: null`;
- `GET /spaces/{id}/history` mostra o histórico em ordem crescente;
- `GET /structure` e `GET /summary` funcionam;
- o frontend em `localhost:3000` consegue chamar a API sem erro de CORS;
- todas as respostas seguem exatamente os exemplos do contrato.
