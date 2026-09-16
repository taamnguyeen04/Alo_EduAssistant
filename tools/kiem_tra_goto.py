import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlit.testing.v1 import AppTest


def chay():
    at = AppTest.from_file("../app.py", default_timeout=60)
    at.run()
    assert not at.exception, at.exception
    # Đăng nhập HS mới
    at.text_input[0].set_value("test_hs_goto")
    at.button[0].click().run()
    assert not at.exception, at.exception
    def ss(key, mac_dinh=None):
        try:
            return at.session_state[key]
        except KeyError:
            return mac_dinh

    assert ss("auth_role") == "hs", "chua login"
    # Sang tab Học theo Chương rồi bấm "Hỏi bài này" (luồng crash cũ)
    at.session_state.tab_hs = "📚 Bài học"
    at.run()
    assert not at.exception, at.exception
    nut_hoi = [b for b in at.button if "Hỏi bài này" in str(b.label)]
    assert nut_hoi, "khong thay nut Hoi bai nay"
    nut_hoi[0].click().run()
    assert not at.exception, at.exception
    assert ss("tab_hs") == "🤖 Hỏi AI", ss("tab_hs")
    # Sang Chat: dropdown + nút Mới + Xóa không crash
    at.session_state.tab_hs = "🤖 Hỏi AI"
    at.run()
    assert not at.exception, at.exception
    nut_moi = [b for b in at.button if "Trò chuyện mới" in str(b.label)]
    assert nut_moi, "khong thay nut Moi"
    nut_moi[0].click().run()
    assert not at.exception, at.exception
    print("THAT BAI: khong (login -> Hoi bai nay -> Chat -> Moi)")

    # Dọn hồ sơ test
    from core import store
    p = store.duong_dan_hs("test_hs_goto")
    if os.path.exists(p):
        os.remove(p)


chay()
