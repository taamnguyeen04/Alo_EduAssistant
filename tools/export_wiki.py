"""Xuất wiki Markdown (kiểu Karpathy llm-wiki) từ data/bank/*.json.

Một chiều JSON -> MD (không đồng bộ ngược):
  - bank JSON là nguồn chính cho máy (ra đề, chấm, lọc do_kho)
  - wiki MD là lớp liên kết cho người + LLM (Obsidian, truy gốc điểm yếu)

  wiki/ -> data/wiki/
    index.md            mục lục (tạo lại mỗi lần chạy)
    overview.md         tổng quan (chỉ tạo mới, LLM sở hữu về sau)
    conventions.md      quy ước (chỉ tạo mới)
    log.md              nhật ký (ghi thêm mỗi lần chạy)
    sources/<stem>.md   1 trang/Bài (chỉ tạo mới — GV hiệu đính tay, không ghi đè)
    concepts/<stem>.md  kiến thức + liên kết [[...]] (chỉ tạo stub, LLM bồi sau)
    dang-bai/<stem>__Dang-N.md  cụm dạng bài (tạo lại)
    analyses/loi-sai-pho-bien.md  tần suất lỗi (tạo lại)

Chạy:  python tools/export_wiki.py
"""
import glob
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

BANK_GLOB = os.path.join(BASE_DIR, "data", "bank", "*.json")
WIKI = os.path.join(BASE_DIR, "data", "wiki")


def bai_so(bai):
    m = re.match(r"(?:Bài|bai)[\s\-_]*(\d+)", bai or "", re.IGNORECASE)
    return int(m.group(1)) if m else 999


def norm_dang(d):
    m = re.match(r"D\s*ạng\s*(\d+)", (d or ""), re.IGNORECASE)
    return f"Dang-{m.group(1)}" if m else ""


def load_bank():
    out = []
    for f in sorted(glob.glob(BANK_GLOB)):
        ds = json.load(open(f, encoding="utf-8"))
        bai = ds[0].get("bai", os.path.basename(f)) if ds else os.path.basename(f)
        out.append({"file": f, "stem": os.path.splitext(os.path.basename(f))[0],
                    "bai": bai, "so": bai_so(bai), "ds": ds})
    return sorted(out, key=lambda b: b["so"])


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(text)


def only_new(path, text):
    if not os.path.exists(path):
        write(path, text)
        return True
    return False


def md_table(rows):
    return "\n".join("| " + " | ".join(r) + " |" for r in rows)


def export_sources(bank):
    for b in bank:
        ds = b["ds"]
        tn = sum(1 for c in ds if c.get("dang") == "TN")
        tl = sum(1 for c in ds if c.get("dang") == "TL")
        kho = Counter(str(c.get("do_kho", "?")) for c in ds)
        ok = sum(1 for c in ds if c.get("chat_luong") == "ok")
        loi = Counter(l for c in ds for l in (c.get("loi_hay_gap") or []))
        dang = Counter(norm_dang(c.get("dang_phan", "")) or "(chung)" for c in ds)
        lines = [f"---\nbai: \"{b['bai']}\"\nbank: \"data/bank/{os.path.basename(b['file'])}\""
                 f"\ntong_cau: {len(ds)}\nchat_luong_ok: {ok}\n---\n",
                 f"# Nguồn: {b['bai']}", "",
                 f"Kho đề: `data/bank/{os.path.basename(b['file'])}` | "
                 f"Tổng {len(ds)} câu (TN {tn} / TL {tl}) | "
                 f"Độ khó {dict(sorted(kho.items()))} | Đạt chuẩn {ok}/{len(ds)}",
                 f"Khái niệm: [[concepts/{b['stem']}]]", "",
                 "## Cụm dạng bài"]
        for d, n in sorted(dang.items()):
            if d == "(chung)":
                lines.append(f"- Trắc nghiệm chung: {n} câu")
            else:
                lines.append(f"- [[dang-bai/{b['stem']}__{d}|{d.replace('Dang-', 'Dạng ')}]]: {n} câu")
        if loi:
            lines += ["", "## Lỗi hay gặp"] + [f"- {l} (×{n})" for l, n in loi.most_common(10)]
        lines += ["", "## Danh sách câu hỏi",
                  "| id | dạng | khó | chuẩn | đề |",
                  "|---|---|---|---|---|"]
        for c in ds:
            de = re.sub(r"\s+", " ", c.get("de", "") or "")[:180]
            cl = "✅" if c.get("chat_luong") == "ok" else "🟡"
            lines.append(f"| {c.get('id')} | {c.get('dang')} | {c.get('do_kho')} | {cl} "
                         f"| {de} |")
        lines += ["", f"_Nguồn chính xác nằm ở `data/bank/{os.path.basename(b['file'])}`._", ""]
        # Trang sources/ do GV hiệu đính tay (2026-09-14) nên KHÔNG ghi đè:
        # chỉ tạo mới khi chưa có. Muốn đồng bộ lại, xóa file rồi chạy lại.
        only_new(os.path.join(WIKI, "sources", b["stem"] + ".md"), "\n".join(lines) + "\n")
    return len(bank)


