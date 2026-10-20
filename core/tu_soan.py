"""Tự soạn bài luyện khi kho thiếu — deterministic theo công thức chuẩn.

Ưu tiên 1 (accuracy): CHỈ soạn dạng có đáp án suy trực tiếp từ công thức
trong LÝ THUYẾT CHUẨN (wiki source_grounded), không dùng LLM bịa đề.
Mỗi câu tự soạn luôn gắn cho_duyet=True để GV duyệt sau, nhưng vẫn giao
ngay cho HS vì đáp án chắc chắn đúng theo công thức.
"""
import random
from . import knowledge
from . import teacher

# Các góc đặc biệt dùng cho drills (tex, diễn giải).
GOC_DAC_BIET = [
    ("\\frac{\\pi}{6}", "pi/6"),
    ("-\\frac{\\pi}{4}", "-pi/4"),
    ("\\frac{2\\pi}{3}", "2pi/3"),
    ("\\frac{\\pi}{4}", "pi/4"),
    ("\\frac{\\pi}{3}", "pi/3"),
]


def _id_moi(prefix, mon="toan11"):
    kho = knowledge.tai_bank(mon)
    for _ in range(50):
        cid = f"{prefix}-{random.randint(100, 999)}"
        if cid not in kho:
            return cid
    return f"{prefix}-{random.randint(1000, 9999)}"


def soan_sin_bang_sin_alpha(alpha_tex, bai="Bài 4. Phương trình lượng giác",
                            mon="toan11"):
    """Soạn 1 drill sin x = sin(alpha) với đáp án tổng quát chính xác.

    Công thức chuẩn: sin x = sin a <=> x = a + k2pi hoặc x = pi - a + k2pi.
    """
    cid = _id_moi("TS-B4-SIN", mon)
    return {
        "id": cid,
        "bai": bai,
        "dang": "TL",
        "dang_phan": "Phương trình sin x = m",
        "do_kho": 2,
        "de": (f"Giải phương trình $\\sin x = \\sin({alpha_tex})$. "
                "Viết nghiệm tổng quát rồi lọc các nghiệm trên đoạn $[0, 2\\pi]$."),
        "dap_an": (f"$x = {alpha_tex} + k2\\pi$ hoặc $x = \\pi - ({alpha_tex}) + k2\\pi$ "
                    "$(k \\in \\mathbb{Z})$, lọc $k$ để $x \\in [0, 2\\pi]$."),
        "buoc_giai": [
            "Áp dụng công thức: $\\sin x = \\sin a \\Leftrightarrow "
            "x = a + k2\\pi$ hoặc $x = \\pi - a + k2\\pi$ $(k \\in \\mathbb{Z})$.",
            f"Thay $a = {alpha_tex}$ được 2 họ nghiệm tổng quát.",
            "Cho $k = \\dots, -1, 0, 1, 2, \\dots$ rồi giữ lại nghiệm thuộc $[0, 2\\pi]$.",
        ],
        "loi_hay_gap": ["quên họ nghiệm thứ hai pi - a", "quên + k2pi",
                        "lọc k sai trên đoạn"],
        "chat_luong": "ok",
        "cho_duyet": True,
        "nguon": "AI tự soạn theo công thức chuẩn (GV chưa duyệt)",
    }


def bo_3_sin_sin_alpha(mon="toan11"):
    """Bộ 3 drills sin x = sin α phủ 3 tình huống: góc nhọn, góc âm, góc tù."""
    bai = "Bài 4. Phương trình lượng giác"
    return [soan_sin_bang_sin_alpha(a, bai, mon)
            for a, _ in GOC_DAC_BIET[:3]]


def co_mau_ptlg_co_ban(cau_text, lesson_id, bai=""):
    """True khi câu hỏi thuộc dạng PTLG cơ bản có mẫu soạn sẵn.

    Hiện hỗ trợ: lesson C1_B4 + nhắc tới sin (mở rộng cos/tan/cot sau).
    """
    if (lesson_id or "") != "C1_B4":
        if "phương trình lượng giác" not in (bai or "").lower():
            return False
    khoa = knowledge.tach_tu(cau_text or "")
    return "sin" in khoa


def lay_cau_tu_soan(cau_text, lesson_id, bai="", mon="toan11", n=3):
    """Trả về list câu tự soạn phù hợp (rỗng nếu chưa có mẫu)."""
    if not co_mau_ptlg_co_ban(cau_text, lesson_id, bai):
        return []
    if "sin" in knowledge.tach_tu(cau_text or ""):
        return bo_3_sin_sin_alpha(mon)[:n]
    return []


def luu_cho_duyet(ds_cau, bai, mon="toan11"):
    """Lưu câu tự soạn vào bank với cờ cho_duyet để GV duyệt sau.

    Trả về list id đã lưu (bỏ qua câu trùng nội dung đã có).
    """
    if not ds_cau:
        return []
    kho_all = teacher.doc_bank(bai, mon)
    da_co_de = {(c.get("de") or "").strip() for c in kho_all}
    moi = []
    for c in ds_cau:
        if (c.get("de") or "").strip() in da_co_de:
            continue
        kho_all.append({**c, "cho_duyet": True})
        da_co_de.add((c.get("de") or "").strip())
        moi.append(c["id"])
    if moi:
        teacher.luu_bank(bai, kho_all, mon)
    return moi
