import os
import requests
from dotenv import load_dotenv

load_dotenv()

resp = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json",
    },
    json={
        "model": "minimax/minimax-m3:free",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": input("Ask: ")},
        ],
    },
)
resp.raise_for_status() # bắt lỗi nếu API trả về kết quả không ổn (lỗi mạng hoặc lỗi hết tiền)
print(resp.json()["choices"][0]["message"]["content"])