import os
import sys
import json
import asyncio
from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# scripts フォルダをパスに追加してインポートできるようにする
sys.path.append(os.path.join(os.path.dirname(__file__), "scripts"))
from rag_qwen_ultimate import process_question

app = FastAPI()

# React/Vue等の外部フロントエンドからのアクセスを許可する設定 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では具体的なURLを指定します (例: ["http://localhost:3000"])
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# テンプレートエンジンの設定 (HTMLを返すため)
templates = Jinja2Templates(directory="templates")

# APIリクエストのボディ定義
class Query(BaseModel):
    question: str

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/ask")
async def ask_api(query: Query):

    async def generate():
        yield json.dumps({"type": "status", "content": "ドキュメントを検索中..."}) + "\n"
        
        # RAGパイプラインをスレッドプールで実行（メインループをブロックしないため）
        result = await run_in_threadpool(process_question, query.question)
        
        yield json.dumps({"type": "status", "content": "回答を生成中..."}) + "\n"
        
        answer = result.get("answer", "")
        sources = result.get("sources", [])

        # 回答を少しずつ送信（擬似ストリーミング）
        chunk_size = 5
        for i in range(0, len(answer), chunk_size):
            chunk = answer[i:i+chunk_size]
            yield json.dumps({"type": "answer", "content": chunk}) + "\n"
            await asyncio.sleep(0.02) # ストリーミング感を出すためのウェイト

        # 最後にソース情報を送信
        yield json.dumps({"type": "sources", "content": sources}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)