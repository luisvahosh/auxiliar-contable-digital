@echo off
REM Auxiliar Contable Digital - arranque local con doble clic
REM Hace: venv + dependencias + migraciones + servidor + abre el navegador
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python no esta instalado o no esta en el PATH.
    echo Instalalo desde https://www.python.org/downloads/ marcando "Add Python to PATH".
    pause
    exit /b 1
)

if not exist .venv (
    echo Creando entorno virtual...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Instalando dependencias...
pip install -r requirements.txt --quiet

if not exist .env (
    echo [AVISO] No existe .env - copiando .env.example. Edita DJANGO_SECRET_KEY.
    copy .env.example .env
)

echo Aplicando migraciones...
python manage.py migrate

echo.
echo Servidor corriendo en http://127.0.0.1:8000 - cierra esta ventana para detenerlo.
start http://127.0.0.1:8000
python manage.py runserver
pause
