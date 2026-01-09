@echo off
echo Starting Backend...
start "Backend API" cmd /k "call .venv\Scripts\activate.bat && uvicorn scripts.rag_server:app --reload --port 8000"

echo Starting Frontend...
cd my-rag-app
npm run dev