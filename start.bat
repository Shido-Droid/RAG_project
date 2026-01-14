@echo off

cd /d %~dp0

echo Starting Backend..
start "Backend API" cmd /k "call .venv\Scripts\activate.bat && uvicorn scripts.rag_server:app --reload --host 0.0.0.0 --port 8000"

echo Waiting for Backend to initialize...
timeout /t 3 /nobreak

echo Starting Frontend...
cd my-rag-app
npm run dev