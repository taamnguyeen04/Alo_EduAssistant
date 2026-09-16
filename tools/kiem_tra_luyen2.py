import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlit.testing.v1 import AppTest
from core import grading

grading.llm.chat = lambda msgs: "Bước 1 em làm đúng hướng nào?"
orig_cham = grading.cham_tung_buoc
goi = {"called": False}
orig_goi = grading.goi_y_buoc_dau


def gia_goi(sid, cau, mon="toan11"):
    goi["called"] = True
    return {"che_do": "goi_y", "goi_y": "Em thử nhớ $\\sin^2x+\\cos^2x$ bằng mấy nào?"}


grading.goi_y_buoc_dau = gia_goi

at = AppTest.from_file("../app.py", default_timeout=120)
at.run()
assert not at.exception, at.exception
at.text_input[0].set_value("test_hs_goiy2")
at.button[0].click().run()
at.session_state.tab_hs = "✏ Luyện tập"
at.run()
nut = [b for b in at.button if str(b.label) == "Câu mới"]
nut[0].click().run()
assert not at.exception, at.exception
# Đúng case trong ảnh: xin hướng dẫn, không nộp bài
at.chat_input[0].set_value("tôi không biết câu này hãy hướng dẫn tôi").run()
assert not at.exception, at.exception
texts = [m.value for m in at.markdown]
assert goi["called"], "khong vao che do goi y"
assert not any("Bước 1: sai" in t or "❌" in t for t in texts), "van cham sai oan"
assert any("Em thử nhớ" in t for t in texts), "thieu goi y Socrates"
print("THAT BAI: khong (xin goi y -> Socrates, khong cham sai)")

from core import store as _s
p = _s.duong_dan_hs("test_hs_goiy2")
if os.path.exists(p):
    os.remove(p)
