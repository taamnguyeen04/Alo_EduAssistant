"""Giải mã ký tự font Symbol / MTExtra trong text trích từ PDF Toán.

Nguyên nhân: file PDF gõ bằng Word + MathType, công thức dùng font Symbol
nên π trích thành \\uf070, α thành \\uf061, ° thành \\uf0b0...
Mỗi mục dưới đều hiệu chuẩn bằng ngữ cảnh thật trong kho, vd:
  "số đo \\uf061" = "số đo α"  |  "15\\uf0b0" = "15°"
  "S = (−∞;−1) \\uf0c8 (1;+∞)" = "... ∪ ..."  |  "m ∈ \\uf0c6" = "m ∈ ∅"
Mã nào chưa chắc chắn thì KHÔNG map (để nguyên cho GV thấy mà sửa).

HS chỉ cần nhớ: trích PDF Toán -> chạy giai_ma() trước khi lưu bank.
"""
import re

# Chữ Hy Lạp Adobe Symbol (vị trí chuẩn)
_SYMBOL_GREEK = {
    0x41: "Α", 0x42: "Β", 0x43: "Χ", 0x44: "Δ", 0x45: "Ε", 0x46: "Φ",
    0x47: "Γ", 0x48: "Η", 0x49: "Ι", 0x4A: "ϑ", 0x4B: "Κ", 0x4C: "Λ",
    0x4D: "Μ", 0x4E: "Ν", 0x4F: "Ο", 0x50: "Π", 0x51: "Θ", 0x52: "Ρ",
    0x53: "Σ", 0x54: "Τ", 0x55: "Υ", 0x56: "ς", 0x57: "Ω", 0x58: "Ξ",
    0x59: "Ψ", 0x5A: "Ζ",
    0x61: "α", 0x62: "β", 0x63: "χ", 0x64: "δ", 0x65: "ε", 0x66: "φ",
    0x67: "γ", 0x68: "η", 0x69: "ι", 0x6A: "ϕ", 0x6B: "κ", 0x6C: "λ",
    0x6D: "μ", 0x6E: "ν", 0x6F: "ο", 0x70: "π", 0x71: "θ", 0x72: "ρ",
    0x73: "σ", 0x74: "τ", 0x75: "υ", 0x76: "ϖ", 0x77: "ω", 0x78: "ξ",
    0x79: "ψ", 0x7A: "ζ",
}

PUA_MAP = {
    # Dấu ASCII nằm trong font Symbol
    0x28: "(", 0x29: ")",
    0x2B: "+", 0x2D: "−", 0x3C: "<", 0x3D: "=", 0x3E: ">",
    0x22: "∀", 0x24: "∃",
    0x30: "0", 0x32: "2", 0x34: "4", 0x37: "7", 0x3B: ";",
    0x5B: "[", 0x5D: "]", 0x7B: "{", 0x7D: "}",
    # Mảnh ngoặc co giãn của Word -> ngoặc thường
    0xE6: "(", 0xE7: "(", 0xE8: "(",
    0xF6: ")", 0xF7: ")", 0xF8: ")",
    0xE9: "[", 0xEA: "[", 0xEB: "[",
    0xF9: "]", 0xFB: "]",
    0xEC: "{", 0xED: "{", 0xEE: "{", 0xEF: "{",  # mảnh ngoặc nhọn trái
    0xFC: "}", 0xFD: "}", 0xFE: "}",            # mảnh ngoặc nhọn phải
    # Ký hiệu Symbol đã đối chiếu context ("k ∈ ∅" loại trừ từng cái)
    0xA2: "′", 0xA3: "≤", 0xA5: "∞", 0xB3: "≥",
    0xAE: "→", 0xB0: "°", 0xB1: "±", 0xB4: "×",
    0xB8: "÷", 0xB9: "≠", 0xBA: "≡", 0xBB: "≈",
    0xCE: "∈", 0xD0: "∠", 0xD6: "√", 0xD7: "/",
    0xC6: "∅", 0xC8: "∪",
    0xDB: "⇔", 0xDE: "⇒",
    0xBE: "",  # con dấu hết bài (3 cái liền cuối lời giải) -> bỏ
    # MTExtra (MathType), hiệu chuẩn bằng context trong kho:
    0xF06C: "²",    # superscript 2 ("cos²A + cos²B + ...")
    0xF0B7: "∠",    # angle ("phân giác góc ∠AOB")
    0xF0A1: "ℝ",    # R in đậm ("TXĐ: C. ℝ", "x ∈ ℝ")
    # LƯU Ý: \\uf0fa chưa rõ nghĩa -> cố ý không map.
}

