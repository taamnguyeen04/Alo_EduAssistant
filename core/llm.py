"""Gọi OpenRouter với 2 chế độ + routing theo tác vụ.

Chế độ (biến môi trường LLM_MODE):
- test (mặc định): giữ nguyên như cũ — model free trong OPENROUTER_MODEL/FALLBACKS.
  Mọi wrapper chat_pro/chat_flash đều đi đường này, code cũ và tool kiểm tra
  (mock llm.chat) chạy y hệt, không tốn tiền.
- prod (thi/demo/thật): PRO = GPT-5.6-Luna (HS hỏi đáp, gợi ý, chấm bài,
  sinh đề, audit Manim — chỗ cần trả lời hay + đúng tuyệt đối).
    FLASH = DeepSeek-V4.1-Flash (báo cáo GV, planner/coder/sửa
            code Manim, vision phụ — nhanh, rẻ, context dài).
  Mỗi task luôn có con còn lại + Luna-Pro làm fallback khi nghẽn 429/5xx.

Đổi mode (dễ nhất -> khó dần):
1. Hằng LLM_MODE ngay đầu app.py ("test" | "prod"), lưu file, chạy lại.
2. Env lúc chạy (được ưu tiên hơn app.py):
  PowerShell:  $env:LLM_MODE="prod"; streamlit run app.py
  CMD:         set LLM_MODE=prod && streamlit run app.py
  Bash:        LLM_MODE=prod streamlit run app.py
3. Mặc định (không đặt gì ở cả 2 chỗ) = test.
"""
import contextvars
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY", "")
URL = os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1/chat/completions")

# ── Mode test: giữ nguyên như hiện tại ──
MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-4-31b-it:free")
# Model dự phòng khi chính nghẽn/lỗi (429/5xx), cách nhau dấu phẩy
FALLBACKS = [m.strip() for m in os.getenv("OPENROUTER_FALLBACKS", "").split(",") if m.strip()]

# ── Mode prod: PRO = GPT hỏi đáp HS (KHÓA chỉ-GPT, không fallback DeepSeek),
# FLASH = DeepSeek việc ngầm ──
MODEL_FLASH = os.getenv("MODEL_FLASH", "deepseek/deepseek-v4.1-flash")
MODEL_PRO = os.getenv("MODEL_PRO", "openai/gpt-5.6-luna")
# Fallback khác họ (VD: qwen/qwen3.7-flash) phòng khi cả 2 DeepSeek cùng nghẽn
FALLBACKS_PROD = [m.strip() for m in os.getenv("FALLBACKS_PROD", "").split(",") if m.strip()]

# Task HS nhìn thấy / cần hay + đúng -> PRO; task ngầm/dài/hàng loạt -> FLASH
TASK_DUNG_PRO = {"chat", "goi_y", "cham", "ra_de", "audit", "pro"}

# Ưu tiên 1 = chính xác toán: nhiệt độ thấp để deterministic, ít bịa.
# PRO (hỏi đáp/chấm/sinh đề/audit): 0.1; FLASH (việc ngầm): 0.3; test: 0.2.
TEMP_PRO = float(os.getenv("TEMP_PRO", "0.1"))
TEMP_FLASH = float(os.getenv("TEMP_FLASH", "0.3"))
TEMP_TEST = float(os.getenv("TEMP_TEST", "0.2"))
# Đủ dài cho lời giải từng bước + JSON ẩn; ảnh/vision tốn token nên để dư.
MAX_TOKENS_PRO = int(os.getenv("MAX_TOKENS_PRO", "2500"))
MAX_TOKENS_FLASH = int(os.getenv("MAX_TOKENS_FLASH", "2000"))

# Task hiện tại (do wrapper chat_pro/chat_flash/chat_theo_task đặt).
# Dùng contextvar để tương thích mock llm.chat cũ trong tools/kiem_tra_*.
_TASK_HIEN_TAI = contextvars.ContextVar("llm_task", default=None)

# Model đã trả lời thành công gần nhất (để debug/log)
LAST_MODEL = MODEL


