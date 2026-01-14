import requests
import json
import time
from typing import List, Dict, Any, Optional
from .config import LMSTUDIO_URL, QWEN_MODEL, LM_TIMEOUT, LM_RETRIES
from .utils import log

def lmstudio_chat(
    messages: List[Dict],
    max_tokens: int = 256,
    temperature: float = 0.2,
    timeout: int = LM_TIMEOUT,
    retries: int = LM_RETRIES
) -> Dict:
    payload = {
        "model": QWEN_MODEL, 
        "messages": messages,
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
            time.sleep(0.3)  # Stable wait
            return r.json()
        except requests.exceptions.Timeout as e:
            last_exc = e
            if attempt < retries:
                log(f"[lmstudio_chat] Timeout retry {attempt+1}/{retries}")
                continue
            raise RuntimeError("LM timeout") from e
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"[lmstudio_chat] HTTP error: {e}") from e

    raise RuntimeError(f"[lmstudio_chat] failed: {last_exc}")
