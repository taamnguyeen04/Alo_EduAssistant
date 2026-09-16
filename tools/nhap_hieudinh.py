"""Nhập bản hiệu đính cột đề từ data/wiki/sources new/*.md vào data/bank/*.json.

Bối cảnh: GV đã sửa tay công thức LaTeX trong 7 file MD (thư mục "sources new").
Chatbot chỉ đọc bank JSON nên phải đưa text đã sửa NGƯỢC vào bank (migrate 1 lần).

- Đọc bảng "Danh sách câu hỏi" trong mỗi file MD: | id | dạng | khó | chuẩn | đề |
- `de` mới = text cột đề, `<br>` -> `\\n` (JSON giữ text sạch, UI tự xuống dòng).
- chat_luong theo cột chuẩn: ✅ -> ok | 🛠️ -> ok (GV đã biên tập) | 🟡 -> can_duyet.
- Backup toàn bộ data/bank trước khi ghi.

Chạy:  python tools/nhap_hieudinh.py --dry-run   (chỉ báo cáo)
        python tools/nhap_hieudinh.py --apply     (backup + ghi thật)
"""
import glob
import json
import os
import re
import shutil
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SRC_DIR = os.path.join("data", "wiki", "sources new")
BANK_DIR = os.path.join("data", "bank")

STATUS_OK = {"✅", "🛠️"}


def doc_bang_hieudinh(path):
    """-> (frontmatter dict, [(id, status, de_moi), ...])."""
    txt = open(path, encoding="utf-8").read()
    fm = {}
    m = re.match(r"---\n(.*?)\n---\n", txt, re.S)
    if m:
        for ln in m.group(1).splitlines():
            if ":" in ln:
                k, v = ln.split(":", 1)
                fm[k.strip()] = v.strip().strip('"')
    rows = []
    for ln in txt.splitlines():
        if not ln.startswith("| B"):
            continue
        cells = [c.strip() for c in ln.split("|")]
        if len(cells) < 7:  # ['', id, dang, kho, chuan, de..., '']
            print(f"  CẢNH BÁO dòng lạ, bỏ qua: {ln[:80]}")
            continue
        cid, status = cells[1], cells[4]
        de_moi = "|".join(cells[5:-1]).replace("<br>", "\n").strip()
        rows.append((cid, status, de_moi))
    return fm, rows


def main():
    ap = __import__("argparse").ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(SRC_DIR, "*.md")))
    if not files:
        print("Không thấy file hiệu đính.")
        return
    tong_row = tong_khop = tong_lech_de = 0
    ke_hoach = []  # (bank_path, id, de_moi, cl_moi, ly_do_moi)
    for f in files:
        fm, rows = doc_bang_hieudinh(f)
        bank_path = os.path.join(BANK_DIR, os.path.basename(fm.get("bank", "")))
        if not os.path.exists(bank_path):
            print(f"BỎ QUA {f}: không thấy {bank_path}")
            continue
        bank = {c["id"]: c for c in json.load(open(bank_path, encoding="utf-8"))}
        n_khop = n_lech = 0
        for cid, status, de_moi in rows:
            tong_row += 1
            if cid not in bank:
                print(f"  CẢNH BÁO {cid} có trong MD nhưng không có trong bank.")
                continue
            n_khop += 1
            cu = bank[cid]
            if (cu.get("de", "") or "").strip() != de_moi.strip():
                n_lech += 1
            if status in STATUS_OK:
                cl_moi, ly_do = "ok", ""
            else:  # 🟡 thiếu hình -> giữ can_duyet
                cl_moi = "can_duyet"
                ly_do = cu.get("ly_do") or "can_hinh"
            ke_hoach.append((bank_path, cid, de_moi, cl_moi, ly_do))
        tong_khop += n_khop
        tong_lech_de += n_lech
        print(f"{os.path.basename(f)[:30]:30s} rows={len(rows)} khớp={n_khop} đổi_de={n_lech}")
    print(f"TỔNG: {tong_row} dòng, khớp bank: {tong_khop}, đổi text: {tong_lech_de}")

    if not args.apply:
        print("Dry-run: chưa ghi gì. Thêm --apply để backup + ghi thật.")
        return
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = os.path.join("data", f"bank_backup_hieudinh_{stamp}")
    shutil.copytree(BANK_DIR, backup)
    print("Backup:", backup)
    theo_file = {}
    for path, cid, de_moi, cl_moi, ly_do in ke_hoach:
        theo_file.setdefault(path, []).append((cid, de_moi, cl_moi, ly_do))
    for path, ds in theo_file.items():
        bank = json.load(open(path, encoding="utf-8"))
        by_id = {c["id"]: c for c in bank}
        for cid, de_moi, cl_moi, ly_do in ds:
            if cid in by_id:
                by_id[cid]["de"] = de_moi
                by_id[cid]["chat_luong"] = cl_moi
                by_id[cid]["ly_do"] = ly_do
        json.dump(bank, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"Đã ghi {os.path.basename(path)} ({len(ds)} câu)")


if __name__ == "__main__":
    main()
