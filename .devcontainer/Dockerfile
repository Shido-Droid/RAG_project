# Microsoft公式のPython DevContainerイメージを使用
FROM mcr.microsoft.com/devcontainers/python:3.11

# uvのインストール
USER vscode
# curlコマンドでuvのインストーラースクリプトを実行
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
# uvの実行パスを環境変数に追加
ENV PATH="/home/vscode/.local/bin:${PATH}"

# 作業ディレクトリの設定
WORKDIR /home/vscode/python

# コンテナを起動したままにする（DevContainerの要件）
CMD ["sleep", "infinity"]