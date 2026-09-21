@echo off
setlocal
set "ROOT=%~dp0"

echo Starting Chamoli Flood Dashboard...

if not exist "%ROOT%node_modules" (
    echo Installing frontend dependencies...
    pushd "%ROOT%"
    call npm install
    if errorlevel 1 (
        echo Frontend dependency installation failed.
        pause
        exit /b 1
    )
    popd
)

start "Chamoli Frontend" cmd /k "cd /d ""%ROOT%"" && npm run dev"

if not exist "%ROOT%backend\.venv\Scripts\python.exe" (
    echo Creating backend Python environment...
    pushd "%ROOT%backend"
    python -m venv .venv
    if errorlevel 1 (
        echo Could not create the Python environment. Install Python 3.10+ first.
        popd
        pause
        exit /b 1
    )
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    if errorlevel 1 (
        echo Backend dependency installation failed.
        popd
        pause
        exit /b 1
    )
    popd
)

if not exist "%ROOT%backend\.env" (
    echo.
    echo WARNING: backend\.env is missing. The backend may not start until it is configured.
    echo Copy backend\.env.example to backend\.env and set DATABASE_URL.
)

start "Chamoli Backend" cmd /k "cd /d ""%ROOT%backend"" && call .venv\Scripts\activate.bat && uvicorn app.main:app --reload"

echo Frontend and backend launch windows have been opened.
endlocal
