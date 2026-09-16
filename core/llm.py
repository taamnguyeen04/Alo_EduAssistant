"""Gọi OpenRouter với 2 chế độ + routing theo tác vụ.

Chế độ (biến môi trường LLM_MODE):
- test (mặc định): giữ nguyên như cũ — model free trong OPENROUTER_MODEL/FALLBACKS.
  Mọi wrapper chat_pro/chat_flash đều đi đường này, code cũ và tool kiểm tra
  (mock llm.chat) chạy y hệt, không tốn tiền.
- prod (thi/demo/thật): dùng 2 DeepSeek, tự chọn theo task:
    PRO   = MODEL_PRO   (deepseek-v4-pro-0813): HS hỏi đáp, gợi ý, chấm bài,
            sinh đề, audit Manim — chỗ cần trả lời hay + đúng tuyệt đối.
    FLASH = MODEL_FLASH (deepseek-v4.1-flash): báo cáo GV, planner/coder/sửa
            code Manim, vision (ảnh TKB/đề mẫu) — nhanh, rẻ, context dài.
  Mỗi task luôn có con còn lại làm fallback khi nghẽn 429/5xx.

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

# ── Mode prod: 2 DeepSeek đã bàn ──
MODEL_FLASH = os.getenv("MODEL_FLASH", "deepseek/deepseek-v4.1-flash")
MODEL_PRO = os.getenv("MODEL_PRO", "deepseek/deepseek-v4-pro-0813")
# Fallback khác họ (VD: qwen/qwen3.7-flash) phòng khi cả 2 DeepSeek cùng nghẽn
FALLBACKS_PROD = [m.strip() for m in os.getenv("FALLBACKS_PROD", "").split(",") if m.strip()]

# Task HS nhìn thấy / cần hay + đúng -> PRO; task ngầm/dài/hàng loạt -> FLASH
TASK_DUNG_PRO = {"chat", "goi_y", "cham", "ra_de", "audit", "pro"}

# Task hiện tại (do wrapper chat_pro/chat_flash/chat_theo_task đặt).
# Dùng contextvar để tương thích mock llm.chat cũ trong tools/kiem_tra_*.
_TASK_HIEN_TAI = contextvars.ContextVar("llm_task", default=None)

# Model đã trả lời thành công gần nhất (để debug/log)
LAST_MODEL = MODEL


def che_do():
    """'prod' khi LLM_MODE=prod/production/real/thi/demo/live, còn lại 'test'."""
    m = (os.getenv("LLM_MODE", "test") or "test").strip().lower()
    return "prod" if m in ("prod", "production", "real", "thi", "demo", "live") else "test"


def _chuoi_model(task=None):
    """Thứ tự model sẽ thử cho 1 task (phần tử đầu = chính)."""
    task = task if task is not None else _TASK_HIEN_TAI.get()
    if che_do() != "prod":
        return [MODEL, *FALLBACKS]
    t = (task or "flash").strip().lower()
    base = [MODEL_PRO, MODEL_FLASH] if t in TASK_DUNG_PRO else [MODEL_FLASH, MODEL_PRO]
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


def _goi_model(model, messages, timeout):
    key = _lay_key()
    if not key:
        raise RuntimeError("Thiếu OPENROUTER_API_KEY (xem .env / secrets).")
    try:
        r = requests.post(
            URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages},
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


def chat(messages, timeout=60):
    global LAST_MODEL
    loi_cuoi = None
    for model in _chuoi_model():
        try:
            out = _goi_model(model, messages, timeout)
            LAST_MODEL = model
            return out
        except Exception as e:
            loi_cuoi = e
            if not _co_the_thu_lai(e):
                raise
            continue
    raise loi_cuoi


def _goi_theo_task(task, messages, timeout):
    """Đặt task rồi gọi chat() module-global (để mock llm.chat cũ vẫn chặn được).

    timeout=None -> gọi chat(messages) đúng 1 arg, giữ tương thích các fake
    dạng `lambda msgs: ...` trong tools/kiem_tra_*.
    """
    tok = _TASK_HIEN_TAI.set(task)
    try:
        if timeout is None:
            return chat(messages)
        return chat(messages, timeout=timeout)
    finally:
        _TASK_HIEN_TAI.reset(tok)


def chat_pro(messages, timeout=None):
    """Task cần hay + đúng (hỏi đáp, gợi ý, chấm, sinh đề, audit). Prod -> PRO."""
    return _goi_theo_task("pro", messages, timeout)


def chat_flash(messages, timeout=None):
    """Task ngầm/nhanh/rẻ (báo cáo, planner/coder Manim, vision). Prod -> FLASH."""
    return _goi_theo_task("flash", messages, timeout)


def chat_theo_task(task, messages, timeout=None):
    """Routing tường minh theo tên task ('pro'/'chat'/'cham'/... -> PRO)."""
    return _goi_theo_task(task, messages, timeout)
