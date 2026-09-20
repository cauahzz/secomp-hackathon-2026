# Mapas SVG

Convenção do contrato:

- nome do arquivo = ID do nível (`unifei-itabira.svg`, `bld-1-f2.svg`);
- no mapa do campus, cada prédio clicável tem `id` igual ao ID do prédio;
- na planta de um andar, cada ambiente clicável tem `id` igual ao ID do space;
- o nível de prédio não precisa de SVG — a interface mostra a lista de andares.

Duas convenções a mais, usadas pela pintura:

- marque o elemento com `class="atlas-space"` (ambiente) ou `class="atlas-building"`
  (prédio). Só os elementos marcados são repintados; paredes, textos e fundo
  ficam como foram desenhados. Um elemento marcado sem ambiente correspondente
  na API fica em `--map-inactive`;
- use os tokens (`var(--map-stroke)`, `var(--map-inactive)`, `var(--text)`) no
  desenho: o SVG é carregado inline e herda as variáveis de `globals.css`.

Textos vão fora do grupo clicável, com `pointer-events="none"`.

O desenho precisa de `viewBox`; `width` e `height` fixos são removidos ao
carregar. A altura sai da proporção do próprio desenho (limitada em
`.map-surface`, no `globals.css`), então o mapa ocupa a tela toda no desktop e
não deixa faixa vazia no celular.

Se o SVG de um nível não existir, a interface cai para a lista de ambientes
daquele andar, sem quebrar.
