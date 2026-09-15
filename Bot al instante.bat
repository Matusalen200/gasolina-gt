@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Bot al instante - Gasolina GT
echo El bot esta escuchando. Escribele por Telegram.
echo Cierra esta ventana para apagarlo.
echo.
".venv\Scripts\python.exe" "bot\telegram.py" --escuchar
pause
