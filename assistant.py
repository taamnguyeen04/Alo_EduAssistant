import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")
URL = os.getenv("OPENROUTER_URL")
MODEL = os.getenv("OPENROUTER_MODEL")
DATA_DIR = "data/students"

SYSTEM_HS = "Bạn là trợ lý học tập. Trả lời tiếng Việt. Cuối câu trả lời PHẢI có 1 khối JSON đúng dạng: ```json\n{\"weaknesses\": [\"điểm yếu 1\"]}\n```. Ghi các điểm yếu em phát hiện. Không có thì để mảng rỗng."
SYSTEM_GV = "Bạn là trợ lý cho giáo viên. Tổng hợp dữ liệu điểm yếu thành báo cáo: (1) điểm yếu phổ biến, (2) học sinh cần quan tâm, (3) gợi ý bài tập ôn lại."


def chat(messages):
    """Gọi LLM với danh sách messages, trả về nội dung assistant trả lời."""
    r = requests.post(URL, headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
                      json={"model": MODEL, "messages": messages})
    return r.json()["choices"][0]["message"]["content"]


def doc_hs(sid):
    """Đọc dữ liệu học sinh từ file. Chưa có thì trả về bản rỗng."""
    path = os.path.join(DATA_DIR, f"{sid}.json")
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    return {"history": [], "weaknesses": []}


def tach_diem_yeu(raw):
    """Tách phần JSON điểm yếu ở cuối câu trả lời, trả về (câu trả lời, danh sách điểm yếu)."""
    if "```json" not in raw:
        return raw, []
    tra_loi = raw[: raw.rfind("```json")].rstrip()
    json_str = raw.split("```json", 1)[1].split("```", 1)[0]
    return tra_loi, json.loads(json_str).get("weaknesses", [])


def hs_chat(sid, cau_hoi):
    """Học sinh hỏi → gọi LLM, lưu lịch sử + điểm yếu ra file JSON của học sinh."""
    data = doc_hs(sid)
    data["history"].append({"role": "user", "content": cau_hoi})
    tra_loi, diem_yeu = tach_diem_yeu(chat([{"role": "system", "content": SYSTEM_HS}] + data["history"]))
    data["history"].append({"role": "assistant", "content": tra_loi})

    da_co = {w.lower() for w in data["weaknesses"]}
    for w in diem_yeu:
        w = w.strip()
        if w and w.lower() not in da_co:
            data["weaknesses"].append(w)
            da_co.add(w.lower())

    os.makedirs(DATA_DIR, exist_ok=True)
    open(os.path.join(DATA_DIR, f"{sid}.json"), "w", encoding="utf-8").write(
        json.dumps(data, ensure_ascii=False, indent=2))
    return tra_loi, diem_yeu


def gv_bao_cao():
    """Đọc file của tất cả học sinh, gọi LLM viết báo cáo tổng hợp cho giáo viên."""
    os.makedirs(DATA_DIR, exist_ok=True)
    ds = []
    for ten_file in os.listdir(DATA_DIR):
        hs = json.load(open(os.path.join(DATA_DIR, ten_file), encoding="utf-8"))
        ds.append({"id": ten_file[:-5], "so_cau_hoi": len(hs["history"]) // 2, "diem_yeu": hs["weaknesses"]})

    if not ds:
        return "Chưa có dữ liệu học sinh."

    return chat([
        {"role": "system", "content": SYSTEM_GV},
        {"role": "user", "content": f"Dữ liệu điểm yếu các học sinh:\n```json\n{json.dumps(ds, ensure_ascii=False, indent=2)}\n```\nHãy viết báo cáo."},
    ])


if __name__ == "__main__":
    """Chạy CLI: 1 = học sinh chat, 2 = giáo viên xem báo cáo."""
    print("Chọn vai trò:  1) Học sinh   2) Giáo viên")
    chon = input("> ").strip()

    if chon == "1":
        sid = input("Mã học sinh: ").strip() or "hs_001"
        print("(gõ 'quit' để thoát)\n")
        while True:
            q = input("HS> ").strip()
            if q in ("quit", ""):
                break
            tra_loi, diem_yeu = hs_chat(sid, q)
            print(f"Bot> {tra_loi}\n")
            if diem_yeu:
                print(f"  [ghi nhận: {', '.join(diem_yeu)}]\n")

    elif chon == "2":
        print("\n" + gv_bao_cao())

    else:
        print("Chọn 1 hoặc 2.")


