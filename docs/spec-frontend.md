# ATLAS — Especificação para Agente de Frontend

## Objetivo

Construir a interface web do MVP do ATLAS: mapa interativo do campus, ocupação dos ambientes, detalhes e visão geral.

O frontend conversa com o resto do sistema **somente** pelos endpoints `GET` do contrato abaixo.

## Stack

- Next.js
- React
- TypeScript
- SVG

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

## Identidade visual e paleta

O ATLAS tem um logo: fundo preto, letra "A" em branco com um orbital azul, câmera e malha de mapa em azul. A interface segue essa identidade: **tema escuro, texto claro, azul como única cor de marca**.

O arquivo do logo fica em `public/brand/atlas-logo.png` e aparece no cabeçalho de todas as telas, à esquerda, com altura de 32 a 40 px.

### Tokens

Declarar em `globals.css`, em `:root`, e usar **somente** os tokens no restante do código. Nada de hex solto em componente.

```css
:root {
  /* superfícies */
  --bg:            #05070A;  /* fundo da página (preto do logo) */
  --surface:       #0E141B;  /* cartões, painel de detalhe */
  --surface-2:     #151E29;  /* linha de tabela em hover, cabeçalho */
  --border:        #22303F;

  /* texto */
  --text:          #F2F5F8;
  --text-muted:    #93A1B0;

  /* marca */
  --brand:         #1E90FF;  /* azul do logo: links, botões, seleção, foco */
  --brand-strong:  #0A66FF;  /* hover/pressionado */
  --brand-soft:    #4FB0FF;  /* realce, brilho, borda do ambiente selecionado */

  /* status de ocupação */
  --status-empty:  #22D3EE;
  --status-normal: #22C55E;
  --status-high:   #F5A524;
  --status-over:   #F04438;
  --status-nodata: #64748B;

  /* mapa */
  --map-stroke:    #22303F;  /* contorno de paredes e ambientes */
  --map-inactive:  #1A2431;  /* elemento do SVG sem ambiente correspondente */
  --map-selected:  #4FB0FF;  /* contorno do ambiente selecionado, 2 px */
}
```

### Regras de uso

- O **azul da marca é para interação** (botões, links, breadcrumb ativo, foco de teclado, contorno do ambiente selecionado). Nunca preencher um ambiente do mapa com ele: no mapa, azul significaria status.
- No mapa, o preenchimento de cada ambiente usa **apenas** as cinco cores de status, com opacidade 0.85 e contorno em `--map-stroke`.
- Cor não pode ser a única informação. Toda representação de status traz também o rótulo em texto (tabela, tooltip, detalhe, legenda).
- Fundo sempre `--bg`. Não usar tema claro no MVP.
- Superfícies elevadas se distinguem por `--surface` e `--border`, não por sombra.
- Gradiente permitido só em detalhes decorativos (cabeçalho, barra de destaque): `linear-gradient(90deg, var(--brand-strong), var(--brand-soft))`.
- Tipografia: uma sans-serif geométrica (Inter, Sora ou similar), números da ocupação em peso 600 ou 700.
- Números grandes de ocupação usam `--text`; a cor do status vai no rótulo e no indicador ao lado, não no número.

### Cartões da Visão Geral

- "Pessoas no campus": destaque com `--brand`.
- Cada contador de status usa a cor do seu status como indicador (ponto ou barra lateral), com o número em `--text`.

## Configuração

- `NEXT_PUBLIC_API_URL` (padrão `http://localhost:8000`).
- `NEXT_PUBLIC_USE_MOCK` (padrão `false`). Quando `true`, o frontend lê arquivos JSON locais em vez da API.
- Rodar na porta `3000`.

Criar os tipos TypeScript (`Space`, `SpaceDetail`, `Occupancy`, `History`, `Summary`, `Structure`, `Status`) exatamente a partir dos exemplos do contrato. `Status` é a união literal `'empty' | 'normal' | 'high' | 'over_limit' | 'no_data'`.

Todas as chamadas passam por um único módulo (`lib/api.ts`) que decide entre API e mock.

## Modo mock (esqueleto andante e plano B)

Criar em `lib/mock/` um JSON para cada endpoint (`structure.json`, `spaces.json`, `summary.json`, um detalhe e um histórico de exemplo), **no formato exato do contrato**, usando os IDs do seed.

- Na FASE 0, o frontend é desenvolvido contra o mock enquanto a API não está pronta.
- Na demo, o mock é o plano B se a API falhar.

## Escopo obrigatório

Somente as telas:

1. Visão Geral
2. Mapa
3. Ambientes (tabela)
4. Detalhe do ambiente (painel lateral ou modal, compartilhado por mapa e tabela)

Não implementar login funcional.

## Mapa

Usar SVG como mapa principal, não PNG.

### Arquivos

Os SVGs ficam em `public/maps/`, seguindo a convenção do contrato:

- `unifei-itabira.svg`: campus; cada prédio clicável tem `id` igual ao ID do prédio.
- `{floor_id}.svg` (ex.: `bld-1-f2.svg`): andar; cada ambiente clicável tem `id` igual ao ID do space.
- O nível de prédio **não precisa de SVG**: pode ser uma lista de botões com os andares, vinda de `GET /structure`.

