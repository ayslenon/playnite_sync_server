# Game Library — Backend v1.3.0

API REST para gerenciamento de biblioteca pessoal de jogos. Recebe dados do Playnite (Windows), serve o dashboard React e mantém metadados (HLTB, notas, status). Pode rodar no Windows ou no Linux, usando uma pasta de dados compartilhada na partição NTFS do computador.

## Stack

| Camada    | Tecnologia                         |
| --------- | ---------------------------------- |
| Framework | FastAPI                            |
| Banco     | SQLite (via SQLModel / SQLAlchemy) |
| Validação | Pydantic                           |
| Servidor  | Uvicorn                            |
| Export    | openpyxl                           |
| Metadados | howlongtobeatpy                    |

## Pré-requisitos

- Python 3.10+
- pip

## Setup rápido

```bash
# Criar ambiente virtual
python -m venv venv

# Ativar
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Iniciar servidor para desenvolvimento da API
uvicorn app.main:app --reload
```

Para operação normal, compile a dashboard e use um dos inicializadores:

```bash
cd ../dashboard
npm install
npm run build
```

Gere o certificado local uma vez no Linux:

```bash
cd ../server
bash scripts/generate_local_cert.sh
```

- Linux: `./scripts/start_linux.sh`
- Windows: `scripts\\start_windows.ps1`

Esses inicializadores sobem backend e dashboard em HTTPS na porta `8000`. O frontend compilado é servido pelo próprio FastAPI.
O endereço principal é `https://ayslenon-pc.local:8000`.

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

- **Swagger UI:** https://localhost:8000/docs
- **OpenAPI JSON:** https://localhost:8000/openapi.json

### Endpoints

#### Jogos

| Método   | Rota               | Descrição                                                                                                                                   |
| -------- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET`    | `/api/games`       | Lista paginada com filtros: `search`, `status`, `platform`, `genre`, `hds`, `coop_type`, `interest_min`, `interest_max`, `favorite`, `sort` |
| `GET`    | `/api/games/{id}`  | Detalhe                                                                                                                                     |
| `POST`   | `/api/games`       | Criar                                                                                                                                       |
| `PUT`    | `/api/games/{id}`  | Atualizar                                                                                                                                   |
| `DELETE` | `/api/games/{id}`  | Remover                                                                                                                                     |
| `POST`   | `/api/games/batch` | Upsert em lote por `playnite_id`                                                                                                            |

#### Catálogos

| Método                         | Rota                   | Descrição                           |
| ------------------------------ | ---------------------- | ----------------------------------- |
| `GET` `/POST` `/PUT` `/DELETE` | `/api/genres`          | CRUD gêneros (com `game_count`)     |
| `GET` `/POST` `/PUT` `/DELETE` | `/api/platforms`       | CRUD plataformas (com `game_count`) |
| `GET` `/POST` `/PUT` `/DELETE` | `/api/storage-devices` | CRUD discos (com `game_count`)      |

#### Sincronização

| Método | Rota                         | Descrição                                                                                                       |
| ------ | ---------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `POST` | `/api/sync/playnite`         | JSON nativo do Playnite → upsert por `playnite_id`. Mapeia campos, preserva HLTB/notas. Ignora Hidden/frontend. |
| `GET`  | `/api/sync/playnite/changes` | (futuro) Pull de modificações                                                                                   |

#### Utilitários

| Método | Rota                               | Descrição                          |
| ------ | ---------------------------------- | ---------------------------------- |
| `GET`  | `/api/export/xlsx`                 | Download .xlsx com formatação      |
| `GET`  | `/api/metadata/hltb?title=`        | Busca HLTB (HowLongToBeat)         |
| `GET`  | `/api/health`                      | Health check                       |
| `GET`  | `/api/covers/playnite/{id}/{file}` | Serve capas da pasta `./app/files` |

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

| Variável       | Default                       | Descrição                                  |
| -------------- | ----------------------------- | ------------------------------------------ |
| `DATABASE_URL` | `sqlite:///./game_library.db` | Caminho do banco                           |
| `DEBUG`        | `false`                       | Modo debug (SQL echo)                      |
| `COVERS_DIR`   | `./app/files`                 | Diretório com capas exportadas do Playnite |
| `FRONTEND_DIST`| `../dashboard/dist`           | Diretório do build React servido pelo backend |
| `SSL_CERTFILE` | `./certs/ayslenon-pc.pem`     | Certificado TLS local                         |
| `SSL_KEYFILE`  | `./certs/ayslenon-pc-key.pem` | Chave privada TLS local                       |

