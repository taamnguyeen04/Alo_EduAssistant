"""Ingest PDF DA-TN / DA-TL -> data/bank/*.json (kho đề cho chatbot).

Logic đơn giản cho HS hiểu (không dùng VectorDB):
  raw PDF (bất biến) -> trích text 1 lần -> tách theo "Câu N." -> tách đề / lời giải
  -> lưu JSON chuẩn {id, bai, dang, do_kho, de, dap_an, buoc_giai} -> app đọc như cũ.

Quy ước file PDF của dự án:
  *-CH.pdf   = lý thuyết + câu hỏi (KHÔNG ingest, vì trùng).
  *-DA-TN.pdf = câu hỏi + đáp án trắc nghiệm (có "Chọn A/B/C/D").
  *-DA-TL.pdf = câu hỏi + lời giải tự luận.

Chạy:  python tools/ingest_pdf.py
        python tools/ingest_pdf.py --dry-run   (chỉ đếm, không ghi)
        python tools/ingest_pdf.py --rebuild   (phân tích lại hết, backup trước)
"""
import argparse
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core import teacher  # noqa: E402
from tools.mathfont import giai_ma, gon_dong, gop_buoc, trich_dung_thu_tu  # noqa: E402

def _doc_mupdf(pdf_path):
    import pymupdf
    d = pymupdf.open(pdf_path)
    out = []
    for pg in d:
        try:
            out.append(trich_dung_thu_tu(pg))
        except Exception:
            out.append(pg.get_text() or chr(34) + chr(34))
    return chr(10).join(out)

def _doc_pypdf(pdf_path):
    from pypdf import PdfReader
    r = PdfReader(pdf_path)
    return chr(10).join([(pg.extract_text() or chr(34)+chr(34)) for pg in r.pages])

# Dòng rác header/footer cần bỏ (quảng cáo nguồn PDF, số trang...)
RAC_PATTERNS = [
    r"Điện thoại", r"0946798489", r"facebook", r"Fanpage", r"FanPage",
    r"Nguyễn Bảo Vương", r"Nguy.*n Bảo", r"nbv\.edu\.vn", r"Blog:",
    r"TOÁN 11", r"KẾT NỐI TRI THỨC", r"CHƯƠNG \d", r"^Trang\s*\d+", r"^\d+\s*$",
]

RE_CAU = re.compile(r"Câu\s+(\d+)\s*\.", re.IGNORECASE)
# pypdf hay bẻ "Lời giải" thành "L\nời giải" -> regex chịu được khoảng trắng
# Đầu lời giải có 3 kiểu trong bộ PDF: "Lời giải", "Bài giải:", "Giải a)..."
# ("Giải phương trình..." trong đề thì KHÔNG tính -> lookahead loại trừ)
RE_LOI_GIAI = re.compile(
    r"L\s*ời\s*giải|Bài\s*giải\s*:?|\nGiải(?!\s*(?:phương|hệ|bất|thích|quyết|tích))",
    re.IGNORECASE,
)
RE_CHON = re.compile(r"Ch\s*ọn\s+([A-D])", re.IGNORECASE)
RE_DANG = re.compile(r"D\s*ạng\s*(\d+)", re.IGNORECASE)


def full_text(pdf_path):
    # PyMuPDF giữ dòng Câu/Lời giải nguyên vẹn hơn pypdf với PDF công thức.
    try:
        return _doc_mupdf(pdf_path)
    except Exception:
        return _doc_pypdf(pdf_path)


def lam_sach(text):
    # Text đã đúng thứ tự + phân số đã dựng ở trich_dung_thu_tu;
    # ở đây chỉ lọc rác (số trang lẻ, header/footer, quảng cáo).
    lines = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            continue
        if any(re.search(p, s, re.IGNORECASE) for p in RAC_PATTERNS):
            continue
        # Bỏ dòng "PHẦN B/C. BÀI TẬP..." và "BÀI 1. ... • CHƯƠNG 1..." lặp ở chân trang
        if re.match(r"^(PH\s*ẦN|BÀI T\s*ẬP|BÀI \d+\.|CHƯƠNG \d+\.)", s):
            # Giữ lại "Dạng N." vì cần làm tag, chỉ bỏ header phần
            if "Dạng" not in s and "DẠNG" not in s.upper():
                if len(s) < 60:
                    continue
        lines.append(s)
    return "\n".join(lines)


