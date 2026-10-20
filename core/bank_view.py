"""Hiển thị câu hỏi bank cho GV: tách phương án A-D, làm đẹp công thức.

CHỈ phục vụ hiển thị — không sửa dữ liệu gốc trong JSON.
Công thức bị mất nét khi trích PDF (vd phân số rã) thì giữ nguyên,
GV sửa tay bằng form Sửa; ở đây chỉ chuẩn hóa khoảng trắng/ký tự.
"""
import base64
import functools
import os
import re

# ── Mức độ chuẩn toàn app: 1 Nhận biết / 2 Thông hiểu / 3 Vận dụng ──
MUC_DO = {1: "Nhận biết", 2: "Thông hiểu", 3: "Vận dụng"}

# ── Dạng câu hỏi trong Kho đề ──
LOAI_CAU = {
    "trac_nghiem": "Trắc nghiệm",
    "dung_sai": "Đúng – Sai",
    "tra_loi_ngan": "Trả lời ngắn",
}

# Thư mục chứa hình wiki (assets/B1/...), tính từ file này: core/ -> root/data/wiki
_WIKI_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "data", "wiki")

_RE_PA = re.compile(r"(?<![A-ZÀ-Ỹa-zà-ỹ0-9])([A-D])\.\s*(.*?)(?=(?<![A-ZÀ-Ỹa-zà-ỹ0-9])[A-D]\.\s*|$)", re.S)
_RE_DAP_AN = re.compile(r"Chọn\s*#?\s*([A-D])", re.I)
_RE_PUA = re.compile(r"[\ue000-\uf8ff]")

# ── Ký tự toán học cần bọc trong $...$ ──────────────────────────────────────
# Các ký tự Hy Lạp toán học
_GREEK = "αβγδεζηθικλμνξοπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ"
# Pattern nhận diện đoạn có chứa toán học
_RE_MATH_INLINE = re.compile(
    r"(?:"
    r"\$[^$]+\$"                        # đã có $...$
    r"|\\[a-zA-Z]+\{[^{}]*\}(\{[^{}]*\})?"  # lệnh LaTeX kèm {} (bọc cả cụm)
    r"|\\frac\{[^}]+\}\{[^}]+\}"        # \frac
    r"|\\[a-zA-Z]+"                     # lệnh LaTeX lẻ
    r"|[" + _GREEK + r"]"               # ký tự Hy Lạp
    r"|[²³¹⁰⁴⁵⁶⁷⁸⁹½⅓⅔¼¾]"            # luỹ thừa unicode
    r"|√"                               # dấu căn
    r"|[≤≥≠≈∞∈∉∩∪⊂⊃∀∃±×÷]"            # ký hiệu toán
    r"|(?<![A-ZÀ-Ỹa-zà-ỹ])(?:sin|cos|tan|cot|arcsin|arccos|arctan|lim|log|ln)\s*[(\[]"  # hàm trig
    r")"
)

# Câu ingest từ DOCX mới dùng \(...\) / \[...\] thay vì $...$ (VD B4-TN-006).
# Streamlit chỉ render $...$/$$...$$ nên phải đổi ở lớp hiển thị (không sửa JSON).
_RE_LATEX_PAREN_INLINE = re.compile(r"\\\((.+?)\\\)", re.S)
_RE_LATEX_PAREN_DISPLAY = re.compile(r"\\\[(.+?)\\\]", re.S)


def _doi_ngoac_latex(text):
    """\(...\) -> $...$, \[...\] -> $$...$$. Chỉ hiển thị, không sửa gốc."""
    if not text or "\\(" not in text and "\\[" not in text:
        return text
    text = _RE_LATEX_PAREN_DISPLAY.sub(r"$$\1$$", text)
    text = _RE_LATEX_PAREN_INLINE.sub(r"$\1$", text)
    return text

# Map ký tự unicode → LaTeX tương đương
_UNICODE_MAP = {
    "²": "^2", "³": "^3", "¹": "^1", "⁰": "^0",
    "⁴": "^4", "⁵": "^5", "⁶": "^6", "⁷": "^7", "⁸": "^8", "⁹": "^9",
    "½": r"\frac{1}{2}", "⅓": r"\frac{1}{3}", "⅔": r"\frac{2}{3}",
    "¼": r"\frac{1}{4}", "¾": r"\frac{3}{4}",
    "√": r"\sqrt",
    "≤": r"\leq", "≥": r"\geq", "≠": r"\neq", "≈": r"\approx",
    "∞": r"\infty", "∈": r"\in", "∉": r"\notin",
    "∩": r"\cap", "∪": r"\cup",
    "⊂": r"\subset", "⊃": r"\supset",
    "∀": r"\forall", "∃": r"\exists",
    "±": r"\pm", "×": r"\times", "÷": r"\div",
    "π": r"\pi", "α": r"\alpha", "β": r"\beta", "γ": r"\gamma",
    "δ": r"\delta", "ε": r"\epsilon", "θ": r"\theta", "λ": r"\lambda",
    "μ": r"\mu", "σ": r"\sigma", "φ": r"\phi", "ω": r"\omega",
    "Δ": r"\Delta", "Π": r"\Pi", "Σ": r"\Sigma", "Ω": r"\Omega",
    "°": r"°",  # giữ nguyên dấu độ
}


