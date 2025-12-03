from sentence_transformers import SentenceTransformer
import chromadb
import uuid  # 一意な ID を作るために使用

# 埋め込みモデル
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

# Chroma クライアント
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection("rag_docs")

# 追加したい文書リスト
documents = [
    "富士山は日本で一番高い山です。",
    "今日は天気がいいですね。",
    "東京タワーは東京にある有名な観光地です。",
    "桜の花は春に咲きます。",
    "日本の人口は約1億2500万人です。"
]

# 文書をベクトル化
embeddings = embed_model.encode(documents)

# 一意の ID を作成
ids = [str(uuid.uuid4()) for _ in documents]

# Chroma に追加
collection.add(
    ids=ids,
    documents=documents,
    embeddings=[emb.tolist() for emb in embeddings]
)

print(f"{len(documents)} 件の文書を追加しました。")
