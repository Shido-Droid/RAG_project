# Node.js (軽量版) を使用
FROM node:20-alpine

WORKDIR /app

# 依存関係のインストール
COPY package*.json ./
RUN npm install

# ソースコードのコピー
COPY . .

# 開発サーバー起動 (ホストからのアクセスを許可するために --host を付与)
CMD ["npm", "run", "dev", "--", "--host"]