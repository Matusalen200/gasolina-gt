# Programa Gasolina GT para que trabaje solo en esta PC.
#   · Cada hora, lunes a viernes de 7 a 15 (hora de Guatemala): revisa precios, mercado y noticias.
#   · Todos los días a las 7:00 de la mañana: publica el resumen en tu canal de Telegram.
# Quitar todo:  .\scripts\automatizar.ps1 -Quitar
param([switch]$Quitar)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$python = Join-Path $raiz ".venv\Scripts\python.exe"
$agente = Join-Path $raiz "agente\agente.py"
$tareaHora = "Gasolina GT - revisar precios"
$tareaDia = "Gasolina GT - publicar resumen"

function Quitar-Tarea($nombre) {
  schtasks /Query /TN $nombre *> $null
  if ($LASTEXITCODE -eq 0) { schtasks /Delete /TN $nombre /F *> $null; Write-Host "   Quitada: $nombre" }
}

if ($Quitar) {
  Quitar-Tarea $tareaHora
  Quitar-Tarea $tareaDia
  Write-Host "`nListo: Gasolina GT ya no corre solo. Puedes volver a programarlo cuando quieras."
  return
}

if (-not (Test-Path $python)) {
  Write-Host "No encuentro Python en $python"
  Write-Host "Abre una terminal en la carpeta del proyecto y corre:  python -m venv .venv"
  exit 1
}

Quitar-Tarea $tareaHora
Quitar-Tarea $tareaDia

# Revisión cada hora, de lunes a viernes, entre las 7 y las 15
$accionHora = "`"$python`" `"$agente`""
schtasks /Create /TN $tareaHora /TR $accionHora /SC HOURLY /MO 1 /ST 07:00 /D MON,TUE,WED,THU,FRI /RL LIMITED /F *> $null
if ($LASTEXITCODE -ne 0) { Write-Host "No pude crear la tarea por hora."; exit 1 }

# Resumen diario a las 7:00 de la mañana, todos los días
$accionDia = "`"$python`" `"$agente`" --diario"
schtasks /Create /TN $tareaDia /TR $accionDia /SC DAILY /ST 07:00 /RL LIMITED /F *> $null
if ($LASTEXITCODE -ne 0) { Write-Host "No pude crear la tarea diaria."; exit 1 }

Write-Host ""
Write-Host "Listo. Tu PC ahora hace esto sola:"
Write-Host "   · Cada hora (lunes a viernes): revisa precios, mercado y noticias."
Write-Host "   · Todos los días a las 7:00 am: publica el resumen en tu canal."
Write-Host ""
Write-Host "Ojo: la PC tiene que estar encendida a esas horas."
Write-Host "Para ver las tareas: abre 'Programador de tareas' y busca 'Gasolina GT'."
Write-Host "Para quitarlas:  .\scripts\automatizar.ps1 -Quitar"
