# RAG Webアプリ 利用手順書

## 1. はじめに
本ドキュメントは、チームメンバーが「RAG Webアプリ」を自身のPCで起動し、利用できるようにするための手順書です。
リポジトリの取得から、アプリケーションの起動、動作確認までの流れを記載しています。

## 2. 前提環境
以下のいずれかの環境をご用意ください。

*   **パターンA (推奨): Docker Desktop**
    *   環境構築が不要で、最も簡単に起動できます。
*   **パターンB: ローカル開発環境**
    *   Python 3.12 以上
    *   Node.js v20 以上
    *   Git

## 3. 導入手順

### Step 1: ソースコードの取得
任意の作業フォルダでターミナル（Windowsの場合はPowerShellやコマンドプロンプト）を開き、以下のコマンドを実行してプロジェクトをダウンロードします。

```bash
git clone https://github.com/Shido-Droid/RAG_project.git
cd RAG_project
```

※ 既にフォルダがある場合は、`cd RAG_project` の後に `git pull` を実行して最新の状態に更新してください。

### Step 2: アプリケーションの起動

環境に合わせて、以下のいずれかの方法で起動してください。

#### 【パターンA】 Dockerで起動する場合 (推奨)
プロジェクトのフォルダ内で以下のコマンドを実行します。

```bash
docker compose up --build
```

初回はイメージの作成に数分かかります。
ログが流れ、サーバーが待機状態になったら起動完了です。

#### 【パターンB】 ローカル環境で起動する場合
Dockerを使わない場合は、初回のみセットアップが必要です。

**1. バックエンド (Python) の準備**
```bash
# 仮想環境の作成 (Mac/Linux)
python3 -m venv .venv
source .venv/bin/activate

# 仮想環境の作成 (Windows)
python -m venv .venv
.venv\Scripts\activate

# ライブラリのインストール
pip install -r requirements.txt
```

**2. フロントエンド (React) の準備**
```bash
cd my-rag-app
npm install
cd ..
```

**3. 起動**
セットアップ完了後は、以下のスクリプトで一括起動します。

*   **Mac/Linux**: `./start.sh`
*   **Windows**: `start.bat`

---

## 4. アプリの利用
起動に成功したら、ブラウザで以下のURLにアクセスしてください。

*   **Webアプリ**: http://localhost:5173
*   **APIドキュメント**: http://localhost:8000/docs

## 5. 終了方法
ターミナルで `Ctrl + C` を押すとサーバーが停止します。

## 6. 困ったときは
*   **データの確認**: 登録されているドキュメント数を確認したい場合は、以下のコマンドを実行してください。
    *   Dockerの場合: `docker compose exec backend python scripts/check_chroma_db.py`
    *   ローカルの場合: `python scripts/check_chroma_db.py`
