@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Automatizar - Gasolina GT
powershell -ExecutionPolicy Bypass -File "scripts\automatizar.ps1"
echo.
pause
