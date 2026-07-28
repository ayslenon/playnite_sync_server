# Game Library — Backend

API REST para gerenciamento de biblioteca pessoal de jogos. Recebe dados do Playnite (Windows), serve o dashboard React e mantém metadados (HLTB, notas, status). Projetado para rodar em servidor local (Ubuntu) na rede doméstica.

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Framework | FastAPI |
| Banco | SQLite via SQLModel / SQLAlchemy |
| Validação | Pydantic v2 |
| Servidor | Uvicorn |
| Export | openpyxl |
| Metadados | howlongtobeatpy |

## Pré-requisitos

- Python 3.10+
- pip

## Setup rápido

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

O servidor cria `game_library.db` e popula automaticamente no primeiro startup:
- **16 plataformas** (PC Steam/Epic/GOG/EA/Ubisoft, 3DS, DS, GBA, N64, GameCube, PS1, PS2, PSP, SNES, Switch, Wii)
- **4 discos** (SSD Windows, HD ROMs, HD Singleplayer, HD Multiplayer)

### Dados de exemplo

```bash
python seed_games.py              # 63 jogos fictícios
python seed_games.py --bulk 413   # N jogos aleatórios (perf test)
```

---

## Documentação da API

Com o servidor rodando:
- **Swagger UI:** http://localhost:8000/docs
- **OpenAPI JSON:** http://localhost:8000/openapi.json

### Endpoints

#### Jogos

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/api/games` | Lista paginada com filtros: `search`, `status`, `platform`, `genre`, `hds`, `coop_type`, `interest_min`, `interest_max`, `favorite`, `sort` |
| `GET` | `/api/games/{id}` | Detalhe |
| `POST` | `/api/games` | Criar |
| `PUT` | `/api/games/{id}` | Atualizar |
| `DELETE` | `/api/games/{id}` | Remover |
| `POST` | `/api/games/batch` | Upsert em lote por `playnite_id` |

#### Catálogos

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` `/POST` `/PUT` `/DELETE` | `/api/genres` | CRUD gêneros (com `game_count`) |
| `GET` `/POST` `/PUT` `/DELETE` | `/api/platforms` | CRUD plataformas (com `game_count`) |
| `GET` `/POST` `/PUT` `/DELETE` | `/api/storage-devices` | CRUD discos (com `game_count`) |

#### Sincronização

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/api/sync/playnite` | JSON nativo do Playnite → upsert por `playnite_id`. Mapeia campos, preserva HLTB/notas. Ignora Hidden/frontend. |
| `GET` | `/api/sync/playnite/changes` | (futuro) Pull de modificações |

#### Utilitários

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/api/export/xlsx` | Download .xlsx com formatação |
| `GET` | `/api/metadata/hltb?title=` | Busca HLTB (HowLongToBeat) |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/covers/playnite/{id}/{file}` | Serve capas da pasta `./app/files` |

### Regras de negócio

- `platform`, `genres`, `storage_device` são **auto-criados** se não existirem
- `coop_type` aceita `list[str]` → serializado como JSON no banco
- Se `gameplay_status == "Finalizado"` e `replay_score` for `null`, assume `3`
- `POST /api/sync/playnite` preserva `hltb_*`, `interest_rating`, `replay_score`, `score`, `must_test`, `finish_hours`, `finish_date`

### Filtros multi-valor

```
GET /api/games?status=Backlog,Jogando&platform=PC,Switch&genre=RPG,Aventura&interest_min=3&favorite=true&sort=title:asc,interest_rating:desc
```

---

## Variáveis de ambiente

| Variável | Default | Descrição |
|----------|---------|-----------|
| `DATABASE_URL` | `sqlite:///./game_library.db` | Caminho do banco |
| `DEBUG` | `true` | Modo debug (SQL echo) |
| `COVERS_DIR` | `./app/files` | Diretório com capas exportadas do Playnite |

Copie `.env.example` para `.env` e ajuste se necessário.

---

## Estrutura do projeto