def tach_cau(text):
    """Cắt text thành list (so_cau, chunk). Câu cuối lấy tới hết file."""
    marks = list(RE_CAU.finditer(text))
    out = []
    for i, m in enumerate(marks):
        start = m.start()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out.append((int(m.group(1)), text[start:end].strip()))
    return out


def tach_de_dapan(chunk, dang):
    parts = RE_LOI_GIAI.split(chunk, maxsplit=1)
    de = parts[0].strip()
    giai = parts[1].strip() if len(parts) > 1 else ""
    # Bỏ tiền tố "Câu N." ở đầu đề
    de = RE_CAU.sub("", de, count=1).strip(" .-:\n")
    dap_an, buoc_giai = "", []
    if dang == "TN":
        m = RE_CHON.search(giai)
        dap_an = f"Chọn {m.group(1).upper()}" if m else (giai[:100].strip())
        buoc_giai = [ln.strip() for ln in giai.splitlines() if len(ln.strip()) > 2][:8]
    else:
        buoc_giai = [ln.strip() for ln in giai.splitlines() if len(ln.strip()) > 2][:8]
        dap_an = buoc_giai[0][:200] if buoc_giai else giai[:200]
    # Giải mã font Symbol (π α ° ≤ ∈...) + gộp dòng vỡ layout công thức
    de = gon_dong(giai_ma(de))
    dap_an = gon_dong(giai_ma(dap_an))
    buoc_giai = [gon_dong(giai_ma(b)) for b in buoc_giai if gon_dong(giai_ma(b))]
    buoc_giai = gop_buoc(buoc_giai)
    return de[:1500], dap_an[:500], buoc_giai


def bai_tu_filename(fname):
    """'Bài 1. ... -DA-TN.pdf' -> 'Bài 1. ...'; 'bai-31-... - DA - TL.pdf' -> 'Bài 31. ...'"""
    s = fname.replace(".pdf", "").strip()
    s = re.sub(r"\s*-\s*DA\s*-\s*T[NL]\s*$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*-\s*DA\s*T[NL]\s*$", "", s, flags=re.IGNORECASE)
    m = re.match(r"bai-(\d+)-(.+)", s, re.IGNORECASE)
    if m:
        ten = re.sub(r"[-_]+", " ", m.group(2)).strip()
        return f"Bài {m.group(1)}. {ten}"
    return s.strip()


def do_kho_theo_vi_tri(idx, tong, dang):
    """Heuristic đơn giản: đề xếp từ dễ -> khó, 1/3 đầu = 1, giữa = 2, cuối = 3.
    GV duyệt lại sau trong ui/gv_bank.py. HS dễ hiểu hơn mọi công thức khác."""
    ti_le = (idx + 1) / max(1, tong)
    if ti_le <= 0.33:
        return 1 if dang == "TN" else 2
    if ti_le <= 0.75:
        return 2
    return 3


