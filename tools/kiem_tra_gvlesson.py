import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlit.testing.v1 import AppTest


def chay():
    at = AppTest.from_file("../app.py", default_timeout=120)
    at.run()
    assert not at.exception, at.exception
    at.radio[0].set_value("Giáo viên").run()
    nut = [b for b in at.button if "Bắt đầu học" in str(b.label)]
    assert nut, "khong thay nut GV"
    nut[0].click().run()
    assert not at.exception, at.exception
    at.session_state.tab_gv = "Tạo video"
    at.run()
    assert not at.exception, at.exception
    # Trang gọn: không tabs, không radio Đồ thị/Tiếp tuyến rườm rà
    assert not at.tabs, "van con tabs cu"
    cac_radio = " ".join(str(r.value) + " " + " ".join(str(o) for o in r.options) for r in at.radio)
    assert "Tiếp tuyến" not in cac_radio and "Đồ thị" not in cac_radio, f"van con muc cu: {cac_radio}"
    # Có: chọn Bài + ô mô tả + chất lượng + nút tạo video
    assert any("Bài" in str(s.label) for s in at.selectbox), "thieu selectbox Bai"
    assert any("Mô tả video" in str(t.label) for t in at.text_area), "thieu o mo ta"
    assert any("Chất lượng" in str(r.label) for r in at.radio), "thieu radio chat luong"
    nut_video = [b for b in at.button if "Tạo video" in str(b.label)]
    assert nut_video, "khong thay nut Tao video"
    print("THAT BAI: khong (trang Tao video gon)")


chay()
