#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
PROJECT_DIR="$(cd -- "$SERVER_DIR/.." && pwd)"
DATA_DIR="/mnt/windows/GameLibraryData"
COVERS_DIR="/mnt/windows/Users/Console/AppData/Roaming/Playnite/library/files"
CERT_FILE="${SSL_CERTFILE:-$SERVER_DIR/certs/ayslenon-pc.pem}"
KEY_FILE="${SSL_KEYFILE:-$SERVER_DIR/certs/ayslenon-pc-key.pem}"

if [[ ! -d "$DATA_DIR" ]]; then
    echo "Pasta de dados não encontrada: $DATA_DIR" >&2
    echo "Confirme se a partição NTFS está montada e se GameLibraryData existe." >&2
    exit 1
fi

if [[ ! -f "$DATA_DIR/game_library.db" ]]; then
    echo "Banco não encontrado: $DATA_DIR/game_library.db" >&2
    exit 1
fi

if [[ ! -d "$COVERS_DIR" ]]; then
    echo "Pasta de capas não encontrada: $COVERS_DIR" >&2
    exit 1
fi

if [[ ! -f "$CERT_FILE" || ! -f "$KEY_FILE" ]]; then
    echo "Certificado HTTPS não encontrado:" >&2
    echo "  certificado: $CERT_FILE" >&2
    echo "  chave:       $KEY_FILE" >&2
    echo "Execute scripts/generate_local_cert.sh ou defina SSL_CERTFILE/SSL_KEYFILE." >&2
    exit 1
fi

cd "$SERVER_DIR"
export DATABASE_URL="sqlite:////mnt/windows/GameLibraryData/game_library.db"
export DEBUG="false"
export COVERS_DIR
export FRONTEND_DIST="$PROJECT_DIR/dashboard/dist"
export SSL_CERTFILE="$CERT_FILE"
export SSL_KEYFILE="$KEY_FILE"

if [[ ! -d "$FRONTEND_DIST" ]]; then
    echo "Build da dashboard não encontrado: $FRONTEND_DIST" >&2
    echo "Execute npm run build no diretório dashboard." >&2
    exit 1
fi

PYTHON_BIN="$SERVER_DIR/venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
    PYTHON_BIN="python3"
fi

exec "$PYTHON_BIN" -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --ssl-certfile "$SSL_CERTFILE" \
    --ssl-keyfile "$SSL_KEYFILE"
