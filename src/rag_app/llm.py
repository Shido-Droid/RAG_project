import requests
import json
import time
from typing import List, Dict, Any, Optional
from .config import LMSTUDIO_URL, QWEN_MODEL, LM_TIMEOUT, LM_RETRIES
from .utils import log

def generate_system_prompt(difficulty: str = "normal") -> str:
    """
    Generate system prompt based on difficulty level.
    """
    base = "You are a helpful AI assistant."
    
    if difficulty == "easy":
        base += " 初心者にもわかりやすく、専門用語を避けて丁寧に解説してください。"
    elif difficulty == "professional":
        base += " 専門家向けに、詳細かつ技術的な内容を含めて回答してください。"
    else: # normal
        base += " 簡潔かつ正確に、バランスの取れた回答を心がけてください。"
        
    return base

def lmstudio_chat(
    arg1: Any = None,
    arg2: Any = None,
    model: str = QWEN_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    timeout: int = LM_TIMEOUT,
    retries: int = LM_RETRIES,
    messages: List[Dict] = None
) -> str:
    """
    Simpler interface for chat completion.
    Compatible with:
      - lmstudio_chat(system_prompt, user_prompt, ...)
      - lmstudio_chat(messages=[...], ...)
      - lmstudio_chat([{"role":...}, ...], ...)
    """
    
    final_messages = []

    # Case 1: messages argument provided
    if messages is not None:
        final_messages = messages
    # Case 2: arg1 is a list (positional list input)
    elif isinstance(arg1, list):
        final_messages = arg1
    # Case 3: old style (system, user)
    elif isinstance(arg1, str) and isinstance(arg2, str):
        final_messages = [
            {"role": "system", "content": arg1},
            {"role": "user", "content": arg2}
        ]
    else:
        raise ValueError("[lmstudio_chat] Invalid arguments provided. Need (system, user) or messages list.")

    
    payload = {
        "model": model, 
        "messages": final_messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False
    }
    headers = {"Content-Type": "application/json"}

    last_exc = None
    for attempt in range(retries + 1):
        try:
            r = requests.post(
                LMSTUDIO_URL,
                headers=headers,
                data=json.dumps(payload),
                timeout=timeout
            )
            r.raise_for_status()
            # Handle empty/invalid JSON response
            try:
                resp_json = r.json()
            except json.JSONDecodeError:
                # If connection worked but response body is empty/bad
                raise ValueError(f"Invalid JSON response: {r.text[:100]}")

            if "choices" not in resp_json or not resp_json["choices"]:
                 raise ValueError(f"Unexpected response format: {resp_json}")

            return resp_json["choices"][0]["message"]["content"]
        except Exception as e:
            last_exc = e
            if attempt < retries:
                log(f"[lmstudio_chat] Retry {attempt+1}/{retries} due to {e}")
                time.sleep(0.3)
                continue
    
    # If all retries failed
    raise RuntimeError(f"[lmstudio_chat] Network/API error after {retries} retries: {last_exc}")
