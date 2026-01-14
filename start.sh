#!/bin/bash

# バックエンド (APIサーバー) をバックグラウンドで起動
source .venv/bin/activate
uvicorn scripts.rag_server:app --reload --port 8000 &
BACKEND_PID=$!

# スクリプト終了時（Ctrl+Cなど）にバックエンドへSIGINTを送信して適切に停止する
cleanup() {
  kill -SIGINT $BACKEND_PID
}
trap cleanup EXIT

echo "Waiting for Backend to initialize..."
while ! (echo > /dev/tcp/localhost/8000) >/dev/null 2>&1; do
  sleep 1
done

# フロントエンド (React) を起動
cd my-rag-app
npm run dev