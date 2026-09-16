"""Test nhanh API OpenRouter. Key đọc từ .env (KHÔNG hardcode)."""
import os
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8")

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

KEY = os.getenv("OPENROUTER_API_KEY", "")
if not KEY:
    sys.exit("Thiếu OPENROUTER_API_KEY trong .env (xem .env.example nếu có).")

q = input("Ask: ")
r = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={"Authorization": f"Bearer {KEY}"},
    json={"model": os.getenv("OPENROUTER_MODEL", "dots-studio/dots-3-note-preview:free"),
          "messages": [{"role": "user", "content": q}]},
    timeout=60,
)
tra_loi = r.json()["choices"][0]["message"]["content"]
print("AI:", tra_loi)
