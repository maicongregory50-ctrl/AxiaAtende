# A casa do AxiaAtende: banco, segredos e os dois servicos, SO LOCAL. #950, passo C3 do plano
# (roda no G2). Molde: C:\AxiaMarketing\servicos\instalar.ps1 (#869, #923).
#
# RODAR EM POWERSHELL COMO ADMINISTRADOR:
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\AxiaAtende\servicos\instalar.ps1
#
# O que faz, em ordem:
#   1. cria a instancia de banco de producao em C:\Dados\AxiaAtende\pgdata, porta 5436, so
#      127.0.0.1, e registra o servico axiaatende-postgres;
#   2. gera as senhas do banco e grava C:\AxiaAtende\.env.secrets (so administrador e SYSTEM) e
#      C:\AxiaAtende\.env.recepcionista (administrador, SYSTEM e LocalService leem). Nenhuma senha
#      aparece na tela. As chaves da Meta e da Anthropic NAO sao escritas aqui: o dono as cola
#      depois (G3), nas linhas comentadas que o arquivo ja traz;
#   3. cria C:\Logs\AxiaAtende e C:\Logs\AxiaAtende\recepcionista (este, LocalService escreve);
#   4. da a LocalService leitura do codigo e do ambiente Python (.venv), e nada mais;
#   5. instala e sobe axiaatende-backend (as telas, 127.0.0.1:8009, LocalSystem);
#   6. instala e sobe axiaatende-recepcionista (127.0.0.1:8008, LocalService), EM ESCUTA: sem
#      ATENDE_RESPONDE=true no .env.recepcionista ele grava e nao responde ninguem;
#   7. confere: tudo so em 127.0.0.1, as duas saudes, e o ERP como antes.
#   NAO abre o Funnel: isso e o G5, com o comando impresso no fim.
#
# PODE RODAR DE NOVO: o banco que ja existe NAO e recriado, e o segredo que ja existe NAO e
# reescrito (trocar a senha ali trancaria o servico fora do proprio banco).
#
# Desfazer: servicos\desinstalar.ps1 (para e desinstala os servicos; nao apaga dado).

$ErrorActionPreference = 'Stop'

$PG        = 'C:\Program Files\PostgreSQL\17\bin'
$RAIZ      = 'C:\AxiaAtende'
$DADOS     = 'C:\Dados\AxiaAtende'
$PGDATA    = Join-Path $DADOS 'pgdata'
$SEGREDOS  = Join-Path $RAIZ '.env.secrets'
$ENVRECEP  = Join-Path $RAIZ '.env.recepcionista'
$LOGS      = 'C:\Logs\AxiaAtende'
$LOGRECEP  = Join-Path $LOGS 'recepcionista'
$SERVICOS  = Join-Path $RAIZ 'servicos'
$PYTHON    = Join-Path $RAIZ '.venv\Scripts\python.exe'
$WINSW     = 'C:\SuporteAxia\servicos\suporteaxia-backend.exe'   # o mesmo WinSW da casa
$PORTA     = 5436
$SUPER     = 'axiaatende_su'
$APP       = 'axiaatende_app'
$BANCO     = 'axiaatende'
$LOCALSERV = '*S-1-5-19'   # NT AUTHORITY\LocalService, pelo SID (o nome muda com o idioma)
$SEM_BOM   = New-Object System.Text.UTF8Encoding($false)

function Passo($texto) { Write-Host ''; Write-Host "== $texto" -ForegroundColor Cyan }
function Ok($texto)    { Write-Host "   ok  $texto" -ForegroundColor Green }
function Falha($texto) { Write-Host "   !!  $texto" -ForegroundColor Red; exit 1 }