def _unicode_to_latex(text):
    """Chuyển ký tự toán unicode → lệnh LaTeX."""
    for ch, latex in _UNICODE_MAP.items():
        text = text.replace(ch, latex)
    return text


def _wrap_math_segments(text):
    """Tự động phát hiện đoạn toán học trong text và bọc vào $...$."""
    if not text:
        return text

    # Nếu đã có nhiều $...$, không wrap thêm
    if text.count("$") >= 4:
        return text

    # Tách text thành các token: [text_thường, toán, text_thường, ...]
    # Chiến lược: bọc từng token toán riêng lẻ vào $...$
    result = []
    pos = 0
    for m in _RE_MATH_INLINE.finditer(text):
        start, end = m.start(), m.end()
        if start > pos:
            result.append(text[pos:start])
        token = text[start:end]
        # Nếu chưa có $, bọc vào
        if not token.startswith("$"):
            token = "$" + _unicode_to_latex(token) + "$"
        result.append(token)
        pos = end
    if pos < len(text):
        result.append(text[pos:])
    return "".join(result)


def tach_phuong_an(de):
    """Tách 'đề ... A. ... B. ...' -> (thân đề, [(nhãn, nội dung)]).
    Không đủ 2 phương án thì trả (de, []) để hiện nguyên văn."""
    # Đề trích thiếu (< 2 phương án) thì giữ nguyên văn để GV sửa tay.
    text = (de or "").strip()
    matches = [(m.group(1).upper(), m.group(2).strip(" .;\n")) for m in _RE_PA.finditer(text)]
    if len(matches) < 2:
        return text, []
    # Thân đề = phần trước phương án đầu; bỏ đuôi "là:"/"là" thừa
    dau = text[: text.find(matches[0][0] + ".")]
    dau = re.sub(r"\s*(là|la)\s*:?\s*$", "", dau).strip()
    return dau, matches


def dap_an_dung(dap_an):
    """'Chọn B' / 'Chọn#B...' -> 'B'. Không rõ -> ''."""
    m = _RE_DAP_AN.search(dap_an or "")
    return m.group(1).upper() if m else ""


def lam_dep(text):
    """Chuẩn hóa hiển thị: khoảng trắng, ký tự toán, ký tự font lỗi còn sót."""
    t = _RE_PUA.sub("", text or "")   # bỏ ký tự vùng Private Use Area
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\s+([°′″.,;:!?%)\]])", r"\1", t)
    t = re.sub(r"([\[()])\s+", r"\1", t)
    t = re.sub(r"\s*\n\s*", "\n", t)
    return t.strip()


def lam_dep_hien_thi(text):
    """Làm đẹp + tự wrap toán unicode → $...$  cho st.markdown render KaTeX."""
    # Chỉ phục vụ hiển thị — không bao giờ sửa dữ liệu gốc trong JSON.
    t = lam_dep(text)
    t = _doi_ngoac_latex(t)
    t = _wrap_math_segments(t)
    return t


# ── Nhúng hình wiki (assets/...) thành data URI để Streamlit hiện được ──
_MIME = {".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg",
         ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}
_RE_IMG_TAG = re.compile(r'(<img\s[^>]*?src=")(assets/[^"]+)(")')
_RE_MD_IMG = re.compile(r'(!\[[^\]]*\]\()(assets/[^)\s]+)(\))')


@functools.lru_cache(maxsize=4000)
def _data_uri(asset):
    """assets/B1/image326.svg -> data:image/svg+xml;base64,... (cache RAM).

    File > 800KB thì bỏ qua (tránh phình trang). Không đọc được -> "".
    """
    try:
        path = os.path.join(_WIKI_DIR, asset.replace("/", os.sep))
        if not os.path.isfile(path) or os.path.getsize(path) > 800 * 1024:
            return ""
        with open(path, "rb") as f:
            raw = f.read()
        mime = _MIME.get(os.path.splitext(path)[1].lower(), "image/png")
        return "data:%s;base64,%s" % (mime, base64.b64encode(raw).decode("ascii"))
    except Exception:
        return ""


def nhung_anh(text):
    """Thay mọi tham chiếu assets/... trong text thành data URI nhúng.

    Hỗ trợ cả <img src="assets/..."> và ![](assets/...). Câu cũ không có
    hình thì trả nguyên văn, không tốn gì.
    """
    if not text or "assets/" not in text:
        return text

    def _doi(m):
        uri = _data_uri(m.group(2))
        return m.group(1) + (uri or m.group(2)) + m.group(3)

    text = _RE_IMG_TAG.sub(_doi, text)
    return _RE_MD_IMG.sub(_doi, text)


def hien_thi(text):
    """Render đầy đủ cho UI: làm đẹp công thức + nhúng hình."""
    return nhung_anh(lam_dep_hien_thi(text))


