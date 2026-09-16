import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlit.testing.v1 import AppTest
from core import grading

# Giả AI chấm (khỏi tốn token): trả đúng 1 JSON lẫn câu chữ như ảnh chụp
RAW_LAW = ('Gợi ý rung gian, tính riêng $\\sin(\\pi/6)$ đã." '
           '"diem_yeu_moi": ["thiếu bước trung gian"]')


def gia_cham(sid, cau, cac_buoc, mon="toan11"):
    from core.grading import tach_json_cham, lam_sach_goi_y, store
    raw = ('Chat trước.\n{"dung_sai_tung_buoc": [true, false], "sai_o_buoc": 2, '
           '"goi_y_sua": "xem lại bước 2", "diem_yeu_moi": []}\n' + RAW_LAW)
    _, data = tach_json_cham(raw)
    goi_y = data.get("goi_y_sua", "")
    if any(k in goi_y for k in ("dung_sai_tung_buoc", "diem_yeu_moi")):
        goi_y = lam_sach_goi_y(raw)
    kq = {"dung_sai_tung_buoc": [True, False], "sai_o_buoc": 2,
          "goi_y_sua": goi_y, "diem_yeu_moi": [], "dung_het": False}
    os.makedirs("data/attempts", exist_ok=True)
    store.ghi_json(f"data/attempts/{sid}_testchat.json", {"sid": sid, **kq})
    return kq, raw


grading.cham_tung_buoc = gia_cham

at = AppTest.from_file("../app.py", default_timeout=120)
at.run()
assert not at.exception, at.exception
at.text_input[0].set_value("test_hs_luyen")
at.button[0].click().run()
assert not at.exception, at.exception
at.session_state.tab_hs = "✏ Luyện tập"
at.run()
assert not at.exception, at.exception
nut = [b for b in at.button if str(b.label) == "Câu mới"]
assert nut, "khong thay nut Cau moi"
def md_texts():
    return [m.value for m in at.markdown]


nut[0].click().run()
assert not at.exception, at.exception
assert any("Câu " in t and "Độ khó" in t for t in md_texts()), "bot chua ra de"
at.chat_input[0].set_value("sin(pi/6)=1/2\ncos(pi/3)=1/2\ntổng=2").run()
assert not at.exception, at.exception
texts = md_texts()
assert any("Sai ở **bước 2**" in t for t in texts), texts[-2][:200]
assert not any("diem_yeu_moi" in t for t in texts), "JSON ro ra man hinh"
print("THAT BAI: khong (login -> Cau moi -> nhan bai -> cham hien chat, khong ro JSON)")

from core import store as _s
for f in ("test_hs_luyen",):
    p = _s.duong_dan_hs(f)
    if os.path.exists(p):
        os.remove(p)
a = "data/attempts/test_hs_luyen_testchat.json"
if os.path.exists(a):
    os.remove(a)
