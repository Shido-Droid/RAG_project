#!/bin/bash

# バックエンド (APIサーバー) をバックグラウンドで起動
source .venv/bin/activate
uvicorn scripts.rag_server:app --reload --port 8000 &
BACKEND_PID=$!

# フロントエンド (React) を起動
cd my-rag-app
npm run dev

# フロントエンド終了時にバックエンドも停止
kill $BACKEND_PID