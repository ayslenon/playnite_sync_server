# Guia de operação — Windows e Linux

Este documento descreve como configurar, iniciar e diagnosticar o servidor da
Biblioteca de Jogos nos dois sistemas operacionais do computador. O backend
FastAPI serve a dashboard React compilada, a API, as capas do Playnite e o
PWA em HTTPS na porta `8000`.

## 1. Arquitetura e pré-requisitos

O fluxo atual é:

```text
Playnite no Windows
        │ POST /api/sync/playnite
        ▼
FastAPI + SQLite
        │ GET /api/games e arquivos estáticos
        ▼
Dashboard/PWA no navegador ou telefone
```

O projeto usa uma pasta de dados compartilhada na partição NTFS do Windows,
mas o banco deve ser aberto por apenas um sistema operacional por vez.

### Linux

- Python 3.10 ou mais recente;
- `python3-venv`, `pip` e `npm`/Node.js se for necessário recompilar a dashboard;
- `mkcert` para HTTPS;
- `avahi-daemon` para anunciar `ayslenon-pc.local` por mDNS;
- partição NTFS montada em `/mnt/windows`.

### Windows

- Python 3.10 ou mais recente;
- Node.js/npm somente se for necessário recompilar a dashboard;
- `mkcert` somente se o certificado for gerado no próprio Windows;
- Playnite instalado;
- PowerShell e Agendador de Tarefas.

Se o certificado for gerado no Linux e copiado para o Windows, não é necessário
instalar `mkcert` no Windows. Nesse caso, copie também a `rootCA.pem` da mesma
CA que assinou o certificado e instale-a como confiável no Windows.

Estrutura esperada dos projetos:

```text
integração_playnite/
├── dashboard/
│   └── dist/
└── server/
    ├── app/
    ├── certs/
    ├── scripts/
    ├── venv/
    └── requirements.txt
```

O `venv` é específico do sistema operacional. Não copie o ambiente virtual do
Linux para o Windows nem o ambiente do Windows para o Linux.

## 2. Banco, capas e dual boot

Os scripts oficiais usam estes caminhos:

| Recurso | Linux | Windows |
| --- | --- | --- |
| Banco | `/mnt/windows/GameLibraryData/game_library.db` | `C:\GameLibraryData\game_library.db` |
| Capas do Playnite | `/mnt/windows/Users/Console/AppData/Roaming/Playnite/library/files` | `C:\Users\Console\AppData\Roaming\Playnite\library\files` |
| Build da dashboard | `../dashboard/dist` | `..\dashboard\dist` |
| Certificado | `server/certs/ayslenon-pc.pem` | `server\certs\ayslenon-pc.pem` |
| Chave privada | `server/certs/ayslenon-pc-key.pem` | `server\certs\ayslenon-pc-key.pem` |

Se a conta do Windows não se chama `Console`, altere `COVERS_DIR` no arquivo
`scripts/start_windows.ps1` e `COVERS_DIR` no arquivo `scripts/start_linux.sh`
para apontar para a pasta real do Playnite.

### Desativar Fast Startup e hibernação

No Windows, abra o PowerShell ou Prompt de Comando como administrador e execute:

```powershell
powercfg /h off
```

Isso desativa a hibernação e o Fast Startup, evitando que o Linux monte uma
partição NTFS que ainda esteja em estado hibernado.

Antes de trocar de sistema:

1. Pare o servidor.
2. Feche o Playnite e qualquer programa que esteja usando o banco.
3. Desligue ou reinicie o sistema corretamente.
4. No Linux, confirme que a partição está montada antes de iniciar o servidor.

No Linux, verifique a montagem com:

```bash
findmnt /mnt/windows
ls -la /mnt/windows/GameLibraryData
```

Não inicie o servidor nos dois sistemas ao mesmo tempo. SQLite não deve ser
usado dessa forma, mesmo que os arquivos estejam em uma partição local.

## 3. Configuração no Linux

### 3.1 Preparar o projeto e o ambiente Python

