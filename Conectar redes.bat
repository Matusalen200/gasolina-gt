@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Conectar Facebook e Instagram - Gasolina GT
".venv\Scripts\python.exe" "scripts\conectar_redes.py"
echo.
pause
