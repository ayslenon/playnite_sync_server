#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
CERT_DIR="${CERT_DIR:-$SERVER_DIR/certs}"

if ! command -v mkcert >/dev/null 2>&1; then
    echo "mkcert não encontrado. Instale-o antes de gerar o certificado." >&2
    exit 1
fi

mkdir -p "$CERT_DIR"
mkcert \
    -cert-file "$CERT_DIR/ayslenon-pc.pem" \
    -key-file "$CERT_DIR/ayslenon-pc-key.pem" \
    ayslenon-pc.local \
    ayslenon-pc \
    localhost \
    127.0.0.1 \
    ::1

chmod 600 "$CERT_DIR/ayslenon-pc-key.pem"
echo "Certificado criado em $CERT_DIR"
echo "CA local: $(mkcert -CAROOT)/rootCA.pem"
