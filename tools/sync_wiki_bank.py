"""Đồng bộ đề mới từ data/wiki/questions (ingest DOCX 2026-09-17) vào data/bank.

Mỗi lần chạy:
1. Backup 4 file bank Bài 1-4 vào data/bank_backup_sync_<timestamp>/.
2. Xóa các câu đã sync trước đó (có trường wiki_id) để chạy lại không trùng.
3. Append câu mới từ wiki, giữ nguyên câu bank cũ (PDF trước đây).

Ánh xạ:
- lesson C1_B1..B4 -> tên Bài trùng bank hiện có (để Luyện tập/Hỏi AI chạy ngay).
- difficulty nhan_biet/thong_hieu/van_dung/van_dung_cao -> do_kho 1/2/3
  + muc_do "Nhận biết"/"Thông hiểu"/"Vận dụng" (van_dung_cao gộp vào Vận dụng).
- multiple_choice_single -> dang TN, de giữ format bank cũ
  (thân + A./B./C./D. từng dòng), dap_an "Chọn X" để Luyện tập phát được ngay.
- true_false -> dang TN + loai dung_sai (hiện ở Kho đề; Luyện tập A-D bỏ qua).
- short_answer -> dang TL + loai tra_loi_ngan.
- Hình công thức/minh họa giữ nguyên tham chiếu assets/... (bank_view.nhung_anh
  nhúng base64 lúc render, không copy file).
- chat_luong "ok" (nguồn DOCX chính thống của GV, có đáp án + lời giải).

Chạy:  python tools/sync_wiki_bank.py
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANK_DIR = os.path.join(ROOT, "data", "bank")
WIKI_DIR = os.path.join(ROOT, "data", "wiki")
Q_DIR = os.path.join(WIKI_DIR, "questions")

# lesson wiki -> tên Bài y hệt bank hiện có (đừng đổi: Luyện tập dò theo tên này)
BAI_MAP = {
    "C1_B1": "Bài 1. Giá trị lượng giác của góc lượng giác",
    "C1_B2": "Bài 2. Công thức lượng giác",
    "C1_B3": "Bài 3. Hàm số lượng giác",
    "C1_B4": "Bài 4. Phương trình lượng giác",
}

DO_KHO = {"nhan_biet": 1, "thong_hieu": 2, "van_dung": 3, "van_dung_cao": 3}
MUC_DO = {1: "Nhận biết", 2: "Thông hiểu", 3: "Vận dụng"}

_RE_CAU_SO = re.compile(r"^\*\*Câu\s*\d+\s*:\*\*\s*")
_RE_GACH_CHAN = re.compile(r"<u>(.*?)</u>")


def _sach(text):
    """Bỏ tiền tố '**Câu N:**' (trùng số sau khi gộp) + thẻ <u> đáp án."""
    t = _RE_CAU_SO.sub("", (text or "").strip())
    return _RE_GACH_CHAN.sub(r"\1", t)


def _giai_thanh_buoc(solution_md):
    """solution markdown -> list bước (bỏ dấu trích dẫn '>', dòng trống)."""
    buoc = []
    for dong in (solution_md or "").splitlines():
        d = re.sub(r"^\s*>\s?", "", dong).strip()
        d = _sach(d)
        if d:
            buoc.append(d)
    return buoc


def _ten_dang_phan(knowledge_ids, don_vi):
    if knowledge_ids and knowledge_ids[0] in don_vi:
        return don_vi[knowledge_ids[0]]
    return ""


def doi_cau(q, don_vi):
    """1 question wiki -> 1 record bank (giữ format bank cũ cho code hiện tại)."""
    lesson = q.get("lesson_id", "")
    label = (q.get("difficulty") or {}).get("label", "thong_hieu")
    dk = DO_KHO.get(label, 2)
    goc = {
        "id": q["id"],
        "bai": BAI_MAP[lesson],
        "do_kho": dk,
        "muc_do": MUC_DO[dk],
        "dang_phan": _ten_dang_phan(q.get("knowledge_ids", []), don_vi),
        "loi_hay_gap": [],
        "chat_luong": "ok",
        "ly_do": "",
        "nguon": "wiki (DOCX GV)",
        "wiki_id": q["id"],
        "assets": q.get("assets", []),
        "knowledge_ids": q.get("knowledge_ids", []),
    }
    qtype = q.get("question_type", "")

    if qtype == "multiple_choice_single":
        dung = str(q.get("correct_answer", "")).strip().upper()
        lua = "\n".join(f"{o['key']}. {o.get('content_md', '').strip()}"
                        for o in q.get("options", []))
        return {**goc,
                "dang": "TN", "loai": "trac_nghiem",
                "de": _sach(q.get("prompt_md") or q.get("stem_md", "")) + "\n" + lua,
                "dap_an": f"Chọn {dung}" if dung else "",
                "buoc_giai": _giai_thanh_buoc(q.get("solution_md", ""))}

    if qtype == "true_false":
        da = q.get("correct_answer", {}) or {}
        dap_an = "\n".join(f"{k.lower()}) {'Đúng' if da.get(k) else 'Sai'}"
                           for k in ["a", "b", "c", "d"] if k in {str(x).lower() for x in da})
        return {**goc,
                "dang": "TN", "loai": "dung_sai",
                "de": _sach(q.get("stem_md", "")),
                "dap_an": dap_an,
                "buoc_giai": _giai_thanh_buoc(q.get("solution_md", ""))}

    # short_answer và mọi loại còn lại -> tự luận
    da = q.get("correct_answer", "")
    return {**goc,
            "dang": "TL", "loai": "tra_loi_ngan",
            "de": _sach(q.get("stem_md", "")),
            "dap_an": da if isinstance(da, str) else json.dumps(da, ensure_ascii=False),
            "buoc_giai": _giai_thanh_buoc(q.get("solution_md", ""))}


def tai_don_vi():
    """id đơn vị kiến thức -> tên (làm dang_phan cho câu mới)."""
    don_vi = {}
    try:
        sy = json.load(io.open(os.path.join(WIKI_DIR, "syllabus.json"), encoding="utf-8"))
        for bai in sy.get("lessons", []):
            for dv in bai.get("knowledge_units", []):
                don_vi[dv["id"]] = dv.get("title", "")
    except Exception as e:
        print("  (không đọc được syllabus.json:", e, ")")
    return don_vi


def main():
    don_vi = tai_don_vi()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(ROOT, "data", f"bank_backup_sync_{ts}")
    os.makedirs(backup_dir, exist_ok=True)

    tong_moi, tong_thieu_hinh = 0, 0
    for lesson, bai in BAI_MAP.items():
        qf = os.path.join(Q_DIR, f"{lesson}.json".replace("C1_", "C1_"))
        d = json.load(io.open(qf, encoding="utf-8"))
        qs = d.get("questions", [])

        # Tìm file bank đúng theo tên Bài (qua teacher._bank_path cho chắc)
        sys.path.insert(0, ROOT)
        from core.teacher import _bank_path
        bf = _bank_path(bai)
        if not os.path.isfile(bf):  # dự phòng: dò theo id wiki cũ
            cands = glob.glob(os.path.join(BANK_DIR, "*.json"))
            bf = next((c for c in cands
                       if any(x.get("bai") == bai
                              for x in json.load(io.open(c, encoding="utf-8")))), None)
            if not bf:
                print(f"  !! Không tìm thấy file bank cho {bai}, bỏ qua.")
                continue
        shutil.copy2(bf, os.path.join(backup_dir, os.path.basename(bf)))

        kho = json.load(io.open(bf, encoding="utf-8"))
        cu = len(kho)
        kho = [c for c in kho if not c.get("wiki_id")]  # chạy lại không trùng
        moi = [doi_cau(q, don_vi) for q in qs]
        kho.extend(moi)

        # Kiểm tra hình có thật trên đĩa không
        thieu = sorted({a for c in moi for a in c["assets"]
                       if not os.path.isfile(os.path.join(WIKI_DIR, a.replace("/", os.sep)))})
        tong_thieu_hinh += len(thieu)

        json.dump(kho, io.open(bf, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        tong_moi += len(moi)
        print(f"  {bai}: {cu} -> {len(kho)} câu (+{len(moi)} wiki, thiếu {len(thieu)} hình)")

    print(f"XONG: +{tong_moi} câu wiki vào bank | backup: {backup_dir} "
          f"| hình thiếu: {tong_thieu_hinh}")

    # Ghi log append-only theo AGENTS.md
    try:
        with io.open(os.path.join(WIKI_DIR, "log.md"), "a", encoding="utf-8") as f:
            f.write(f"\n## [{datetime.now():%Y-%m-%d %H:%M}] sync | wiki/questions C1_B1-B4 "
                    f"-> bank (+{tong_moi} cau, muc do NB/TH/VD, hinh giu assets/)\n")
    except Exception as e:
        print("  (không ghi được log.md:", e, ")")


if __name__ == "__main__":
    main()