for _code, _ch in _SYMBOL_GREEK.items():
    PUA_MAP[0xF000 + _code] = _ch
for _code, _ch in list(PUA_MAP.items()):
    if _code < 0x100:  # mã Symbol thô -> dạng PUA trích được
        PUA_MAP[0xF000 + _code] = _ch

_RE_PUA = re.compile(r"[\ue000-\uf8ff]")
_PUA_A2 = "\uf0a2"
_PUA_BC = "\uf0bc"


def giai_ma(text):
    """Thay ký tự PUA bằng ký tự Toán thật. Ký tự lạ chưa biết -> giữ nguyên."""
    t = text or ""
    # Ngoại lệ font: cùng mã, khác font, khác nghĩa (đã đối chiếu PDF gốc).
    # Chạy TRƯỚC map chung vì lúc này text vẫn còn mã PUA thô.
    # - "k <F0CE><F0A2>" là "k ∈ ℤ" (MTExtra), còn lại <F0A2> là dấu phút ′ (Symbol)
    t = re.sub("\uf0ce\\s*" + _PUA_A2, "∈ ℤ", t)
    # - "<F0BC>" giữa 2 dấu + là ⋯ (tổng cấp số), cạnh "cung AM" là ⌢ (cung tròn)
    t = re.sub(r"\+\s*" + _PUA_BC + r"\s*\+", "+ ⋯ +", t)
    t = re.sub(_PUA_BC + r"(?=[\s\S]{0,20}AM)", "⌢", t)
    t = t.replace(_PUA_BC, "⋯")
    return _RE_PUA.sub(lambda m: PUA_MAP.get(ord(m.group(0)), m.group(0)), t)


def gon_dong(text):
    """Gộp dòng vỡ do layout công thức: mỗi glyph 1 dòng -> 1 dòng đọc được."""
    lines = [ln.strip() for ln in (text or "").splitlines()]
    lines = [ln for ln in lines if ln]
    return re.sub(r"\s+", " ", " ".join(lines)).strip()


# Phân số trong PDF Word nằm DỌC: tử / mẫu / π mỗi thứ 1 dòng
# ("7\\n2\\nπ." = 7π/2). Dựng lại thành LaTeX TRƯỚC khi dòng số lẻ bị xóa
# (lam_sach xóa dòng chỉ có số để bỏ số trang).
_RE_PS_DOC = re.compile(
    r"(?<!\d)(\d+(?:[.,]\d+)?)\s*\n\s*(\d+(?:[.,]\d+)?)\s*\n\s*π"
)


def ghep_phan_so_doc(text):
    """Số\\nmẫu\\nπ dọc -> $\\frac{số\\pi}{mẫu}$. Chỉ ghép khi đủ 3 dòng khớp."""

    def _thay(m):
        return "$\\frac{" + m.group(1) + "\\pi}{" + m.group(2) + "}$"

    return _RE_PS_DOC.sub(_thay, text or "")


