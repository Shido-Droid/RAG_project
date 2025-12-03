from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.utils import embedding_functions

# Embedding モデル
embed_model = SentenceTransformer("all-MiniLM-L6-v2")
ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

# Chroma DB
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection("rag_docs", embedding_function=ef)

# 複数文書を追加
docs = [
    "富士山は日本で一番高い山です。",
    "今日は天気がいいですね。",
    "明日は雨が降る予定です。",
    "東京タワーは東京にある有名な観光地です。",
    "桜の花は春に咲きます。",
    "京都にはたくさんの寺があります。",
    "日本の人口は約1億2500万人です。",
    "北海道は冬に雪が多い地域です。",
    "新幹線は日本の高速鉄道です。",
    "富士山の標高は3776メートルです。"
]

ids = [f"doc{i}" for i in range(len(docs))]
embeddings = embed_model.encode(docs).tolist()

collection.add(
    ids=ids,
    documents=docs,
    embeddings=embeddings
)

print(f"{len(docs)} 件の文書を Chroma DB に追加しました。")