def export_concepts(bank):
    moi = 0
    for i, b in enumerate(bank):
        prev = f"[[concepts/{bank[i-1]['stem']}|{bank[i-1]['bai']}]]" if i > 0 else "(đầu chương trình)"
        nxt = f"[[concepts/{bank[i+1]['stem']}|{bank[i+1]['bai']}]]" if i + 1 < len(bank) else "(chưa có)"
        loi = Counter(l for c in b["ds"] for l in (c.get("loi_hay_gap") or [])).most_common(5)
        text = (f"---\nbai: \"{b['bai']}\"\nnguon: \"[[sources/{b['stem']}]]\"\n---\n\n"
                f"# Khái niệm: {b['bai']}\n\n"
                f"- Nguồn chi tiết: [[sources/{b['stem']}]]\n"
                f"- Kiến thức nền: {prev}\n- Học tiếp: {nxt}\n\n"
                f"## Lỗi sai điển hình\n" +
                ("".join(f"- {l} (×{n})\n" for l, n in loi) if loi else "- (chưa thống kê)\n") +
                "\n## Gốc rễ điểm yếu (LLM bồi đắp dần)\n\n"
                f"- TODO: khi HS sai dạng bài thuộc [[sources/{b['stem']}]], "
                "ghi lại ở đây là hổng từ khái niệm nền nào (xem AGENTS.md).\n")
        if only_new(os.path.join(WIKI, "concepts", b["stem"] + ".md"), text):
            moi += 1
    return moi


def export_dang(bank):
    n = 0
    for b in bank:
        nhom = {}
        for c in b["ds"]:
            d = norm_dang(c.get("dang_phan", ""))
            if d:
                nhom.setdefault(d, []).append(c)
        for d, ds in sorted(nhom.items()):
            kho = Counter(str(c.get("do_kho", "?")) for c in ds)
            rows = ["| id | khó | chuẩn | đề |", "|---|---|---|---|"]
            for c in ds:
                de = re.sub(r"\s+", " ", c.get("de", "") or "")[:150]
                cl = "✅" if c.get("chat_luong") == "ok" else "🟡"
                rows.append(f"| {c.get('id')} | {c.get('do_kho')} | {cl} | {de} |")
            text = (f"---\nbai: \"{b['bai']}\"\ndang: \"{d}\"\n---\n\n"
                    f"# {d.replace('Dang-', 'Dạng ')} — {b['bai']}\n\n"
                    f"- Thuộc: [[sources/{b['stem']}]] / [[concepts/{b['stem']}]]\n"
                    f"- {len(ds)} câu, độ khó {dict(sorted(kho.items()))}\n\n" + "\n".join(rows) + "\n")
            write(os.path.join(WIKI, "dang-bai", f"{b['stem']}__{d}.md"), text)
            n += 1
    return n


