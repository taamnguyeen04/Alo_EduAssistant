import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import conversations, store, student

sid = "test_tmp_threads"
try:
    os.remove(store.duong_dan_hs(sid))
except OSError:
    pass

# Giả AI: trả đúng 1 JSON hợp lệ
student.llm.chat = lambda msgs: (
    "Gợi ý nè.\n```json\n{\"weaknesses\": [\"nhầm dấu\"], \"bai_de_xuat\": [], "
    "\"can_cu_bank_ids\": [], \"bai_hien_tai\": \"\", \"video_goi_y\": \"\", "
    "\"muc_do_hieu\": \"tot\"}\n```"
)

# 1. Tạo 2 cuộc đúng 2 Bài
a = conversations.tao_cuoc(sid, bai="Bài 1. Giá trị lượng giác của góc lượng giác")
b = conversations.tao_cuoc(sid, bai="Bài 32. cac quy tat tinh dao ham")
assert a != b, "id trùng"
print("PASS tao-2-cuoc")

# 2. Chat trong cuộc A: tin nhắn vào đúng cuộc + sổ tổng, Bài giữ nguyên
tra_loi, extra = student.hs_chat(sid, "sin bao nhiêu?", cid=a)
ca = conversations.lay_cuoc(sid, a)
cb = conversations.lay_cuoc(sid, b)
assert len(ca["messages"]) == 2, ca["messages"]
assert cb["messages"] == [], "lẫn sang cuộc B"
assert "nhầm dấu" in store.doc_hs(sid)["weaknesses"], "mất điểm yếu"
assert store.doc_hs(sid)["bai_hien_tai"].startswith("Bài 1"), "Bài bị đổi"
assert len(store.doc_hs(sid)["history"]) == 2, "sổ tổng thiếu"
assert ca["tieu_de"].startswith("B1:"), ca["tieu_de"]
print("PASS chat-dung-cuoc + giu-bai + so-tong")

# 3. Xóa cuộc B
conversations.xoa_cuoc(sid, b)
assert conversations.lay_cuoc(sid, b) is None
assert len(conversations.ds_cuoc(sid)) == 1
print("PASS xoa-cuoc")

# 4. Tương thích cũ: chat không cid vẫn chạy
student.hs_chat(sid, "câu hỏi chung")
assert len(store.doc_hs(sid)["history"]) == 4
print("PASS tuong-thich-cu")

os.remove(store.duong_dan_hs(sid))
print("THAT BAI: khong")
