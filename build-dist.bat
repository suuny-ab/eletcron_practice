@echo off
setlocal EnableExtensions EnableDelayedExpansion
pushd "%~dp0"

echo ====================================
echo  One-Click Build Script
echo ====================================
echo.

set GITIGNORE_TEMP=.gitignore.bak
set GITIGNORE_MODIFIED=0

REM Preflight checks
echo [0/5] Preflight checks...

if not exist ".gitignore" (
    echo [ERROR] .gitignore not found. Please run from project root.
    pause
    exit /b 1
)

where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found in PATH. Please install Node.js 18+.
    pause
    exit /b 1
)

where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] npm not found in PATH. Please reinstall Node.js.
    pause
    exit /b 1
)

set BUILD_PYTHON=
set BUILD_PYTHON_SOURCE=
if exist "backend\.venv\Scripts\python.exe" (
    set BUILD_PYTHON=backend\.venv\Scripts\python.exe
    set BUILD_PYTHON_SOURCE=backend\.venv
) else (
    where python >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] System Python not found in PATH. Please install Python 3.10+.
        pause
        exit /b 1
    )
    set BUILD_PYTHON=python
    set BUILD_PYTHON_SOURCE=system
)

for /f "tokens=2 delims= " %%v in ('"%BUILD_PYTHON%" -V 2^>^&1') do set PYVER=%%v
for /f "tokens=1,2 delims=." %%a in ("!PYVER!") do (
    set PYMAJOR=%%a
    set PYMINOR=%%b
)
if "!PYMAJOR!"=="" (
    echo [ERROR] Failed to detect Python version. Please ensure Python 3.10+ is installed.
    pause
    exit /b 1
)
if !PYMAJOR! LSS 3 (
    echo [ERROR] Python 3.10+ required. Current: !PYVER!
    pause
    exit /b 1
)
if !PYMAJOR! EQU 3 if !PYMINOR! LSS 10 (
    echo [ERROR] Python 3.10+ required. Current: !PYVER!
    pause
    exit /b 1
)

"%BUILD_PYTHON%" -m pip --version >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] pip is not available in the selected Python. Please reinstall Python with pip.
    pause
    exit /b 1
)

echo [OK] Using Python: %BUILD_PYTHON% (%BUILD_PYTHON_SOURCE%)

if not exist "backend\requirements.txt" (
    echo [ERROR] backend\requirements.txt not found.
    pause
    exit /b 1
)

if not exist "frontend\package.json" (
    echo [ERROR] frontend\package.json not found.
    pause
    exit /b 1
)

if not exist "python\python*.exe" (
    echo [ERROR] Python embeddable runtime not found!
    echo.
    echo Please run setup-python.bat first, or:
    echo 1. Download Python 3.12 embeddable from:
    echo    https://www.python.org/downloads/windows/
    echo 2. Extract to python/ folder
    echo.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('"python\python.exe" -V 2^>^&1') do set EMBED_PYVER=%%v
for /f "tokens=1,2 delims=." %%a in ("!EMBED_PYVER!") do (
    set EMBED_PYMAJOR=%%a
    set EMBED_PYMINOR=%%b
)

if "!EMBED_PYMAJOR!"=="" (
    echo [ERROR] Failed to detect embedded Python version. Please re-extract python/.
    pause
    exit /b 1
)

if "!PYMAJOR!" NEQ "!EMBED_PYMAJOR!" (
    echo [ERROR] Build Python version !PYVER! does not match embedded Python !EMBED_PYVER!.
    echo Please install a matching Python or replace python/ with the same version.
    pause
    exit /b 1
)
if "!PYMINOR!" NEQ "!EMBED_PYMINOR!" (
    echo [ERROR] Build Python version !PYVER! does not match embedded Python !EMBED_PYVER!.
    echo Please install a matching Python or replace python/ with the same version.
    pause
    exit /b 1
)

if not exist "node_modules\" (
    echo [INFO] Installing root dependencies...
    call npm install
    if %errorlevel% neq 0 goto fail
)

if not exist "frontend\node_modules\" (
    echo [INFO] Installing frontend dependencies...
    call npm --prefix frontend install
    if %errorlevel% neq 0 goto fail
)

echo [OK] Preflight checks passed.
echo.

REM Temporarily remove python/ from .gitignore
echo [1/5] Temporarily removing python/ from .gitignore...
copy .gitignore %GITIGNORE_TEMP% >nul
findstr /V "^python/$" .gitignore > .gitignore.tmp
move /Y .gitignore.tmp .gitignore >nul
set GITIGNORE_MODIFIED=1

echo [OK] .gitignore updated (backup saved to %GITIGNORE_TEMP%)
echo.

REM Build all
echo [2/5] Building Python dependencies...
call "%BUILD_PYTHON%" -m pip install -r backend/requirements.txt --target backend/.pydeps --upgrade
if %errorlevel% neq 0 goto fail

echo.
echo [3/5] Building frontend...
call npm run build:renderer
if %errorlevel% neq 0 goto fail

echo.
echo [4/5] Building Electron package...
call npm run dist
if %errorlevel% neq 0 goto fail

echo.
echo [5/5] Restoring .gitignore...
if "%GITIGNORE_MODIFIED%"=="1" (
    copy /Y %GITIGNORE_TEMP% .gitignore >nul
    del %GITIGNORE_TEMP%
)

echo [OK] .gitignore restored
echo.
echo ====================================
echo  [SUCCESS] Build Complete!
echo ====================================
echo.
echo Output: dist/
echo.
echo You can now distribute the installer from dist/ folder.
echo.
popd
pause
exit /b 0

:fail
echo [ERROR] Build failed.
if "%GITIGNORE_MODIFIED%"=="1" (
    echo [INFO] Restoring .gitignore...
    copy /Y %GITIGNORE_TEMP% .gitignore >nul
    del %GITIGNORE_TEMP% >nul 2>nul
)
popd
pause
exit /b 1
