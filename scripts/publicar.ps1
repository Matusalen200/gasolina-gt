# Publica Gasolina GT en GitHub: repo público, secrets, Pages y primera corrida.
# Requisitos: gh auth login (una vez). Uso:
#   .\scripts\publicar.ps1 -Nombre gasolina-gt -AnthropicKey "sk-ant-..." [-TelegramToken "..."] [-TelegramChannel "@canal"]
param(
  [string]$Nombre = "gasolina-gt",
  [string]$AnthropicKey = $env:ANTHROPIC_API_KEY,
  [string]$TelegramToken = $env:TELEGRAM_BOT_TOKEN,
  [string]$TelegramChannel = $env:TELEGRAM_CHANNEL_ID
)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

gh auth status | Out-Null
$usuario = gh api user --jq .login
Write-Host "Usuario GitHub: $usuario"

if (-not (git remote 2>$null | Select-String -Quiet "origin")) {
  gh repo create $Nombre --public --source . --remote origin --description "Dónde y cuándo llenar gasolina en Guatemala" --push
} else {
  git push -u origin main
}

if ($AnthropicKey) { gh secret set ANTHROPIC_API_KEY --body $AnthropicKey } else { Write-Warning "Sin ANTHROPIC_API_KEY: el agente usará reglas en vez de Claude." }
if ($TelegramToken) { gh secret set TELEGRAM_BOT_TOKEN --body $TelegramToken }
if ($TelegramChannel) { gh secret set TELEGRAM_CHANNEL_ID --body $TelegramChannel }

# GitHub Pages desde la rama main, carpeta raíz.
try {
  gh api -X POST "repos/$usuario/$Nombre/pages" -f "source[branch]=main" -f "source[path]=/" | Out-Null
} catch {
  gh api -X PUT "repos/$usuario/$Nombre/pages" -f "source[branch]=main" -f "source[path]=/" | Out-Null
}

gh workflow run agente.yml -f modo=diaria
Start-Sleep -Seconds 5
gh run list --workflow agente.yml --limit 1

Write-Host ""
Write-Host "Repo:    https://github.com/$usuario/$Nombre"
Write-Host "Tablero: https://$usuario.github.io/$Nombre/web/  (tarda 1-3 minutos en aparecer)"
