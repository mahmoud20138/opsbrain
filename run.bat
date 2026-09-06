@echo off
setlocal enabledelayedexpansion

REM ============================================================================
REM  OpsBrain - Windows Launcher & Management Script
REM ============================================================================

REM Set working directory to script location
cd /d "%~dp0"

REM Determine runner command (prefer uv, fallback to .venv python)
where uv >nul 2>nul
if %errorlevel% equ 0 (
    set "RUNNER=uv run"
    set "PY=uv run python"
) else (
    if exist ".venv\Scripts\python.exe" (
        set "RUNNER=.venv\Scripts\"
        set "PY=.venv\Scripts\python.exe"
    ) else (
        set "RUNNER=python -m"
        set "PY=python"
    )
)

REM If arguments provided, handle directly
if not "%~1"=="" goto handle_args

:menu
cls
echo ================================================================
echo           [*] O P S B R A I N  -  M E N U
echo    Multi-Agent Enterprise Operations & Optimization
echo ================================================================
echo.
echo   [1] Run All Tests (pytest 88 tests)
echo   [2] Run Code Quality Check (ruff lint)
echo   [3] Quickstart Demo (Database Connection Pool Incident)
echo   [4] IT System Outage Scenario (Full 5-Stage Multi-Agent)
echo   [5] Supply Chain Scenario (Port Congestion & Allocation)
echo   [6] Workflow Delay Scenario (Invoice SLA Approval Optimization)
echo   [7] Run All 4 Operational Scenarios in Sequence
echo   [8] Run OpsBrain CLI Pipeline (Offline Mock Mode)
echo   [9] List LLM Providers & Connectivity Status
echo   [U] Launch Organizational Graph UI (Web Browser)
echo   [C] Generate Default Config File (configs/default.yaml)
echo   [0] Exit
echo.
echo ================================================================
set /p "CHOICE=Enter selection [0-9, U, C]: "

if "%CHOICE%"=="1" goto opt_test
if "%CHOICE%"=="2" goto opt_lint
if "%CHOICE%"=="3" goto opt_quickstart
if "%CHOICE%"=="4" goto opt_it
if "%CHOICE%"=="5" goto opt_supply
if "%CHOICE%"=="6" goto opt_workflow
if "%CHOICE%"=="7" goto opt_all_scenarios
if "%CHOICE%"=="8" goto opt_cli_mock
if "%CHOICE%"=="9" goto opt_providers
if /i "%CHOICE%"=="u" goto opt_ui
if /i "%CHOICE%"=="c" goto opt_config
if "%CHOICE%"=="0" goto opt_exit

echo.
echo [!] Invalid selection: %CHOICE%
timeout /t 2 >nul
goto menu

:opt_test
cls
echo [*] Running full test suite...
echo.
%RUNNER% pytest tests/ -v
echo.
pause
goto menu

:opt_lint
cls
echo [*] Running linter checks...
echo.
%RUNNER% ruff check src/ tests/ examples/
echo.
pause
goto menu

:opt_quickstart
cls
echo [*] Running Quickstart Demo...
echo.
%PY% examples/quickstart.py
echo.
pause
goto menu

:opt_it
cls
echo [*] Running IT System Outage Scenario...
echo.
%PY% examples/it_system_outage.py
echo.
pause
goto menu

:opt_supply
cls
echo [*] Running Supply Chain Disruption Scenario...
echo.
%PY% examples/supply_chain_disruption.py
echo.
pause
goto menu

:opt_workflow
cls
echo [*] Running Workflow Optimization Scenario...
echo.
%PY% examples/cross_dept_workflow_delay.py
echo.
pause
goto menu

:opt_all_scenarios
cls
echo [*] Running all 4 operational scenarios...
echo.
echo === 1/4: Quickstart ===
%PY% examples/quickstart.py
echo.
echo === 2/4: IT System Outage ===
%PY% examples/it_system_outage.py
echo.
echo === 3/4: Supply Chain Disruption ===
%PY% examples/supply_chain_disruption.py
echo.
echo === 4/4: Cross-Departmental Workflow Delay ===
%PY% examples/cross_dept_workflow_delay.py
echo.
echo [+] All scenarios completed!
echo.
pause
goto menu

