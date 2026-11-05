@echo off
REM Agente de vacantes - ejecucion en Windows con Google Chrome
REM Requiere Python 3.10+ (https://www.python.org/downloads/ - marcar "Add python.exe to PATH")
REM y Google Chrome instalado.
cd /d "%~dp0"
if not exist .venv (
  python -m venv .venv || (echo No se encontro Python. Instalelo y vuelva a intentar. & pause & exit /b 1)
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt || (echo Fallo la instalacion de dependencias. & pause & exit /b 1)

echo.
echo 1 = Verificar la pagina del SIGEP en Chrome (recomendado la primera vez)
echo 2 = Ejecutar el agente (contratos y vacantes)
set /p OPCION="Opcion: "
set /p CODIGO="Codigo de entidad (Enter = 5202 al verificar / todas al ejecutar): "

if "%OPCION%"=="1" (
  if "%CODIGO%"=="" set CODIGO=5202
  python -m agente_vacantes verificar --codigo %CODIGO%
  echo.
  echo Envie a Claude la carpeta "verificacion" (informe.txt, .html y .png^).
  pause
  exit /b 0
)

if not exist entidades.csv (
  echo Descargando lista de entidades del SIGEP...
  python -m agente_vacantes entidades
)
if "%CODIGO%"=="" (
  python -m agente_vacantes ejecutar --desde 2026-08-01 --hasta 2026-11-30 --sin-ia
) else (
  python -m agente_vacantes ejecutar --codigo %CODIGO% --desde 2026-08-01 --hasta 2026-11-30 --sin-ia
)
echo.
echo Listo. Revise la carpeta "salida". Si una consulta no trajo filas, el HTML quedo en .cache\sigep_debug\
pause
