@echo off
REM ATLAS - sobe API, visao e site, cada um na sua janela.
REM
REM Uso:  atlas.bat         pipeline real (YOLO sobre o video da camera)
REM       atlas.bat fake    contagens falsas, sem video nem modelo
REM
REM As portas podem ser trocadas pelo ambiente:
REM       set API_PORT=8001 && atlas.bat

setlocal

set "ROOT=%~dp0"
if not defined API_PORT set "API_PORT=8000"
if not defined WEB_PORT set "WEB_PORT=3000"
if not defined CAMERA_ID set "CAMERA_ID=CAM-01"

set "VISION_ARGS="
if /i "%~1"=="fake" set "VISION_ARGS=--fake"
REM Argumento errado calado viraria modo real numa demo que pedia --fake.
if not "%~1"=="" if not defined VISION_ARGS (
    echo   [ERRO] Argumento desconhecido: %~1
    echo          Uso: atlas.bat [fake]
    exit /b 1
)

echo.
echo   ATLAS - subindo os tres modulos
echo.

REM Porta ocupada nao da erro visivel: o uvicorn morre sozinho e o site fica
REM repetindo "API indisponivel". Conferir antes e mais barato que descobrir
REM na demo.
call :check_port %API_PORT% API
if errorlevel 1 exit /b 1
call :check_port %WEB_PORT% site
if errorlevel 1 exit /b 1

REM Cada modulo usa o proprio .venv quando existe; senao, o Python do sistema.
set "PY_API=python"
if exist "%ROOT%api\.venv\Scripts\python.exe" set "PY_API=.venv\Scripts\python.exe"
set "PY_VISION=python"
if exist "%ROOT%vision\.venv\Scripts\python.exe" set "PY_VISION=.venv\Scripts\python.exe"

echo   [1/3] API     http://localhost:%API_PORT%
start "ATLAS API" /D "%ROOT%api" cmd /k %PY_API% -m uvicorn app.main:app --port %API_PORT%

REM A visao so tem o que fazer depois que /ingest responde; subir junto so
REM encheria o log de warning de conexao recusada.
set /a tries=0
:wait_api
set /a tries+=1
curl -s -o nul http://localhost:%API_PORT%/health && goto api_ready
if %tries% geq 30 (
    echo.
    echo   [ERRO] A API nao respondeu em 30s. Veja a janela "ATLAS API".
    exit /b 1
)
REM ping no lugar de timeout: timeout aborta quando o stdin esta
REM redirecionado (CI, pipe), e ai o loop giraria sem pausa nenhuma.
ping -n 2 127.0.0.1 >nul
goto wait_api
:api_ready

echo   [2/3] Site    http://localhost:%WEB_PORT%
start "ATLAS Site" /D "%ROOT%website" cmd /k npm run dev -- --port %WEB_PORT%

echo   [3/3] Visao   camera %CAMERA_ID% %VISION_ARGS%
start "ATLAS Visao" /D "%ROOT%vision" cmd /k %PY_VISION% run.py --seed ../api/seed.json --camera-id %CAMERA_ID% --api-url http://localhost:%API_PORT% %VISION_ARGS%

echo.
echo   No ar. Abra http://localhost:%WEB_PORT%
echo   Feche as tres janelas para encerrar.
echo.
exit /b 0

REM %1 = porta, %2 = nome do modulo
:check_port
netstat -ano -p tcp | findstr /c:":%~1 " | findstr /c:"LISTENING" >nul
if errorlevel 1 exit /b 0
echo   [ERRO] Porta %~1 ocupada - %~2 nao vai subir.
for /f "tokens=5" %%p in ('netstat -ano -p tcp ^| findstr /c:":%~1 " ^| findstr /c:"LISTENING"') do echo          PID %%p
echo          Para liberar:  taskkill /PID ^<pid^> /F
exit /b 1
