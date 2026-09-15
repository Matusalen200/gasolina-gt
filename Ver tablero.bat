@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Tablero - Gasolina GT
".venv\Scripts\python.exe" "scripts\tablero.py"