```bash
cd "/caminho/para/integração_playnite/server"
python3 -m venv venv
./venv/bin/python -m pip install --upgrade pip
./venv/bin/python -m pip install -r requirements.txt
```

O script `scripts/start_linux.sh` usa o ambiente `venv/bin/python` quando ele
existe e recorre a `python3` caso contrário.

### 3.2 Conferir dados e capas

```bash
test -f /mnt/windows/GameLibraryData/game_library.db
test -d /mnt/windows/Users/Console/AppData/Roaming/Playnite/library/files
```

Se algum comando falhar, corrija a montagem NTFS ou o caminho configurado no
script antes de iniciar o servidor.

### 3.3 Preparar a dashboard

Se o diretório `dashboard/dist` já foi gerado depois das últimas alterações do
frontend, ele pode ser copiado diretamente para o projeto. Não é necessário
instalar `node_modules` apenas para executar o backend.

Recompile somente quando o código da dashboard, o manifest, os ícones ou o
service worker tiverem sido alterados:

```bash
cd "/caminho/para/integração_playnite/dashboard"
npm install
npm run build
```

Depois, confirme que o build existe:

```bash
test -f dist/index.html
test -f dist/manifest.webmanifest
```

### 3.4 Gerar o certificado local

Instale o `mkcert` conforme a distribuição Linux. Depois, no diretório
`server`, execute:

```bash
cd "/caminho/para/integração_playnite/server"
bash scripts/generate_local_cert.sh
```

O certificado deve conter pelo menos:

```text
ayslenon-pc.local
ayslenon-pc
localhost
127.0.0.1
::1
```

O script cria:

```text
server/certs/ayslenon-pc.pem
server/certs/ayslenon-pc-key.pem
```

A pasta `certs/` e a chave privada são ignoradas pelo Git. Faça backup e
transfira esses arquivos de forma segura quando necessário; não os adicione ao
repositório.

Para descobrir a autoridade certificadora local:

```bash
mkcert -CAROOT
```

O arquivo `rootCA.pem` dessa pasta precisa ser confiado pelo Windows e pelo
telefone se eles forem acessar o hostname sem alerta de certificado. Nunca
compartilhe a chave privada da CA.

### 3.5 Configurar o hostname no Linux

Instale e habilite o Avahi:

```bash
sudo apt install avahi-daemon
sudo systemctl enable --now avahi-daemon
```

Se o NetworkManager estiver anunciando mDNS simultaneamente, desative o mDNS
na conexão usada pelo computador e reinicie o Avahi:

```bash
nmcli connection show
nmcli connection modify "<nome-da-conexao>" connection.mdns 0
sudo systemctl restart avahi-daemon
```

Teste a resolução:

```bash
getent hosts ayslenon-pc.local
avahi-resolve-host-name ayslenon-pc.local
```

Redes de convidados, isolamento entre clientes e alguns roteadores bloqueiam
mDNS. Nesses casos, o hostname pode funcionar no Linux, mas não no telefone.

### 3.6 Iniciar manualmente

```bash
cd "/caminho/para/integração_playnite/server"
chmod +x scripts/start_linux.sh
./scripts/start_linux.sh
```

O servidor ficará disponível em:

```text
https://localhost:8000/
https://ayslenon-pc.local:8000/
```

Teste a API em outro terminal:

```bash
curl -k https://localhost:8000/api/health
```

O resultado esperado é semelhante a:

```json
{"status":"ok"}
```

O `-k` ignora temporariamente a validação da CA. Depois de instalar a CA no
sistema, prefira testar sem `-k`.

### 3.7 Iniciar automaticamente com systemd

Primeiro confirme que o script funciona manualmente. Depois crie o serviço:

```bash
sudo nano /etc/systemd/system/game-library.service
```

Use o caminho real do projeto. Em caminhos com espaço, o `ExecStart` usa `\x20`
para representar o espaço:

