import json
import re
import datetime
from .config import VERBOSE

def log(*args, **kwargs):
    if VERBOSE:
        print(*args, **kwargs)

def safe_json_load(s: str):
    try:
        return json.loads(s)
    except Exception:
        return None

def try_fast_path(question: str) -> str | None:
    # --- 正規化 ---
    q = question.strip()

    # 全角 → 半角
    trans = str.maketrans({
        "０":"0","１":"1","２":"2","３":"3","４":"4",
        "５":"5","６":"6","７":"7","８":"8","９":"9",
        "＋":"+","－":"-","＊":"*","×":"*","÷":"/",
        "（":"(","）":")"
    })
    q = q.translate(trans)

    # 日本語助詞・疑問符など除去
    q = re.sub(r"[=は？\?を]", "", q)
    q = q.replace(" ", "").replace("　", "")

    # --- 四則演算 ---
    if re.fullmatch(r"[0-9+\-*/().]+", q):
        try:
            return str(eval(q, {"__builtins__": {}}, {}))
        except Exception:
            return None

    # --- 現在時刻 ---
    if any(k in question for k in ["現在の時刻", "今何時", "今の時間", "今の時刻", "現在時刻", "何時です"]):
        now = datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=9))
        )
        return f"現在の日本時刻は {now.strftime('%H時%M分')} です。"

    # --- 超常識 ---
    COMMON = {
        "日本の首都": "日本の首都は東京です。",
        "1日は何時間": "1日は24時間です。",
        "1年は何日": "通常の年は365日、うるう年は366日です。",
    }
    for k, v in COMMON.items():
        if k in q:
            return v

    return None
