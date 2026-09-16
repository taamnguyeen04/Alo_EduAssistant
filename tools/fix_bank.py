"""Giải mã font Toán cho toàn bộ data/bank/*.json + vá lỗi ingest cũ.

- Lần chạy 1 (bản map cũ) đã ghi nhầm \\uf0a1 thành ϒ -> hoàn lại để GV duyệt.
- Câu nào dap_an rỗng (đầu lời giải kiểu "Giải a)..." bản cũ cắt hụt)
  -> tách lại đề / lời giải bằng pattern mới.
- Áp dụng bảng mathfont mới nhất + gộp dòng.

Chạy:  python tools/fix_bank.py   rồi   python tools/loc_bank.py
"""
import glob
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from tools.mathfont import giai_ma, gon_dong, gop_buoc  # noqa: E402
from tools.ingest_pdf import RE_LOI_GIAI, RE_CAU, RE_CHON  # noqa: E402

import re  # noqa: E402
RE_PUA = re.compile(r"[\ue000-\uf8ff]")
# Chân trang PDF còn sót trong text đã gộp dòng ("...là: • CHƯƠNG 1. ... GIÁC A. ...")
RE_FOOTER = re.compile(
    r"\s*•\s*[^•]*?(CHƯƠNG|FanPage|Facebook|Blog|nbv)[^•]*", re.IGNORECASE
)
# Pattern tách lại trên text ĐÃ gộp dòng: "Giải a)" nội tuyến vẫn bắt được,
# nhưng "Giải phương trình..." trong đề thì không (lookahead loại trừ).
RE_GIAI_GOP = re.compile(
    r"L\s*ời\s*giải|Bài\s*giải\s*:?|(?<!\S)Giải(?!\s*(?:phương|hệ|bất|thích|quyết|tích))",
    re.IGNORECASE,
)


def tach_lai(de_gop, dang):
    """Tách lại de chứa lẫn lời giải (cho câu ingest cũ bị hụt)."""
    parts = RE_GIAI_GOP.split(de_gop, maxsplit=1)
    if len(parts) < 2:
        return None
    de = RE_CAU.sub("", parts[0], count=1).strip(" .-:\n")
    giai = parts[1].strip()
    if dang == "TN":
        m = RE_CHON.search(giai)
        dap_an = f"Chọn {m.group(1).upper()}" if m else giai[:100].strip()
    else:
        dap_an = giai[:200].strip()
    buoc = [ln.strip() for ln in giai.splitlines() if len(ln.strip()) > 2][:8]
    return gon_dong(de)[:1500], gon_dong(dap_an)[:500], buoc


def main():
    files = sorted(glob.glob(os.path.join(BASE_DIR, "data", "bank", "*.json")))
    t_tach = t_cau = 0
    for f in files:
        ds = json.load(open(f, encoding="utf-8"))
        for c in ds:
            # 0. Đảo ngược vết bản map cũ để decode lại cho đúng:
            #    "∈′" thật ra là "k ∈ ℤ" | "⋯" cạnh "AM" thật ra là ⌢ (cung tròn)
            for k in ("de", "dap_an"):
                c[k] = (c.get(k, "") or "").replace("∈′", "\uf0ce\uf0a2")
                c[k] = re.sub("⋯(?=[\\s\\S]{0,10}AM)", "⌢", c[k])
            # 1. Hoàn lại mã chưa rõ nghĩa bị map nhầm ở bản cũ
            for k in ("de", "dap_an"):
                c[k] = (c.get(k, "") or "").replace("ϒ", "\uf0a1")
            c["buoc_giai"] = [(b or "").replace("ϒ", "\uf0a1") for b in c.get("buoc_giai", []) or []]
            # 2. Tách lại câu hụt lời giải
            if not (c.get("dap_an", "") or "").strip():
                got = tach_lai(c.get("de", ""), c.get("dang", "TL"))
                if got and got[1].strip():
                    c["de"], c["dap_an"], c["buoc_giai"] = got[0], got[1], got[2]
                    t_tach += 1
            # 3. Giải mã + gộp dòng bản mới + cắt chân trang còn sót
            c["de"] = gon_dong(giai_ma(RE_FOOTER.sub(" ", c.get("de", ""))))
            c["dap_an"] = gon_dong(giai_ma(RE_FOOTER.sub(" ", c.get("dap_an", ""))))
            c["buoc_giai"] = [g for b in c.get("buoc_giai", []) or []
                              for g in [gon_dong(giai_ma(b))] if g]
            # 4. Gộp mảnh vỡ 1-2 từ thành bước đọc được (830/1057 câu bị nát)
            c["buoc_giai"] = gop_buoc(c.get("buoc_giai", []))
            c.pop("chat_luong", None)
            c.pop("ly_do", None)
            t_cau += 1
        json.dump(ds, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Xong {t_cau} cau, tach lai loi giai: {t_tach}.")
    print("Chay tiep: python tools/loc_bank.py")


if __name__ == "__main__":
    main()
