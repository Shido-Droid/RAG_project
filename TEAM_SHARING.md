# RAG Project チーム共有・セットアップ手順書

このドキュメントは、チームメンバーにプロジェクトを共有し、開発環境を構築するための手順をまとめたものです。

## 1. オーナー（共有元）向け手順

プロジェクトの最新状態をGitリポジトリに反映します。

### 1-1. 変更のコミットとプッシュ
まだGitに反映していない変更がある場合は、以下のコマンドでプッシュします。

```bash
cd /home/shido/RAG_project
git add .
git commit -m "Update project for team sharing"
git push origin main
```

### 1-2. リポジトリの共有
Gitホスティングサービス（GitHub, GitLabなど）の設定画面から、チームメンバーを招待（Invite）してください。

---

## 2. チームメンバー（共有先）向け手順

メンバーは以下の手順で環境を構築してください。

### 2-1. ソースコードの取得 (Clone)
任意の作業フォルダでターミナルを開き、リポジトリをクローンします。

```bash
git clone <リポジトリのURL>
cd RAG_project
```

### 2-2. 開発環境のセットアップ

#### バックエンド (Python)
Python 3.12以上が必要です。

1. **仮想環境の作成**:
   ```bash
   # Mac/Linux
   python3 -m venv .venv
   
   # Windows
   python -m venv .venv
   ```

2. **仮想環境の有効化**:
   ```bash
   # Mac/Linux
   source .venv/bin/activate
   
   # Windows (PowerShell)
   .\.venv\Scripts\Activate.ps1
   ```

3. **ライブラリのインストール**:
   ```bash
   pip install -r requirements.txt
   ```

#### フロントエンド (Node.js)
Node.js v20以上が必要です。

```bash
cd my-rag-app
npm install
cd ..
```

### 2-3. 環境変数の設定 (必要な場合)
本プロジェクトは、デフォルトで社内ネットワーク上のLLMサーバー (`10.23.130.252`) を使用するように設定されています (`src/rag_app/config.py`)。
もし接続先やモデルを変更したい場合は、環境変数を設定してください。

例 (Linux/Mac):
```bash
export LMSTUDIO_URL="http://your-server-ip:1234/v1/chat/completions"
```

### 2-4. 起動確認
セットアップ完了後、以下のスクリプトで起動を確認してください。

- **Mac/Linux**: `./start.sh`
- **Windows**: `start.bat`

ブラウザで `http://localhost:5173` にアクセスできれば成功です。
