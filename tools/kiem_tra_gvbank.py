import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlit.testing.v1 import AppTest


def chay():
    at = AppTest.from_file("../app.py", default_timeout=120)
    at.run()
    assert not at.exception, at.exception
    # Đăng nhập GV: chọn radio Giáo viên rồi bấm vào
    at.radio[0].set_value("Giáo viên").run()
    nut = [b for b in at.button if "Bắt đầu học" in str(b.label)]
    assert nut, "khong thay nut GV"
    nut[0].click().run()
    assert not at.exception, at.exception
    # Sang tab Kho đề
    at.session_state.tab_gv = "Kho đề"
    at.run()
    assert not at.exception, at.exception
    # Đủ 7 Bài từ bank (kể cả Chương 9, trước đây thiếu). selectbox[0] là chọn Môn.
    bai_box = [s for s in at.selectbox if "31" in str(s.options) or "Bài" in str(s.options[0])]
    assert bai_box, "khong thay o chon Bai"
    opts = list(bai_box[0].options)
    assert len(opts) == 7, f"chi thay {len(opts)} bai: {opts}"
    assert any("31" in o for o in opts), "thieu Bai 31-33"
    # Lọc Mức độ phải có đủ Nhận biết / Thông hiểu / Vận dụng
    muc_box = [s for s in at.selectbox if "Vận dụng" in str(s.options)]
    assert muc_box, "khong thay o loc muc do"
    muc_box[0].set_value("Nhận biết").run()
    assert not at.exception, at.exception
    # Lọc Dạng câu hỏi phải có Trắc nghiệm / Đúng – Sai / Trả lời ngắn
    loai_box = [s for s in at.selectbox if "Trả lời ngắn" in str(s.options)]
    assert loai_box, "khong thay o loc dang cau hoi"
    loai_box[0].set_value("Trắc nghiệm").run()
    assert not at.exception, at.exception
    # Mở expander đầu tiên, bấm Sửa -> form hiện
    assert len(at.expander) > 0, "loc Trach nghiem + Nhan biet rong?"
    sua = [b for b in at.button if str(b.label).startswith("✏️")]
    assert sua, "khong thay nut Sua"
    sua[0].click().run()
    assert not at.exception, at.exception
    assert any("Lưu" in str(b.label) for b in at.button), "form sua khong hien"
    assert len(at.text_area) > 0, "thieu o nhap sua"
    n_xanh = sum(1 for s in at.success if "✅" in str(s.value))
    print(f"THAT BAI: khong ({len(opts)} bai | loc dang + muc do + sua OK | {n_xanh} dap-an xanh)")


chay()