def gop_buoc(buoc, toi_da_tu=30, toi_thieu_tu=6):
    """Gộp mảnh vỡ 1-2 từ (do trích PDF) thành bước đọc được.

    Chỉ gộp, không xóa từ nào nên chạy lại nhiều lần vẫn ổn định
    (bước đã dài thì giữ nguyên). GV sửa tay phần công thức còn hỏng.
    """
    items = [re.sub(r"\s+", " ", (b or "")).strip() for b in (buoc or [])]
    items = [b for b in items if b]
    if not items:
        return []
    if all(len(b.split()) >= toi_thieu_tu for b in items):
        return items  # đã đẹp, không đụng
    # Chỉ gộp khi nát thật (>= nửa số bước là mảnh 1-2 từ); còn lại giữ nguyên
    # để khỏi gộp oan bước chuẩn ngắn nhưng đúng (vd "Chọn B").
    if sum(1 for b in items if len(b.split()) <= 2) < len(items) / 2:
        return items
    steps, buf = [], ""
    for b in items:
        buf = (buf + " " + b).strip()
        if len(buf.split()) >= toi_da_tu:
            steps.append(buf)
            buf = ""
    if buf:
        steps.append(buf)
    return steps or items


_LATEX_TOKEN = {
    "π": "\\pi", "α": "\\alpha", "β": "\\beta", "γ": "\\gamma",
    "δ": "\\delta", "θ": "\\theta", "λ": "\\lambda", "μ": "\\mu",
    "σ": "\\sigma", "φ": "\\phi", "ϕ": "\\phi", "ω": "\\omega",
    "×": "\\times", "÷": "\\div", "±": "\\pm", "∓": "\\mp",
    "≤": "\\le", "≥": "\\ge", "≠": "\\ne", "≈": "\\approx",
    "≡": "\\equiv", "∈": "\\in", "∉": "\\notin", "∞": "\\infty",
    "√": "\\sqrt{}", "∪": "\\cup", "∩": "\\cap", "∅": "\\emptyset",
    "→": "\\to", "⇒": "\\Rightarrow", "⇔": "\\Leftrightarrow",
    "∠": "\\angle", "△": "\\triangle", "⊥": "\\perp", "∥": "\\parallel",
}

_RE_SO = re.compile(r"^[\d\s.,]+$")
_RE_CO_SO = re.compile(r"\d")
# Từ toán hay bị chẻ đôi ("t an", "c os20"): gộp lại khi khít nhau
_RE_TU_TOAN = re.compile(r"^(sin|cos|tan|cot|sec|csc|log|lim|ln|exp)[a-z0-9°′]*$", re.I)


def _latex_hoa(t):
    for k, v in _LATEX_TOKEN.items():
        t = t.replace(k, v)
    return t


def _giao_x(a0, a1, b0, b1):
    return max(0.0, min(a1, b1) - max(a0, b0))