```ini
[Unit]
Description=Game Library HTTPS Server
Wants=network-online.target
After=network-online.target
RequiresMountsFor=/mnt/windows

[Service]
Type=simple
User=ayslenon
WorkingDirectory=/home/ayslenon/Documentos/projetos/projetos\x20github/integração_playnite/server
ExecStart=/bin/bash /home/ayslenon/Documentos/projetos/projetos\x20github/integração_playnite/server/scripts/start_linux.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Se o nome do usuário ou o caminho forem diferentes, ajuste `User`,
`WorkingDirectory` e `ExecStart`. Confirme o caminho real com:

```bash
pwd
realpath scripts/start_linux.sh
```

Ative e inicie o serviço:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now game-library.service
systemctl status game-library.service
```

Para acompanhar os logs:

```bash
journalctl -u game-library.service -f
```

Se aparecer `Changing to the requested working directory failed`, o caminho
em `WorkingDirectory` não existe ou foi digitado incorretamente. Se aparecer
`code=exited, status=200/CHDIR`, corrija esse caminho antes de investigar o
Python ou o HTTPS.

## 4. Configuração no Windows

### 4.1 Preparar o projeto e o ambiente Python

Abra o PowerShell e entre no diretório `server`:

```powershell
Set-Location "C:\caminho\para\integração_playnite\server"
py -3 -m venv venv
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -c "import fastapi, uvicorn; print('Python OK')"
```

O ambiente virtual do Linux não funciona no Windows. Mesmo que o projeto tenha
sido copiado completo, crie o `venv` novamente no Windows.

### 4.1.1 Troubleshooting do PowerShell e da `venv`

Se a execução de scripts estiver desabilitada, não é necessário alterar
permanentemente a política do Windows. Execute o script com uma política válida
somente para esse processo:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\start_windows.ps1"
```

Se aparecer `python.exe: No module named uvicorn`, o script pode ter usado o
Python global porque `venv\Scripts\python.exe` não foi encontrado, ou a `venv`
ainda não recebeu as dependências. Recrie o ambiente e teste-o diretamente:

```powershell
Set-Location "C:\caminho\para\integração_playnite\server"
py -3 -m venv venv
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m uvicorn --version
```

Não é necessário executar `Activate.ps1`: chamar diretamente
`venv\Scripts\python.exe` também evita problemas de Execution Policy. O script
atual usa o Python global como fallback quando a `venv` não existe; para a
inicialização automática, confirme sempre que a `venv` foi criada e contém
`uvicorn`.

### 4.2 Conferir dados, capas e build

```powershell
Test-Path "C:\GameLibraryData\game_library.db"
Test-Path "C:\Users\Console\AppData\Roaming\Playnite\library\files"
Test-Path "C:\caminho\para\integração_playnite\dashboard\dist\index.html"
```

Se a conta Windows não for `Console`, edite `$CoversDir` em
`server\scripts\start_windows.ps1`.

Uma `dashboard\dist` atualizada pode ser copiada do Linux ou de outra máquina
sem novo build. Para recompilar no Windows:

```powershell
Set-Location "C:\caminho\para\integração_playnite\dashboard"
npm install
npm run build
```

O runtime do servidor precisa somente da pasta `dist`; `node_modules` não é
necessário para iniciar o backend.

### 4.3 Gerar ou copiar o certificado

Há dois cenários.

#### Opção A — gerar o certificado no próprio Windows

Instale o `mkcert`:

```powershell
winget install FiloSottile.mkcert
```

Depois, abra um novo PowerShell e instale a CA local:

```powershell
mkcert -install
```

Se o certificado ainda não existir, execute no diretório `server`:

```powershell
Set-Location "C:\caminho\para\integração_playnite\server"
New-Item -ItemType Directory -Force .\certs
mkcert `
  -cert-file .\certs\ayslenon-pc.pem `
  -key-file .\certs\ayslenon-pc-key.pem `
  ayslenon-pc.local `
  ayslenon-pc `
  localhost `
  127.0.0.1 `
  ::1
```

#### Opção B — reutilizar no Windows o certificado gerado no Linux

