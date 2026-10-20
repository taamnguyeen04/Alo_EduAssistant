import os
import random
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlit.testing.v1 import AppTest
from core import grading

# Giả câu dẫn dắt (khỏi tốn token LLM)
grading.sinh_cau_dan_dat = lambda sid, cau, mon="toan11": (
    [{"de": "Câu dẫn dắt: bước đầu nên làm gì?",
      "phuong_an": ["Đổi đơn vị trước", "Đoán mò", "Bỏ qua", "Chép đáp án"],
      "dap_an": "A", "giai_thich": "Luôn chuẩn hóa đơn vị trước."}],
    ["chưa biết bắt đầu từ đâu"],
)

random.seed(11)
SID = "test_hs_goiy2"

at = AppTest.from_file("../app.py", default_timeout=120)
at.run()
assert not at.exception, at.exception
at.text_input[0].set_value(SID)
at.button[0].click().run()
at.session_state.tab_hs = "✏ Luyện tập"
at.run()
[n for n in (b for b in at.button if str(b.label) == "▶ Phát đề")][0].click().run()
assert not at.exception, at.exception

cau = at.session_state["tn_cau"]

def all_texts():
    vals = [m.value for m in at.markdown]
    for kind in ("success", "error", "warning", "info"):
        try:
            vals += [m.value for m in getattr(at, kind)]
        except Exception:
            pass
    return vals


# Chọn E "Em không biết" -> sang chế độ dẫn dắt, KHÔNG chấm sai oan
e_label = [o for o in at.radio[0].options if str(o).startswith("E")][0]
at.radio[0].set_value(e_label).run()
[n for n in (b for b in at.button if str(b.label) == "Trả lời")][0].click().run()
assert not at.exception, at.exception
assert at.session_state["tn_che_do"] == "dan_dat", "khong vao che do dan dat"
texts = all_texts()
assert any("dẫn dắt" in t for t in texts), "thieu cau dan dat"
assert not any("Chưa đúng" in t for t in texts), "cham sai oan khi chon E"

# Trả lời câu dẫn dắt đúng -> Tiếp tục -> được chọn lại câu gốc
[r for r in at.radio if r.label == "Đáp án"][0].set_value("A").run()
[n for n in (b for b in at.button if str(b.label) == "Trả lời câu dẫn dắt")][0].click().run()
assert not at.exception, at.exception
[n for n in (b for b in at.button if str(b.label) == "Tiếp tục →")][0].click().run()
assert not at.exception, at.exception
assert at.session_state["tn_che_do"] == "lam_lai", "khong sang buoc lam lai"

[r for r in at.radio if r.label == "Chọn lại đáp án"][0].set_value(cau["dung"]).run()
[n for n in (b for b in at.button if str(b.label) == "Chốt đáp án")][0].click().run()
assert not at.exception, at.exception
assert any("Đúng rồi" in t for t in all_texts()), "thieu feedback lam lai"

from core import store as _s
hs = _s.doc_hs(SID)
assert any("chưa biết bắt đầu từ đâu" in w for w in hs.get("weaknesses", [])), \
    f"diem yeu E khong luu DB: {hs.get('weaknesses')}"
print("THAT BAI: khong (E -> dan dat -> lam lai -> luu diem yeu DB)")

p = _s.duong_dan_hs(SID)
if os.path.exists(p):
    os.remove(p)
import glob as _g
_goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for f in _g.glob(os.path.join(_goc, "data", "attempts", f"{SID}_*.json")):
    os.remove(f)
