"""Rà soát + sửa nhãn kho đề (chạy khi GV thấy nhãn sai nhiều).

Sửa (có backup toàn bank trước khi ghi):
1. Câu gắn TN nhưng đề là câu hỏi tự luận thật (không A-D, không a-d,
   đáp án ngắn, không phải "Chọn X") -> dang TL + loai tra_loi_ngan.
   (VD B1-01..03, AI-DEMO-001.)
2. Điền muc_do chữ + loai còn thiếu ở câu bank cũ (suy từ do_kho/dang).

KHÔNG đụng tới (để GV sửa tay, không được bịa):
- Câu mất phương án A-D khi trích PDF ([CẦN ĐỐI CHIẾU]/[CẦN HÌNH...],
  đề là mảnh đáp án): giữ nguyên + giữ chat_luong can_duyet.
- Câu TN đáp án là đoạn lời giải (không rõ "Chọn X"): giữ nguyên.
- Câu TL nhiều ý a) b) (VD B3-TL-002): đúng là tự luận, KHÔNG phải Đúng-Sai.

Chạy:  python tools/sua_nhan_bank.py
"""
import glob
import io
import json
import os
import re
import shutil
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import bank_view

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MUC_DO = {1: "Nhận biết", 2: "Thông hiểu", 3: "Vận dụng"}

# Đề mở đầu bằng các động từ này + đáp án ngắn gọn = câu tự luận bị gán nhầm TN
_RE_CAU_HOI = re.compile(
    r"^\s*(tính|tìm|chứng minh|cho|giải|đổi|rút gọn|viết|biểu diễn|dựa|"
    r"xét|tinh|tim|chung minh|giai|doi|rut gon|viet|bieu dien|dua|xet)",
    re.I)


def main():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(ROOT, "data", f"bank_backup_nhan_{ts}")
    os.makedirs(backup_dir, exist_ok=True)

    doi_tl, giu_nguyen = [], []
    dien_muc = 0
    for bf in sorted(glob.glob(os.path.join(ROOT, "data", "bank", "*.json"))):
        shutil.copy2(bf, os.path.join(backup_dir, os.path.basename(bf)))
        kho = json.load(io.open(bf, encoding="utf-8"))
        for c in kho:
            loai = bank_view.loai_cau(c)
            de, da = c.get("de", "") or "", c.get("dap_an", "") or ""
            _, pas = bank_view.tach_phuong_an(de)
            _, mds = bank_view.tach_menh_de(de)

            # 1. TN gắn nhầm -> TL (điều kiện chặt, tránh đụng câu mất đề)
            if (loai == "trac_nghiem" and len(pas) < 2 and len(mds) < 2
                    and not bank_view.dap_an_dung(da)
                    and "[CẦN" not in de and not da.strip().startswith("[C")
                    and len(da.strip()) <= 60
                    and _RE_CAU_HOI.search(bank_view.lam_dep(de))):
                c["dang"] = "TL"
                c["loai"] = "tra_loi_ngan"
                doi_tl.append(c["id"])
            elif loai == "trac_nghiem" and (len(pas) < 2 or not bank_view.dap_an_dung(da)):
                giu_nguyen.append(c["id"])  # mất đề/đáp án -> GV sửa tay

            # 2. Điền muc_do + loai còn thiếu (không đổi câu đã có)
            if not c.get("muc_do"):
                c["muc_do"] = MUC_DO.get(bank_view.muc_do_cau(c), "Thông hiểu")
                dien_muc += 1
            if not c.get("loai"):
                c["loai"] = "tra_loi_ngan" if c.get("dang") == "TL" else "trac_nghiem"

        json.dump(kho, io.open(bf, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"XONG | backup: {backup_dir}")
    print(f"  TN->TL ({len(doi_tl)}): {doi_tl}")
    print(f"  Điền muc_do thiếu: {dien_muc} câu")
    print(f"  Giữ nguyên chờ GV sửa tay ({len(giu_nguyen)}): {giu_nguyen}")

    with io.open(os.path.join(ROOT, "data", "wiki", "log.md"), "a", encoding="utf-8") as f:
        f.write(f"\n## [{datetime.now():%Y-%m-%d %H:%M}] sua-nhan | TN->TL {len(doi_tl)} cau, "
                f"dien muc_do {dien_muc} cau, giu {len(giu_nguyen)} cau mat de\n")


if __name__ == "__main__":
    main()