def export_analyses(bank):
    loi = Counter()
    for b in bank:
        for c in b["ds"]:
            for l in (c.get("loi_hay_gap") or []):
                loi[(l, b["bai"])] += 1
    rows = ["| lỗi | bài | số câu |", "|---|---|---|"]
    for (l, bai), n in loi.most_common(30):
        rows.append(f"| {l} | {bai[:32]} | {n} |")
    text = ("---\nloai: \"tong-hop-loi-sai\"\n---\n\n# Lỗi sai phổ biến toàn kho\n\n"
            "Nguồn: cộng gộp `loi_hay_gap` từ `data/bank/*.json`.\n\n" + "\n".join(rows) + "\n")
    write(os.path.join(WIKI, "analyses", "loi-sai-pho-bien.md"), text)


def export_index(bank):
    lines = ["---\nloai: \"index\"\n---\n", "# Index wiki Toán 11", "",
             "## Nguồn theo Bài (chi tiết từng câu)", ""]
    for b in bank:
        lines.append(f"- [[sources/{b['stem']}|{b['bai']}]] ({len(b['ds'])} câu) "
                     f"— khái niệm: [[concepts/{b['stem']}]]")
    lines += ["", "## Cụm dạng bài", ""]
    for f in sorted(glob.glob(os.path.join(WIKI, "dang-bai", "*.md"))):
        s = os.path.splitext(os.path.basename(f))[0]
        lines.append(f"- [[dang-bai/{s}]]")
    lines += ["", "## Phân tích", "", "- [[analyses/loi-sai-pho-bien]]", "",
              "## Khung", "", "- [[overview]] | [[conventions]] | [[log]]", ""]
    write(os.path.join(WIKI, "index.md"), "\n".join(lines) + "\n")


def scaffold_static(tong, ok):
    only_new(os.path.join(WIKI, "overview.md"),
             f"# Tổng quan kho Toán 11\n\nKho hiện có **{tong} câu** ({ok} đạt chuẩn), "
             "8 Bài từ Chương 1 (lượng giác) và Chương 9 (đạo hàm).\n\n"
             "- Nguồn máy đọc: `data/bank/*.json` (lọc theo `do_kho`, trừ `id` đã đúng).\n"
             "- Wiki này để người + LLM đọc: truy gốc điểm yếu qua liên kết `[[...]]`.\n"
             "- Bắt đầu từ [[index]].\n")
    only_new(os.path.join(WIKI, "conventions.md"),
             "# Quy ước wiki\n\n"
             "1. `data/bank/*.json` là nguồn chính xác. Wiki không tự bịa đề/đáp án.\n"
             "2. Công thức viết LaTeX `$...$`, text thuần cho phần chữ.\n"
             "3. Liên kết khái niệm dùng `concepts/...`, dạng bài `dang-bai/...`.\n"
             "4. Câu `chat_luong != ok` gắn 🟡, không đưa cho HS luyện.\n"
             "5. Mỗi lần ingest/export ghi 1 dòng vào [[log]].\n")
    if not os.path.exists(os.path.join(WIKI, "log.md")):
        write(os.path.join(WIKI, "log.md"), "# Log wiki\n\n")


def main():
    bank = load_bank()
    tong = sum(len(b["ds"]) for b in bank)
    ok = sum(1 for b in bank for c in b["ds"] if c.get("chat_luong") == "ok")
    n_src = export_sources(bank)
    n_con = export_concepts(bank)
    n_dang = export_dang(bank)
    export_analyses(bank)
    export_index(bank)
    scaffold_static(tong, ok)
    with open(os.path.join(WIKI, "log.md"), "a", encoding="utf-8") as f:
        f.write(f"\n## [{datetime.now():%Y-%m-%d %H:%M}] export | {n_src} sources, "
                f"{n_dang} dang-bai, +{n_con} concept mới | {tong} câu ({ok} ok)\n")
    print(f"Wiki: {n_src} sources, {n_dang} dang-bai, +{n_con} concept mới, "
          f"index + analyses xong ({tong} cau, {ok} ok).")


if __name__ == "__main__":
    main()