function Nova-Senha {
    $b = New-Object byte[] 24
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
    return ([Convert]::ToBase64String($b)).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

function Fechar($caminho, [string[]] $extra) {
    # SIDs, e nao nomes: "Administradores" no Windows em portugues, "Administrators" em ingles.
    $regras = @('*S-1-5-32-544:F', '*S-1-5-18:F') + $extra
    & icacls $caminho /inheritance:r /grant:r @regras | Out-Null
    if ($LASTEXITCODE -ne 0) { Falha "nao consegui fechar $caminho" }
}

function Ler-Segredo($chave) {
    foreach ($linha in [IO.File]::ReadAllLines($SEGREDOS)) {
        if ($linha.StartsWith($chave + '=')) { return $linha.Substring($chave.Length + 1) }
    }
    return ''
}

function Instalar-Servico($id, $porta) {
    $exe = Join-Path $SERVICOS "$id.exe"
    $xml = Join-Path $SERVICOS "$id.xml"
    try { [xml](Get-Content $xml -Raw) | Out-Null } catch { Falha "$xml nao e XML valido: $($_.Exception.Message)" }
    if (-not (Test-Path $exe)) { Copy-Item $WINSW $exe }
    if (Get-Service $id -ErrorAction SilentlyContinue) {
        Stop-Service $id -ErrorAction SilentlyContinue
        & $exe uninstall | Out-Null
        Start-Sleep -Seconds 2
    }
    & $exe install | Out-Null
    if ($LASTEXITCODE -ne 0) { Falha "nao consegui instalar $id" }
    Start-Service $id
    $saude = $null
    for ($i = 0; $i -lt 30 -and -not $saude; $i++) {
        try { $saude = Invoke-RestMethod "http://127.0.0.1:$porta/saude" -TimeoutSec 2 } catch { Start-Sleep -Seconds 1 }
    }
    if (-not $saude -or -not $saude.de_pe) { Falha "$id nao respondeu em /saude; veja $LOGS" }
    if ($saude.ambiente -ne 'producao') { Falha "$id subiu como '$($saude.ambiente)', e nao producao" }
    return $saude
}

# ── 0. administrador e pre-requisitos ────────────────────────────────────────
$eu = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $eu.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Falha 'rode este script numa janela do PowerShell COMO ADMINISTRADOR'
}
if (-not (Test-Path $PYTHON)) { Falha "nao achei o ambiente Python em $PYTHON. Peca a sessao: python -m venv .venv e pip install -r requirements.txt" }
if (-not (Test-Path (Join-Path $RAIZ 'frontend\dist\index.html'))) {
    Falha 'a tela nao esta construida (frontend\dist). Peca a sessao: npm run build'
}
if (-not (Test-Path $WINSW)) { Falha "nao achei o WinSW da casa em $WINSW" }

# ── 1 e 2. banco e segredos ──────────────────────────────────────────────────
Passo '1. Banco de producao (porta 5436) e 2. arquivos de segredo'
$existeBanco = Test-Path (Join-Path $PGDATA 'PG_VERSION')
$existeSegredo = Test-Path $SEGREDOS
if ($existeBanco -and -not $existeSegredo) { Falha "o banco ja existe em $PGDATA, mas $SEGREDOS nao. Nada foi mexido: chame a sessao." }
if (-not $existeBanco -and $existeSegredo) { Falha "$SEGREDOS existe sem banco em $PGDATA. Nada foi mexido: chame a sessao." }

