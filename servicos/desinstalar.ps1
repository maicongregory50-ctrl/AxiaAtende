# Desfaz os servicos do AxiaAtende (#950). NAO apaga dado: o banco, os segredos e os logs ficam.
# RODAR EM POWERSHELL COMO ADMINISTRADOR:
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\AxiaAtende\servicos\desinstalar.ps1
#
# Antes, se o numero ja estiver apontado para o AxiaAtende (Fase H), DESFACA A TROCA: sem isso,
# quem chamar a Renascer no WhatsApp fica sem resposta. Desfazer a troca devolve o numero ao Opa.

$ErrorActionPreference = 'Stop'
$SERVICOS = 'C:\AxiaAtende\servicos'

& 'C:\Program Files\Tailscale\tailscale.exe' funnel --https=443 off 2>$null
foreach ($id in 'axiaatende-recepcionista', 'axiaatende-backend') {
    if (Get-Service $id -ErrorAction SilentlyContinue) {
        Stop-Service $id -ErrorAction SilentlyContinue
        & (Join-Path $SERVICOS "$id.exe") uninstall | Out-Null
        Write-Host "   ok  $id parado e desinstalado" -ForegroundColor Green
    }
}
if (Get-Service axiaatende-postgres -ErrorAction SilentlyContinue) {
    Stop-Service axiaatende-postgres -ErrorAction SilentlyContinue
    Set-Service axiaatende-postgres -StartupType Disabled
    Write-Host '   ok  axiaatende-postgres parado e desabilitado (os dados ficam em C:\Dados\AxiaAtende\pgdata)' -ForegroundColor Green
}
