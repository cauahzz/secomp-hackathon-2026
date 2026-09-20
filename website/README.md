# ATLAS — Frontend

Interface web do MVP do ATLAS: mapa interativo do campus, ocupação dos
ambientes, detalhe e visão geral. Next.js + React + TypeScript + SVG.

O frontend conversa com o resto do sistema **somente** pelos `GET` do contrato
compartilhado (spec `ATLAS_agente_Frontend.md`).

## Rodar

```bash
npm install
npm run dev          # http://localhost:3000
```

## Configuração

Variáveis lidas em tempo de build (`.env.local`, fora do versionamento):

| Variável | Padrão | Efeito |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | base da API |
| `NEXT_PUBLIC_USE_MOCK` | `false` | `true` lê os JSON de `lib/mock/` no lugar da API |

Trocar o valor exige reiniciar o `next dev` (o próprio Next reinicia ao salvar
o `.env.local`).

O modo mock é o esqueleto andante da FASE 0 e o plano B da demo: tem os nove
ambientes, as cinco situações de status e uma câmera offline. Detalhes em
`lib/mock/README.md`.

## Telas

| Rota | Tela |
|---|---|
| `/` | Visão Geral (`GET /summary`) |
| `/mapa` | Mapa: campus → prédio → andar (`GET /structure`) |
| `/ambientes` | Tabela (`GET /spaces`) |

O detalhe do ambiente é um painel compartilhado pelo mapa e pela tabela,
alimentado por `GET /spaces/{id}` e `GET /spaces/{id}/history`.

## Telas estreitas

A mesma interface serve celular e desktop; três pontos mudam de forma:

| Largura | Navegação | Ambientes | Detalhe |
|---|---|---|---|
| < 640 px | barra inferior | lista de cartões | folha que sobe |
| 640–1023 px | barra inferior até 768 px | cartões em duas colunas | gaveta à direita |
| ≥ 1024 px | menu no cabeçalho | tabela de seis colunas | gaveta à direita |

O mapa é o mesmo em toda largura: a altura sai da proporção do desenho, o toque
abre o nível seguinte e o tooltip só existe onde há mouse.

## Atualização

Polling de 2 s em `GET /spaces` e `GET /summary`; com o detalhe aberto,
também em `GET /spaces/{id}` e `.../history`. `GET /structure` carrega uma vez.
Sem WebSocket no MVP.

Se a API cair, a última tela continua no lugar, um aviso fixo aparece no topo
e o polling segue tentando.

## Estrutura

```
app/                 rotas (as três telas)
components/          interface; tudo que depende de dado é client component
lib/api.ts           único ponto de contato com o backend
lib/types.ts         tipos do contrato
lib/mock/            modo mock, no formato exato do contrato
public/maps/         SVGs do campus e dos andares (ver README de lá)
app/globals.css      tokens de cor — nenhum hex fora daqui
```

## Convenções

- Identificadores em inglês; comentários, textos de tela e documentação em
  português.
- Cor só sai de token CSS (`var(--status-high)`), nunca de hex em componente.
- O status vem pronto da API. O frontend nunca recalcula faixa nem status —
  só traduz o código em rótulo e cor.
- Cor nunca é a única informação: todo indicador vem com rótulo em texto.
- Movimento também sai de token (`--ease-out`, `--dur-panel`) e respeita
  `prefers-reduced-motion`: quem pede menos movimento continua vendo a
  transição, só sem deslocamento.
- Única exceção à regra do hex: `themeColor`, em `app/layout.tsx`. A meta tag
  não lê `var()`, então o valor espelha `--bg` na mão.
