# Mock do contrato

`NEXT_PUBLIC_USE_MOCK=true` faz `lib/api.ts` servir estes dados no lugar da API.

| Arquivo | Papel |
|---|---|
| `structure.json` | `GET /structure` |
| `spaces.json` | `GET /spaces` — também é a base da simulação (nomes, capacidade, limite) |
| `summary.json` | `GET /summary` — referência do formato; o valor servido é derivado de `spaces.json` |
| `space-detail.json` | `GET /spaces/{id}` — exemplo literal do contrato |
| `history.json` | `GET /spaces/{id}/history` — exemplo literal do contrato |
| `sources.json` | câmeras e ROIs, espelhando o que a visão leria do seed |

`simulate.ts` faz o papel do servidor: move os números a cada 5 s e calcula o
status pela tabela do contrato, para que o polling de 2 s tenha o que mostrar.
A câmera `CAM-04` fica offline de propósito, mantendo a Sala 202 em `no_data`.
