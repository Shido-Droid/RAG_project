import requests
from test_search import simple_search


# === 設定 ===
QWEN_SERVER_URL = "http://10.23.130.252:1234/v1/chat/completions"  # ← LM Studio の Qwen の REST API URL
MODEL_NAME = "Qwen/Qwen1.5-7B-Chat"  # LM Studio の REST API が要求するモデル名


def build_prompt(question: str, docs: list[str]) -> str:
    """検索結果の文書をもとにプロンプト(コンテキスト)を作成"""
    context_text = "\n".join(f"- {d}" for d in docs)

    prompt = f"""
あなたは高度な日本語アシスタントです。
次のユーザー質問に対して、与えられたコンテキストを使って正確に答えてください。

### コンテキスト
{context_text}

### 質問
{question}

### 回答
"""
    return prompt


def query_qwen(prompt: str) -> str:
    """Qwen LM Studio REST API に問い合わせて回答を取得"""

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 200
    }

    try:
        response = requests.post(QWEN_SERVER_URL, json=payload, timeout=30)
        response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"]

    except Exception as e:
        return f"Qwen API 呼び出しエラー: {e}"


def main():
    question = "日本で一番高い山は？"

    # === Step1: 検索 ===
    docs = simple_search(question, n_results=2)
    print("検索結果:")
    for d in docs:
        print("-", d)

    # === Step2: Qwen へ問い合わせ ===
    prompt = build_prompt(question, docs)
    answer = query_qwen(prompt)

    print("\n=== Qwen の回答 ===")
    print(answer)


if __name__ == "__main__":
    main()
