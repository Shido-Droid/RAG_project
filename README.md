# RAG プロジェクト

これは、RAG (Retrieval-Augmented Generation) プロジェクトのための開発環境です。
VS CodeのDev Container機能利用を前提としており、誰でも一貫した・再現可能な開発環境を簡単に構築できます。

## ✨ この開発環境に含まれるもの

この開発環境には、以下のツールがプリセットされています。

- **Python 3.11**
- **uv**: 高速なPythonパッケージマネージャー
- **主要ライブラリ**:
  - FastAPI: APIの構築用
  - Pydantic: データバリデーション用
- **開発ツール**:
  - pytest: テスト実行用
  - black: コードフォーマッター
  - mypy: 静的型チェッカー
- **VS Code 連携**:
  - 推奨拡張機能（Python, Pylance, Black Formatter）の自動インストール
  - ファイル保存時の自動フォーマットや、テスト設定が構成済み

---

## 🚀 使い方

### 必要なもの

作業を始める前に、お使いのPCに以下のソフトウェアがインストールされていることを確認してください。

1.  [Git](https://git-scm.com/)
2.  [Docker Desktop](https://www.docker.com/products/docker-desktop/)
3.  [Visual Studio Code](https://code.visualstudio.com/)
4.  VS Code拡張機能 [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

### 環境構築の手順

1.  **リポジトリをクローンする:**
    ```bash
    git clone https://github.com/Shido-Droid/RAG_project.git
    ```

2.  **VS Codeでフォルダを開く:**
    ```bash
    cd RAG_project
    code .
    ```

3.  **コンテナで再度開く:**
    フォルダを開くと、VS Codeが `.devcontainer` の設定を検出し、画面右下に通知が表示されます。その通知内の **「Reopen in Container」** ボタンをクリックしてください。

4.  **完了！**
    VS Codeが自動的にDockerコンテナのビルドと開発環境のセットアップを開始します。初回は数分かかることがあります。完了すると、VS Codeがコンテナに接続された状態になり、開発を始めることができます。
    まとめ
    1. ターミナルで git clone https://github.com/Shido-Droid/RAG_project.git
    　を実行して、プロジェクトをダウンロードします。
   2. VS Codeで、ダウンロードした RAG_project フォル　　ダを開きます。
   3. VS Codeの右下に「Reopen in
      Container」という通知が表示されたら、そのボタンをクリックします。


---

## 🏃 アプリケーションの実行

このプロジェクトにはFastAPIが含まれています。開発サーバーを起動するには、以下の手順を実行します。

1.  VS Codeでターミナルを開きます（自動的にコンテナに接続されています）。
2.  次のコマンドを実行します（FastAPIのインスタンスが `main.py` にあると仮定）。

    ```bash
    uvicorn main:app --reload --host 0.0.0.0
    ```
3.  ブラウザで `http://localhost:8000` にアクセスすると、アプリケーションが表示されます。
