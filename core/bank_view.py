"""Hiển thị câu hỏi bank cho GV: tách phương án A-D, làm đẹp công thức.

CHỈ phục vụ hiển thị — không sửa dữ liệu gốc trong JSON.
Công thức bị mất nét khi trích PDF (vd phân số rã) thì giữ nguyên,
GV sửa tay bằng form Sửa; ở đây chỉ chuẩn hóa khoảng trắng/ký tự.
"""
import re

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
    r"|\\frac\{[^}]+\}\{[^}]+\}"        # \frac
    r"|\\[a-zA-Z]+"                     # lệnh LaTeX
    r"|[" + _GREEK + r"]"               # ký tự Hy Lạp
    r"|[²³¹⁰⁴⁵⁶⁷⁸⁹½⅓⅔¼¾]"            # luỹ thừa unicode
    r"|√"                               # dấu căn
    r"|[≤≥≠≈∞∈∉∩∪⊂⊃∀∃±×÷]"            # ký hiệu toán
    r"|(?<![A-ZÀ-Ỹa-zà-ỹ])(?:sin|cos|tan|cot|arcsin|arccos|arctan|lim|log|ln)\s*[(\[]"  # hàm trig
    r")"
)

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
    t = lam_dep(text)
    t = _wrap_math_segments(t)
    return t


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

