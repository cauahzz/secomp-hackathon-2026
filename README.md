# ATLAS

**A**mbiente **T**ecnológico para **L**ogística e **A**nálise **S**istêmica — uma
camada operacional única para o campus universitário.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white)
![YOLO](https://img.shields.io/badge/Ultralytics-YOLO11-0B0B0B)
![License](https://img.shields.io/badge/license-MIT-blue)

Projeto desenvolvido durante o **hackathon da SECOMP — UNIFEI, campus de
Itajubá, 2026**, com o tema *Visão Computacional aplicada à Logística
Universitária*.

O que está aqui é o MVP, que responde a uma pergunta só:

> "Quantas pessoas estão em cada ambiente da universidade **agora**?"

A resposta vem de uma câmera comum: o vídeo vira detecção, a detecção vira
contagem por ambiente, e a contagem vira um mapa que alguém olha antes de
decidir para onde ir.

![Visão geral do campus](demo_pictures/home.jpeg)

## Índice

- [O problema](#o-problema)
- [O que o ATLAS é — e o que ele não é](#o-que-o-atlas-é--e-o-que-ele-não-é)
- [O contexto do hackathon](#o-contexto-do-hackathon)
- [Como funciona](#como-funciona)
- [Os três módulos](#os-três-módulos)
- [Requisitos](#requisitos) · [Instalação](#instalação) · [Como iniciar](#como-iniciar)
- [Configuração](#configuração) · [Testes](#testes)
- [A demonstração](#a-demonstração)
- [Precisão e limitações](#precisão-e-limitações)
- [Privacidade e LGPD](#privacidade-e-lgpd)
- [Documentação](#documentação) · [Estrutura do repositório](#estrutura-do-repositório)
- [Visão futura](#visão-futura) · [Licença](#licença) · [Equipe](#equipe)

## O problema

Saber quantas pessoas há em uma sala é um **dado**, não uma dor. A dor é a
decisão que alguém não consegue tomar por falta dele.

**O aluno procurando lugar para estudar.** "Para qual sala ou laboratório eu vou
agora?" Hoje ele anda pelos prédios abrindo portas. Com o ATLAS, abre o mapa e
vê quais ambientes estão livres.

**A gestão de infraestrutura.** "Onde desligar ar-condicionado e luzes?" "Esse
laboratório reservado está sendo usado de verdade?" Hoje se descobre por
reclamação, ou não se descobre. Com o ATLAS, o ambiente vazio aparece no mapa e
o uso real fica registrado no histórico.

Essas informações existem no campus, mas ficam dispersas — ou simplesmente não
são coletadas. A dor que o ATLAS resolve é a **falta de uma visão operacional
consolidada**.

## O que o ATLAS é — e o que ele não é

O ATLAS não é um contador de pessoas com YOLO. Contar pessoas é o primeiro dado
que ele produz, não o produto.

A proposta é uma camada operacional do campus: **mapear** onde estão as coisas,
**entender** o que está acontecendo, **integrar** fontes diferentes e **operar**
— transformar dado em decisão. Ocupação por câmera é uma fonte; agenda, chamada,
filas, estacionamento e sensores são outras, que entram depois pela mesma porta.

Por isso o centro do modelo de dados é o **espaço**, nunca a câmera:

```
SALA 102
 ├── câmera        ← a única fonte implementada no MVP
 ├── agenda
 ├── chamada
 ├── ocupação
 ├── histórico
 └── outras fontes
```

A câmera é apenas uma fonte de informação sobre o espaço. Trocar a câmera por um
sensor de presença, ou somar os dois, não muda o resto do sistema.

## O contexto do hackathon

| | |
|---|---|
| **Evento** | Hackathon da SECOMP — UNIFEI, campus de Itajubá, 2026 |
| **Tema** | Visão Computacional aplicada à Logística Universitária |
| **Janela de implementação** | cerca de 3 h 30 |
| **Equipe** | 5 pessoas — visão, backend, frontend e integração/pitch |
| **Apresentação** | pitch de 5 minutos |

O prazo curto definiu a estratégia: **pouco escopo, fluxo completo, demonstração
forte**. A regra que a equipe aplicou a cada decisão foi "isso é necessário para
demonstrar o MVP?" — e o que não era ficou de fora, declarado como visão futura
em vez de ficar pela metade.

A consequência prática disso foi o **esqueleto andante**: a cadeia inteira
existiu desde a primeira meia hora, com dados falsos nas pontas. A visão já
enviava contagens sintéticas pelo mesmo código de envio do modo real, a API já
respondia no formato final do contrato e o frontend já lia um JSON mockado com o
mesmo formato. Depois, cada pessoa trocou só a sua peça falsa pela real — e, se
alguma peça atrasasse, ainda haveria uma demo de ponta a ponta.

Os modos de teste que sobraram disso (`--fake` na visão, `NEXT_PUBLIC_USE_MOCK`
no site) continuam no repositório e estão documentados abaixo.

## Como funciona

Três módulos independentes, conectados por um contrato HTTP e por um arquivo de
configuração compartilhado:

```
   câmera / vídeo
         │
         ▼
  ┌─────────────┐   POST /ingest    ┌─────────────┐   GET /spaces    ┌─────────────┐
  │   vision/   │ ────────────────▶ │    api/     │ ◀─────────────── │  website/   │
  │ YOLO + ROIs │  a cada ~5 s      │  FastAPI    │  polling de 2 s  │  Next.js    │
  └─────────────┘                   └─────────────┘                  └─────────────┘
         │                                 │
         └──────── api/seed.json ──────────┘
              (estrutura do campus + ROIs)
```

**A visão** abre o vídeo, detecta apenas pessoas com YOLO, decide em qual região
(ROI) cada pessoa está pelo ponto dos pés, suaviza a contagem com uma mediana
deslizante e envia um `POST /ingest` por câmera.

![Detecção e contagem por ROI](demo_pictures/yolo.png)

**A API** grava cada contagem como um snapshot e calcula o status **na leitura**,
nunca na gravação. A razão é direta: um status gravado no ingest jamais viraria
`no_data`, porque `no_data` significa exatamente que o ingest parou de chegar.

| Status | Quando | Cor |
|---|---|---|
| `no_data` | a câmera está em silêncio há mais de 30 s, ou a ROI foi desabilitada | cinza |
| `empty` | nenhuma pessoa detectada | azul |
| `normal` | abaixo de 70 % do limite do ambiente | verde |
| `high` | entre 70 % e o limite | amarelo |
| `over_limit` | acima do limite | vermelho |

O limite é o `operational_limit` do ambiente; na falta dele, a `capacity`. Em
`no_data` a API devolve `person_count` e `occupancy_rate` como `null` e mantém o
`captured_at`: o dado some, o silêncio fica datado.

**O site** consome só os `GET` do contrato e nunca recalcula status — traduz o
código que vem da API em rótulo e cor. Se a API cair, a última tela continua no
lugar, um aviso aparece no topo e o polling segue tentando.

**`api/seed.json`** é a fonte única da estrutura: a API popula o banco a partir
dele e a visão lê dele as câmeras e as ROIs. Não existe endpoint de configuração
de ROI — mudar o campus é editar esse arquivo. Seed inválido derruba a API de
propósito, porque subir com a estrutura pela metade esconderia o erro até a hora
da demo.

| Rota | O quê |
|---|---|
| `GET /health` | `{"status": "ok"}` |
| `GET /structure` | campus → prédios → andares → ambientes |
| `GET /spaces` | todos os ambientes com a ocupação atual |
| `GET /spaces/{id}` | idem, mais a câmera/ROI de origem |
| `GET /spaces/{id}/history?minutes=30` | série temporal, até 500 pontos |
| `GET /summary` | agregados do campus |
| `POST /ingest` | usado **somente** pelo módulo de visão |

## Os três módulos

| Pasta | O quê | Stack | Porta | Detalhes |
|---|---|---|---|---|
| `api/` | backend e banco | Python · FastAPI · SQLAlchemy · SQLite | 8000 | [README](api/README.md) · [spec](docs/spec-api.md) |
| `vision/` | detecção e contagem | Python · OpenCV · Ultralytics YOLO | — | [README](vision/README.md) · [spec](docs/spec-visao.md) |
| `website/` | interface web | Next.js · React · TypeScript | 3000 | [README](website/README.md) · [spec](docs/spec-frontend.md) |

Cada módulo roda sozinho: a API sobe sem a visão (os ambientes ficam em
`no_data`), o site sobe sem a API (modo mock) e a visão sobe sem vídeo e sem
modelo (modo fake).

## Requisitos

- **Python 3.10 ou superior** — para a API e para a visão.
- **Node.js 20.9 ou superior** e **npm** — para o site.
- **Git**.
- Windows, se quiser usar o `atlas.bat`. Em Linux e macOS, a inicialização
  manual abaixo funciona igual.

O modelo YOLO (`yolo11n.pt`, ~6 MB) é baixado pela Ultralytics na primeira
execução real da visão — essa primeira vez precisa de internet.

## Instalação

Cada módulo Python tem o próprio ambiente virtual. O `atlas.bat` usa o `.venv`
de cada pasta quando ele existe e cai no Python do sistema quando não existe.

```bash
git clone <url-do-repositorio>
cd ATLAS
```

**API:**

```bash
cd api
python -m venv .venv
.venv\Scripts\activate           # Windows;  Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cd ..
```

**Visão:**

```bash
cd vision
python -m venv .venv
.venv\Scripts\activate           # Windows;  Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cd ..
```

**Site:**

```bash
cd website
npm install
cd ..
```

Nenhum dos três precisa de configuração para rodar: os padrões já apontam para
`localhost:8000` e `localhost:3000`, e o banco é criado e populado na primeira
subida da API.

## Como iniciar

### Windows, em um comando

```batch
atlas.bat
```

Sobe os três módulos, cada um na sua janela, na ordem certa: confere se as
portas estão livres, sobe a API, **espera o `/health` responder** e só então abre
o site e a visão. Depois é só abrir <http://localhost:3000>. Fechar as três
janelas encerra tudo.

```batch
atlas.bat fake
```

Mesma coisa, mas com a visão em modo fake: contagens sintéticas, sem vídeo e sem
YOLO. É o plano B para demonstrar o sistema em uma máquina sem câmera, sem GPU
ou sem internet.

As portas e a câmera saem do ambiente:

```batch
set API_PORT=8001 && set WEB_PORT=3001 && set CAMERA_ID=CAM-02 && atlas.bat
```

### Manualmente, em três terminais

Necessário em Linux e macOS, e útil para acompanhar o log de um módulo isolado.

```bash
# Terminal 1 — API
cd api
uvicorn app.main:app --reload --port 8000
```

```bash
# Terminal 2 — site
cd website
npm run dev
```

```bash
# Terminal 3 — visão (espere a API responder antes)
cd vision
python run.py --seed ../api/seed.json --camera-id CAM-01 --api-url http://localhost:8000
```

Acrescente `--fake` no terceiro para o modo sem vídeo, ou `--source 0` para usar
a webcam no lugar do vídeo de demonstração. A tecla `q` na janela da visão
encerra o processo.

Com tudo no ar:

| Endereço | O quê |
|---|---|
| <http://localhost:3000> | o site |
| <http://localhost:8000/docs> | documentação interativa da API |
| <http://localhost:8000/health> | teste rápido de que a API está viva |

### Sem backend nenhum

O site tem um modo mock com nove ambientes, as cinco situações de status e uma
câmera offline. Em `website/.env.local`:

```
NEXT_PUBLIC_USE_MOCK=true
```

## Configuração

Todas as variáveis são opcionais; os valores abaixo são os padrões.

**API** (`api/.env`, modelo em `api/.env.example`) — caminhos relativos são
resolvidos a partir de `api/`, não do diretório atual:

| Variável | Padrão | O quê |
|---|---|---|
| `ATLAS_DB_PATH` | `atlas.db` | arquivo SQLite |
| `ATLAS_SEED_PATH` | `seed.json` | seed lido pela API **e** pela visão |
| `ATLAS_CORS_ORIGINS` | `http://localhost:3000` | origens liberadas, separadas por vírgula |
| `ATLAS_NO_DATA_SECONDS` | `30` | silêncio da câmera que derruba o ambiente para `no_data` |

**Site** (`website/.env.local`, lido em tempo de build):

| Variável | Padrão | O quê |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | base da API |
| `NEXT_PUBLIC_USE_MOCK` | `false` | `true` lê os JSON de `lib/mock/` no lugar da API |

**Visão** (argumentos de linha de comando):

| Argumento | Padrão | O quê |
|---|---|---|
| `--seed` | `../api/seed.json` | de onde vêm câmera e ROIs |
| `--camera-id` | `CAM-01` | qual câmera do seed processar |
| `--api-url` | `http://localhost:8000` | para onde mandar o `/ingest` |
| `--source` | do seed | arquivo, índice de webcam ou URL de stream |
| `--process-fps` | `3.0` | quadros analisados por segundo |
| `--window` | `7.0` | janela da mediana, em segundos |
| `--send-interval` | `5.0` | intervalo entre ingests, em segundos |
| `--model` | `yolo11n.pt` | peso do modelo |
| `--conf` | `0.4` | limiar de confiança da detecção |
| `--no-window` | — | roda sem a janela do OpenCV |
| `--fake` | — | contagens sintéticas, sem vídeo e sem modelo |

Mudar `.env` ou `.env.local` exige reiniciar o processo correspondente.

## Testes

```bash
cd api
pip install -r requirements-dev.txt
python -m pytest
```

```bash
cd vision
python -m pytest tests -q          # ou: make test
```

Há ainda um smoke test ponta a ponta da visão contra uma API de mentira
(`vision/tools/mock_api.py`) e um `vision/evaluate.py`, que mede o erro da
contagem contra frames anotados à mão. Os dois estão descritos no
[README da visão](vision/README.md).

## A demonstração

As três telas, alimentadas pelo vídeo de demonstração em loop:

| Rota | Tela |
|---|---|
| `/` | Visão Geral: pessoas no campus, ambientes por situação, mais cheios agora |
| `/mapa` | Mapa: campus → prédio → andar → ambiente |
| `/ambientes` | Tabela com todos os ambientes, com busca |

<p align="center">
  <img src="demo_pictures/map_main.jpeg" width="49%" alt="Mapa do campus">
  <img src="demo_pictures/map_sala102_2.jpeg" width="49%" alt="Detalhe de um ambiente">
</p>

Cada prédio no mapa recebe a cor do seu ambiente mais crítico. Cor nunca é a
única informação: todo indicador vem acompanhado de rótulo em texto.

**Uma ressalva honesta sobre a demo:** o seed usa **uma câmera só**, dividida em
duas ROIs que representam duas salas diferentes. É uma simulação de várias
fontes, não duas câmeras de verdade — a equipe declarou isso no pitch em vez de
deixar o jurado descobrir. O caminho dos dados, esse é o real: vídeo → YOLO →
ROI → ocupação → banco → API → frontend, sem atalho em nenhum ponto.

O vídeo roda em loop justamente porque, quando ele termina, os envios param e,
30 segundos depois, todos os ambientes viram "sem dados" no meio da
apresentação.

## Precisão e limitações

O MVP usa um modelo pré-treinado, sem ajuste para o campus. Ele erra, e as
limitações são parte da entrega, não um detalhe escondido:

- **oclusão** — pessoas atrás de outras, de cadeiras e de mesas; é o erro mais
  comum em sala com gente sentada;
- **iluminação** e contraste da cena;
- **ângulo e posição da câmera** — ângulo alto e corpo inteiro visível contam
  muito melhor do que câmera de frente;
- **câmera sem calibração**;
- **modelo pré-treinado**, não ajustado para o campus;
- **avaliação em um único vídeo**, que não representa o campus inteiro.

Para medir em vez de estimar, o repositório traz o `vision/evaluate.py`: ele
extrai ~20 frames espaçados do vídeo, a equipe anota manualmente a contagem de
cada ROI em um CSV, e o script roda o mesmo modelo com o mesmo limiar e imprime
o **erro médio absoluto (MAE) por ROI e geral**, sem suavização. O passo a passo
está no [README da visão](vision/README.md).

## Privacidade e LGPD

Imagem de pessoas é dado pessoal pela LGPD, mesmo sem identificação. O ATLAS foi
desenhado em volta disso:

- detecta **pessoas, não identidades** — só a classe `person` do YOLO, sem
  reconhecimento facial e sem tracking entre quadros;
- processa o vídeo **em memória** e descarta o frame após a contagem;
- **nenhum frame é gravado ou transmitido** — o que sai da câmera é um número
  inteiro por região;
- o banco guarda contagens e horários, **nunca imagens**.

Reconhecimento facial e chamada por identificação não estão na visão do produto.
Se um dia forem considerados, terão que ser um módulo separado, com requisitos
próprios de segurança, governança e autorização.

## Documentação

| Documento | O quê |
|---|---|
| [`docs/spec-api.md`](docs/spec-api.md) | contrato HTTP, modelo de dados, regras de status |
| [`docs/spec-visao.md`](docs/spec-visao.md) | detecção, ROIs, suavização, resiliência, avaliação |
| [`docs/spec-frontend.md`](docs/spec-frontend.md) | telas, estados, identidade visual e paleta |
| [`docs/pitch.pdf`](docs/pitch.pdf) | os slides apresentados no pitch de 5 minutos |

As três specs foram escritas **antes** do código, na primeira meia hora do
hackathon. É delas que sai o contrato que permitiu os três módulos avançarem em
paralelo, sem um esperar pelo outro.

## Estrutura do repositório

```
api/                 backend FastAPI + SQLite
  seed.json          estrutura do campus e ROIs (fonte única)
  app/               aplicação
  tests/             um teste por item do Definition of Done
vision/              agente de visão computacional
  run.py             ponto de entrada
  atlas_vision/      detecção, ROIs, suavização, cliente de ingest
  evaluate.py        medição de precisão contra anotação manual
  tools/mock_api.py  API de mentira para smoke test
website/             interface Next.js
  app/               as três telas
  lib/api.ts         único ponto de contato com o backend
  lib/mock/          modo mock, no formato exato do contrato
docs/                as specs dos três módulos
demo_pictures/       capturas de tela usadas neste README
atlas.bat            sobe os três módulos de uma vez (Windows)
```

## Convenções

- Identificadores em inglês; comentários, textos de tela e documentação em
  português.
- Comentário explica o **porquê** de uma decisão não-óbvia, nunca o que o código
  já diz.
- O status vem pronto da API; nenhum outro módulo recalcula faixa ou status.
- No site, cor só sai de token CSS — nenhum hex fora de `app/globals.css`.

## Visão futura

O MVP entrega ocupação. A mesma arquitetura, com o espaço no centro, comporta as
próximas fontes sem reescrita:

chamada e frequência (como integração com o sistema acadêmico, não por
identificação em câmera) · filas e tempo de espera do RU · alerta de
superlotação · estacionamento · objetos perdidos · integração com a agenda de
salas · eventos · sensores · APIs externas.

O destino é uma plataforma única para entender e operar o campus.

### Fora do escopo do MVP

Autenticação, permissões, WebSocket, eventos, reconhecimento facial, filas,
microserviços, cloud, endpoint de configuração de ROI e streaming de vídeo.

O MVP não existe para ser a plataforma completa — existe para provar, de ponta a
ponta, que a arquitetura funciona.

## Licença

Este projeto está sob a licença [MIT](LICENSE): use, modifique e redistribua à
vontade, mantendo o aviso de copyright.

### Licenças de terceiros

Nenhuma dependência está incluída neste repositório — todas são instaladas pelo
`pip` ou pelo `npm` e mantêm a própria licença. Uma delas pede atenção:

| Dependência | Licença |
|---|---|
| **`ultralytics` (YOLO)** | **AGPL-3.0** |
| FastAPI, SQLAlchemy, Next.js, React | MIT |
| OpenCV, requests | Apache-2.0 |
| uvicorn, numpy | BSD-3-Clause |

A AGPL-3.0 do `ultralytics` alcança quem distribui uma obra derivada **e também
quem oferece o sistema como serviço pela rede** — nos dois casos, com a
obrigação de publicar o código-fonte correspondente. Para uso fechado, a
Ultralytics vende licença comercial.

A outra saída é trocar o detector: todo o contato com o YOLO está em uma classe
só, `PersonDetector`, em `vision/atlas_vision/detector.py`. O restante do módulo
de visão enxerga apenas uma lista de `Detection`, então substituir o modelo por
um de licença permissiva é mexer em um arquivo.

## Equipe

Desenvolvido por uma equipe de cinco pessoas durante o hackathon da SECOMP na
UNIFEI (Itajubá, 2026), com as frentes divididas entre visão computacional,
backend, frontend e integração.

Este repositório é mantido por [@cauahzz](https://github.com/cauahzz).
