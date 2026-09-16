"""Seed dữ liệu demo KHKT: 3 HS mẫu (yếu/khá/giỏi) + lớp 11A1 + bài giao mẫu.

Chạy:  python tools/seed_demo.py
Idempotent: file/lớp/bài đã tồn tại thì bỏ qua, không ghi đè.
Kho đề dùng bank thật (Bài 1. Giá trị lượng giác... + Bài 31. Đạo hàm...).
"""
import os
import sys
from datetime import date, timedelta

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import lop, store, teacher

BAI_YEU = "Bài 1. Giá trị lượng giác của góc lượng giác"
BAI_GIOI = "Bài 31. dinh nghia va y nghia dao ham"


def seed_hs(sid, ten, trinh_do, bai, manh, phong_cach):
    if os.path.exists(store.duong_dan_hs(sid)):
        print(f"  giữ nguyên {sid} (đã có)")
        return
    hs = store.doc_hs(sid)
    hs.update({"ten": ten, "lop": "11A1", "trinh_do_toan": trinh_do,
               "bai_hien_tai": bai, "manh": manh, "phong_cach": phong_cach})
    store.luu_hs(sid, hs)
    print(f"  + {sid} ({ten}, {trinh_do}, {bai[:30]}...)")


def main():
    print("Seed HS mẫu:")
    seed_hs("hs_001", "An (yếu)", "yếu", BAI_YEU,
            ["chăm chỉ"], "thích ví dụ hình ảnh, từng bước nhỏ")
    seed_hs("hs_002", "Bình (khá)", "khá", BAI_YEU,
            ["tính nhẩm"], "thích đi thẳng vào công thức")
    seed_hs("hs_003", "Chi (giỏi)", "giỏi", BAI_GIOI,
            ["tư duy trừu tượng"], "thích bài thách đố")

    print("Seed lớp 11A1:")
    for sid in ("hs_001", "hs_002", "hs_003"):
        lop.them_hs_vao_lop("11A1", sid)
    print("  lớp 11A1:", lop.hoc_sinh_lop("11A1"))

    print("Seed bài giao mẫu:")
    han = (date.today() + timedelta(days=7)).isoformat()
    da_co = {(g.get("bai"), g.get("ghi_chu")) for g in lop.ds_giaobai()}
    if (BAI_YEU, "Bài demo KHKT") not in da_co:
        ma = lop.them_giaobai(BAI_YEU, 3, han, "Bài demo KHKT")
        print(f"  + {ma} (hạn {han})")
    else:
        print("  giữ nguyên bài giao mẫu (đã có)")

    print("Seed 1 câu AI-sinh chờ duyệt (để demo nút Duyệt):")
    kho = teacher.doc_bank(BAI_YEU)
    if not any(c.get("id") == "AI-DEMO-001" for c in kho):
        kho.append({"id": "AI-DEMO-001", "bai": BAI_YEU, "do_kho": 2,
                    "de": "Tính $\\sin\\frac{\\pi}{3} + \\cos\\frac{\\pi}{6}$.",
                    "dap_an": "$\\sqrt{3}$",
                    "buoc_giai": ["$\\sin\\frac{\\pi}{3}=\\frac{\\sqrt{3}}{2}$",
                                  "$\\cos\\frac{\\pi}{6}=\\frac{\\sqrt{3}}{2}$",
                                  "Tổng $=\\sqrt{3}$"],
                    "loi_hay_gap": ["nhầm giá trị đặc biệt"],
                    "chat_luong": "ok", "ly_do": "", "cho_duyet": True})
        teacher.luu_bank(BAI_YEU, kho)
        print("  + AI-DEMO-001")
    else:
        print("  giữ nguyên AI-DEMO-001 (đã có)")
    print("Xong.")


if __name__ == "__main__":
    main()
