import os
import random
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlit.testing.v1 import AppTest

random.seed(7)
SID = "test_hs_luyen"

at = AppTest.from_file("../app.py", default_timeout=120)
at.run()
assert not at.exception, at.exception
at.text_input[0].set_value(SID)
at.button[0].click().run()
assert not at.exception, at.exception
at.session_state.tab_hs = "✏ Luyện tập"
at.run()
assert not at.exception, at.exception

nut = [b for b in at.button if str(b.label) == "▶ Phát đề"]
assert nut, "khong thay nut Phat de"
nut[0].click().run()
assert not at.exception, at.exception


def md_texts():
    vals = [m.value for m in at.markdown]
    for kind in ("success", "error", "warning", "info"):
        try:
            vals += [m.value for m in getattr(at, kind)]
        except Exception:
            pass
    return vals


texts = md_texts()
assert any("Nhận biết" in t or "Thông hiểu" in t or "Vận dụng" in t for t in texts), "thieu muc do"
assert any("**A.**" in t for t in texts), "thieu phuong an A-D render markdown"

cau = at.session_state["tn_cau"]
dung = cau["dung"]
sai = "A" if dung != "A" else "B"

# 1. Trả lời sai -> báo sai + đáp án đúng + bước giải, không rò JSON
at.radio[0].set_value(sai).run()
[n for n in (b for b in at.button if str(b.label) == "Trả lời")][0].click().run()
assert not at.exception, at.exception
texts = md_texts()
assert any("Chưa đúng" in t and dung in t for t in texts), "thieu feedback sai + dap an"
assert len(at.expander) >= 1, "thieu expander buoc giai / lich su"
mau_buoc = (cau.get("buoc_giai") or [""])[0][:18].strip()
assert mau_buoc and any(mau_buoc in t for t in texts), "thieu noi dung buoc giai"
assert not any("diem_yeu_moi" in t or "dung_sai_tung_buoc" in t for t in texts), "JSON ro ra man hinh"

# 2. Câu tiếp theo -> câu mới (đúng trình độ, không lặp)
cu_id = cau["id"]
[n for n in (b for b in at.button if str(b.label) == "Câu tiếp theo →")][0].click().run()
assert not at.exception, at.exception
cau2 = at.session_state["tn_cau"]
assert cau2["id"] != cu_id, "lap cau lien tiep"

# 3. Trả lời đúng -> khen + attempt lưu
at.radio[0].set_value(cau2["dung"]).run()
[n for n in (b for b in at.button if str(b.label) == "Trả lời")][0].click().run()
assert not at.exception, at.exception
assert any("Đúng rồi" in t for t in md_texts()), "thieu feedback dung"

from core import store as _s
hs = _s.doc_hs(SID)
assert hs.get("trinh_do_bai"), "thieu trinh_do_bai per-Bai"
print("THAT BAI: khong (login -> Phat de TN -> sai/dung -> feedback + buoc giai, khong ro JSON)")

p = _s.duong_dan_hs(SID)
if os.path.exists(p):
    os.remove(p)
import glob as _g
_goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for f in _g.glob(os.path.join(_goc, "data", "attempts", f"{SID}_*.json")):
    os.remove(f)