def ingest_file(pdf_path, dry_run=False, rebuild=False):
    fname = os.path.basename(pdf_path)
    dang = "TN" if re.search(r"TN\.pdf$", fname, re.IGNORECASE) else "TL"
    bai = bai_tu_filename(fname)
    chuong = os.path.basename(os.path.dirname(pdf_path))
    # Thứ tự bắt buộc: giải mã font TRƯỚC (π hiện ra) -> ghép phân số dọc
    # -> lọc rác (lúc này xóa dòng số lẻ mới an toàn)
    text = lam_sach(giai_ma(full_text(pdf_path)))
    caus = tach_cau(text)
    # Tag Dạng N. gần nhất đứng trước mỗi câu (cho tự luận phân dạng)
    dang_marks = [(m.start(), m.group(0)) for m in RE_DANG.finditer(text)]

    kho_cu = teacher.doc_bank(bai)
    de_cu = {c.get("de", "")[:30] for c in kho_cu}
    loi_cu = {c.get("id"): c.get("loi_hay_gap", []) for c in kho_cu if c.get("loi_hay_gap")}
    moi = []
    prefix = re.match(r"(?:Bài|bai)[\s\-_]*(\d+)", bai, re.IGNORECASE)
    pfx = f"B{prefix.group(1)}" if prefix else "BK"

    for i, (so, chunk) in enumerate(caus):
        de, dap_an, buoc = tach_de_dapan(chunk, dang)
        if len(de) < 10:  # chunk rác
            continue
        if not rebuild and de[:30] in de_cu:
            continue
        tag_dang = ""
        pos = text.find(chunk[:30])
        for p, t in dang_marks:
            if p < pos:
                tag_dang = t
        cid = f"{pfx}-{dang}-{so:03d}"
        moi.append({
            "id": cid,
            "bai": bai,
            "chuong": chuong,
            "dang": dang,  # TN / TL
            "dang_phan": tag_dang,  # vd: "Dạng 2" (tự luận)
            "do_kho": do_kho_theo_vi_tri(i, len(caus), dang),
            "de": de,
            "dap_an": dap_an,
            "buoc_giai": buoc,
            "loi_hay_gap": loi_cu.get(cid, []),  # giữ công GV đã ghi tay
            "nguon_pdf": fname,
        })
    if moi and not dry_run:
        if rebuild:
            # Thay từng ID (giữ thứ tự cũ). TN và TL ghi chung 1 file bank
            # nên KHÔNG được ghi đè cả file ở đây.
            cu_map = {c.get("id"): c for c in kho_cu}
            for m in moi:
                cu_map[m["id"]] = m
            teacher.luu_bank(bai, list(cu_map.values()))
        else:
            teacher.luu_bank(bai, kho_cu + moi)
    return bai, len(caus), len(moi)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="chỉ đếm, không ghi JSON")
    ap.add_argument("--rebuild", action="store_true",
                    help="phân tích lại TẤT CẢ câu và thay theo ID (có backup data/bank trước)")
    ap.add_argument("--data", default=os.path.join(BASE_DIR, "data"),
                    help="thư mục data chứa PDF")
    args = ap.parse_args()

    pdfs = []
    for root, _, files in os.walk(args.data):
        for fn in sorted(files):
            if not fn.lower().endswith(".pdf"):
                continue
            # CHỈ ingest file đáp án (đã có cả đề + giải). Bỏ file CH (trùng câu hỏi).
            if "-CH" in fn.upper() or "CH.pdf" in fn:
                continue
            if "DA-TN" in fn.upper() or "DA-TL" in fn.upper() or "DA -" in fn.upper():
                pdfs.append(os.path.join(root, fn))
    if not pdfs:
        print("Không tìm thấy file *-DA-TN/TL.pdf nào.")
        return

    if args.rebuild and not args.dry_run:
        import shutil
        from datetime import datetime
        bank_dir = os.path.join(BASE_DIR, "data", "bank")
        backup = bank_dir + "_backup_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copytree(bank_dir, backup)
        print(f"Đã backup bank -> {backup}")

    print(f"Tìm thấy {len(pdfs)} file đáp án. {'(DRY-RUN)' if args.dry_run else ''}"
          f"{' (REBUILD)' if args.rebuild else ''}")
    tong_moi = 0
    for p in pdfs:
        try:
            bai, tong, moi = ingest_file(p, dry_run=args.dry_run, rebuild=args.rebuild)
            tong_moi += moi
            print(f"  {os.path.basename(p)[:55]:55s} | {bai[:40]:40s} | câu:{tong:3d} -> mới:{moi:3d}")
        except Exception as e:
            print(f"  LỖI {os.path.basename(p)}: {e}")
    print(f"Xong. Tổng câu mới: {tong_moi}. " +
          ("Chạy lại không --dry-run để ghi." if args.dry_run else "GV mở Kho đề duyệt lại do_kho."))


if __name__ == "__main__":
    main()