Se `ayslenon-pc.pem` e `ayslenon-pc-key.pem` foram gerados no Linux, copie os
dois arquivos para `server\certs` no Windows. Eles continuam válidos desde que
o certificado contenha `ayslenon-pc.local` no SAN.

Além desses dois arquivos, o Windows precisa confiar na mesma CA do `mkcert`
que assinou o certificado. No Linux onde o certificado foi criado, descubra a
pasta da CA:

```bash
mkcert -CAROOT
ls -la "$(mkcert -CAROOT)"
```

Copie somente este arquivo:

```text
rootCA.pem
```

Nunca copie nem distribua `rootCA-key.pem`: ela é a chave privada da autoridade
certificadora. O certificado do servidor (`ayslenon-pc.pem`) também não deve ser
instalado como uma CA raiz.

Por exemplo, para copiar a CA para Downloads no Linux:

```bash
cp "$(mkcert -CAROOT)/rootCA.pem" ~/Downloads/rootCA.pem
```

Transfira `rootCA.pem` para o Windows, por exemplo para:

```text
C:\GameLibraryData\rootCA.pem
```

Antes de instalar, confirme que o arquivo é a CA raiz:

```powershell
certutil -dump "C:\GameLibraryData\rootCA.pem"
```

O `Subject` deve identificar `mkcert development CA` e, em uma CA raiz, o
`Subject` e o `Issuer` correspondem. Não confunda `rootCA.pem` com
`ayslenon-pc.pem`: o segundo é o certificado do servidor.

Em um PowerShell aberto como administrador, instale a CA:

```powershell
certutil -addstore -f Root "C:\GameLibraryData\rootCA.pem"
```

Confirme o certificado instalado:

```powershell
Get-ChildItem Cert:\LocalMachine\Root |
    Where-Object { $_.Subject -like "*mkcert*" } |
    Format-List Subject,Issuer,Thumbprint,NotBefore,NotAfter
```

O esperado é uma entrada da `mkcert development CA`. Se aparecer
`O=mkcert development certificate` como `Subject`, provavelmente o certificado
do servidor foi instalado por engano. Anote o `Thumbprint` e remova somente a
entrada incorreta:

```powershell
Remove-Item "Cert:\LocalMachine\Root\<THUMBPRINT>"
```

Depois, instale a `rootCA.pem` correta.

Verifique os arquivos:

```powershell
Test-Path ".\certs\ayslenon-pc.pem"
Test-Path ".\certs\ayslenon-pc-key.pem"
```

Não inclua a chave privada nem a CA no Git.

### 4.4 Configurar o hostname no Windows

Teste primeiro se o hostname resolve:

```powershell
Resolve-DnsName ayslenon-pc.local
Test-NetConnection ayslenon-pc.local -Port 8000
```

O sufixo `.local` depende de mDNS. Se o Windows não anunciar ou resolver o
nome automaticamente, use um responder Bonjour/mDNS ou o DNS local do
roteador.

Para um teste somente no próprio Windows, pode-se adicionar como administrador
ao arquivo:

```text
C:\Windows\System32\drivers\etc\hosts
```

a entrada:

```text
127.0.0.1 ayslenon-pc.local
```

Depois, limpe o cache DNS:

```powershell
ipconfig /flushdns
```

Essa entrada não configura o telefone. Para o telefone, o hostname precisa ser
resolvido pela rede via mDNS ou DNS local e apontar para o IP atual do
computador. Um IP pode mudar quando a rede muda; `ayslenon-pc.local` só é
localizável enquanto o mecanismo de resolução local da rede estiver disponível.

### 4.5 Iniciar manualmente

```powershell
Set-Location "C:\caminho\para\integração_playnite\server"
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\start_windows.ps1
```

Não use `https://0.0.0.0:8000` no navegador. Esse endereço é apenas o bind do
servidor para escutar em todas as interfaces.

Teste em outro PowerShell, primeiro ignorando temporariamente a validação TLS:

```powershell
curl.exe -vk https://localhost:8000/api/health
curl.exe -vk https://ayslenon-pc.local:8000/api/health
```

