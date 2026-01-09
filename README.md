# AI Search Assistant (RAG Project)

## 環境構築と起動方法

このプロジェクトを新しい環境（自宅PCなど）でセットアップし、起動するための手順です。

### 1. インストール手順

#### 前提条件
*   Git
*   Python 3.12
*   Node.js (npm)

#### 手順

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

---

### 2. アプリの起動方法 (Windows/Mac/Linux共通)

アプリを使用する際は、2つのターミナルを開き、バックエンドとフロントエンドをそれぞれ起動します。

#### ターミナル1: バックエンド (APIサーバー)
```bash
# プロジェクトのルートディレクトリに移動
cd RAG_project

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