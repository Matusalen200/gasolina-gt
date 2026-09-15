@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Publicar en internet - Gasolina GT
".venv\Scripts\python.exe" "scripts\publicar.py"
echo.
pause