Depois de instalar a `rootCA.pem`, teste sem `-k`:

```powershell
curl.exe https://ayslenon-pc.local:8000/api/health
```

Se o Schannel aceitar a CA, mas falhar somente na verificação de revogação de
uma CA local do `mkcert`, teste mantendo a validação do certificado e ignorando
apenas essa verificação:

```powershell
curl.exe --ssl-no-revoke https://ayslenon-pc.local:8000/api/health
```

Se `localhost` funcionar e `ayslenon-pc.local` falhar, o problema é resolução
do hostname, rota ou confiança do certificado — não o build da dashboard.

Verifique a porta:

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen
```

### 4.6 Iniciar automaticamente com o Agendador de Tarefas

Só configure a inicialização automática depois que o script funcionar
manualmente.

1. Abra **Agendador de Tarefas**.
2. Escolha **Criar tarefa**.
3. Em **Geral**, use o nome `Game Library Server`.
4. Selecione **Executar estando o usuário conectado ou não**.
5. Use uma conta que tenha acesso a `C:\GameLibraryData`, à pasta do Playnite,
   ao certificado e ao projeto.
6. Em **Disparadores**, crie um disparador **Ao iniciar** e, se necessário,
   adicione um atraso de 30 segundos para a rede e os discos estarem prontos.
7. Em **Ações**, configure:
   - Programa: `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`
   - Argumentos: `-NoProfile -ExecutionPolicy Bypass -File "C:\caminho\para\integração_playnite\server\scripts\start_windows.ps1"`
   - Iniciar em: `C:\caminho\para\integração_playnite\server`
8. Em **Condições**, não exija alimentação externa se o computador for usado
   em bateria.
9. Em **Configurações**, habilite a reinicialização da tarefa em caso de falha.
10. Salve, execute a tarefa manualmente e confirme a porta `8000`.

Se a tarefa iniciar e parar imediatamente, abra o histórico da tarefa e execute
o script manualmente para ver a mensagem original. Os erros mais comuns são
Python ausente, certificado ausente, caminho de capas incorreto ou `dist`
inexistente.

## 5. HTTPS, dashboard e PWA

Use sempre uma destas URLs:

```text
https://localhost:8000/
https://ayslenon-pc.local:8000/
```

O dashboard é servido pelo próprio FastAPI a partir de `dashboard/dist`. Não é
necessário manter o Vite Preview rodando na porta `4173` para a operação normal.

O PWA pode ser instalado pelo navegador quando a página for aberta por HTTPS.
O service worker mantém a interface, o manifest e os ícones em cache, mas os
jogos, capas e demais dados continuam dependendo do servidor estar ligado.

Abra a aplicação pelo hostname HTTPS com certificado confiável. O fato de uma
página abrir depois de ignorar um alerta não garante que o navegador considere a
origem segura para service worker ou instalação do PWA.

Depois de atualizar a `dist`:

1. Abra a aplicação pelo hostname HTTPS.
2. Recarregue a página.
3. Se o telefone mantiver o ícone ou interface antigos, remova o PWA instalado.
4. Limpe os dados do site, se necessário.
5. Instale o PWA novamente.

## 6. Diagnóstico rápido

### O servidor não inicia

Linux:

```bash
./scripts/start_linux.sh
```

Windows:

```powershell
.\scripts\start_windows.ps1
```

Leia a primeira mensagem de erro. Os scripts verificam banco, capas, build,
certificado e chave antes de iniciar o Uvicorn.

### Erro de diretório de trabalho no systemd

```bash
systemctl status game-library.service
journalctl -u game-library.service -n 100 --no-pager
pwd
realpath scripts/start_linux.sh
```

Corrija `WorkingDirectory` e `ExecStart` para o caminho real. Um erro
`status=200/CHDIR` indica que o systemd não conseguiu entrar no diretório.

### A porta 8000 está fechada

Linux:

```bash
ss -ltnp | grep ':8000'
```

Windows:

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen
```

