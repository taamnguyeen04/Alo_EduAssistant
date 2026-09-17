"""Bài thích ứng: tìm kho GV trước, thiếu mới sinh bù."""
import json
import os
import random
from . import store
from . import llm
from . import prompts
from . import teacher

ATTEMPT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "attempts")


def _da_gap(sid):
    """Set id mọi câu sid đã từng mở/chấm (đúng + sai) để tránh giao lặp."""
    # Quét file attempts vì attempt là bằng chứng duy nhất câu đã giao.
    gap = set()
    if not os.path.isdir(ATTEMPT_DIR):
        return gap
    for ten in os.listdir(ATTEMPT_DIR):
        if ten.startswith(sid + "_") and ten.endswith(".json"):
            d = store.doc_json(os.path.join(ATTEMPT_DIR, ten), {})
            cid = d.get("cau_id", "")
            if cid:
                gap.add(cid)
    return gap


def _da_lam_dung(sid):
    """Trả về set id câu đã làm đúng để tránh lặp."""
    done = set()
    if not os.path.isdir(ATTEMPT_DIR):
        return done
    for ten in os.listdir(ATTEMPT_DIR):
        if ten.startswith(sid + "_") and ten.endswith(".json"):
            d = store.doc_json(os.path.join(ATTEMPT_DIR, ten), {})
            if d.get("dung_het"):
                done.add(d.get("cau_id", ""))
    return done


def ra_bai(sid, bai, do_kho=2, mon="toan11", loai_tru=None, cau_hien_tai_id=None):
    """Ưu tiên kho GV. Trả về dict {id, de, dap_an, buoc_giai, nguon}.

    Chống lặp: loại mọi câu sid đã gặp (file attempts) + câu đã hiện trong
    session (loai_tru) + câu đang làm. Hết câu mới thì xoay vòng ôn lại
    nhưng vẫn tránh lặp liên tiếp câu hiện tại.
    """
    kho_all = teacher.doc_bank(bai, mon)
    # App không giao câu chưa đạt chuẩn cho HS (AGENTS.md §5).
    kho = [c for c in kho_all
           if not c.get("cho_duyet") and c.get("chat_luong", "ok") == "ok"]
    if not kho:
        # Bài chưa có câu đạt chuẩn thì nới ra câu thường (vẫn trừ câu chờ duyệt).
        kho = [c for c in kho_all if not c.get("cho_duyet")]
    da_gap = _da_gap(sid) | set(loai_tru or set())
    if cau_hien_tai_id:
        da_gap.add(cau_hien_tai_id)
    try:
        dk = int(do_kho)
    except (TypeError, ValueError):
        dk = 2
    def _dk(c):
        try:
            return int(c.get("do_kho", 2))
        except (TypeError, ValueError):
            return 2

    moi_cung_do_kho = [c for c in kho if _dk(c) == dk and c.get("id") not in da_gap]
    if moi_cung_do_kho:
        # Ưu tiên 1: câu mới đúng độ khó đang cần.
        return {**random.choice(moi_cung_do_kho), "nguon": "kho GV"}
    # Nới lỏng: cùng bài, độ khó gần nhất, chưa gặp
    moi = [c for c in kho if c.get("id") not in da_gap]
    if moi:
        def _lech(c):
            try:
                return abs(int(c.get("do_kho", 2)) - dk)
            except (TypeError, ValueError):
                return 9
        gan_nhat = min(_lech(c) for c in moi)
        return {**random.choice([c for c in moi if _lech(c) == gan_nhat]), "nguon": "kho GV"}
    # Hết câu mới -> xoay vòng ôn lại, tránh lặp liên tiếp câu hiện tại
    vong = [c for c in kho if c.get("id") != cau_hien_tai_id] or kho
    if vong:
        return {**random.choice(vong), "nguon": "kho GV (ôn lại)"}
    # Hết kho -> sinh bù, gắn cờ chờ duyệt
    raw = llm.chat_pro([
        {"role": "system", "content": prompts.prompt_ra_de(mon)},
        {"role": "user", "content": f"Ra 1 bài thuộc: {bai}, độ khó {do_kho}/3."},
    ])
    from .student import tach_json_cuoi
    _, data = tach_json_cuoi(raw)
    cau = {
        "id": f"AI-{abs(hash((bai, do_kho, raw))) % 100000}",
        "bai": bai,
        "do_kho": do_kho,
        "de": data.get("de", raw[:300]) if isinstance(data, dict) else raw[:300],
        "dap_an": data.get("dap_an", "") if isinstance(data, dict) else "",
        "buoc_giai": data.get("buoc_giai", []) if isinstance(data, dict) else [],
        "loi_hay_gap": data.get("loi_hay_gap", []) if isinstance(data, dict) else [],
    }
    # Lưu vào kho để GV duyệt sau
    kho_all.append({**cau, "cho_duyet": True})
    teacher.luu_bank(bai, kho_all, mon)
    return {**cau, "nguon": "AI sinh - chờ duyệt"}


def lay_cau_theo_id(sid, cid, mon="toan11"):
    """Lấy đúng 1 câu theo mã ID (nút 'Làm câu này' từ chat). Bỏ qua câu đã đúng để khỏi lặp."""
    from . import knowledge
    c = knowledge.tim_cau_theo_id(cid, mon)
    if not c or c.get("chat_luong") != "ok":
        return None
    if c["id"] in _da_lam_dung(sid):
        return {**c, "nguon": "kho GV (đã làm đúng trước đây)"}
    return {**c, "nguon": "kho GV"}


def doi_kho_hien_tai(sid, bai, do_kho, lam_dung):
    # Thích ứng độ khó: đúng +1 bậc, sai −1 bậc, kẹp trong 1–3.
    if lam_dung:
        return min(3, int(do_kho) + 1)
    return max(1, int(do_kho) - 1)
