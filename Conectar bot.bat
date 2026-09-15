@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Conectar bot de Telegram - Gasolina GT
".venv\Scripts\python.exe" "scripts\conectar.py"
echo.
pause
