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
    # Token ngắn hơn 2 ký tự toàn từ nối vô nghĩa nên bỏ.
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
    # Nạp 1 lần rồi cache để tìm kiếm mỗi lượt chat không quét lại đĩa.
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
    # Không tách được từ khóa thì trả rỗng ngay để khỏi quét bank vô ích.
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
    # Giữ tương thích stub cũ (concepts/<stem Bài>.md); hệ mới C1_Bx_Kxx
    # đọc qua doc_ly_thuyet() nên hàm này chỉ còn fallback.
    p = os.path.join(_wiki_dir(mon), "concepts", _safe_stem(bai) + ".md")
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                return f.read()[:max_chars]
        except Exception:
            return ""
    # Fallback hệ mới: lấy concepts của lesson khớp nhất.
    _, concepts, _ = doc_ly_thuyet(bai, "", mon=mon, max_wiki_chars=0,
                                   max_concepts=1, max_concept_chars=max_chars)
    return concepts


@lru_cache(maxsize=4)
def _tai_syllabus(mon="toan11"):
    """Nạp syllabus.json (map Bài -> wiki_page + knowledge_units). Cache."""
    p = os.path.join(_wiki_dir(mon), "syllabus.json")
    try:
        import json
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        lessons = d.get("lessons", []) if isinstance(d, dict) else []
        return [l for l in lessons if isinstance(l, dict)]
    except Exception:
        return []


def bai_sang_lesson(bai, cau_hoi="", mon="toan11"):
    """Map tên Bài bank (tiếng Việt) -> lesson C1_Bx trong syllabus.

    Chấm bằng trùng từ khóa giữa tên Bài + câu hỏi với title/summary từng
    lesson. Không khớp -> None (để caller vét theo câu hỏi).
    """
    lessons = _tai_syllabus(mon)
    if not lessons:
        return None
    khoa_bai = tach_tu(f"{bai or ''} {cau_hoi or ''}")
    if not khoa_bai:
        return None
    best, best_diem = None, 0
    for l in lessons:
        van = f"{l.get('title', '')} {l.get('id', '')} " + " ".join(
            f"{k.get('title', '')} {k.get('summary', '')}"
            for k in (l.get("knowledge_units") or []) if isinstance(k, dict))
        trung = khoa_bai & tach_tu(van)
        diem = len(trung)
        # Ưu tiên khớp trực tiếp tên Bài với title lesson.
        if tach_tu(bai or "") & tach_tu(l.get("title", "")):
            diem += 2
        if diem > best_diem:
            best, best_diem = l, diem
    return best if best_diem >= 2 else None


def _doc_file(mon, rel, max_chars):
    if not rel:
        return ""
    p = os.path.join(_wiki_dir(mon), rel.replace("/", os.sep))
    if not os.path.exists(p):
        return ""
    try:
        with open(p, encoding="utf-8") as f:
            t = f.read()
        # Bỏ frontmatter ---...--- đầu file cho gọn token.
        if t.startswith("---"):
            end = t.find("---", 3)
            if 0 < end < 2000:
                t = t[end + 3:].lstrip()
        return t[:max_chars].strip()
    except Exception:
        return ""


def doc_ly_thuyet(bai, cau_hoi="", mon="toan11", max_wiki_chars=3000,
                  max_concepts=2, max_concept_chars=1200):
    """Đọc lý thuyết chuẩn cho hỏi đáp: (wiki_bai, concepts_ghep, lesson_id).

    - wiki_bai: nội dung wiki/<lesson>.md (source_grounded, ~4-5KB) cắt gọn.
    - concepts_ghep: 1-2 units C1_Bx_Kxx khớp câu hỏi nhất (công thức cốt lõi).
    - lesson_id: 'C1_B1'... hoặc '' khi không map được.
    Thiếu file nào thì trả rỗng phần đó, không bao giờ raise.
    """
    lesson = bai_sang_lesson(bai, cau_hoi, mon)
    if lesson is None:
        # Vét theo câu hỏi trên toàn syllabus khi tên Bài không khớp.
        lessons = _tai_syllabus(mon)
        khoa = tach_tu(cau_hoi or "")
        best, best_diem = None, 0
        for l in lessons:
            van = f"{l.get('title', '')} " + " ".join(
                f"{k.get('title', '')} {k.get('summary', '')}"
                for k in (l.get("knowledge_units") or []) if isinstance(k, dict))
            d = len(khoa & tach_tu(van))
            if d > best_diem:
                best, best_diem = l, d
        lesson = best if best_diem >= 1 else None
    if lesson is None:
        return "", "", ""
    lid = lesson.get("id", "") or ""
    wiki_text = _doc_file(mon, lesson.get("wiki_page", ""), max_wiki_chars)
    # Chọn concepts khớp câu hỏi nhất trong lesson.
    units = [k for k in (lesson.get("knowledge_units") or []) if isinstance(k, dict)]
    khoa = tach_tu(f"{cau_hoi or ''} {bai or ''}")
    scored = []
    for k in units:
        van = f"{k.get('title', '')} {k.get('summary', '')} {k.get('id', '')}"
        trung = khoa & tach_tu(van)
        scored.append((len(trung), k))
    scored.sort(key=lambda x: -x[0])
    # Không tách được từ khóa thì lấy 1 unit đầu để HS luôn có nền.
    top = [k for s, k in scored[:max_concepts] if s > 0] or units[:1]
    parts = []
    for k in top[:max_concepts]:
        t = _doc_file(mon, f"concepts/{k.get('id', '')}.md", max_concept_chars)
        if t:
            parts.append(f"[{k.get('id', '')} — {k.get('title', '')}]\n{t}")
    return wiki_text, "\n\n---\n\n".join(parts), lid


def tom_tat_kho(mon="toan11"):
    """Thống kê nhanh để đưa vào prompt GV."""
    tong, ok, theo_bai = 0, 0, {}
    for c in tai_bank(mon).values():
        tong += 1
        theo_bai[c.get("bai", "?")] = theo_bai.get(c.get("bai", "?"), 0) + 1
        if c.get("chat_luong") == "ok":
            ok += 1
    return {"tong": tong, "ok": ok, "theo_bai": theo_bai}
