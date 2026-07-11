@echo off
REM Primer commit del proyecto (una sola vez)
cd /d "%~dp0"
where git >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Git no esta instalado. Descargalo de https://git-scm.com/download/win
    pause
    exit /b 1
)
if exist .git (
    echo Ya existe un repositorio git aqui. No se hace nada.
    pause
    exit /b 0
)
git init -b main
git add .
git commit -m "Dia 1: proyecto Django corriendo con configuracion por .env"
echo.
echo Listo: repositorio creado y primer commit hecho.
pause
