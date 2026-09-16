"""Chấm chất lượng câu hỏi trong data/bank/*.json sau ingest PDF.

Vấn đề: PDF Toán gõ bằng Word Equation, khi trích text thì công thức vỡ
thành từng ký tự rời ("cos | +cos", "y | x | x", ký tự \uf0b0...).
Script này KHÔNG sửa công thức (sửa bừa còn nguy hiểm hơn), chỉ gắn cờ:
  chat_luong = "ok" | "can_duyet", kèm ly_do để GV lọc trong Kho đề.

Chạy:  python tools/loc_bank.py
"""
import glob
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANK_GLOB = os.path.join(BASE_DIR, "data", "bank", "*.json")
RE_PUA = re.compile(r"[\ue000-\uf8ff]")


def cham(cau):
    de = cau.get("de", "") or ""
    giai = cau.get("dap_an", "") or ""
    buoc = cau.get("buoc_giai", []) or []
    ly_do = []
    # 1. Ký tự font lạ còn sót (sau tools/mathfont.py): công thức chưa đọc được
    pua = len(RE_PUA.findall(de + giai))
    if pua >= 2:
        ly_do.append(f"ky_tu_la({pua})")
    # 3. Đề quá ngắn / không có lời giải -> không dùng được
    if len(de.strip()) < 30:
        ly_do.append("de_ngan")
    if not giai.strip() or not buoc:
        ly_do.append("thieu_loi_giai")
    # 4. Câu dạng bảng/hình (bảng số, đồ thị) text trích ra vô nghĩa
    if re.search(r"Hoàn thành bảng|Sử dụng đồ thị|hình (vẽ|dưới|trên|sau)", de, re.IGNORECASE):
        ly_do.append("can_hinh_bang_goc")
    # 5. Ngoặc nhọn dính chùm "{{" (phân số cao bị rã, thứ tự mất).
    # Ngoặc tập hợp legit ("{ }", "{π/2+kπ}") không dính nhau nên không sao.
    if re.search(r"\{\s*\{|\}\s*\}", de):
        ly_do.append("ngoac_vun")
    # 5b. Phân số suy biến do ghép nhầm (1/1, 3/3...): toán thật hiếm khi
    # viết \frac{a}{a}. Phát hiện dựng nhầm gạch phân số -> GV kiểm tra.
    full = de + " " + giai + " " + " ".join(buoc)
    for m in re.finditer(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", full):
        a, b = (re.sub(r"\s+", "", m.group(1)), re.sub(r"\s+", "", m.group(2)))
        if a and a == b:
            ly_do.append(f"phan_so_suy_bien({a}/{b})")
            break
    # 6. Trắc nghiệm hỏng phương án: 2+ ô A/B/C/D rỗng, hoặc 2 ô giống hệt nhau
    if cau.get("dang") == "TN":
        opts = re.findall(r"([A-D])\.\s*(.*?)(?=\s*[A-D]\.|$)", de)
        if len(opts) >= 2:
            norm = [re.sub(r"\s+", "", o[1]) for o in opts]
            if sum(1 for o in norm if not o) >= 2:
                ly_do.append("mat_phuong_an")
            elif len(set(norm)) < len(norm):
                ly_do.append("trung_phuong_an")
    if ly_do:
        return "can_duyet", ";".join(ly_do)
    return "ok", ""


def main():
    files = sorted(glob.glob(BANK_GLOB))
    t_ok = t_xau = 0
    for f in files:
        ds = json.load(open(f, encoding="utf-8"))
        ok = xau = 0
        for c in ds:
            if c.get("chat_luong") in ("ok", "can_duyet") and c.get("ly_do"):
                pass  # đã chấm rồi vẫn chấm lại cho chắc
            cl, ld = cham(c)
            c["chat_luong"] = cl
            c["ly_do"] = ld
            if cl == "ok":
                ok += 1
            else:
                xau += 1
        json.dump(ds, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        t_ok += ok
        t_xau += xau
        print(f"{os.path.basename(f)[:50]:50s} ok:{ok:3d} can_duyet:{xau:3d}")
    print(f"TONG: ok={t_ok} can_duyet={t_xau} / {t_ok + t_xau}")
    print("Cau can_duyet KHONG hien cho HS luyen (xem core/exercises.py). GV sua/xoa trong Kho de.")


if __name__ == "__main__":
    main()
