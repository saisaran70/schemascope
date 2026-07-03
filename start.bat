@echo off
echo Starting SchemaScope...

:: Start backend
start "SchemaScope Backend" cmd /k "cd /d "%~dp0" && .venv\Scripts\uvicorn api.main:app --reload --port 8000"

:: Start frontend
start "SchemaScope Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

:: Wait 5 seconds then open browser
timeout /t 5 /nobreak >nul
start http://localhost:5173

echo Done! SchemaScope is opening in your browser.