```
server/
├── app/
│   ├── main.py                 # FastAPI app, CORS, lifespan, seed, covers
│   ├── config.py               # Settings (pydantic-settings)
│   ├── database.py             # Engine + sessão SQLite
│   ├── schemas.py              # Pydantic schemas (GameCreate, PlayniteGame, etc.)
│   ├── models/
│   │   ├── game.py             # Game + GameGenreLink (SQLModel)
│   │   ├── genre.py            # Genre
│   │   ├── platform.py         # Platform
│   │   └── storage_device.py   # StorageDevice
│   ├── routers/
│   │   ├── games.py            # CRUD jogos + batch upsert
│   │   ├── sync.py             # Sincronização Playnite
│   │   ├── genres.py           # CRUD gêneros
│   │   ├── platforms.py        # CRUD plataformas
│   │   ├── storage.py          # CRUD discos
│   │   ├── export.py           # Export XLSX
│   │   └── metadata.py         # Busca HLTB
│   ├── services/
│   │   └── hltb.py             # Cliente HowLongToBeat
│   └── utils/
│       └── xlsx.py             # Geração de planilha
├── requirements.txt
├── .env / .env.example
├── seed_games.py               # Dados de exemplo
├── DOCS_BACKEND.md             # Documentação técnica completa
└── README.md                   # Este arquivo
```

## Arquitetura

### Fluxo de dados principal

```
Playnite (Windows)
    │ POST /api/sync/playnite
    ▼
FastAPI → SQLite (game_library.db)
    │ GET /api/games
    ▼
Dashboard (React) → usuário
```

### Camadas

- **Routers** recebem requests, delegam para helpers, retornam responses
- **Models** (SQLModel) definem schema do banco + relacionamentos
- **Schemas** (Pydantic) definem contratos de entrada/saída com validação
- **Services** encapsulam lógica externa (HLTB)
- **Utils** funções auxiliares (export XLSX)

O banco é SQLite com WAL mode implícito. Timestamps são strings ISO 8601. `coop_type` é JSON serializado em coluna `Text`.

---

## Changelog

### v1.2.1
- Fix: `COVERS_DIR` alterado de `./playnite_covers` para `./app/files` (diretório real com 648 capas)
- Fix: `PLATFORM_MAP` — adicionadas chaves faltantes (Nintendo Game Boy Advance, Nintendo SNES, Sony PlayStation/2/PSP, macOS)
- Fix: `COMPLETION_MAP` — adicionadas entradas em português (jogando, finalizado, abandonado)
- Fix: gênero "Outro" não é mais atribuído automaticamente — jogos sem gênero ficam sem gênero
- Schema: `GameCreate.genres` sem `min_length` obrigatório (permite jogos sem gênero)
- Docs: README.md reescrito com arquitetura, DOCS_BACKEND.md com nova seção de arquitetura

### v1.2.0
- Campo `favorite` (bool) adicionado ao model Game + schemas + CRUD + filtro `?favorite=true`
- `_normalize_platform()`: extrai plataforma base removendo parênteses (ex: "PC (Windows)" → "PC")
- `_map_tags_coop_players()`: Tags do Playnite sobrescrevem `coop_players` detectado via Categories
- Endpoint `GET /api/covers/playnite/{id}/{file}` para servir capas
- `fromApi()` no frontend normaliza URLs de cover/background para absolutas

### v1.1.2
- `POST /api/sync/playnite` com mapeamento completo de campos Playnite → Game Library
- `_detect_platform()`: case-insensitive, suporta PC (Steam/Epic/GOG/EA/Ubisoft), Switch, 3DS, DS, GBA, N64, PS1, PS2, PSP, SNES, Wii, GameCube
- `_detect_storage_from_path()`: extrai drive letter do `InstallDirectory`
- Skip de jogos ocultos (Hidden) e categoria "frontend launcher"
- `_update_game_from_playnite()`: preserva HLTB, interesse, nota, must_test, horas/data de finalização

### v1.1.1
- Validação Pydantic: Literal types para status, coop, input; validação de campos não-negativos; ISO date
- `GET /api/metadata/hltb`: busca HLTB com arredondamento `ceil(x*2)/2`
- Cache-Control: `no-cache` para games, 1h para catálogos, 1 ano para covers
- Batch upsert: `POST /api/games/batch` com upsert por `playnite_id`
- Timeout de 15s no fetch do frontend via AbortController

### v1.1.0
- `GET /api/export/xlsx`: exporta planilha .xlsx com formatação (cabeçalho roxo, linhas coloridas por status)
- Termos padronizados: Versus, Tela Dividida, 1 Jogador

### v1.0.0
- Versão inicial: CRUD jogos, CRUD catálogos, seed de plataformas/discos, SQLite via SQLModel

---

## Desenvolvimento

### Commits

Os commits seguem versão semântica (`v1.2.1`). Tanto server quanto dashboard têm repositórios git independentes.

### Convenções

- Campos em **português** (gameplay_status, coop_type, input_recommendation)
- `playnite_id` como chave de matching (unique, nullable)
- Rotas prefixadas com `/api/`
- CORS aberto (`allow_origins=["*"]`) — rede local
- Capas com Cache-Control de 1 ano (imutável)
- Dados com `no-cache` (sempre revalidar)
