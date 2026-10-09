# Liga a leitura do cadastro do ERP (#969): gera o segredo do agente ATENDIMENTO e grava nos dois
# lugares, sem mostrar o valor. Serve tambem para TROCAR o segredo (rodar de novo).
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\AxiaAtende\scripts\ligar_leitura_do_cadastro.ps1
#
# Janela ELEVADA (os dois arquivos sao fechados a administrador). Grava sem BOM: BOM no .env derruba
# servico. Depois: restart do ERP (8001) e dos dois servicos do AxiaAtende.
$ErrorActionPreference = 'Stop'
$semBom = New-Object Text.UTF8Encoding($false)
$bytes = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
$segredo = -join ($bytes | ForEach-Object { $_.ToString('x2') })

# 1. ERP: o JSON de AGENTE_SEGREDOS, no .env.secrets ou no .env (o que tiver a linha)
$feito = $false
foreach ($arq in 'C:\AxiaGestao\.env.secrets', 'C:\AxiaGestao\.env') {
    if (-not (Test-Path $arq)) { continue }
    $linhas = [IO.File]::ReadAllLines($arq)
    for ($i = 0; $i -lt $linhas.Count; $i++) {
        if ($linhas[$i] -match '^\s*AGENTE_SEGREDOS\s*=\s*(.*)$') {
            $v = $matches[1].Trim(); $aspas = ''
            if ($v.Length -ge 2 -and ($v[0] -eq "'" -or $v[0] -eq '"') -and $v[-1] -eq $v[0]) {
                $aspas = [string]$v[0]; $v = $v.Substring(1, $v.Length - 2)
            }
            $j = $v | ConvertFrom-Json
            if ($j.PSObject.Properties.Name -contains 'ATENDIMENTO') { $j.ATENDIMENTO = $segredo }
            else { $j | Add-Member -NotePropertyName ATENDIMENTO -NotePropertyValue $segredo }
            $novo = $j | ConvertTo-Json -Compress
            $null = $novo | ConvertFrom-Json   # o JSON tem de voltar a ler: senao nenhum agente autentica
            $linhas[$i] = 'AGENTE_SEGREDOS=' + $aspas + $novo + $aspas
            [IO.File]::WriteAllText($arq, ($linhas -join "`r`n") + "`r`n", $semBom)
            "ERP: o agente ATENDIMENTO entrou em $arq ($(@($j.PSObject.Properties).Count) agentes no total)"
            $feito = $true
            break
        }
    }
    if ($feito) { break }
}
if (-not $feito) { throw 'Nao achei AGENTE_SEGREDOS no .env do ERP. Nada foi gravado.' }

# 2. AxiaAtende: so o .env.secrets (o das telas); o recepcionista nunca le o ERP
$f = 'C:\AxiaAtende\.env.secrets'
$l = @([IO.File]::ReadAllLines($f) | Where-Object { $_ -notmatch '^AXIAATENDE_ERP_SEGREDO=' }) + "AXIAATENDE_ERP_SEGREDO=$segredo"
[IO.File]::WriteAllText($f, ($l -join "`r`n") + "`r`n", $semBom)
"AxiaAtende: o segredo entrou em $f"
$segredo = $null
