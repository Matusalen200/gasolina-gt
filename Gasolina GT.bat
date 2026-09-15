@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Gasolina GT
echo Buscando los precios de hoy... esto tarda un minuto.
echo.
".venv\Scripts\python.exe" "agente\agente.py" --diario
echo.
".venv\Scripts\python.exe" "scripts\tablero.py"
