# Python 3.12 (軽量版) を使用
FROM python:3.12-slim

WORKDIR /app

# 依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ソースコードのコピー
COPY scripts ./scripts

# サーバー起動 (ホスト 0.0.0.0 で待機)
CMD ["uvicorn", "scripts.rag_server:app", "--host", "0.0.0.0", "--port", "8000"]