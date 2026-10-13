<#
.SYNOPSIS
    Cria o papel SO-LEITURA `axiaatende_ro` no banco de producao do AxiaAtende e o pgpass da sessao
    (C:\AxiaAtende\.pgpass_leitura). #981, 13/10/2026.
.DESCRIPTION
    Rodar em janela ELEVADA (le C:\AxiaAtende\.env.secrets, fechado a Administradores):
        & C:\AxiaAtende\servicos\criar_leitura.ps1            # papel, grants, pgpass, provas
        & C:\AxiaAtende\servicos\criar_leitura.ps1 -ComLog    # idem, e liga o coletor de log do Postgres
                                                              #   (REINICIA o axiaatende-postgres: segundos)
        & C:\AxiaAtende\servicos\criar_leitura.ps1 -Rotacionar   # senha nova para o papel, nos dois lugares
        & C:\AxiaAtende\servicos\criar_leitura.ps1 -SoPgpass     # so reescreve o pgpass a partir do .env.secrets

    POR QUE EXISTE: a sessao de agente (que roda como o dono, sem elevacao) nao le nada do que
    acontece no atendimento em producao; cada decisao do #970 nasceu de um print. O molde e o do
    ERP (C:\AxiaSecurity\scripts\criar_pgpass_executor.ps1, #337): um papel com SELECT e nada mais,
    a senha dele num pgpass de UMA linha, fechado por ACL (SYSTEM, Administradores, o dono lendo).
    Quem recusa escrever e o Postgres: o papel nao tem o privilegio E nasce com
    default_transaction_read_only = on.

    O QUE FAZ, em ordem, e PODE RODAR DE NOVO:
      1. AXIAATENDE_RO_SENHA no .env.secrets: gera se nao existe (ou se -Rotacionar). E a origem
         da rotacao: o pgpass e sempre reescrito a partir dela.
      2. No banco (como axiaatende_su, senha por variavel do psql, nunca no texto): CREATE/ALTER
         ROLE axiaatende_ro LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
         default_transaction_read_only = on; log_statement = 'all' (o log so deste papel);
         GRANT USAGE no schema atendimento, SELECT em todas as tabelas dele, e ALTER DEFAULT
         PRIVILEGES FOR ROLE axiaatende_app (quem cria tabela nas migracoes) para a tabela nova
         nascer legivel. NADA em casa (hash de senha) nem em public.
      3. C:\AxiaAtende\.pgpass_leitura: uma linha, UTF-8 sem BOM, ACL por SID. Se o icacls falhar,
         o arquivo e apagado: pgpass sem ACL nao fica no disco.
      4. PROVA PELO EFEITO, com PGPASSFILE apontando para o arquivo: entra como axiaatende_ro sem
         senha digitada; o banco recusa um UPDATE (where false: nenhuma linha, mas o privilegio e
         conferido antes); casa.usuarios e recusada; e o superusuario NAO entra por este arquivo.
      5. -ComLog: ALTER SYSTEM liga o coletor de log em C:\Logs\AxiaAtende\postgres (um arquivo
         por dia, prefixo com usuario@banco), reinicia o axiaatende-postgres e prova que o arquivo
         do dia tem uma linha do papel.

    O QUE NAO FAZ: nao imprime senha; nao mexe no pgpass.conf do dono; nao toca no .env.recepcionista;
    nao cria papel com escrita.

    DESFAZER: psql -U axiaatende_su -d axiaatende -c "DROP OWNED BY axiaatende_ro; DROP ROLE axiaatende_ro;"
    e Remove-Item C:\AxiaAtende\.pgpass_leitura; tirar AXIAATENDE_RO_SENHA do .env.secrets.
#>
param([switch]$Rotacionar, [switch]$SoPgpass, [switch]$ComLog)

$ErrorActionPreference = 'Stop'

$PG       = 'C:\Program Files\PostgreSQL\17\bin'
$RAIZ     = 'C:\AxiaAtende'
$SEGREDOS = Join-Path $RAIZ '.env.secrets'
$PGPASS   = Join-Path $RAIZ '.pgpass_leitura'
$LOGPG    = 'C:\Logs\AxiaAtende\postgres'
$PORTA    = 5436
$SUPER    = 'axiaatende_su'
$APP      = 'axiaatende_app'
$RO       = 'axiaatende_ro'
$BANCO    = 'axiaatende'
$DONO     = "$env:COMPUTERNAME\Maicon"
$SEM_BOM  = New-Object System.Text.UTF8Encoding($false)

function Ok($texto)    { Write-Host "   ok  $texto" -ForegroundColor Green }
function Falha($texto) { Write-Host "   !!  $texto" -ForegroundColor Red; exit 1 }

function Nova-Senha {
    $b = New-Object byte[] 24
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
    return ([Convert]::ToBase64String($b)).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

function Ler-Segredo($chave) {
    foreach ($linha in [IO.File]::ReadAllLines($SEGREDOS)) {
        if ($linha.StartsWith($chave + '=')) { return $linha.Substring($chave.Length + 1) }
    }
    return ''
}

function Gravar-Segredo($chave, $valor) {
    # Troca a linha se existe; acrescenta se nao. As outras linhas ficam byte a byte.
    $linhas = [IO.File]::ReadAllLines($SEGREDOS)
    $achou = $false
    $novas = foreach ($l in $linhas) { if ($l.StartsWith($chave + '=')) { $achou = $true; "$chave=$valor" } else { $l } }
    if (-not $achou) { $novas += "$chave=$valor" }
    [IO.File]::WriteAllText($SEGREDOS, (($novas -join "`r`n") + "`r`n"), $SEM_BOM)
}

function Psql($banco, $sql, $variaveis = @()) {
    $saida = $sql | & "$PG\psql.exe" -h 127.0.0.1 -p $PORTA -U $SUPER -d $banco -v ON_ERROR_STOP=1 -q -At @variaveis 2>&1
    if ($LASTEXITCODE -ne 0) { Falha "psql falhou em '$($sql.Substring(0, [Math]::Min(60, $sql.Length)))...': $saida" }
    return ($saida | Out-String).Trim()
}

# -- 0. elevacao e pre-requisitos -------------------------------------------------------------
$eu = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $eu.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Falha 'rode este script numa janela do PowerShell COMO ADMINISTRADOR'
}
if (-not (Test-Path $SEGREDOS)) { Falha "nao achei ${SEGREDOS}: rode servicos\instalar.ps1 antes" }
if (-not (Test-Path "$PG\psql.exe")) { Falha "nao achei o psql em $PG" }
if ($SoPgpass -and $Rotacionar) { Falha '-SoPgpass e -Rotacionar nao andam juntos: rotacionar e trocar a senha nos dois lugares' }

# -- 1. a senha do papel, no .env.secrets -----------------------------------------------------
$senhaRo = Ler-Segredo 'AXIAATENDE_RO_SENHA'
if ($SoPgpass -and -not $senhaRo) { Falha 'AXIAATENDE_RO_SENHA nao existe no .env.secrets: rode sem -SoPgpass' }
$senhaNova = $false
if ($Rotacionar -or -not $senhaRo) {
    $senhaRo = Nova-Senha
    Gravar-Segredo 'AXIAATENDE_RO_SENHA' $senhaRo
    $senhaNova = $true
    Ok "AXIAATENDE_RO_SENHA $(if ($Rotacionar) { 'rotacionada' } else { 'criada' }) em $SEGREDOS (nao exibida)"
} else {
    Ok 'AXIAATENDE_RO_SENHA ja existe no .env.secrets; reaproveitada'
}

# -- 2. o papel e as permissoes ---------------------------------------------------------------
if (-not $SoPgpass) {
    $env:PGPASSWORD = Ler-Segredo 'AXIAATENDE_SU_SENHA'
    if (-not $env:PGPASSWORD) { Falha 'AXIAATENDE_SU_SENHA vazia no .env.secrets' }
    try {
        $tem = Psql 'postgres' "SELECT 1 FROM pg_roles WHERE rolname = '$RO'"
        if ($tem -ne '1') {
            Psql 'postgres' "CREATE ROLE $RO LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT PASSWORD :'senha';" @('-v', "senha=$senhaRo") | Out-Null
            Ok "papel $RO criado"
        } elseif ($senhaNova) {
            Psql 'postgres' "ALTER ROLE $RO PASSWORD :'senha';" @('-v', "senha=$senhaRo") | Out-Null
            Ok "senha do papel $RO trocada no banco"
        } else {
            Ok "papel $RO ja existe; reaproveitado"
        }
        Psql 'postgres' "ALTER ROLE $RO SET default_transaction_read_only = on;" | Out-Null
        Psql 'postgres' "ALTER ROLE $RO SET log_statement = 'all';" | Out-Null
        Psql $BANCO ("GRANT USAGE ON SCHEMA atendimento TO $RO; " +
                     "GRANT SELECT ON ALL TABLES IN SCHEMA atendimento TO $RO; " +
                     "ALTER DEFAULT PRIVILEGES FOR ROLE $APP IN SCHEMA atendimento GRANT SELECT ON TABLES TO $RO;") | Out-Null
        $n = Psql $BANCO "SELECT count(*) FROM information_schema.table_privileges WHERE grantee = '$RO' AND privilege_type = 'SELECT' AND table_schema = 'atendimento'"
        $casa = Psql $BANCO "SELECT count(*) FROM information_schema.table_privileges WHERE grantee = '$RO' AND table_schema <> 'atendimento'"
        if ($casa -ne '0') { Falha "o papel $RO tem privilegio fora de atendimento ($casa): desfaca com DROP OWNED BY $RO e avise" }
        Ok "SELECT em $n tabelas de atendimento, nada fora; transacao so-leitura; log_statement=all"

        if ($ComLog) {
            New-Item -ItemType Directory -Force $LOGPG | Out-Null
            $dir = $LOGPG.Replace('\', '/')
            Psql 'postgres' "ALTER SYSTEM SET logging_collector = on;" | Out-Null
            Psql 'postgres' "ALTER SYSTEM SET log_directory = '$dir';" | Out-Null
            Psql 'postgres' "ALTER SYSTEM SET log_filename = 'postgres-%Y-%m-%d.log';" | Out-Null
            Psql 'postgres' "ALTER SYSTEM SET log_rotation_age = '1d';" | Out-Null
            Psql 'postgres' "ALTER SYSTEM SET log_rotation_size = 0;" | Out-Null
            Psql 'postgres' "ALTER SYSTEM SET log_truncate_on_rotation = off;" | Out-Null
            Psql 'postgres' "ALTER SYSTEM SET log_line_prefix = '%m [%p] %u@%d ';" | Out-Null
            Ok "coletor de log configurado para $LOGPG (ALTER SYSTEM); reiniciando o axiaatende-postgres"
            # As telas e o recepcionista DEPENDEM do servico do banco (WinSW): sem parar os dois antes,
            # o Restart-Service recusa ("possui servicos dependentes", 13/10/2026). Para os que estao
            # rodando, reinicia o banco, e sobe os mesmos de volta -- segundos, e so os que estavam de pe.
            $dependentes = @((Get-Service axiaatende-postgres).DependentServices | Where-Object { $_.Status -eq 'Running' } | ForEach-Object { $_.Name })
            foreach ($d in $dependentes) { Stop-Service $d -ErrorAction Stop }
            Restart-Service axiaatende-postgres -ErrorAction Stop
            $pronto = $false
            for ($i = 0; $i -lt 30 -and -not $pronto; $i++) {
                & "$PG\pg_isready.exe" -h 127.0.0.1 -p $PORTA -t 2 | Out-Null
                if ($LASTEXITCODE -eq 0) { $pronto = $true } else { Start-Sleep -Seconds 1 }
            }
            if (-not $pronto) { Falha "o axiaatende-postgres nao voltou na $PORTA. Volte: ALTER SYSTEM RESET logging_collector (ou apague a linha em C:\Dados\AxiaAtende\pgdata\postgresql.auto.conf), Start-Service axiaatende-postgres e depois $($dependentes -join ', ')" }
            Ok 'axiaatende-postgres de pe'
            foreach ($d in ($dependentes | Sort-Object)) {   # axiaatende-backend antes de axiaatende-recepcionista
                Start-Service $d -ErrorAction Stop
                # NAO chamar de $porta: no PowerShell o nome nao distingue maiusculas e isto sobrescreveria
                # a $PORTA do banco (aconteceu em 13/10/2026: o pgpass saiu com a 8008).
                $portaSaude = if ($d -eq 'axiaatende-backend') { 8009 } elseif ($d -eq 'axiaatende-recepcionista') { 8008 } else { 0 }
                if ($portaSaude) {
                    $saude = $null
                    for ($i = 0; $i -lt 30 -and -not $saude; $i++) {
                        try { $saude = Invoke-RestMethod "http://127.0.0.1:$portaSaude/saude" -TimeoutSec 2 } catch { Start-Sleep -Seconds 1 }
                    }
                    if (-not $saude) { Falha "$d nao respondeu em /saude depois do reinicio do banco; veja C:\Logs\AxiaAtende" }
                }
                Ok "$d de volta"
            }
        }
    } finally {
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
    }
}

# -- 3. o pgpass: uma linha, UTF-8 sem BOM, ACL por SID ---------------------------------------
# O BOM grudaria no primeiro campo e o libpq nunca casaria. `\` e `:` sao os dois caracteres que
# o formato exige escapar. Host/porta/banco explicitos: este arquivo so serve para este banco.
$escapada = $senhaRo.Replace('\', '\\').Replace(':', '\:')
[IO.File]::WriteAllText($PGPASS, "127.0.0.1:${PORTA}:${BANCO}:${RO}:$escapada`n", $SEM_BOM)
$senhaRo = $null; $escapada = $null
& icacls $PGPASS /inheritance:r /grant:r "${DONO}:(R)" '*S-1-5-32-544:(F)' '*S-1-5-18:(F)' | Out-Null
if ($LASTEXITCODE -ne 0) {
    Remove-Item $PGPASS -Force -ErrorAction SilentlyContinue
    Falha "icacls falhou ($LASTEXITCODE): o pgpass foi apagado; nada ficou aberto"
}
Ok "gravado $PGPASS (ACL: $DONO leitura, Administradores, SYSTEM)"

# -- 4. a prova, pelo efeito ------------------------------------------------------------------
# Tres das quatro provas ESPERAM erro do psql no stderr. Com `Stop`, o PowerShell 5.1 transforma
# a primeira linha de stderr de executavel nativo em excecao antes de a prova le-la.
$env:PGPASSFILE = $PGPASS
$ErrorActionPreference = 'Continue'
try {
    $quem = & "$PG\psql.exe" -h 127.0.0.1 -p $PORTA -U $RO -d $BANCO -w -Atc 'select current_user' 2>&1
    if (($quem | Out-String).Trim() -ne $RO) { Falha "a conexao nao entrou como ${RO}: $quem" }
    Ok "entra como $RO sem digitar senha"

    $escrita = & "$PG\psql.exe" -h 127.0.0.1 -p $PORTA -U $RO -d $BANCO -w -Atc 'update atendimento.ajustes set valor = valor where false' 2>&1
    if (($escrita | Out-String) -notmatch 'read-only|somente leitura|permission denied|permiss') {
        Falha "o banco NAO recusou a escrita do ${RO}: $escrita -- apague $PGPASS e avise"
    }
    Ok "o banco recusa escrever ($(($escrita | Out-String).Trim().Split([Environment]::NewLine)[0]))"

    $casaProva = & "$PG\psql.exe" -h 127.0.0.1 -p $PORTA -U $RO -d $BANCO -w -Atc 'select count(*) from casa.usuarios' 2>&1
    if (($casaProva | Out-String) -notmatch 'permission denied|permiss') {
        Falha "o ${RO} LEU casa.usuarios: $casaProva -- DROP OWNED BY $RO e avise"
    }
    Ok 'casa.usuarios recusada'

    $su = & "$PG\psql.exe" -h 127.0.0.1 -p $PORTA -U $SUPER -d $BANCO -w -Atc 'select 1' 2>&1
    if (($su | Out-String) -notmatch 'no password|senha|password') {
        Falha "com este PGPASSFILE o $SUPER ainda entrou -- o arquivo nao esta isolando: $su"
    }
    Ok "o superusuario nao entra por este arquivo"

    if ($ComLog) {
        Start-Sleep -Seconds 2
        $arq = Get-ChildItem $LOGPG -Filter 'postgres-*.log' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime | Select-Object -Last 1
        if (-not $arq) { Falha "o coletor nao escreveu em $LOGPG" }
        if (-not (Select-String -Path $arq.FullName -Pattern "$RO@$BANCO" -Quiet)) { Falha "o log do dia ($($arq.Name)) nao tem linha do $RO" }
        Ok "log do Postgres em $($arq.FullName), com o $RO"
    }
} finally {
    Remove-Item Env:\PGPASSFILE -ErrorAction SilentlyContinue
}

Write-Host ''
Write-Host "Pronto. Na sessao (sem elevacao): python C:\AxiaAtende\scripts\ler_conversa.py --ultimas 20" -ForegroundColor Cyan
Write-Host "Registro das leituras: C:\Logs\AxiaAtende\leituras.jsonl. Desfazer: ver o cabecalho deste script." -ForegroundColor Cyan