Copie `.env.example` para `.env` e ajuste se necessário.

### Dados compartilhados no dual boot

Os exemplos `.env.linux.example` e `.env.windows.example` apontam para a mesma área de dados:

- Banco: `GameLibraryData/game_library.db`
- Capas: `C:/Users/Console/AppData/Roaming/Playnite/library/files`

No Linux, a partição deve estar montada em `/mnt/windows`. O banco deve ser acessado somente pelo sistema operacional atualmente inicializado. Desative o Fast Startup/hibernação do Windows com `powercfg /h off` antes de permitir escrita no volume pelo Linux.

Depois que o volume estiver gravável e o servidor parado, normalize as capas antigas:

```bash
DEBUG=false venv/bin/python scripts/normalize_playnite_urls.py
DEBUG=false venv/bin/python scripts/normalize_playnite_urls.py --apply
```

O segundo comando cria um backup ao lado do banco antes de alterar os seis URLs legados.

### Hostname, HTTPS e PWA

O hostname `ayslenon-pc.local` é anunciado por mDNS. No Linux, mantenha o serviço Avahi ativo. Se o NetworkManager também estiver habilitando mDNS na mesma interface, desative-o nessa conexão para evitar conflito e reinicie o Avahi:

```bash
nmcli connection modify "<nome-da-conexao>" connection.mdns 0
sudo systemctl enable --now avahi-daemon
```

No Windows, use um responder Bonjour/mDNS caso o nome não seja resolvido automaticamente. Redes guest ou com isolamento de clientes podem bloquear mDNS.

Para que o telefone e o Windows não exibam alerta de certificado, instale a CA local indicada por `mkcert -CAROOT` (`rootCA.pem`) nesses dispositivos. O certificado é válido para o hostname e para `localhost`, não para qualquer IP futuro da máquina.

O dashboard contém um manifest e service worker PWA. Ele pode ser instalado pela URL HTTPS, mantém a interface estática em cache e exige o servidor ligado para jogos, capas e demais dados.

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
│       ├── playnite_assets.py  # URLs relativas de capas/backgrounds
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

O banco é SQLite. Timestamps são strings ISO 8601. `coop_type` é JSON serializado em coluna `Text`. A pasta de dados compartilhada é local; não coloque o SQLite ativo em uma unidade de rede.

---

## Changelog

### v1.3.0

- Integração das atualizações remotas de mapeamento Playnite e validação de gêneros vazios.
- Capas e backgrounds sincronizados como URLs relativas, com compatibilidade para payloads antigos.
- HTTPS local em `ayslenon-pc.local`, scripts para Linux/Windows e certificado compartilhado.
- Dashboard instalável como PWA, com interface estática em cache e dados online.
- Documentação consolidada para dual boot, NTFS compartilhado, hostname mDNS e operação local.

### v1.2.1

- Correção do diretório de capas e atualização dos mapeamentos Playnite.

## Desenvolvimento

### Commits

Os commits seguem versão semântica (`v1.3.0`). Tanto server quanto dashboard têm repositórios git independentes.

### Convenções

- Campos em **português** (gameplay_status, coop_type, input_recommendation)
- `playnite_id` como chave de matching (unique, nullable)
- Rotas prefixadas com `/api/`
- CORS aberto (`allow_origins=["*"]`) — rede local
- Capas com Cache-Control de 1 ano (imutável)
- Dados com `no-cache` (sempre revalidar)

### Capas da sincronização Playnite

O plugin envia `CoverImage` e `BackgroundImage` como links relativos no formato `/api/covers/playnite/{Id}/{filename}`. O backend também normaliza caminhos absolutos enviados por versões antigas do plugin antes de salvar no banco.
