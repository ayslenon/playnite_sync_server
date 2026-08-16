$ErrorActionPreference = "Stop"

$ServerDir = Split-Path -Parent $PSScriptRoot
$ProjectDir = Split-Path -Parent $ServerDir
$DataDir = "C:\GameLibraryData"
$CoversDir = "C:\Users\Console\AppData\Roaming\Playnite\library\files"
$FrontendDist = Join-Path $ProjectDir "dashboard\dist"
$CertFile = if ($env:SSL_CERTFILE) { $env:SSL_CERTFILE } else { Join-Path $ServerDir "certs\ayslenon-pc.pem" }
$KeyFile = if ($env:SSL_KEYFILE) { $env:SSL_KEYFILE } else { Join-Path $ServerDir "certs\ayslenon-pc-key.pem" }

if (-not (Test-Path $DataDir -PathType Container)) {
    throw "Pasta de dados não encontrada: $DataDir"
}

$DatabasePath = Join-Path $DataDir "game_library.db"
if (-not (Test-Path $DatabasePath -PathType Leaf)) {
    throw "Banco não encontrado: $DatabasePath"
}

if (-not (Test-Path $CoversDir -PathType Container)) {
    throw "Pasta de capas não encontrada: $CoversDir"
}

if (-not (Test-Path $FrontendDist -PathType Container)) {
    throw "Build da dashboard não encontrado: $FrontendDist. Execute npm run build no diretório dashboard."
}

if (-not (Test-Path $CertFile -PathType Leaf)) {
    throw "Certificado HTTPS não encontrado: $CertFile"
}

if (-not (Test-Path $KeyFile -PathType Leaf)) {
    throw "Chave HTTPS não encontrada: $KeyFile"
}

$env:DATABASE_URL = "sqlite:///C:/GameLibraryData/game_library.db"
$env:DEBUG = "false"
$env:COVERS_DIR = $CoversDir
$env:FRONTEND_DIST = $FrontendDist
$env:SSL_CERTFILE = $CertFile
$env:SSL_KEYFILE = $KeyFile

Set-Location $ServerDir
$Python = Join-Path $ServerDir "venv\Scripts\python.exe"
if (-not (Test-Path $Python -PathType Leaf)) {
    $Python = "python"
}

& $Python -m uvicorn app.main:app `
    --host 0.0.0.0 `
    --port 8000 `
    --ssl-certfile $CertFile `
    --ssl-keyfile $KeyFile
