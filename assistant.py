"""Wrapper giữ tương thích CLI cũ. Logic thật nằm ở core/. Chaỵ: python assistant.py"""
from core.student import hs_chat
from core.teacher import gv_bao_cao
from core.store import doc_hs
from core.prompts import SYSTEM_HS, SYSTEM_GV
from core.llm import chat

if __name__ == "__main__":
    """Chạy CLI: 1 = học sinh chat, 2 = giáo viên xem báo cáo."""
    print("Chọn vai trò:  1) Học sinh   2) Giáo viên")
    chon = input("> ").strip()

    if chon == "1":
        sid = input("Mã học sinh: ").strip() or "hs_001"
        print("(gõ 'quit' để thoát)\n")
        while True:
            q = input("HS> ").strip()
            if q in ("quit", ""):
                break
            tra_loi, extra = hs_chat(sid, q)
            print(f"Bot> {tra_loi}\n")
            if extra.get("diem_yeu"):
                print(f"  [ghi nhận: {', '.join(extra['diem_yeu'])}]\n")

    elif chon == "2":
        print("\n" + gv_bao_cao())

    else:
        print("Chọn 1 hoặc 2.")