def che_do():
    """'prod' khi LLM_MODE=prod/production/real/thi/demo/live, còn lại 'test'."""
    m = (os.getenv("LLM_MODE", "test") or "test").strip().lower()
    return "prod" if m in ("prod", "production", "real", "thi", "demo", "live") else "test"


def _la_gpt(model):
    """True khi model thuộc họ GPT/OpenAI (dùng khóa HS chỉ-GPT)."""
    m = (model or "").strip().lower()
    return m.startswith("openai/") or m.startswith("gpt-")


def _chuoi_model(task=None):
    """Thứ tự model sẽ thử cho 1 task (phần tử đầu = chính)."""
    # Test: giữ đúng thứ tự model free cũ. Prod: PRO trước cho task cần đúng.
    task = task if task is not None else _TASK_HIEN_TAI.get()
    if che_do() != "prod":
        return [MODEL, *FALLBACKS]
    t = (task or "flash").strip().lower()
    if t in TASK_DUNG_PRO:
        # HS nhìn thấy (hỏi đáp, gợi ý, chấm, sinh đề, audit):
        # CHỈ họ GPT — không rớt sang DeepSeek/Qwen để khỏi lẫn chữ Hán.
        # PRO nghẽn thì thử tiếp fallback GPT, hết thì báo bận (không trả lời kém).
        chuoi = [MODEL_PRO, *[m for m in FALLBACKS_PROD if m not in (MODEL_PRO,)]]
        chuoi_gpt = [m for m in chuoi if _la_gpt(m)]
        return chuoi_gpt or [MODEL_PRO]
    base = [MODEL_FLASH, MODEL_PRO]
    return base + [m for m in FALLBACKS_PROD if m not in base]


def model_chinh(task=None):
    """Model chính của mode/task hiện tại (để hiện badge + debug, không gọi API)."""
    return _chuoi_model(task)[0]


def mo_ta_mode():
    """Chuỗi ngắn hiện ở sidebar để biết đang chạy mode nào."""
    if che_do() != "prod":
        return f"TEST (free): {MODEL}"
    return f"THI (prod): PRO={MODEL_PRO} / FLASH={MODEL_FLASH}"


def _lay_key():
    # Ưu tiên st.secrets khi chạy Streamlit Cloud, fallback .env local
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "OPENROUTER_API_KEY" in st.secrets:
            return st.secrets["OPENROUTER_API_KEY"]
    except Exception:
        pass
    return API_KEY


def _nhiet_do_mac_dinh(task=None):
    """Nhiệt độ mặc định theo task hiện tại (accuracy trước)."""
    task = (task if task is not None else _TASK_HIEN_TAI.get() or "").strip().lower()
    if che_do() != "prod":
        return TEMP_TEST
    if task in TASK_DUNG_PRO:
        return TEMP_PRO
    return TEMP_FLASH


def _max_tokens_mac_dinh(task=None):
    task = (task if task is not None else _TASK_HIEN_TAI.get() or "").strip().lower()
    if che_do() != "prod":
        return MAX_TOKENS_FLASH
    if task in TASK_DUNG_PRO:
        return MAX_TOKENS_PRO
    return MAX_TOKENS_FLASH


def _goi_model(model, messages, timeout, temperature=None, max_tokens=None):
    key = _lay_key()
    if not key:
        raise RuntimeError("Thiếu OPENROUTER_API_KEY (xem .env / secrets).")
    if temperature is None:
        temperature = _nhiet_do_mac_dinh()
    if max_tokens is None:
        max_tokens = _max_tokens_mac_dinh()
    payload = {"model": model, "messages": messages,
               "temperature": temperature, "max_tokens": max_tokens}
    try:
        r = requests.post(
            URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
            timeout=timeout,
        )
    except requests.RequestException as e:
        raise RuntimeError(f"Lỗi mạng khi gọi {model}: {e}")
    try:
        data = r.json()
    except Exception:
        raise RuntimeError(f"API trả về không phải JSON ({r.status_code}): {r.text[:300]}")
    if "choices" not in data:
        raise RuntimeError(f"API lỗi {r.status_code}: {str(data)[:500]}", r.status_code)
    msg = data["choices"][0].get("message", {}) or {}
    content = msg.get("content")
    # DeepSeek/reasoning model hay để content=null, dồn chữ vào reasoning_content
    if content is None:
        content = msg.get("reasoning_content") or msg.get("reasoning") or ""
    # Một số provider trả content dạng list các part
    if isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, str):
                parts.append(p)
            elif isinstance(p, dict):
                parts.append(p.get("text", "") or "")
        content = "".join(parts)
    if not isinstance(content, str):
        content = str(content) if content else ""
    if not content.strip():
        raise RuntimeError(
            "Model chưa trả kết quả (nội dung rỗng). Bạn bấm gửi lại giúp mình nhé."
        )
    return content