Se não houver processo escutando, o servidor não iniciou ou foi encerrado.
Se houver processo, teste primeiro `https://localhost:8000` e depois o
hostname.

### `localhost` funciona, mas `ayslenon-pc.local` não

Teste:

```powershell
Resolve-DnsName ayslenon-pc.local
curl.exe -vk https://ayslenon-pc.local:8000/api/health
```

Se a resolução falhar, configure mDNS/Bonjour/DNS local. Se o `curl -k`
funcionar, mas o navegador reclamar, instale a CA local no dispositivo ou
confirme que o certificado contém `ayslenon-pc.local`.

### O navegador informa certificado não confiável

O certificado do servidor foi assinado por uma CA privada do `mkcert`. O arquivo
que deve ser confiado pelos clientes é `rootCA.pem`, não
`ayslenon-pc.pem`. Descubra a CA com:

```bash
mkcert -CAROOT
```

ou, no Windows:

```powershell
mkcert -CAROOT
```

A CA precisa ser instalada separadamente no Linux, Windows e telefone. Se o
certificado foi gerado no Linux, copie `rootCA.pem` para o Windows e instale-a
como administrador:

```powershell
certutil -addstore -f Root "C:\caminho\para\rootCA.pem"
```

Confirme que a entrada é a `mkcert development CA`, com `Subject` e `Issuer`
correspondentes. Se aparecer `SEC_E_UNTRUSTED_ROOT`, a CA que assinou o
certificado ainda não é confiável. Gerar um certificado novo em outro sistema
também pode gerar uma CA diferente.

Se aparecer `CRYPT_E_NO_REVOCATION_CHECK`, a cadeia já passou pela validação da
raiz, mas o Schannel não consegue verificar a revogação da CA local. Para
diagnóstico, use:

```powershell
curl.exe --ssl-no-revoke https://ayslenon-pc.local:8000/api/health
```

Não use `-k` como teste final de confiança, pois ele ignora toda a validação do
certificado. Depois de corrigir a CA, feche e reabra o navegador antes de testar
o PWA. No iPhone/iPad, instale a mesma `rootCA.pem` e habilite a confiança total
do certificado nas configurações de confiança de certificados.

### Capas não aparecem

Confirme a pasta configurada e a existência do arquivo:

```text
/api/covers/playnite/{playnite_id}/{filename}
```

No Linux, verifique se `/mnt/windows` está montado e acessível. No Windows,
confirme `$CoversDir` em `scripts/start_windows.ps1`. O backend espera que o
valor persistido seja uma URL relativa; o navegador monta a URL usando a
origem HTTPS atual.

### A dashboard não abre ou retorna build ausente

Confirme:

```text
dashboard/dist/index.html
dashboard/dist/manifest.webmanifest
```

Se esses arquivos não existirem ou estiverem desatualizados, execute `npm run
build` no diretório `dashboard` e copie a nova pasta `dist`.

## 7. Checklist de operação

Antes de iniciar:

- [ ] O computador está conectado à rede correta.
- [ ] O Windows não está com Fast Startup/hibernação ativo.
- [ ] A partição NTFS está montada em `/mnt/windows` no Linux.
- [ ] O servidor não está rodando no outro sistema.
- [ ] O banco existe no caminho configurado.
- [ ] A pasta de capas do Playnite existe.
- [ ] `dashboard/dist` contém o build atual.
- [ ] O certificado e a chave existem em `server/certs`.
- [ ] A CA local está confiável no dispositivo que acessará a aplicação.
- [ ] `ayslenon-pc.local` resolve na rede, quando o acesso for por hostname.

Após iniciar:

- [ ] `https://localhost:8000/api/health` responde.
- [ ] `https://ayslenon-pc.local:8000/api/health` responde, quando aplicável.
- [ ] A dashboard abre pela mesma origem HTTPS.
- [ ] O manifest e o service worker carregam.
- [ ] As capas são carregadas.
- [ ] O Playnite Sync consegue fazer `POST /api/sync/playnite`.