def trich_dung_thu_tu(page):
    """Trích text 1 trang PDF theo ĐÚNG thứ tự đọc (dùng tọa độ span).

    - Gom span thành dòng theo y, sắp theo x (get_text() mặc định hay xáo trộn).
    - Phát hiện phân số dọc qua GẠCH NGANG trong drawings: số trên + số dưới
      có giao x với gạch -> dựng $\\frac{}{}$ ngay đúng vị trí, π lẻ kề bên
      được gộp vào tử.
    Trả về text nhiều dòng (mỗi dòng vật lý 1 dòng text).
    """
    dd = page.get_text("dict")
    spans = []
    for b in dd["blocks"]:
        if b.get("type", 0) != 0:
            continue
        for l in b.get("lines", []):
            for s in l["spans"]:
                t = (s["text"] or "").strip()
                if not t:
                    continue
                x0, y0, x1, y1 = s["bbox"]
                spans.append({"x0": x0, "y0": y0, "x1": x1, "y1": y1,
                              "size": s.get("size", 11),
                              "text": giai_ma(t), "xai": False})
    if not spans:
        return ""
    # Gạch ngang (nghi là gạch phân số)
    gach = []
    try:
        drawings = page.get_drawings()
    except Exception:
        drawings = []
    for dr in drawings:
        r = dr["rect"]
        if r.height < 2.5 < r.width and r.width > 6:
            gach.append({"x0": r.x0, "y0": r.y0, "x1": r.x1, "y1": r.y1})
    gach.sort(key=lambda g: g["y0"])  # duyệt từ trên xuống để khỏi ăn tranh span
    # Vẽ lại toàn bộ drawings để nhận diện dấu = và dấu căn (cần hình dạng)
    all_draw = []
    try:
        _dd = page.get_drawings()
    except Exception:
        _dd = []
    for dr in _dd:
        r = dr["rect"]
        all_draw.append({"x0": r.x0, "y0": r.y0, "x1": r.x1, "y1": r.y1})
    # Loại gạch là 1 nét của dấu = (gạch khác kề trên/dưới mà khoảng giữa trống
    # chữ). Phân số lồng nhau thì giữa 2 gạch luôn có tử/mẫu nên không bị loại.
    def _co_chu_giua(y_a, y_b, x0, x1):
        lo, hi = (y_a, y_b) if y_a < y_b else (y_b, y_a)
        for s in spans:
            if s.get("xai"):
                continue
            cy = (s["y0"] + s["y1"]) / 2
            if lo < cy < hi and _giao_x(s["x0"], s["x1"], x0, x1) >= 0.4 * (x1 - x0):
                return True
        return False

    gach_sach = []
    gach_bo = set()  # idx gạch là nét dấu = (cả dọc lẫn inline đều bỏ)
    for gi, g in enumerate(gach):
        ke = [h for h in gach
              if h is not g and abs(h["y0"] - g["y0"]) <= 14
              and _giao_x(h["x0"], h["x1"], g["x0"], g["x1"]) >= 0.5 * min(h["x1"] - h["x0"], g["x1"] - g["x0"])]
        if ke and not any(_co_chu_giua(g["y0"], h["y0"], g["x0"], g["x1"]) for h in ke):
            gach_bo.add(gi)  # nét của dấu =, bỏ
            continue
        gach_sach.append((gi, g))
    gach = gach_sach
    # Ghép phân số: gạch + số trên + số dưới
    fractions = []  # dict(text, x0, y0, x1, y1)
    gach_dung = set()  # idx gạch đã dựng phân số dọc
    for gi, g in gach:
        rong = max(g["x1"] - g["x0"], 1.0)
        tren = [s for s in spans if not s["xai"]
                and 0 < g["y0"] - s["y1"] <= 18
                and _giao_x(s["x0"], s["x1"], g["x0"], g["x1"]) >= 0.4 * min(s["x1"] - s["x0"], rong)]
        duoi = [s for s in spans if not s["xai"]
                and 0 < s["y0"] - g["y1"] <= 18
                and _giao_x(s["x0"], s["x1"], g["x0"], g["x1"]) >= 0.4 * min(s["x1"] - s["x0"], rong)]
        if not tren or not duoi:
            continue
        # Ưu tiên span CÓ CHỮ SỐ (kẻo vớ nhầm span π/chữ kề bên gần tâm gạch hơn)
        tren_so = [s for s in tren if _RE_CO_SO.search(s["text"])] or tren
        duoi_so = [s for s in duoi if _RE_SO.match(s["text"])] or duoi
        x_giua = (g["x0"] + g["x1"]) / 2
        a = min(tren_so, key=lambda s: (g["y0"] - s["y1"], abs((s["x0"] + s["x1"]) / 2 - x_giua)))
        b = min(duoi_so, key=lambda s: (s["y0"] - g["y1"], abs((s["x0"] + s["x1"]) / 2 - x_giua)))
        if not (_RE_CO_SO.search(a["text"]) and _RE_SO.match(b["text"])):
            continue
        # Chống ghép nhầm: tử/mẫu phải THẲNG HÀNG nhau và nằm gọn trên gạch,
        # gạch không được dài hơn hẳn chữ (kẻo ăn gạch chân tiêu đề,
        # dấu = trong hệ phương trình trình bày dọc).
        xa = (a["x0"] + a["x1"]) / 2
        xb = (b["x0"] + b["x1"]) / 2
        if abs(xa - xb) > 6:
            continue
        if not (g["x0"] - 4 <= xa <= g["x1"] + 4 and g["x0"] - 4 <= xb <= g["x1"] + 4):
            continue
        wa, wb = (a["x1"] - a["x0"]), (b["x1"] - b["x0"])
        if rong > 3.5 * min(max(wa, 1.0), max(wb, 1.0)):
            continue
        # Dấu căn VẼ BẰNG VECTOR (không có text √): nhận diện qua nét dọc
        # cao + hẹp đứng ngay đầu trái gạch (cái mũ √ thõng xuống dưới).
        # Xử lý đúng: bọc số dưới gạch vào \sqrt{} tại chỗ, rồi BỎ gạch này
        # (mẫu số thật do gạch phân số bên dưới lo).
        can = None
        for d in all_draw:
            dw, dh = (d["x1"] - d["x0"]), (d["y1"] - d["y0"])
            if (dw <= 9 < dh and dh >= 12
                    and g["x0"] - 9 <= d["x1"] <= g["x0"] + 4
                    and d["y0"] <= g["y0"] + 4 and d["y1"] >= g["y0"] + 10):
                can = d
                break
        if can is not None:
            rad_ds = [s for s in duoi if _RE_SO.match(s["text"])] or []
            if rad_ds:
                rad = min(rad_ds, key=lambda s: (s["y0"] - g["y1"]))
                rad["text"] = "\\sqrt{%s}" % rad["text"]
            continue
        tu_text = a["text"]
        # π lẻ kề bên CÙNG DÒNG tử số (vd "7"+"π" tách đôi) -> gộp vào tử.
        # Bắt buộc cùng dòng để khỏi ăn nhầm π của phân số khác. Bỏ qua khi
        # tử đã là \sqrt{} (trường hợp dấu căn ở trên).
        if can is None:
            for s in spans:
                if (not s["xai"] and s is not a and s is not b
                        and s["text"].strip() == "π"
                        and abs(s["y0"] - a["y0"]) <= 6
                        and abs((s["x0"] + s["x1"]) / 2 - (g["x0"] + g["x1"]) / 2) <= max(rong, 20)):
                    tu_text = tu_text + "π"
                    s["xai"] = True
                    break
        a["xai"] = True
        b["xai"] = True
        gach_dung.add(gi)
        fractions.append({
            "text": "$\\frac{%s}{%s}$" % (_latex_hoa(tu_text), _latex_hoa(b["text"])),
            "x0": min(a["x0"], b["x0"]), "y0": a["y0"],
            "x1": max(a["x1"], b["x1"]), "y1": b["y1"],
        })
    # Lượt 2: phân số INLINE (tử/gạch/mẫu cùng dòng, chữ nhỏ), vd cot 3π/5.
    # Dấu trừ/vd trong PDF này là TEXT (Symbol) nên gạch ngang còn lại mà
    # 2 bên là số kề sát thì gần như chắc là gạch phân số.
    for gi, g in gach:
        if gi in gach_dung or gi in gach_bo:
            continue
        rong = g["x1"] - g["x0"]
        if rong > 34:
            continue
        gy = (g["y0"] + g["y1"]) / 2
        trai = [s for s in spans if not s["xai"]
                and _RE_CO_SO.search(s["text"]) and len(s["text"]) <= 14
                and 0 <= g["x0"] - s["x1"] <= 10
                and abs((s["y0"] + s["y1"]) / 2 - gy) <= 5]
        phai = [s for s in spans if not s["xai"]
                and _RE_SO.match(s["text"])
                and 0 <= s["x0"] - g["x1"] <= 10
                and abs((s["y0"] + s["y1"]) / 2 - gy) <= 5]
        if not trai or not phai:
            continue
        L = min(trai, key=lambda s: g["x0"] - s["x1"])
        R = min(phai, key=lambda s: s["x0"] - g["x1"])
        lw, rw = (L["x1"] - L["x0"]), (R["x1"] - R["x0"])
        if rong > 3 * min(max(lw, 1.0), max(rw, 1.0)):
            continue
        L["xai"] = True
        R["xai"] = True
        fractions.append({
            "text": "$\\frac{%s}{%s}$" % (_latex_hoa(L["text"]), _latex_hoa(R["text"])),
            "x0": g["x0"], "y0": L["y0"],
            "x1": g["x1"], "y1": R["y1"],
        })
    # Gom dòng theo y (ngưỡng 5pt). Render 1 lần cuối: gộp span còn lại
    # + phân số theo x (render dần từng cái sẽ ghi đè lẫn nhau).
    con_lai = [s for s in spans if not s["xai"]]
    con_lai.sort(key=lambda s: (s["y0"], s["x0"]))
    rows, cur, ref = [], [], None
    for s in con_lai:
        if ref is None or s["y0"] - ref > 5:
            if cur:
                rows.append(cur)
            cur, ref = [s], s["y0"]
        else:
            cur.append(s)
    if cur:
        rows.append(cur)
    gan = {i: [] for i in range(len(rows))}  # idx dòng -> [(x0, text phân số)]
    chua_gan = []
    for f in fractions:
        best, best_d = None, None
        for i, r in enumerate(rows):
            y_dau = min(s["y0"] for s in r)
            d = abs(y_dau - f["y0"])
            if best_d is None or d < best_d:
                best, best_d = i, d
        if best is None:
            chua_gan.append(f["text"])
        else:
            gan[best].append((f["x0"], f))
    out = []
    for i, r in enumerate(rows):
        r.sort(key=lambda s: s["x0"])
        sizes = sorted(s.get("size", 11) for s in r)
        med_size = sizes[len(sizes) // 2] if sizes else 11
        med_y0 = sorted(s["y0"] for s in r)[len(r) // 2]
        # token trong dòng: [(x0, x1, text, y0, size)]
        toks = []
        for s in r:
            gap = s["x0"] - toks[-1][1] if toks else 99
            prev_y0 = toks[-1][3] if toks else 999
            prev_sz = toks[-1][4] if toks else 11
            # 1. Mũ trên: nhỏ hơn hẳn + nhô lên so với token NGAY TRƯỚC nó
            # (vd cos³a tách làm cos/3/a). So với token trước để số ở dòng
            # fraction-stack bên dưới không bị hút nhầm.
            if (toks and s.get("size", 11) < 0.8 * prev_sz
                    and s["y0"] < prev_y0 - 0.8 and gap < 12):
                x0, x1, t, _, _ = toks[-1]
                toks[-1] = (x0, s["x1"], t + "^{" + s["text"] + "}", prev_y0, prev_sz)
                continue
            # 2. Từ toán bị chẻ đôi khít nhau ("t an" -> "tan")
            if (toks and gap < 1.5 and len(toks[-1][2] + s["text"]) <= 8
                    and _RE_TU_TOAN.match(toks[-1][2] + s["text"])):
                x0, x1, t, _, _ = toks[-1]
                toks[-1] = (x0, s["x1"], t + s["text"], prev_y0, prev_sz)
                continue
            toks.append((s["x0"], s["x1"], s["text"], s["y0"], s.get("size", 11)))
        items = [(x0, x1, t) for x0, x1, t, _, _ in toks]
        items += [(x0, f["x1"], ("FRAC", f)) for x0, f in gan[i]]
        items.sort(key=lambda t: t[0])
        dong = []
        for x0, x1, t in items:
            if isinstance(t, tuple):  # phân số
                _, f = t
                dong.append(f["text"])
                continue
            # Bỏ dấu "." lạc (đuôi câu của phương án) nằm trong tầm phân số
            if t.strip() == "." and any(
                    abs((x0 + x1) / 2 - (f["x0"] + f["x1"]) / 2) <= 14
                    for _, f in gan[i]):
                continue
            dong.append(t)
        out.append(" ".join(dong))
    out.extend(chua_gan)
    return "\n".join(out)