# ── Dạng câu hỏi / mức độ (tương thích ngược câu bank cũ) ──
def loai_cau(c):
    """'trac_nghiem' | 'dung_sai' | 'tra_loi_ngan' (câu cũ suy từ dang)."""
    loai = (c or {}).get("loai", "")
    if loai in LOAI_CAU:
        return loai
    return "tra_loi_ngan" if (c or {}).get("dang") == "TL" else "trac_nghiem"


def muc_do_cau(c):
    """1/2/3 từ do_kho (câu mới có sẵn muc_do chữ thì vẫn quy về số)."""
    try:
        return max(1, min(3, int((c or {}).get("do_kho", 2) or 2)))
    except (TypeError, ValueError):
        return 2


def ten_loai(c):
    return LOAI_CAU.get(loai_cau(c), "Trắc nghiệm")


def ten_muc_do(c):
    return MUC_DO.get(muc_do_cau(c), "Thông hiểu")


# ── Tách mệnh đề Đúng/Sai: "stem a) ... b) ..." -> (thân, [(nhãn, nội dung)]) ──
# Chấp nhận cả "a)" lẫn "a\)" (markdown escape từ ingest DOCX).
_RE_MENH_DE = re.compile(r"(?<![A-Za-zÀ-Ỹà-ỹ0-9])([a-dA-D])\\?\)\s*(.*?)(?=(?<![A-Za-zÀ-Ỹà-ỹ0-9])[a-dA-D]\\?\)\s*|$)", re.S)
_RE_DUNG_SAI = re.compile(r"([a-dA-D])\)\s*(Đúng|Sai|dung|sai|ĐUNG|SAI)")


def _sach_menh_de(s):
    """Bỏ dấu trích dẫn '>' + sao markdown '**' còn sót quanh mệnh đề wiki."""
    dong = [re.sub(r"^\s*>\s?", "", d) for d in (s or "").splitlines()]
    s = " ".join(d.strip() for d in dong if d.strip())
    s = re.sub(r"^[\s>*]+", "", s)
    s = re.sub(r"[\s*<]+$", "", s)
    return s.strip(" .;\n")


def tach_menh_de(de):
    """Tách câu Đúng/Sai thành thân đề + 4 mệnh đề a)–d).

    Không đủ 2 mệnh đề thì trả (de, []) để hiện nguyên văn.
    """
    text = (de or "").strip()
    matches = [(m.group(1).lower(), _sach_menh_de(m.group(2)))
               for m in _RE_MENH_DE.finditer(text)]
    if len(matches) < 2:
        return text, []
    dau = text[: text.lower().find(matches[0][0] + ")")]
    dau = _sach_menh_de(re.sub(r"\s*(sau|:\s*)$", "", dau))
    return dau, matches


def dap_an_dung_sai(dap_an):
    """'a) Đúng b) Sai ...' -> {'a': True, 'b': False, ...}."""
    kq = {}
    for m in _RE_DUNG_SAI.finditer(dap_an or ""):
        kq[m.group(1).lower()] = m.group(2).lower().startswith("đ") or m.group(2).lower() == "dung"
    return kq


# Pattern nhận biết công thức bị rã nặng từ PDF
_RE_CONG_THUC_RA = re.compile(
    r"(?:"
    r"[=+\-×÷<>][\s]*[πα-ωΑ-Ω]"          # dấu toán + ký tự Hy Lạp rời
    r"|[πα-ωΑ-Ω][\s]*[=+\-]"               # ký tự Hy Lạp trước dấu toán
    r"|\d+\s+[πα-ωΑ-Ω](?!\w)"              # số rồi ký tự Hy Lạp cách nhau
    r"|[A-Za-z]\s+[A-Za-z]\s+[A-Za-z]\s+\(" # chuỗi ký tự đơn rời rạc kiểu "sin cos tan ("
    r"|(?:sin|cos|tan)\s+[a-z]\s+[a-z]"    # sin/cos theo sau 2 biến rời
    r")"
)


def phat_hien_cong_thuc_ra(de, dap_an="", buoc_giai=None):
    """Kiểm tra câu có dấu hiệu công thức bị rã từ PDF hay không.
    Trả về list[str] mô tả vấn đề, rỗng nếu OK."""
    van_de = []
    all_text = " ".join([de or "", dap_an or ""] + (buoc_giai or []))
    if _RE_CONG_THUC_RA.search(all_text):
        van_de.append("công thức có thể bị rã khi trích PDF")
    # Kiểm tra ký tự dấu hỏi thay thế (PUA đã bị xóa trước)
    if "?" in all_text and any(c in all_text for c in "πα"):
        van_de.append("có ký tự ? thay thế ký tự toán")
    # Chuỗi toán tự ngắn liên tiếp (dấu hiệu phân số rã)
    if re.search(r"\b[a-z]\s+[a-z]\s+[a-z]\b", all_text) and any(c in all_text for c in "πα²"):
        van_de.append("phân số/biểu thức có thể bị tách dòng")
    return van_de

