# AI Search Assistant (RAG Project)

##  Dockerで起動 (推奨・環境構築不要)

Dockerがインストールされていれば、以下のコマンドだけで起動できます。PythonやNode.jsのインストールは不要です。

```bash
docker compose up --build
```

起動後、ブラウザで [http://localhost:5173](http://localhost:5173) にアクセスしてください。

---

## 🚀 ローカル環境での起動方法 (Quick Start)

ローカル環境（Python/Node.jsインストール済み）で動かす場合は、以下のスクリプトを使用できます。

### Mac/Linux
```bash
# 初回のみ実行権限を付与
chmod +x start.sh

# アプリ起動
./start.sh
```

### Windows
```cmd
start.bat
```

起動後、ブラウザで [http://localhost:5173](http://localhost:5173) にアクセスしてください。

---

## 🛠️ 環境構築 (初回セットアップ)

このプロジェクトを新しい環境でセットアップするための手順です。

#### 前提条件
*   Git
*   Python 3.12
*   Node.js (npm)

#### インストール手順

1.  **リポジトリのクローン**
    任意のフォルダでターミナルを開き、Gitからプロジェクトをダウンロードします。
    ```bash
    git clone <あなたのリポジトリURL>
    cd RAG_project
    ```

2.  **バックエンド (Python) のセットアップ**
    ```bash
    # 仮想環境の作成
    # Mac/Linux (Ubuntu) の場合:
    python3 -m venv .venv
    # (※ Ubuntuでエラーが出る場合は `sudo apt install python3-venv` を実行してください)

    # Windowsの場合:
    python -m venv .venv

    # 仮想環境の有効化
    # Mac/Linux (Ubuntu) の場合:
    source .venv/bin/activate

    # Windowsの場合:
    # (PowerShell)
    # .\.venv\Scripts\Activate.ps1
    # (コマンドプロンプト)
    # .venv\Scripts\activate.bat

    # ※ PowerShellでエラーが出る場合は、下記の「3. Windowsでの注意点」を参照してください。
    # ライブラリのインストール
    pip install -r requirements.txt
    ```

3.  **フロントエンド (React) のセットアップ**
    ```bash
    cd my-rag-app
    npm install
    ```

## 📦 手動での起動方法 (スクリプトを使わない場合)

手動で起動する場合は、2つのターミナルを開いてそれぞれ実行してください。

### 1. バックエンド (APIサーバー)
```bash
# 上記の手順で仮想環境を有効化
# (例: source .venv/bin/activate)

uvicorn scripts.rag_server:app --reload --port 8000
```

#### ターミナル2: フロントエンド (画面)
```bash
cd RAG_project/my-rag-app
npm run dev
```

起動後、ターミナルに表示されるURL（例: `http://localhost:5173`）をブラウザで開くとアプリが使用できます。