def _co_the_thu_lai(err):
    """Chỉ fallback với lỗi tạm thời (nghẽn 429, lỗi server 5xx, lỗi mạng)."""
    msg = str(err)
    code = err.args[1] if len(err.args) > 1 else None
    if code in (429, 500, 502, 503, 504):
        return True
    return "Lỗi mạng" in msg or "temporarily rate-limited" in msg or "Provider returned error" in msg


def chat(messages, timeout=60, temperature=None, max_tokens=None):
    global LAST_MODEL
    loi_cuoi = None
    # Thử lần lượt từng model; lỗi tạm thời (429/5xx/mạng) thì qua con tiếp theo.
    for model in _chuoi_model():
        try:
            out = _goi_model(model, messages, timeout,
                             temperature=temperature, max_tokens=max_tokens)
            LAST_MODEL = model
            return out
        except Exception as e:
            loi_cuoi = e
            if not _co_the_thu_lai(e):
                raise
            continue
    raise loi_cuoi


def _goi_theo_task(task, messages, timeout, temperature=None, max_tokens=None):
    """Đặt task rồi gọi chat() module-global (để mock llm.chat cũ vẫn chặn được).

    Giữ tương thích fake `lambda msgs: ...` trong tools/kiem_tra_*: thử gọi
    đủ kwargs trước, rớt TypeError thì fallback về 1 arg.
    """
    tok = _TASK_HIEN_TAI.set(task)
    try:
        kw = {}
        if timeout is not None:
            kw["timeout"] = timeout
        if temperature is not None:
            kw["temperature"] = temperature
        if max_tokens is not None:
            kw["max_tokens"] = max_tokens
        try:
            return chat(messages, **kw) if kw else chat(messages)
        except TypeError as e:
            if "unexpected keyword" in str(e) or "takes" in str(e):
                return chat(messages)
            raise
    finally:
        _TASK_HIEN_TAI.reset(tok)


def chat_pro(messages, timeout=None, temperature=None, max_tokens=None):
    """Task cần hay + đúng (hỏi đáp, gợi ý, chấm, sinh đề, audit). Prod -> PRO."""
    # HS nhìn thấy kết quả nên ưu tiên model mạnh nhất + nhiệt độ thấp (0.1).
    return _goi_theo_task("pro", messages, timeout, temperature, max_tokens)


def chat_flash(messages, timeout=None, temperature=None, max_tokens=None):
    """Task ngầm/nhanh/rẻ (báo cáo, planner/coder Manim, vision). Prod -> FLASH."""
    # Việc ngầm/dài dùng model rẻ để tiết kiệm chi phí.
    return _goi_theo_task("flash", messages, timeout, temperature, max_tokens)


def chat_theo_task(task, messages, timeout=None, temperature=None, max_tokens=None):
    """Routing tường minh theo tên task ('pro'/'chat'/'cham'/... -> PRO)."""
    return _goi_theo_task(task, messages, timeout, temperature, max_tokens)


def audit_dap_an(messages, timeout=90):
    """Vòng verify ưu tiên 1 (accuracy): chấm lại số học/công thức bằng PRO.

    Dùng cho câu khó/ảnh/ngoài bank ở student.hs_chat. Nhiệt độ 0.0 để
    deterministic tuyệt đối.
    """
    return _goi_theo_task("audit", messages, timeout, 0.0, MAX_TOKENS_PRO)
