# ATLAS — API

Backend do ATLAS: recebe a ocupação calculada pelo módulo de visão, persiste os
dados e entrega ao frontend tudo o que ele precisa.

Spec completa: [`docs/spec-api.md`](../docs/spec-api.md).

## Stack

Python · FastAPI · SQLAlchemy · SQLite

## Como rodar

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows;  no Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000
```

A API sobe em `http://localhost:8000` (docs interativas em `/docs`). Se o banco
estiver vazio, o seed é carregado automaticamente na inicialização.

### Recriar o banco do zero

```bash
python -m app.seed --reset
```

Sem `--reset`, o comando só popula um banco vazio e avisa se já houver dados.

### Testes

```bash
pip install -r requirements-dev.txt
python -m pytest
```

## Configuração

| Variável | Padrão | O quê |
|---|---|---|
| `ATLAS_DB_PATH` | `atlas.db` | arquivo SQLite |
| `ATLAS_SEED_PATH` | `seed.json` | seed lido pela API **e** pela visão |
| `ATLAS_CORS_ORIGINS` | `http://localhost:3000` | origens liberadas, separadas por vírgula |
| `ATLAS_NO_DATA_SECONDS` | `30` | silêncio da câmera que derruba o space para `no_data` |

Caminhos relativos são resolvidos a partir de `api/`, não do diretório atual —
assim `uvicorn` e `python -m app.seed` apontam sempre para o mesmo arquivo,
rodados de onde forem.

## Endpoints

| Método | Rota | O quê |
|---|---|---|
| `GET` | `/health` | `{"status": "ok"}` |
| `GET` | `/structure` | árvore campus → prédios → andares → ambientes |
| `GET` | `/spaces` | todos os ambientes com ocupação atual |
| `GET` | `/spaces/{id}` | idem, mais a câmera/ROI de origem |
| `GET` | `/spaces/{id}/occupancy` | só a ocupação |
| `GET` | `/spaces/{id}/history?minutes=30` | até 500 pontos, em ordem crescente |
| `GET` | `/summary` | agregados do campus |
| `POST` | `/ingest` | usado **somente** pelo módulo de visão |

## Duas decisões que valem explicar

**Status é calculado na leitura, nunca gravado.** Não existe coluna de status em
`occupancy_snapshots`. Um status gravado no ingest jamais viraria `no_data`,
porque `no_data` significa exatamente que o ingest parou de chegar. A regra vive
em uma função só — `app/services/occupancy.py::build_state` — usada por todos os
endpoints que devolvem status.

**A API usa sempre o horário do próprio servidor** para `last_seen_at` e para o
`captured_at` dos snapshots. O `captured_at` enviado pela visão é opcional e vai
só para o log. Isso elimina divergência de fuso e de relógio entre as máquinas.

Consequência da primeira decisão: quando o status é `no_data`, a API devolve
`person_count` e `occupancy_rate` como `null`, mas mantém `captured_at` — o dado
some, o silêncio fica datado.

## Estrutura

```
api/
├── seed.json                  estrutura da demo (lido também pela visão)
├── app/
│   ├── main.py                app FastAPI, CORS, seed na inicialização
│   ├── config.py              variáveis de ambiente
│   ├── database.py            engine, sessão, Base
│   ├── models.py              tabelas
│   ├── schemas.py             request/response do contrato
│   ├── seed.py                carga e validação do seed (+ CLI)
│   ├── timeutil.py            horário do servidor e ISO 8601 UTC
│   ├── routers/               um módulo por grupo de endpoints
│   └── services/occupancy.py  cálculo de status
└── tests/                     um teste por item do Definition of Done
```

## Seed

`seed.json` é a fonte única da estrutura da demo: a API popula o banco com ele e
a visão lê dele as ROIs. Não existe endpoint de configuração de ROI.

A carga valida e **aborta com mensagem clara** se algo não fecha: ROI apontando
para ambiente inexistente, ambiente em duas ROIs, ID duplicado, ambiente sem
capacidade. Seed quebrado derruba a API de propósito — subir com a estrutura
pela metade esconderia o erro até a hora da demo.

A `geometry` das ROIs está em pixels da resolução declarada da câmera
(`width` × `height`); frame em outra resolução é escalado pela visão.

## Fora do escopo

Autenticação, permissões, WebSocket, eventos, reconhecimento facial, filas,
microserviços, cloud, endpoint de ROI, streaming de vídeo.
