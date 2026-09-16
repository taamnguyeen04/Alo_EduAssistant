"""Lớp truy xuất tri thức: nối chatbot với kho bank JSON + wiki MD + video.

Nguyên tắc:
- Bank JSON là nguồn chính xác (đề/đáp án/bước giải), chỉ lấy câu chat_luong == "ok".
- Wiki MD là lớp liên kết (truy gốc điểm yếu qua concepts/dang-bai).
- Tìm kiếm bằng trùng từ khóa (đơn giản, HS hiểu được, không cần vectorDB).
- KHÔNG bao giờ lộ đáp án ra UI — đáp án chỉ đưa vào prompt nội bộ cho AI định hướng.
"""
import glob
import os
import re
from functools import lru_cache

from . import subjects

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANK_GLOB = os.path.join(BASE_DIR, "data", "bank", "*.json")  # giữ để tương thích cũ
WIKI_DIR = os.path.join(BASE_DIR, "data", "wiki")  # giữ để tương thích cũ

STOPWORDS = {
    "la", "cua", "cac", "mot", "nhung", "voi", "trong", "khong", "cho", "de",
    "va", "co", "duoc", "nhu", "nao", "sao", "thi", "ma", "em", "tai",
    "theo", "ve", "den", "tu", "da", "se", "hay", "gi", "vi", "bai", "cau",
    "hoi", "giai",     "tinh", "biet", "tim", "chung", "minh", "rang",
    "is", "are", "to", "of", "and", "the", "a", "an",
}


def tach_tu(text):
    """Tách từ khóa: thường hóa, bỏ stopword, giữ token toán (sin, u_n...)."""
    toks = re.findall(r"[a-z0-9_]+", (text or "").lower())
    return {t for t in toks if len(t) >= 2 and t not in STOPWORDS}


def _safe_stem(bai):
    return "".join(c if c.isalnum() else "_" for c in (bai or ""))[:60] or "chung"


def _bank_glob(mon):
    return os.path.join(subjects.lay_mon(mon)["bank_dir"], "*.json")


def _wiki_dir(mon):
    return subjects.lay_mon(mon)["wiki_dir"]


@lru_cache(maxsize=8)
def tai_bank(mon="toan11"):
    """Nạp toàn bộ bank của 1 môn: {id: cau_d đầy đủ}. Cache theo môn."""
    kho = {}
    for f in glob.glob(_bank_glob(mon)):
        try:
            import json
            for c in json.load(open(f, encoding="utf-8")):
                if isinstance(c, dict) and c.get("id"):
                    kho[c["id"]] = c
        except Exception:
            continue
    return kho


def tim_cau_theo_id(cid, mon="toan11"):
    return tai_bank(mon).get((cid or "").strip())


def _diem(trung, do_dai_de):
    # Trùng nhiều từ hiếm + đề ngắn gọn thì điểm cao hơn
    return len(trung) / (1 + do_dai_de / 300)


def tim_cau_lien_quan(cau_hoi, bai=None, n=3, chi_ok=True, bo_id_da_dung=frozenset(), mon="toan11"):
    """Tìm n câu liên quan nhất bằng trùng từ khóa. Trả về list dict đầy đủ."""
    khoa = tach_tu(cau_hoi)
    if not khoa:
        return []
    ung = []
    for cid, c in tai_bank(mon).items():
        if chi_ok and c.get("chat_luong") != "ok":
            continue
        if bai and c.get("bai") != bai:
            continue
        if cid in bo_id_da_dung:
            continue
        de_tok = tach_tu(c.get("de", ""))
        trung = khoa & de_tok
        if not trung:
            continue
        ung.append((_diem(trung, len(c.get("de", ""))), c))
    ung.sort(key=lambda x: -x[0])
    return [c for _, c in ung[:n]]


def cau_theo_diem_yeu(diem_yeu, bai=None, n=3, mon="toan11"):
    """Gộp kết quả tìm kiếm cho từng điểm yếu, khử trùng, giữ thứ tự hay nhất."""
    thay, thay_id = [], set()
    for w in (diem_yeu or []):
        for c in tim_cau_lien_quan(w, bai=bai, n=n, mon=mon):
            if c["id"] not in thay_id:
                thay_id.add(c["id"])
                thay.append(c)
    return thay[: max(n, len(diem_yeu or []))]


def loi_sai_cua_bai(bai, n=5, mon="toan11"):
    """Gom lỗi hay gặp nhất của 1 Bài (để AI nhắc trước khi HS vấp)."""
    dem = {}
    for c in tai_bank(mon).values():
        if c.get("bai") != bai or c.get("chat_luong") != "ok":
            continue
        for l in (c.get("loi_hay_gap") or []):
            dem[l] = dem.get(l, 0) + 1
    return sorted(dem, key=lambda k: -dem[k])[:n]


def doc_concept(bai, max_chars=1500, mon="toan11"):
    """Đọc trang khái niệm wiki của Bài (truy gốc điểm yếu). Không có -> ''."""
    p = os.path.join(_wiki_dir(mon), "concepts", _safe_stem(bai) + ".md")
    if not os.path.exists(p):
        return ""
    try:
        with open(p, encoding="utf-8") as f:
            return f.read()[:max_chars]
    except Exception:
        return ""


def tom_tat_kho(mon="toan11"):
    """Thống kê nhanh để đưa vào prompt GV."""
    tong, ok, theo_bai = 0, 0, {}
    for c in tai_bank(mon).values():
        tong += 1
        theo_bai[c.get("bai", "?")] = theo_bai.get(c.get("bai", "?"), 0) + 1
        if c.get("chat_luong") == "ok":
            ok += 1
    return {"tong": tong, "ok": ok, "theo_bai": theo_bai}
