# Python 3.12 (軽量版) を使用
FROM python:3.12-slim

WORKDIR /app

# OCR (Tesseract) と PDF処理 (Poppler) のシステム依存関係をインストール
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# 依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ソースコードのコピー
COPY scripts ./scripts

# サーバー起動 (ホスト 0.0.0.0 で待機)
CMD ["uvicorn", "scripts.rag_server:app", "--host", "0.0.0.0", "--port", "8000"]