import os
from langchain_community.llms import Ollama

def run_local_llm():
    """
    ローカルで動作するLLMを呼び出して、簡単な質問に答えさせる関数
    """
    print("ローカルLLM (phi3:mini) をロードしています...")
    try:
        # compose.ymlで設定した環境変数を読み込む
        ollama_host = os.getenv("OLLAMA_HOST")

        # 1. LLMを準備
        # base_urlにollamaコンテナの場所を指定する
        llm = Ollama(model="phi3:mini", base_url=ollama_host)
        print("✅ LLMのロード完了。")

        # 2. LLMに簡単な質問をします
        question = "自己紹介として、あなたの名前と役割を教えてください。"
        print(f'\n質問: "{question}"')
        print("LLMが回答を生成中です...")

        # .invoke() でLLMを呼び出します
        answer = llm.invoke(question)

        # 3. 回答を表示します
        print("\n--- 回答 ---")
        print(answer)
        print("------------")

    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        print("Ollamaコンテナがバックグラウンドで起動しているか確認してください。")

if __name__ == "__main__":
    run_local_llm()