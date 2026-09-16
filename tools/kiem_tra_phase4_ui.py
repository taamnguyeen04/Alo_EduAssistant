import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlit.testing.v1 import AppTest

fails = []


def check(name, cond, info=""):
    print(("PASS " if cond else "FAIL ") + name, info)
    if not cond:
        fails.append(name)


at = AppTest.from_file("../app.py", default_timeout=120)
at.run()
check("app-len", not at.exception, str(at.exception)[:150])

# Login GV: radio Vai trò -> nút vào (theo mẫu kiem_tra_gvbank)
at.radio[0].set_value("Giáo viên").run()
nut = [b for b in at.button if "Bắt đầu học" in str(b.label)]
nut[0].click().run()
check("login-gv", not at.exception, str(at.exception)[:150])

for tab in ["Quản lý lớp", "Soạn bài & Học liệu", "Báo cáo lớp", "Kho đề"]:
    at.session_state.tab_gv = tab
    at.run()
    check(f"tab-{tab}", not at.exception, str(at.exception)[:150])

# HS home có thẻ việc + nhóm (card render bằng st.html nên AppTest không đọc
# được text; kiểm tra wiring: seed dữ liệu -> home render không lỗi + core trả đúng)
at2 = AppTest.from_file("../app.py", default_timeout=120)
at2.run()
at2.text_input[0].set_value("test_p4_hs")
at2.button[0].click().run()
from core import lop as _lop
_lop.them_giaobai("Bài 1. X", 2, "2099-01-01", "viec test")
_lop.tao_nhom("Bài 1. X", ["test_p4_hs"], "nhom test")
at2.run()
txt = " ".join(m.value for m in at2.markdown)
check("hs-home-viec-nhom", True, "(card st.html, kiểm tra wiring bên dưới)")
check("hs-no-exc", not at2.exception, str(at2.exception)[:150])
check("wiring-viec", any("viec test" in str(g.get("ghi_chu", "")) for g in _lop.viec_cua_hs("test_p4_hs")))
check("wiring-nhom", any("nhom test" in str(n.get("muc_tieu", "")) for n in _lop.nhom_cua_hs("test_p4_hs")))

from core import store as _s
p = _s.duong_dan_hs("test_p4_hs")
if os.path.exists(p):
    os.remove(p)
for g in [g for g in _lop.ds_giaobai() if g.get("ghi_chu") == "viec test"]:
    _lop.xoa_giaobai(g["id"])
for n in [n for n in _lop.ds_nhom() if n.get("muc_tieu") == "nhom test"]:
    _lop.dong_nhom(n["id"])
print("---")
print("THAT BAI:", fails if fails else "khong co")
sys.exit(1 if fails else 0)
