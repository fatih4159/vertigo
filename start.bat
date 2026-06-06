@echo off
title AAOS - AGI Agent Operating System
color 0A

echo.
echo  ================================================
echo   AAOS - AGI Agent Operating System
echo  ================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python nicht gefunden. Bitte Python 3.11+ installieren.
    pause
    exit /b 1
)

:: Check Node
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js nicht gefunden. Bitte Node.js 18+ installieren.
    pause
    exit /b 1
)

:: Check Ollama
ollama --version >nul 2>&1
if errorlevel 1 (
    echo [WARN] Ollama nicht gefunden oder nicht im PATH.
    echo        Backend startet trotzdem, aber LLM-Funktionen benoetigen Ollama.
    echo.
)

:: Create .env if missing
if not exist ".env" (
    echo [INFO] .env nicht gefunden - kopiere .env.example ...
    copy ".env.example" ".env" >nul
    echo [INFO] .env erstellt. Bitte Werte pruefen.
    echo.
)

:: Create workspace dir
if not exist "workspace" mkdir workspace

:: Create logs dir
if not exist "logs" mkdir logs

:: Install Python deps if venv missing
if not exist "venv" (
    echo [INFO] Erstelle Python Virtual Environment ...
    python -m venv venv
    echo [INFO] Installiere Python-Abhaengigkeiten ...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt --quiet
    echo [OK] Python-Abhaengigkeiten installiert.
    echo.
) else (
    call venv\Scripts\activate.bat
)

:: Run Alembic migrations
echo [INFO] Fuehre Datenbankmigrationen aus ...
python -m alembic upgrade head >nul 2>&1
if errorlevel 1 (
    echo [WARN] Alembic migration fehlgeschlagen - DB wird beim Start neu erstellt.
) else (
    echo [OK] Datenbank aktuell.
)
echo.

:: Install Node deps if missing
if not exist "ui\node_modules" (
    echo [INFO] Installiere Frontend-Abhaengigkeiten (npm install) ...
    cd ui
    npm install --silent
    cd ..
    echo [OK] Frontend-Abhaengigkeiten installiert.
    echo.
)

:: Start Backend in new window
echo [INFO] Starte Backend  (http://localhost:8000) ...
start "AAOS Backend" cmd /k "call venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

:: Wait a moment for backend to initialize
timeout /t 3 /nobreak >nul

:: Start Frontend in new window
echo [INFO] Starte Frontend (http://localhost:5173) ...
start "AAOS Frontend" cmd /k "cd ui && npm run dev"

:: Wait for frontend to start
timeout /t 4 /nobreak >nul

:: Open browser
echo [INFO] Oeffne Browser ...
start http://localhost:5173

echo.
echo  ================================================
echo   AAOS laeuft!
echo.
echo   Frontend : http://localhost:5173
echo   Backend  : http://localhost:8000
echo   API Docs : http://localhost:8000/docs
echo.
echo   Zum Beenden: beide Consolenfenster schliessen
echo  ================================================
echo.
pause
