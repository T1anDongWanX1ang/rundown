@echo off
setlocal
cd /d "%~dp0"
set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
if /i "%~1"=="setup" (
    python -m venv .venv
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    goto end
)
if /i "%~1"=="daily" (
    if "%~2"=="" ("%PY%" rundown_etl.py daily) else ("%PY%" rundown_etl.py daily --date %~2)
    goto end
)
if /i "%~1"=="live" (
    "%PY%" rundown_etl.py live %2
    goto end
)
if /i "%~1"=="serve" (
    "%PY%" rundown_etl.py serve
    goto end
)
echo 用法: run.bat {setup^|daily [日期]^|live [--once]^|serve}
exit /b 1
:end
endlocal