if (-not $existeBanco) {
    $senhaSuper = Nova-Senha
    $senhaApp = Nova-Senha
    New-Item -ItemType Directory -Force $DADOS | Out-Null

    # O segredo nasce ANTES do banco: se algo falhar no meio, a senha nao se perde.
    $conteudo = "# Segredos do AxiaAtende (#950), so das TELAS. Fechado a administrador. Nao copie, nao mostre.`r`n" +
                "AXIAATENDE_BANCO_SENHA=$senhaApp`r`n" +
                "AXIAATENDE_SU_SENHA=$senhaSuper`r`n" +
                "AXIAATENDE_CHAVE_PEDIDO=$(Nova-Senha)`r`n"
    [IO.File]::WriteAllText($SEGREDOS, $conteudo, $SEM_BOM)
    Fechar $SEGREDOS @()
    Ok "segredo das telas em $SEGREDOS (so administrador e sistema leem)"

    $arqSenha = Join-Path $env:TEMP ('axatd_' + [guid]::NewGuid().ToString('N'))
    [IO.File]::WriteAllText($arqSenha, $senhaSuper, $SEM_BOM)
    try {
        & "$PG\initdb.exe" -D $PGDATA -U $SUPER --pwfile=$arqSenha --auth=scram-sha-256 `
            -E UTF8 --locale-provider=icu --icu-locale=pt-BR --locale=Portuguese_Brazil.1252 | Out-Null
        if ($LASTEXITCODE -ne 0) { Falha 'initdb falhou' }
    } finally {
        Remove-Item $arqSenha -Force -ErrorAction SilentlyContinue
    }
    $conf = Join-Path $PGDATA 'postgresql.conf'
    [IO.File]::AppendAllText($conf, "`r`n# AxiaAtende (#950)`r`nport = $PORTA`r`nlisten_addresses = '127.0.0.1'`r`n", $SEM_BOM)
    $hba = "# AxiaAtende (#950): so desta maquina, so por senha.`r`n" +
           "host    all             all             127.0.0.1/32            scram-sha-256`r`n"
    [IO.File]::WriteAllText((Join-Path $PGDATA 'pg_hba.conf'), $hba, $SEM_BOM)
    Ok "instancia criada em $PGDATA"
} else {
    Ok "a instancia ja existe em $PGDATA; reaproveitada"
}

if (-not (Test-Path $ENVRECEP)) {
    # O arquivo do recepcionista: a senha do banco ja vem; as chaves de fora vem COMENTADAS, para
    # o dono tirar o # e colar o valor (uma linha comentada nunca e lida como valor).
    $senhaApp = Ler-Segredo 'AXIAATENDE_BANCO_SENHA'
    $conteudo = "# Segredos do RECEPCIONISTA do AxiaAtende (#950). Nao copie, nao mostre.`r`n" +
                "AXIAATENDE_BANCO_SENHA=$senhaApp`r`n" +
                "# Cole cada valor depois do = e tire o # do comeco da linha (G3 do plano):`r`n" +
                "# META_TOKEN=`r`n# META_APP_SECRET=`r`n# META_VERIFY_TOKEN=`r`n# ANTHROPIC_API_KEY=`r`n" +
                "# A chave que liga as respostas. So no ensaio e na troca do dia (Fase H):`r`n" +
                "ATENDE_RESPONDE=false`r`n"
    [IO.File]::WriteAllText($ENVRECEP, $conteudo, $SEM_BOM)
    $senhaApp = $null
}
Fechar $ENVRECEP @("${LOCALSERV}:R")
Ok "segredo do recepcionista em $ENVRECEP (administrador, sistema e LocalService leem)"

if (-not (Get-Service axiaatende-postgres -ErrorAction SilentlyContinue)) {
    & "$PG\pg_ctl.exe" register -N axiaatende-postgres -D $PGDATA -S auto -w | Out-Null
    if ($LASTEXITCODE -ne 0) { Falha 'nao consegui registrar o servico axiaatende-postgres' }
}
Set-Service axiaatende-postgres -StartupType Automatic
Start-Service axiaatende-postgres
& "$PG\pg_isready.exe" -h 127.0.0.1 -p $PORTA -t 30 | Out-Null
if ($LASTEXITCODE -ne 0) { Falha 'o banco nao respondeu na 5436' }
Ok 'axiaatende-postgres de pe na 5436'

# O usuario dos servicos e o dono do banco dele. Nao e superusuario.
$env:PGPASSWORD = Ler-Segredo 'AXIAATENDE_SU_SENHA'
$senhaApp = Ler-Segredo 'AXIAATENDE_BANCO_SENHA'
try {
    $temApp = & "$PG\psql.exe" -h 127.0.0.1 -p $PORTA -U $SUPER -d postgres -Atc "SELECT 1 FROM pg_roles WHERE rolname = '$APP'"
    if ($temApp -ne '1') {
        # A senha vai por variavel do psql (:'senha'), e nao colada no texto do comando.
        "CREATE ROLE $APP LOGIN PASSWORD :'senha';" |
            & "$PG\psql.exe" -h 127.0.0.1 -p $PORTA -U $SUPER -d postgres -v ON_ERROR_STOP=1 -q -v "senha=$senhaApp" | Out-Null
        if ($LASTEXITCODE -ne 0) { Falha "nao consegui criar o usuario $APP" }
    }
    $temBanco = & "$PG\psql.exe" -h 127.0.0.1 -p $PORTA -U $SUPER -d postgres -Atc "SELECT 1 FROM pg_database WHERE datname = '$BANCO'"
    if ($temBanco -ne '1') {
        & "$PG\psql.exe" -h 127.0.0.1 -p $PORTA -U $SUPER -d postgres -v ON_ERROR_STOP=1 -qc "CREATE DATABASE $BANCO OWNER $APP" | Out-Null
        if ($LASTEXITCODE -ne 0) { Falha "nao consegui criar o banco $BANCO" }
        & "$PG\psql.exe" -h 127.0.0.1 -p $PORTA -U $SUPER -d $BANCO -v ON_ERROR_STOP=1 -qc "REVOKE ALL ON SCHEMA public FROM PUBLIC" | Out-Null
    }
} finally {
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
    $senhaApp = $null
}
Ok "banco $BANCO, dono $APP"

# A chave do pedido de envio vai tambem para o AxiaMarketing (o servico confere a lista; o publicador pede).
# Instalacao antiga sem a chave: ela nasce agora, nos dois lados.
if (-not (Ler-Segredo 'AXIAATENDE_CHAVE_PEDIDO')) {
    [IO.File]::AppendAllText($SEGREDOS, "AXIAATENDE_CHAVE_PEDIDO=$(Nova-Senha)`r`n", $SEM_BOM)
}
$chave = Ler-Segredo 'AXIAATENDE_CHAVE_PEDIDO'
$ENVPUB = 'C:\AxiaMarketing\.env.secrets'   # o config do marketing le a chave daqui (#950)
if (Test-Path $ENVPUB) {
    $linhas = [IO.File]::ReadAllLines($ENVPUB) | Where-Object { -not $_.StartsWith('AXIAATENDE_CHAVE_PEDIDO=') }
    [IO.File]::WriteAllText($ENVPUB, (($linhas + "AXIAATENDE_CHAVE_PEDIDO=$chave") -join "`r`n") + "`r`n", $SEM_BOM)
    Ok 'chave do pedido de envio escrita tambem no .env.secrets do AxiaMarketing'
} else {
    Write-Host "   ??  $ENVPUB nao existe: o Marketing ainda nao consegue pedir envio" -ForegroundColor Yellow
}
$chave = $null

# ── 3. logs ──────────────────────────────────────────────────────────────────
Passo '3. Pastas de log e das imagens dos envios'
$ENVIOS = Join-Path $DADOS 'envios'
New-Item -ItemType Directory -Force $ENVIOS | Out-Null
# As telas (LocalSystem) copiam as imagens do pedido para ca; o recepcionista (LocalService) le.
& icacls $ENVIOS /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' "${LOCALSERV}:(OI)(CI)RX" | Out-Null
if ($LASTEXITCODE -ne 0) { Falha "nao consegui fechar $ENVIOS" }
Ok "$ENVIOS (sistema escreve, LocalService le)"
New-Item -ItemType Directory -Force $LOGS, $LOGRECEP | Out-Null
& icacls $LOGRECEP /grant "${LOCALSERV}:(OI)(CI)M" | Out-Null
if ($LASTEXITCODE -ne 0) { Falha 'nao consegui dar o log do recepcionista a LocalService' }
Ok "$LOGS e $LOGRECEP (este, LocalService escreve)"

# ── 4. LocalService le o codigo e o Python, e so ─────────────────────────────
Passo '4. Leitura do codigo para o recepcionista'
& icacls $RAIZ /grant "${LOCALSERV}:(OI)(CI)RX" | Out-Null
if ($LASTEXITCODE -ne 0) { Falha "nao consegui dar a LocalService leitura de $RAIZ" }
Fechar $SEGREDOS @()   # de novo: a heranca nova nao pode alcancar o segredo das telas
$ace = (& icacls $SEGREDOS) -join ' '
if ($ace -match 'S-1-5-19|SERVI.O LOCAL|LOCAL SERVICE') { Falha "$SEGREDOS ficou legivel a LocalService" }
Ok 'LocalService le o codigo e o .venv; o .env.secrets continua so de administrador e sistema'

# ── 5 e 6. servicos ──────────────────────────────────────────────────────────
Passo '5. Servico axiaatende-backend (as telas, 127.0.0.1:8009)'
$s = Instalar-Servico 'axiaatende-backend' 8009
Ok ("/saude de pe, mudancas aplicadas: " + ($s.mudancas -join ', '))

Passo '6. Servico axiaatende-recepcionista (127.0.0.1:8008, LocalService)'
$s = Instalar-Servico 'axiaatende-recepcionista' 8008
if ($s.responde) { Write-Host '   ??  ATENDE_RESPONDE=true: o recepcionista RESPONDE. So no ensaio e na troca do dia.' -ForegroundColor Yellow }
else { Ok 'recepcionista de pe, EM ESCUTA (grava e nao responde)' }

# ── 7. conferencia ───────────────────────────────────────────────────────────
Passo '7. Conferencia'
$escuta = netstat -ano | Select-String 'LISTENING' | Select-String ':(5436|8008|8009) '
$escuta | ForEach-Object { Write-Host "   $($_.Line.Trim())" }
if ($escuta | Where-Object { $_.Line -notmatch '127\.0\.0\.1:(5436|8008|8009) ' }) { Falha '5436, 8008 ou 8009 escutando fora de 127.0.0.1' }
Ok '5436, 8008 e 8009 so em 127.0.0.1'
foreach ($u in 'http://127.0.0.1:8001/health', 'http://127.0.0.1:8006/saude') {
    try { Invoke-WebRequest $u -UseBasicParsing -TimeoutSec 10 | Out-Null; Ok "$u responde como antes" }
    catch { Write-Host "   ??  $u -- $($_.Exception.Message)" -ForegroundColor Yellow }
}

Write-Host ''
Write-Host 'PRONTO. Proximos passos (plano do #950):' -ForegroundColor Green
Write-Host '   G3: cole as chaves no .env.recepcionista:  notepad C:\AxiaAtende\.env.recepcionista'
Write-Host '       e reinicie o recepcionista:            Restart-Service axiaatende-recepcionista'
Write-Host '   Usuario das telas:  $env:AXIAATENDE_AMBIENTE = ''producao''; C:\AxiaAtende\.venv\Scripts\python.exe C:\AxiaAtende\scripts\criar_usuario.py'
Write-Host '   G5 (o endereco publico, so depois do G3 e G4):'
Write-Host "       & 'C:\Program Files\Tailscale\tailscale.exe' funnel --bg --https=443 http://127.0.0.1:8008"
Write-Host '       Desligar: tailscale funnel --https=443 off' -ForegroundColor Green
