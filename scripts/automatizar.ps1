# Programa Gasolina GT para que trabaje solo en esta PC.
#   · Cada hora, lunes a viernes de 7 a 15 (hora de Guatemala): revisa precios, mercado y noticias.
#   · Todos los días a las 7:00 de la mañana: publica el resumen en tu canal de Telegram.
# Quitar todo:  .\scripts\automatizar.ps1 -Quitar
param([switch]$Quitar)

# Ojo: los comandos de Windows como schtasks se llaman con cmd /c para que PowerShell no
# convierta en error un "esta tarea no existe", que aquí es una respuesta normal.
$ErrorActionPreference = "Continue"
$raiz = Split-Path -Parent $PSScriptRoot
$python = Join-Path $raiz ".venv\Scripts\python.exe"
$agente = Join-Path $raiz "agente\agente.py"
$tareaHora = "Gasolina GT - revisar precios"
$tareaDia = "Gasolina GT - publicar resumen"

function Existe-Tarea($nombre) {
  cmd /c "schtasks /Query /TN `"$nombre`" >nul 2>&1"
  return ($LASTEXITCODE -eq 0)
}

function Quitar-Tarea($nombre) {
  if (Existe-Tarea $nombre) {
    cmd /c "schtasks /Delete /TN `"$nombre`" /F >nul 2>&1"
    Write-Host "   Quitada: $nombre"
  }
}

function Crear-Tarea($nombre, $accion, $extra) {
  $comando = "schtasks /Create /TN `"$nombre`" /TR `"$accion`" $extra /RL LIMITED /F >nul 2>&1"
  cmd /c $comando
  return ($LASTEXITCODE -eq 0)
}

if ($Quitar) {
  Quitar-Tarea $tareaHora
  Quitar-Tarea $tareaDia
  Write-Host ""
  Write-Host "Listo: Gasolina GT ya no corre solo en esta PC."
  Write-Host "Puedes volver a programarlo cuando quieras con Automatizar.bat."
  return
}

if (-not (Test-Path $python)) {
  Write-Host "No encuentro Python en $python"
  Write-Host "Abre una terminal en la carpeta del proyecto y corre:  python -m venv .venv"
  exit 1
}

Quitar-Tarea $tareaHora
Quitar-Tarea $tareaDia

$accionHora = "\`"$python\`" \`"$agente\`""
$accionDia = "\`"$python\`" \`"$agente\`" --diario"

# Windows no acepta "cada hora" junto con "solo dias de semana".
# Se hace con una tarea semanal que arranca a las 7:00 y se repite cada 60 minutos durante 8 horas.
$okHora = Crear-Tarea $tareaHora $accionHora "/SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 07:00 /RI 60 /DU 0008:00"
$okDia = Crear-Tarea $tareaDia $accionDia "/SC DAILY /ST 07:00"

if (-not $okHora -and -not $okDia) {
  Write-Host ""
  Write-Host "No pude programar las tareas en esta PC."
  Write-Host "No es grave: si publicas el proyecto en internet (Publicar en internet.bat),"
  Write-Host "todo corre en los servidores de GitHub y no hace falta esto."
  exit 1
}

Write-Host ""
Write-Host "Listo. Tu PC ahora hace esto sola:"
if ($okHora) { Write-Host "   . Cada hora (lunes a viernes): revisa precios, mercado y noticias." }
if ($okDia) { Write-Host "   . Todos los dias a las 7:00 am: publica el resumen en tu canal." }
Write-Host ""
Write-Host "Ojo: la PC tiene que estar encendida a esas horas."
Write-Host "Si la vas a tener apagada, usa Publicar en internet.bat: ahi no hace falta."
Write-Host ""
Write-Host "Para ver las tareas: abre 'Programador de tareas' y busca 'Gasolina GT'."
Write-Host "Para quitarlas: doble clic en Automatizar.bat y elige quitar, o corre:"
Write-Host "   .\scripts\automatizar.ps1 -Quitar"