:opt_cli_mock
cls
echo [*] Running OpsBrain CLI in offline mock mode...
echo.
%RUNNER% opsbrain run incident_response --mock
echo.
pause
goto menu

:opt_providers
cls
echo [*] Checking LLM providers...
echo.
%RUNNER% opsbrain providers list
echo.
pause
goto menu

:opt_ui
cls
echo [*] Launching OpsBrain Enterprise Organizational Graph UI...
echo [*] Opening default web browser at http://127.0.0.1:8080
echo.
%RUNNER% opsbrain ui --port 8080
echo.
pause
goto menu

:opt_config
cls
echo [*] Generating default config file...
echo.
%RUNNER% opsbrain config init -o configs/default.yaml
echo.
pause
goto menu

:opt_exit
echo Exiting OpsBrain launcher.
exit /b 0

REM ============================================================================
REM  Command-line arguments router
REM ============================================================================
:handle_args
set "CMD=%~1"
set "EXTRA_ARGS="
shift

:collect_args
if not "%~1"=="" (
    set "EXTRA_ARGS=!EXTRA_ARGS! %1"
    shift
    goto collect_args
)

if /i "%CMD%"=="test" (
    %RUNNER% pytest tests/ -v !EXTRA_ARGS!
    exit /b !errorlevel!
)

if /i "%CMD%"=="lint" (
    %RUNNER% ruff check src/ tests/ examples/ !EXTRA_ARGS!
    exit /b !errorlevel!
)

if /i "%CMD%"=="quickstart" (
    %PY% examples/quickstart.py !EXTRA_ARGS!
    exit /b !errorlevel!
)

if /i "%CMD%"=="demo" (
    %PY% examples/quickstart.py !EXTRA_ARGS!
    exit /b !errorlevel!
)

if /i "%CMD%"=="it" (
    %PY% examples/it_system_outage.py !EXTRA_ARGS!
    exit /b !errorlevel!
)

if /i "%CMD%"=="supply" (
    %PY% examples/supply_chain_disruption.py !EXTRA_ARGS!
    exit /b !errorlevel!
)

if /i "%CMD%"=="workflow" (
    %PY% examples/cross_dept_workflow_delay.py !EXTRA_ARGS!
    exit /b !errorlevel!
)

if /i "%CMD%"=="scenarios" (
    echo [*] Running Scenario 1/4: Quickstart...
    %PY% examples/quickstart.py
    echo.
    echo [*] Running Scenario 2/4: IT Outage...
    %PY% examples/it_system_outage.py
    echo.
    echo [*] Running Scenario 3/4: Supply Chain...
    %PY% examples/supply_chain_disruption.py
    echo.
    echo [*] Running Scenario 4/4: Workflow Delay...
    %PY% examples/cross_dept_workflow_delay.py
    exit /b 0
)

if /i "%CMD%"=="providers" (
    %RUNNER% opsbrain providers list !EXTRA_ARGS!
    exit /b !errorlevel!
)

if /i "%CMD%"=="ui" (
    %RUNNER% opsbrain ui !EXTRA_ARGS!
    exit /b !errorlevel!
)

if /i "%CMD%"=="help" (
    echo OpsBrain Windows Launcher
    echo.
    echo Usage:
    echo   run.bat                    Open interactive menu
    echo   run.bat test               Run pytest test suite
    echo   run.bat lint               Run ruff linting
    echo   run.bat demo               Run quickstart example
    echo   run.bat scenarios          Run all 4 operational scenarios
    echo   run.bat it                 Run IT outage scenario
    echo   run.bat supply             Run supply chain scenario
    echo   run.bat workflow           Run workflow optimization scenario
    echo   run.bat providers          List LLM providers
    echo   run.bat ui                 Launch web browser UI
    echo   run.bat ^<cli-command^>      Pass command directly to opsbrain CLI
    echo.
    echo Examples:
    echo   run.bat ui --port 8080
    echo   run.bat run incident_response --mock
    echo   run.bat analyze examples/incident.json --mock
    exit /b 0
)

REM Default: pass straight to opsbrain CLI
%RUNNER% opsbrain %CMD% !EXTRA_ARGS!
exit /b !errorlevel!
