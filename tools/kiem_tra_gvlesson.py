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
    at.session_state.tab_gv = "Soạn bài & Học liệu"
    at.run()
    assert not at.exception, at.exception
    # Đã xoá preset Đường tròn hard-code: radio chỉ còn Đồ thị + Tiếp tuyến
    cac_radio = " ".join(str(r.value) + " " + " ".join(str(o) for o in r.options) for r in at.radio)
    assert "Đường tròn" not in cac_radio, f"van con preset duong tron: {cac_radio}"
    assert any("Hàm" in str(s.label) for s in at.selectbox), "thieu selectbox Ham (nhanh Do thi)"
    # Chuyển sang Tiếp tuyến: phải có slider h cát tuyến
    radio_hinh = [r for r in at.radio if any("Tiếp tuyến" in str(o) for o in r.options)]
    assert radio_hinh, "thieu radio Hinh minh hoa"
    radio_hinh[0].set_value("Tiếp tuyến & đạo hàm (Chương 9)").run()
    assert not at.exception, at.exception
    assert at.slider, "thieu slider h (nhanh Tiep tuyen)"
    at.slider[0].set_value(0.5).run()
    assert not at.exception, at.exception
    nut_ai = [b for b in at.button if "AI dựng học liệu" in str(b.label)]
    assert nut_ai, "khong thay nut AI dung hoc lieu"
    assert any("Mô tả video" in str(t.label) for t in at.text_area), "thieu o mo ta"
    print("THAT BAI: khong (tab Soan bai truc quan render + muc AI, da xoá duong tron)")


chay()
