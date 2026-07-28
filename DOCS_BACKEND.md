# Game Library — Backend (FastAPI + SQLite)

## Índice

1. [Stack e Decisões Técnicas](#1-stack-e-decisões-técnicas)
2. [Estrutura de Pastas](#2-estrutura-de-pastas)
3. [Schema do Banco de Dados](#3-schema-do-banco-de-dados)
4. [Endpoints da API](#4-endpoints-da-api)
5. [Contratos JSON](#5-contratos-json)
6. [Fluxo de Sincronização Playnite](#6-fluxo-de-sincronização-playnite)
7. [Sequência de Implementação](#7-sequência-de-implementação)

---

## 1. Stack e Decisões Técnicas

| Decisão                | Escolha                 | Motivo                                                                              |
| ---------------------- | ----------------------- | ----------------------------------------------------------------------------------- |
| **Framework**          | FastAPI                 | Assíncrono, validação automática com Pydantic, gera Swagger/OpenAPI grátis          |
| **Banco**              | SQLite via SQLModel     | Zero configuração, arquivo único, embarcado. Perfeito para Raspberry Pi/Oracle Free |
| **ORM**                | SQLModel                | Unifica Pydantic + SQLAlchemy. Models servem como schema de validação E tabelas     |
| **Migration**          | SQLModel `create_all()` | Sem ferramenta externa. No startup, cria as tabelas se não existirem                |
| **Servidor**           | Uvicorn                 | ASGI server padrão do FastAPI                                                       |
| **Export XLSX**        | openpyxl                | Maduro, sem dependências pesadas                                                    |
| **Cache de metadados** | SQLite (na mesma DB)    | Evita refetch de HLTB/IGDB                                                          |
| **Auth**               | Nenhuma (fase 1)        | Ambiente local/Raspberry. Futuramente API Key simples                               |

### Por que SQLite em vez de PostgreSQL?

- Você quer rodar em Raspberry Pi ou Oracle Cloud Free Tier — SQLite é zero configuração
- Biblioteca de jogos: < 10.000 registros, < 50MB — SQLite aguenta tranquilamente
- WAL mode (`PRAGMA journal_mode=WAL`) permite leitura concorrente durante escrita
- Backup = copiar o arquivo `.db`

---

## 2. Estrutura de Pastas

```
server/
├── app/
│   ├── __init__.py
│   ├── main.py                # FastAPI app, CORS, startup, importadores
│   ├── config.py              # Settings via pydantic-settings (.env)
│   ├── database.py            # Engine SQLite + init_db()
│   ├── models/
│   │   ├── __init__.py
│   │   ├── game.py            # Game model + schemas Pydantic
│   │   ├── genre.py           # Genre model + schema
│   │   ├── platform.py        # Platform model + schema
│   │   └── storage_device.py  # StorageDevice model + schema
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── games.py           # CRUD /api/games
│   │   ├── genres.py          # CRUD /api/genres
│   │   ├── platforms.py       # CRUD /api/platforms
│   │   ├── storage.py         # CRUD /api/storage-devices
│   │   ├── export.py          # GET /api/export/xlsx
│   │   ├── sync.py            # (futuro) POST /api/sync/playnite
│   │   └── metadata.py        # (futuro) Busca IGDB/RAWG/HLTB
│   ├── services/
│   │   ├── __init__.py
│   │   ├── playnite_merge.py  # Lógica de merge bidirecional
│   │   ├── metadata.py        # Clientes IGDB, RAWG, SteamGridDB
│   │   └── hltb.py            # Cliente HowLongToBeat
│   └── utils/
│       ├── __init__.py
│       └── xlsx.py            # Export/import de planilha .xlsx
├── .env.example
├── requirements.txt
├── seed_games.py               # Popula 63 jogos fictícios para teste
└── DOCS_BACKEND.md            # Este arquivo
```

---

## 3. Schema do Banco de Dados

### Tabela: `games`

```sql
CREATE TABLE games (
    id              TEXT PRIMARY KEY,          -- UUID string (ex: "1", "abc-123")
    playnite_id     TEXT UNIQUE,               -- GUID do Playnite (chave de matching)
    title           TEXT NOT NULL,
    cover_url       TEXT,
    background_url  TEXT,

    -- Plataforma (FK)
    platform_id     INTEGER REFERENCES platforms(id),

    -- Armazenamento (FK, nullable = não instalado)
    storage_device_id INTEGER REFERENCES storage_devices(id),

    -- Gameplay
    gameplay_status     TEXT NOT NULL DEFAULT 'Backlog',  -- Backlog | Jogando | Finalizado | Abandonado
    interest_rating     INTEGER NOT NULL DEFAULT 3,       -- 1-5
    replay_score        INTEGER,                          -- 1-5 (NULL se não finalizado)
    score               TEXT,                              -- "9/10", "8.5"
    must_test           INTEGER NOT NULL DEFAULT 0,       -- BOOL

    -- Finalização
    finish_hours        REAL,
    finish_date         TEXT,                -- ISO 8601

    -- HLTB
    hltb_main           REAL NOT NULL DEFAULT 0,
    hltb_main_extra     REAL NOT NULL DEFAULT 0,
    hltb_full           REAL NOT NULL DEFAULT 0,

    -- Coop (serializado como JSON string)
    coop_players        TEXT NOT NULL DEFAULT '1 Jogador',
    coop_type           TEXT NOT NULL DEFAULT '["Um Jogador"]',  -- JSON array
    coop_screen_type    TEXT NOT NULL DEFAULT 'Tela Inteira',

    -- Input
    input_recommendation TEXT NOT NULL DEFAULT 'Controle',

    -- Tempo registrado (não usado como regra de finalização)
    playtime_seconds    INTEGER DEFAULT 0,

    -- Anotações
    notes               TEXT,

    -- Auditoria
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### Tabela: `genres`

```sql
CREATE TABLE genres (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL UNIQUE
);
```

### Tabela: `platforms`

```sql
CREATE TABLE platforms (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL UNIQUE
);
```

### Tabela: `storage_devices`

```sql
CREATE TABLE storage_devices (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL UNIQUE
);
```

### Tabela: `game_genres` (N:N)

```sql
CREATE TABLE game_genres (
    game_id     TEXT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    genre_id    INTEGER NOT NULL REFERENCES genres(id) ON DELETE CASCADE,
    PRIMARY KEY (game_id, genre_id)
);
```

### ⚠️ Nota sobre `coop_type` como JSON string

`coop_type` armazena um JSON array serializado como texto, ex: `'["Sofá","Online"]'`. Motivo:

- Evitar mais 2 tabelas (coop_types, game_coop_types) para um campo de uso marginal
- SQLite suporta `json_extract()` para consultas, se necessário
- Pydantic valida na serialização: o campo chega como `list[str]` no Python e é stringificado ao salvar

### Seed Data: Plataformas e Discos

No startup, o backend popula as tabelas `platforms` e `storage_devices` com os valores padrão:

**Plataformas:**
PC (Steam), PC (Epic), PC (GOG), PC (EA), PC (Ubisoft), 3DS, DS, GBA, N64, GameCube, PS1, PS2, PSP, SNES, Switch, Wii

**Discos (mapeamento real do usuário):**
| Letra | Nome | Uso |
|---|---|---|
| C: | SSD Windows | Sistema + jogos atuais |
| R: | HD ROMs | ROMs de emuladores |
| J: | HD Singleplayer | Jogos singleplayer |
| M: | HD Multiplayer | Jogos multiplayer |

---

## 4. Endpoints da API

### 4.1 CRUD de Jogos

| Método   | Rota                                                                                  | Descrição                          |
| -------- | ------------------------------------------------------------------------------------- | ---------------------------------- |
| `GET`    | `/api/games`                                                                          | Lista jogos (paginado, 60 por vez) |
| `GET`    | `/api/games?limit=60&offset=0&search=witcher&platform_id=1&status=Backlog&genre_id=3` | Lista com filtros                  |
| `GET`    | `/api/games/{id}`                                                                     | Detalhe de um jogo                 |
| `POST`   | `/api/games`                                                                          | Criar jogo                         |
| `PUT`    | `/api/games/{id}`                                                                     | Atualizar jogo                     |
| `DELETE` | `/api/games/{id}`                                                                     | Remover jogo                       |

**Regras de negócio na criação/atualização:**

- Se `platform.name` não existe em `platforms`, **cria automaticamente** antes de associar
- Se `storage_device.name` não existe em `storage_devices`, **cria automaticamente**
- Se `genres[].name` não existe em `genres`, **cria cada um automaticamente**
- Se `gameplay_status == "Finalizado"` e `replay_score` for `null`, define como `3` (neutro)
- `coop_type` aceita `list[str]` e converte para JSON string ao salvar

### 4.2 Catálogos (para alimentar selects do frontend)

| Método   | Rota                        | Descrição                               |
| -------- | --------------------------- | --------------------------------------- |
| `GET`    | `/api/genres`               | Lista todos os gêneros                  |
| `POST`   | `/api/genres`               | Criar gênero                            |
| `PUT`    | `/api/genres/{id}`          | Renomear gênero                         |
| `DELETE` | `/api/genres/{id}`          | Remover gênero (erro se estiver em uso) |
| `GET`    | `/api/platforms`            | Lista todas as plataformas              |
| `POST`   | `/api/platforms`            | Criar plataforma                        |
| `PUT`    | `/api/platforms/{id}`       | Renomear plataforma                     |
| `DELETE` | `/api/platforms/{id}`       | Remover plataforma (erro se em uso)     |
| `GET`    | `/api/storage-devices`      | Lista todos os discos                   |
| `POST`   | `/api/storage-devices`      | Criar disco                             |
| `PUT`    | `/api/storage-devices/{id}` | Renomear disco                          |
| `DELETE` | `/api/storage-devices/{id}` | Remover disco (erro se em uso)          |

### 4.3 Sincronização

| Método | Rota                                        | Descrição                                           |
| ------ | ------------------------------------------- | --------------------------------------------------- |
| `POST` | `/api/sync/playnite`                        | Recebe batch do Playnite, upsert, retorna merge     |
| `GET`  | `/api/sync/playnite/changes?since=ISO_DATE` | Jogos modificados após data (para pull do Playnite) |

### 4.4 Migração (Planilha → Banco)

| Método | Rota                | Descrição                             |
| ------ | ------------------- | ------------------------------------- |
| `POST` | `/api/migrate/xlsx` | Upload de .xlsx, importa para o banco |
| `GET`  | `/api/export/xlsx`  | Gera .xlsx dump do banco              |

### 4.5 Metadados (futuro)

| Método | Rota                             | Descrição                            |
| ------ | -------------------------------- | ------------------------------------ |
| `GET`  | `/api/metadata/search?title=...` | Busca capa + metadados via IGDB/RAWG |
| `GET`  | `/api/metadata/hltb?title=...`   | Busca no HowLongToBeat               |

> Nota: metadados de `release_date`, `developers`, `publishers` e `tags` não são armazenados no servidor. O foco é capa, background e HLTB.

---

## 5. Contratos JSON

### 5.1 GET `/api/games` (Lista paginada)

**Response:**

```json
{
	"items": [
		{
			"id": "abc123def456",
			"playnite_id": "893d56b2-6014-411a-84bf-3b62fefae101",
			"title": "The Witcher 3: Wild Hunt",
			"cover_url": "https://images.igdb.com/.../co1wyy.jpg",
			"background_url": "https://images.igdb.com/.../sc867u.jpg",
			"genres": ["RPG", "Aventura", "Mundo Aberto"],
			"platform": { "id": 1, "name": "PC (Steam)" },
			"storage_device": { "id": 1, "name": "SSD Windows" },
			"gameplay_status": "Jogando",
			"interest_rating": 5,
			"replay_score": null,
			"score": null,
			"must_test": false,
			"finish_hours": null,
			"finish_date": null,
			"hltb_main": 51,
			"hltb_main_extra": 102,
			"hltb_full": 172,
			"coop_players": "1 Jogador",
			"coop_type": ["Um Jogador"],
			"coop_screen_type": "Tela Inteira",
			"input_recommendation": "Controle",
			"playtime_seconds": 0,
			"notes": "Sensacional.",
			"created_at": "2026-07-26T10:00:00",
			"updated_at": "2026-07-26T10:00:00"
		}
	],
	"total": 312,
	"limit": 60,
	"offset": 0,
	"has_more": true
}
```

### 5.2 POST `/api/games` (Criar Jogo)

**Request:**

```json
{
	"title": "Elden Ring",
	"cover_url": "https://...",
	"background_url": "https://...",
	"genres": ["RPG", "Ação", "Mundo Aberto"],
	"platform": "PC (Steam)",
	"storage_device": "SSD Windows",
	"gameplay_status": "Backlog",
	"interest_rating": 5,
	"must_test": false,
	"coop_players": "1 Jogador",
	"coop_type": ["Online"],
	"coop_screen_type": "Tela Inteira",
	"input_recommendation": "Controle",
	"hltb_main": 58,
	"hltb_main_extra": 101,
	"hltb_full": 133,
	"playtime_seconds": 0,
	"notes": "Instalar após zerar Witcher 3."
}
```

**Regras do payload:**

- `title` (obrigatório), `genres` (obrigatório, min 1), `platform` (obrigatório)
- `coop_type` é `list[str]` (array). Backend serializa como JSON string
- `storage_device` pode ser `null` (jogo não instalado / instalação não informada)
- `gameplay_status` default: `"Backlog"`
- `interest_rating` default: `3`

**Response (201):**

```json
{
	"id": "abc123def456",
	"title": "Elden Ring",
	"platform": { "id": 1, "name": "PC (Steam)" },
	"genres": [
		{ "id": 5, "name": "RPG" },
		{ "id": 10, "name": "Ação" },
		{ "id": 3, "name": "Mundo Aberto" }
	],
	"storage_device": { "id": 1, "name": "SSD Windows" },
	"created_at": "2026-07-26T10:00:00"
}
```

### 5.3 POST `/api/sync/playnite` (Batch do Playnite)

**Request** — vide seção 6 abaixo.

### 5.4 GET `/api/genres` (Lista catálogos)

**Response:**

```json
[
	{ "id": 1, "name": "RPG", "game_count": 12 },
	{ "id": 2, "name": "Aventura", "game_count": 8 },
	{ "id": 3, "name": "Mundo Aberto", "game_count": 5 }
]
```

`game_count` é opcional (via `LEFT JOIN`), útil para saber quais gêneros estão em uso.

### 5.5 DELETE `/api/genres/{id}` (Proteção de integridade)

**Response (409) se o gênero estiver em uso:**

```json
{
	"detail": "Cannot delete genre 'RPG': it is used by 12 games."
}
```

---

## 6. Fluxo de Sincronização Playnite

### Premissas

- **Servidor é a fonte da verdade.** O primeiro upload vem da planilha (via `POST /api/migrate/xlsx`). Os dados do servidor (nota, status, coop, etc.) prevalecem sobre os do Playnite.
- **Direção do sync:** Servidor → Playnite (o servidor exporta, a extensão C# importa no Playnite).
- `user_score` do Playnite **não é utilizado**. A nota que vale é `interest_rating` (servidor).
- Metadados (`release_date`, `developers`, `publishers`) **não são armazenados** no servidor.
- `playtime_seconds` é armazenado mas sem regra de negócio vinculada a `finish_hours`.
- Tags do Playnite podem ser usadas **apenas de forma transiente** para mapear `coop_type` (opcional).

### Contrato: Servidor → Extensão C# (Pull)

A extensão C# chama o endpoint para obter jogos modificados:

**Request** `GET /api/sync/playnite/changes?since=2026-07-01T00:00:00`

**Response:**

```json
{
	"games": [
		{
			"playnite_id": "893d56b2-6014-411a-84bf-3b62fefae101",
			"title": "The Witcher 3: Wild Hunt",
			"genres": ["RPG", "Aventura", "Mundo Aberto"],
			"platforms": ["PC (Steam)"],
			"cover_url": "https://...",
			"background_url": "https://...",
			"completion_status": "Finalizado",
			"playtime_seconds": 45000,
			"notes": "Sensacional.",
			"is_installed": true,
			"install_directory": "J:\\Jogos\\TheWitcher3"
		}
	]
}
```

**Mapeamento `gameplay_status` (servidor) → Playnite:**

| Servidor       | Playnite    |
| -------------- | ----------- |
| `"Backlog"`    | `NotPlayed` |
| `"Jogando"`    | `Playing`   |
| `"Finalizado"` | `Beaten`    |
| `"Abandonado"` | `Abandoned` |

### Contrato: Extensão C# → Servidor (Push)

Para informações que o Playnite possui e o servidor não (como `install_directory` e `playtime`):

**Request** `POST /api/sync/playnite`:

```json
{
	"games": [
		{
			"playnite_id": "893d56b2-6014-411a-84bf-3b62fefae101",
			"title": "The Witcher 3: Wild Hunt",
			"is_installed": true,
			"install_directory": "J:\\Jogos\\TheWitcher3",
			"playtime_seconds": 45000,
			"last_activity": "2026-07-20T18:30:00",
			"tags": ["Open World", "Fantasy", "Coop"]
		}
	]
}
```

**Lógica do servidor ao receber:**

```
1. Para cada game no array:
   a. Busca por playnite_id
   b. Se achar: atualiza apenas is_installed, install_directory, playtime_seconds
      PRESERVA tudo que veio da planilha (status, notas, coop, etc.)
   c. Se não achar: cria registro mínimo com defaults
   d. Extrai letra do disco de InstallDirectory → mapeia para storage_device
      Ex: "J:\\..." → "HD Singleplayer"
   e. Mapeamento de tags multiplayer (opcional):
      - Se tags incluir "Coop" → adiciona "Sofá" ao coop_type
      - Se tags incluir "Online Coop" → adiciona "Online" ao coop_type
      (Apenas na criação. Em atualização, coop_type do servidor prevalece.)

2. Retorna response com os IDs processados
```

**Extração do disco a partir do `install_directory`:**

```python
DISK_MAP = {
    "C:": "SSD Windows",
    "R:": "HD ROMs",
    "J:": "HD Singleplayer",
    "M:": "HD Multiplayer",
}

def extract_disk(install_dir: str | None) -> str | None:
    if not install_dir:
        return None
    letter = install_dir[:2].upper()
    return DISK_MAP.get(letter)
```

---

## 7. Sequência de Implementação

### ✅ Fase 1: Core do Backend (concluído)

```
[x] Criar estrutura de pastas e dependências (requirements.txt)
[x] Implementar database.py (engine + init_db)
[x] Implementar todos os models SQLModel
[x] Implementar seed de platforms + storage_devices
[x] Implementar CRUD de jogos (/api/games)
[x] Implementar CRUD de catálogos (/api/genres, /api/platforms, /api/storage-devices)
[x] Implementar auto-criação de referências no POST/PUT games
[x] Testar com dados mock via Swagger
[x] Seed de 63 jogos fictícios (seed_games.py)
```

### ✅ Fase 2: Migração de Dados

```
[x] Implementar GET /api/export/xlsx (dump do banco)
[x] 63 jogos seedados para teste (seed_games.py)
```

### ✅ Fase 3: Conectar Frontend (concluído)

```
[x] src/services/api.js com funções fetch (createGame, updateGame, deleteGame, fetchGames)
[x] Library.jsx conectado à API com fallback para mock data
[x] Paginação com "Load More" (60 itens por página)
[x] FilterBar busca plataformas/gêneros da API (/api/genres, /api/platforms)
[x] GameModal envia/recebe da API (POST/PUT/DELETE)
[x] GameModal com botão "Excluir Jogo" e confirmação
[x] Seletor de HD no popup StatsCard integrado com filtro
```

### ✅ Fase 4: Filtros Multi-Valor (concluído)

```
[x] Suporte a interest_min, interest_max, coop_type, hds (incluindo __uninstalled__)
[x] Ordenador multi-campo no frontend
[x] Frontend: componente de ordenação (sort builder) com SortDropdown
[x] Filtro client-side mantido no front (useMemo) para busca textual e filtros combinados locais
```

### ✅ Cache-Control (v1.1.1)

```
[x] /api/games: no-cache (browser sempre revalida com servidor)
[x] Frontend: _t cache-busting no fetchGames
[x] /api/covers/: mantido (1 ano)
[x] /api/catalogs: mantido (1 hora)
```

### ✅ Toast + UX (v1.1.1 — frontend)

```
[x] ToastProvider + useToast: notificações não-bloqueantes (success/error/info)
[x] Auto-dismiss 4s + animação slide-in
[x] Salvar/excluir jogo: modal fecha imediatamente → toast → reload silencioso
[x] Export XLSX com toast de sucesso/erro
```

### ✅ Validação Pydantic (concluído)

```
[x] Literal types: gameplay_status, coop_players, coop_screen_type, input_recommendation
[x] coop_type items validados (Um Jogador, Sofá, Online, LAN)
[x] Campos não-negativos: hltb_*, playtime_seconds, finish_hours
[x] finish_date validado como ISO date
[x] score vazio convertido para null
[x] Cross-field: se Finalizado, replay_score default = 3
[x] PlayniteSyncEntry + PlayniteSyncRequest schemas
[x] Timeout de 15s no fetch do frontend via AbortController
```

### ✅ Batch Upsert (v1.1.1)

```
[x] GameCreate.playnite_id adicionado ao schema
[x] POST /api/games/batch: upsert por playnite_id
[x] Se playnite_id existe → UPDATE completo via _update_game_from_create
[x] Se playnite_id não existe ou não informado → INSERT via _create_single_game
[x] Resposta inclui action: "created" | "updated" por item
[x] playnite_id = unique=True no banco (model já existia)
```

### ✅ Fase 5: Metadados (parcial)

```
[ ] GET /api/metadata/search (IGDB/RAWG para capa + background) — futuro
[x] GET /api/metadata/hltb — busca HLTB com arredondamento ceil(x*2)/2
[x] Botão "Buscar HLTB" conectado no modal (preenche hltb_* e cover_url)
```

### Fase 6: Sincronização Playnite (futuro)

```
[ ] Implementar GET /api/sync/playnite/changes (pull: servidor → Playnite)
[ ] Implementar POST /api/sync/playnite (push: Playnite → servidor, apenas install + playtime)
[ ] Construir extensão C# do Playnite seguindo o contrato
```

### Fase 7: Deploy (futuro)

```
[ ] Configurar uvicorn + systemd no Raspberry Pi
[ ] Configurar Cloudflare Tunnel (ou similar)
[ ] Fazer build do frontend e servir via nginx/caddy
[ ] Configurar cron de backup do .db e export .xlsx
```

---

## Referência Rápida: Como os Catálogos Integram com o Frontend

Atualmente o frontend (`FilterBar.jsx`) extrai plataformas, gêneros e discos únicos percorrendo **todos os jogos mockados**. Com o backend, esses dados virão de endpoints dedicados:

| Componente                | Hoje (mock)                                                      | Amanhã (API)                                                  |
| ------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------- |
| `FilterBar` — plataformas | `uniquePlatforms = [...new Set(games.map(g => g.platform))]`     | `GET /api/platforms` → `[{id, name}]`                         |
| `FilterBar` — gêneros     | `uniqueGenres = [...new Set(games.flatMap(g => g.genres))]`      | `GET /api/genres` → `[{id, name}]`                            |
| `GameModal` — HD selector | `existingHds = [...new Set(games.map(g => g.install_location))]` | `GET /api/storage-devices` → `[{id, name}]`                   |
| `StatsCard` — HD popup    | Mesmo cálculo manual                                             | `GET /api/games?group_by=storage_device` (ou contar no front) |

Isso significa que o frontend **não precisa mais percorrer a lista inteira de jogos** só para montar os options dos filtros — uma chamada leve de catálogo resolve.
