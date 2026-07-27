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

## Documentação da API

Com o servidor rodando, acesse:

- **Swagger UI:** http://localhost:8000/docs
- **OpenAPI JSON:** http://localhost:8000/openapi.json

### Endpoints

#### Jogos

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/api/games` | Lista paginada (limit=60, offset=0). Suporta `?search=`, `?platform_id=`, `?status=`, `?genre_id=` |
| `GET` | `/api/games/{id}` | Detalhe de um jogo |
| `POST` | `/api/games` | Criar jogo |
| `PUT` | `/api/games/{id}` | Atualizar jogo |
| `DELETE` | `/api/games/{id}` | Remover jogo |

**Regras de negócio no POST/PUT:**
- `platform` (nome) e `genres[]` são criados automaticamente se não existirem
- `storage_device` (nome) é criado automaticamente se não existir
- `coop_type` aceita `list[str]` (ex: `["Sofá", "Online"]`), serializado como JSON no banco
- Se `gameplay_status == "Finalizado"` e `replay_score` for `null`, assume `3`

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
| `GET` | `/api/health` | Health check |

## Testar com curl

```bash
# Health
curl http://localhost:8000/api/health

# Plataformas
curl http://localhost:8000/api/platforms

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

# Listar jogos (com filtro)
curl "http://localhost:8000/api/games?status=Jogando&limit=10"
```

## Variáveis de ambiente

Copie `.env.example` para `.env`:

```
DATABASE_URL=sqlite:///./game_library.db
DEBUG=true
```

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
│   │   ├── games.py          # CRUD jogos
│   │   ├── genres.py         # CRUD gêneros
│   │   ├── platforms.py      # CRUD plataformas
│   │   └── storage.py        # CRUD discos
│   ├── services/             # (futuro: lógica de sync, metadados)
│   └── utils/                # (futuro: export/import xlsx)
├── requirements.txt
├── .env.example
├── DOCS_BACKEND.md           # Documentação técnica completa
└── README.md                 # Este arquivo
```