Os SVGs são desenhados manualmente pela equipe (Pessoa 3/4), de preferência antes da FASE 3. Se um SVG ainda não existir, o frontend mostra a lista de ambientes daquele andar como fallback, sem quebrar.

### Comportamento

- Carregar o SVG inline (não como `<img>`), para poder colorir e clicar nos elementos pelo `id`.
- Colorir cada ambiente pela cor do seu `status`, conforme a tabela do contrato.
- Elementos do SVG sem ambiente correspondente ficam neutros.
- Ao clicar em um ambiente: destacar o ambiente, abrir o detalhe e mostrar a ocupação atual.
- Tooltip ao passar o mouse: nome, pessoas/capacidade e rótulo do status.
- Mostrar uma legenda com as cinco cores e rótulos.

O mapa não armazena dados de ocupação. Ele representa a geometria e referencia os IDs.

## Navegação

A hierarquia vem de `GET /structure`:

```
Campus → Prédio → Andar → Ambiente
```

Breadcrumb clicável:

```
UNIFEI > Prédio 1 > 2º andar > Sala 204
```

Permitir voltar a qualquer nível anterior.

Se houver tempo, busca simples por nome de ambiente (filtrando os dados de `/structure`), que navega até o andar e destaca o ambiente. Busca avançada não é prioridade.

## Status e cores

- Usar **somente** os códigos de status vindos da API e o mapeamento visual do contrato.
- **Não recalcular** status nem faixas no frontend. A API é a fonte de verdade.
- `no_data` é sempre **cinza**, nunca vermelho: vermelho significa acima do limite, e um jurado leria como superlotação.
- `empty` tem cor própria (azul): para o aluno procurando lugar, ambiente vazio é a informação mais importante.

## Detalhe do ambiente

Dados de `GET /spaces/{id}` e `GET /spaces/{id}/history`:

- nome, prédio e andar;
- capacidade;
- limite operacional;
- pessoas atuais;
- percentual de ocupação (`occupancy_rate × 100`, arredondado);
- status (rótulo e cor);
- última atualização (horário local, convertido de UTC);
- fonte: nome da câmera e se está online;
- histórico dos últimos 30 minutos, em gráfico de linha simples ou tabela.

Quando `status === 'no_data'`:

- não mostrar número de pessoas nem percentual (a API envia `null`);
- mostrar "Sem dados" e, se `captured_at` existir, "Última leitura às HH:MM".

Não gastar tempo com gráficos sofisticados.

## Visão Geral

Dados de `GET /summary`. Mostrar cartões com:

- pessoas no campus;
- ambientes vazios;
- ambientes normais;
- ambientes em alta ocupação;
- ambientes acima do limite;
- ambientes sem dados;
- câmeras online (`cameras_online / cameras_total`).

## Tabela de ambientes

Dados de `GET /spaces`. Colunas:

- Ambiente
- Prédio
- Capacidade
- Pessoas (`—` quando `no_data`)
- Ocupação (`—` quando `no_data`)
- Status (rótulo e cor)

Clicar na linha abre o mesmo detalhe usado pelo mapa.

## Atualização

Polling a cada ~2 segundos:

- sempre: `GET /spaces` e `GET /summary`;
- com o detalhe aberto: `GET /spaces/{id}` e `GET /spaces/{id}/history`.

`GET /structure` é carregado uma única vez.

Não usar WebSocket no MVP.

## Estados da interface

Representar explicitamente:

- **carregando**: primeira carga, antes de qualquer resposta;
- **dados normais**;
- **ambiente sem dados**: cinza, sem número;
- **ambiente vazio**: azul;
- **erro da API**: manter a última tela carregada, exibir um aviso fixo ("API indisponível — dados podem estar desatualizados") e continuar tentando no próximo ciclo de polling.

## Vídeo

O frontend **não** exibe vídeo. Na demo, o vídeo com as detecções é a janela do OpenCV do módulo de visão, posicionada ao lado do navegador.

## Fora do escopo

Não implementar: login, permissões reais, páginas de chamadas, filas, estacionamento, objetos, monitoramento de câmera ao vivo ou streaming de vídeo, mobile, animações complexas, GIS, busca avançada.

## Prioridade

1. mapa funcional;
2. ocupação visível (cores e legenda);
3. clique → detalhe;
4. tabela;
5. visão geral;
6. polimento.

O mapa e a informação de ocupação são mais importantes que efeitos visuais.

## Definition of Done

O frontend está pronto quando:

- funciona tanto com `NEXT_PUBLIC_USE_MOCK=true` quanto com a API real;
- abre o campus e navega até prédio e andar pelo breadcrumb;
- mostra ambientes coloridos pelo status da API, com legenda;
- `no_data` aparece em cinza e sem número;
- permite clicar em uma sala e ver seus dados e histórico;
- mostra a tabela, que abre o mesmo detalhe;
- mostra a visão geral;
- atualiza os dados automaticamente a cada ~2 s;
- sobrevive à API fora do ar sem tela em branco.
