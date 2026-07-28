# Game Library — Backend

API REST para gerenciamento de biblioteca pessoal de jogos. Parte do sistema Game Library Dashboard.

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Framework | FastAPI |
| Banco | SQLite (via SQLModel / SQLAlchemy) |
| Validação | Pydantic |
| Servidor | Uvicorn |
| Export | openpyxl |

## Pré-requisitos

- Python 3.10+
- pip

## Setup

```bash
# Criar ambiente virtual
python -m venv venv

# Ativar
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Iniciar servidor (http://localhost:8000)
uvicorn app.main:app --reload
```

O servidor cria o banco `game_library.db` e popula automaticamente no primeiro startup:
- **16 plataformas** (PC Steam, Epic, GOG, EA, Ubisoft, 3DS, DS, GBA, N64, GameCube, PS1, PS2, PSP, SNES, Switch, Wii)
- **4 discos** (SSD Windows, HD ROMs, HD Singleplayer, HD Multiplayer)

Para popular com dados de exemplo (63 jogos fictícios):
```bash
python seed_games.py
```

## Documentação da API

Com o servidor rodando, acesse:

- **Swagger UI:** http://localhost:8000/docs
- **OpenAPI JSON:** http://localhost:8000/openapi.json

### Endpoints

#### Jogos

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/api/games` | Lista paginada (limit=60, offset=0). Suporta `?search=`, `?status=`, `?platform=`, `?genre=`, `?hds=`, `?coop_type=`, `?interest_min=`, `?interest_max=`, `?sort=` |
| `GET` | `/api/games/{id}` | Detalhe de um jogo |
| `POST` | `/api/games` | Criar jogo |
| `PUT` | `/api/games/{id}` | Atualizar jogo (permite alterar todos os campos) |
| `DELETE` | `/api/games/{id}` | Remover jogo |

**Regras de negócio no POST/PUT:**
- `platform` (nome) e `genres[]` são criados automaticamente se não existirem
- `storage_device` (nome) é criado automaticamente se não existir
- `coop_type` aceita `list[str]` (ex: `["Sofá", "Online"]`), serializado como JSON no banco
- Se `gameplay_status == "Finalizado"` e `replay_score` for `null`, assume `3`
- Qualquer campo não informado mantém o valor atual (no PUT)

#### Catálogos

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/api/genres` | Lista gêneros (com `game_count`) |
| `POST` | `/api/genres` | Criar gênero |
| `PUT` | `/api/genres/{id}` | Renomear gênero |
| `DELETE` | `/api/genres/{id}` | Remove (erro 409 se em uso) |
| `GET` | `/api/platforms` | Lista plataformas (com `game_count`) |
| `POST` | `/api/platforms` | Criar plataforma |
| `PUT` | `/api/platforms/{id}` | Renomear plataforma |
| `DELETE` | `/api/platforms/{id}` | Remove (erro 409 se em uso) |
| `GET` | `/api/storage-devices` | Lista discos (com `game_count`) |
| `POST` | `/api/storage-devices` | Criar disco |
| `PUT` | `/api/storage-devices/{id}` | Renomear disco |
| `DELETE` | `/api/storage-devices/{id}` | Remove (erro 409 se em uso) |

#### Utilitários

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/api/export/xlsx` | Exportar planilha .xlsx |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/metadata/hltb?title=` | Busca HLTB (HowLongToBeat) com arredondamento |

#### Sincronização

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/api/sync/playnite` | Recebe JSON nativo do Playnite, upsert por `playnite_id`. Mapeamento completo de campos |
| `POST` | `/api/games/batch` | Upsert em lote via JSON. Se `playnite_id` existir, atualiza; se não, cria |

**Regras do `POST /api/sync/playnite`:**
- Aceita o formato nativo de exportação do Playnite (`PlayniteGame[]`)
- Mapeia `Id`, `Name`, `Platforms`+`Source`, `Genres`, `CompletionStatus`, `Categories` (coop), `Features` (input/screen), `InstallDirectory` (storage), `CoverImage`/`BackgroundImage` (cover serving), `Playtime`, `Notes`
- Upsert por `playnite_id`: se existir, atualiza apenas campos do Playnite (preserva `hltb_*`, `interest_rating`, `replay_score`, `score`, `must_test`, `finish_hours`, `finish_date`)
- Jogos com `Hidden: true` ou categoria `frontend launcher` são ignorados
- `_detect_platform()`: case-insensitive, suporta PC(Steam/Epic/GOG/EA/Ubisoft), Switch, 3DS, DS, GBA, N64, GameCube, SNES, Wii, PS1, PS2, PSP
- `_detect_storage_from_path()`: extrai drive letter do `InstallDirectory` → busca `StorageDevice.drive_letter`

**Regras do batch upsert (`POST /api/games/batch`):**
- `playnite_id` é opcional — se omitido, sempre cria registro novo
- Se `playnite_id` informado e já existir, todos os campos são sobrescritos
- Resposta inclui `action: "created" | "updated"` por item

#### Covers

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/api/covers/playnite/{playnite_id}/{filename}` | Serve imagens de capa da pasta `./playnite_covers` |

## Testar com curl

```bash
# Health
curl http://localhost:8000/api/health

# Plataformas
curl http://localhost:8000/api/platforms

# Listar jogos com filtros
curl "http://localhost:8000/api/games?status=Jogando&limit=10"

# Criar jogo
curl -X POST http://localhost:8000/api/games \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Elden Ring",
    "genres": ["RPG", "Ação", "Mundo Aberto"],
    "platform": "PC (Steam)",
    "storage_device": "SSD Windows",
    "gameplay_status": "Jogando",
    "interest_rating": 5,
    "coop_type": ["Online"],
    "input_recommendation": "Controle"
  }'
```

## Filtros Multi-Valor

A API suporta filtros multi-valor via query params separados por vírgula:

```
GET /api/games?status=Backlog,Jogando&platform=PC (Steam),Switch&genre=RPG,Aventura&interest_min=3&interest_max=5&coop_type=Sofá,Online&hds=SSD Windows,__uninstalled__&sort=title:asc,interest_rating:desc
```

## Variáveis de ambiente

Copie `.env.example` para `.env`:

```
DATABASE_URL=sqlite:///./game_library.db
DEBUG=true
COVERS_DIR=./playnite_covers
```

- `COVERS_DIR`: diretório com as capas exportadas do Playnite. O endpoint `GET /api/covers/playnite/{id}/{file}` serve arquivos daqui.

## Estrutura de pastas

```
server/
├── app/
│   ├── main.py              # FastAPI app + CORS + seed
│   ├── config.py             # Settings
│   ├── database.py           # Engine + sessão SQLite
│   ├── models/
│   │   ├── game.py           # Game + GameGenreLink
│   │   ├── genre.py          # Genre
│   │   ├── platform.py       # Platform
│   │   └── storage_device.py # StorageDevice
│   ├── routers/
│   │   ├── games.py          # CRUD jogos + batch upsert
│   │   ├── genres.py         # CRUD gêneros
│   │   ├── platforms.py      # CRUD plataformas
│   │   ├── storage.py        # CRUD discos
│   │   ├── export.py         # Export XLSX
│   │   ├── sync.py           # POST /api/sync/playnite
│   │   └── metadata.py       # GET /api/metadata/hltb
│   ├── services/
│   │   └── hltb.py           # Busca HLTB + arredondamento
│   └── utils/
│       └── xlsx.py           # Geração de planilha .xlsx
├── requirements.txt
├── .env.example
├── DOCS_BACKEND.md           # Documentação técnica completa
└── README.md                 # Este arquivo
```
