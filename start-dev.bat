@echo off
chcp 65001 >nul
echo ====================================
echo  AI Knowledge Assistant - Dev Start
echo ====================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Please install Node.js 18+
    pause
    exit /b 1
)

echo [1/4] Checking Python dependencies...
pip show fastapi >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installing Python dependencies...
    pip install -r backend\requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install Python dependencies
        pause
        exit /b 1
    )
    echo [OK] Python dependencies installed
) else (
    echo [OK] Python dependencies already installed
)

echo.
echo [2/4] Checking Node.js dependencies...
if not exist "node_modules" (
    echo [INFO] Installing Node.js dependencies...
    call npm install
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install Node.js dependencies
        pause
        exit /b 1
    )
    echo [OK] Node.js dependencies installed
) else (
    echo [OK] Node.js dependencies already installed
)

echo.
echo [3/4] Checking frontend dependencies...
if not exist "frontend\node_modules" (
    echo [INFO] Installing frontend dependencies...
    cd frontend
    call npm install
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install frontend dependencies
        cd ..
        pause
        exit /b 1
    )
    echo [OK] Frontend dependencies installed
    cd ..
) else (
    echo [OK] Frontend dependencies already installed
)

echo.
echo [4/4] Starting development environment...
echo ====================================
echo.
echo Backend: http://127.0.0.1:8000
echo Frontend: http://localhost:5173
echo API Docs: http://127.0.0.1:8000/docs
echo.
echo Press Ctrl+C to stop all services
echo ====================================
echo.

start "Backend" cmd /k "cd /d %~dp0 && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"
timeout /t 3 /nobreak >nul
start "Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
timeout /t 3 /nobreak >nul
start "Electron App" cmd /k "cd /d %~dp0 && npm start"

echo.
echo [SUCCESS] Development environment started!
echo.
echo Note: Electron app will open automatically
echo.
pause
