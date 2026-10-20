"""Bài thích ứng: tìm kho GV trước, thiếu mới sinh bù."""
import json
import os
import random
from . import store
from . import llm
from . import prompts
from . import teacher
from . import bank_view

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


def cau_tn_dung_duoc(c):
    """True khi câu TN đủ chuẩn để giao cho HS làm trắc nghiệm.

    Điều kiện: dang TN, đạt chuẩn, đề tách được đủ 4 phương án A-D,
    đáp án ghi rõ phương án (dạng 'Chọn X'), không phải placeholder
    '[CẦN ĐỐI CHIẾU]'. Câu không đạt thì để GV sửa, không giao cho HS.
    """
    if not isinstance(c, dict):
        return False
    if c.get("dang") != "TN":
        return False
    if c.get("cho_duyet") or c.get("chat_luong") != "ok":
        return False
    if (c.get("de") or "").strip().startswith("[C"):
        return False
    _, pas = bank_view.tach_phuong_an(c.get("de", ""))
    if len(pas) < 4:
        return False
    return bool(bank_view.dap_an_dung(c.get("dap_an", "")))


def lam_giau_tn(c):
    """Gắn trường đã tách (than_de, phuong_an, dung) để UI render + chấm local."""
    than, pas = bank_view.tach_phuong_an(c.get("de", ""))
    return {**c, "than_de": bank_view.hien_thi(than),
            "phuong_an": [(nhan, bank_view.hien_thi(nd)) for nhan, nd in pas],
            "dung": bank_view.dap_an_dung(c.get("dap_an", ""))}


def cau_tl_dung_duoc(c):
    """True khi câu TỰ LUẬN đủ chuẩn để giao cho HS (làm ra vở + chụp chấm).

    Điều kiện: dang TL, đạt chuẩn (chat_luong ok, không cho_duyet),
    có đề thật (không placeholder '[CẦN ĐỐI CHIẾU]'). Không yêu cầu
    4 phương án như TN.
    """
    if not isinstance(c, dict):
        return False
    if c.get("dang") != "TL":
        return False
    if c.get("cho_duyet") or c.get("chat_luong") != "ok":
        return False
    if (c.get("de") or "").strip().startswith("[C"):
        return False
    return bool((c.get("de") or "").strip())


def ds_bai_tl(mon="toan11"):
    """Các Bài có câu TỰ LUẬN dùng được (kèm số câu) để HS chọn."""
    from . import knowledge
    dem = {}
    for c in knowledge.tai_bank(mon).values():
        if cau_tl_dung_duoc(c):
            b = c.get("bai", "")
            dem[b] = dem.get(b, 0) + 1
    return dem


def ra_bai_tl(sid, bai, do_kho=1, mon="toan11", loai_tru=None, cau_hien_tai_id=None):
    """Phát 1 câu TỰ LUẬN dùng được cho HS (làm ra vở, chụp ảnh nộp).

    Lọc: đúng Bài + đúng mức, chống lặp như bản TN. Không sinh AI bừa.
    """
    kho_all = teacher.doc_bank(bai, mon)
    kho = [c for c in kho_all if cau_tl_dung_duoc(c)]
    da_gap = _da_gap(sid) | set(loai_tru or set())
    if cau_hien_tai_id:
        da_gap.add(cau_hien_tai_id)
    try:
        dk = max(1, min(3, int(do_kho)))
    except (TypeError, ValueError):
        dk = 1

    def _dk(c):
        try:
            return max(1, min(3, int(c.get("do_kho", 2))))
        except (TypeError, ValueError):
            return 2

    moi_cung_muc = [c for c in kho if _dk(c) == dk and c.get("id") not in da_gap]
    if moi_cung_muc:
        return {**random.choice(moi_cung_muc), "nguon": "kho GV"}
    moi = [c for c in kho if c.get("id") not in da_gap]
    if moi:
        gan_nhat = min(abs(_dk(c) - dk) for c in moi)
        return {**random.choice([c for c in moi if abs(_dk(c) - dk) == gan_nhat]),
                "nguon": "kho GV (mức gần nhất)"}
    vong = [c for c in kho if c.get("id") != cau_hien_tai_id] or kho
    if vong:
        return {**random.choice(vong), "nguon": "kho GV (ôn lại)"}
    raise ValueError(f"Bài «{bai}» chưa có câu tự luận dùng được — nhờ GV bổ sung ở Kho đề.")


def ds_bai_tn(mon="toan11"):
    """Các Bài có câu TN dùng được (kèm số câu) để HS chọn bài giảng."""
    from . import knowledge
    dem = {}
    for c in knowledge.tai_bank(mon).values():
        if cau_tn_dung_duoc(c):
            b = c.get("bai", "")
            dem[b] = dem.get(b, 0) + 1
    return dem


def ra_bai_tn(sid, bai, do_kho=1, mon="toan11", loai_tru=None, cau_hien_tai_id=None):
    """Phát 1 câu TRẮC NGHIỆM dùng được cho HS.

    Lọc: đúng Bài + đúng mức (1 Nhận biết / 2 Thông hiểu / 3 Vận dụng),
    chống lặp (attempts + session + câu hiện tại). Hết câu mới đúng mức
    thì lấy mức gần nhất cùng Bài; hết Bài thì raise để UI báo GV bổ sung.
    Không sinh AI bừa để khỏi bịa đáp án.
    """
    kho_all = teacher.doc_bank(bai, mon)
    kho = [c for c in kho_all if cau_tn_dung_duoc(c)]
    da_gap = _da_gap(sid) | set(loai_tru or set())
    if cau_hien_tai_id:
        da_gap.add(cau_hien_tai_id)
    try:
        dk = max(1, min(3, int(do_kho)))
    except (TypeError, ValueError):
        dk = 1

    def _dk(c):
        try:
            return max(1, min(3, int(c.get("do_kho", 2))))
        except (TypeError, ValueError):
            return 2

    moi_cung_muc = [c for c in kho if _dk(c) == dk and c.get("id") not in da_gap]
    if moi_cung_muc:
        return {**lam_giau_tn(random.choice(moi_cung_muc)), "nguon": "kho GV"}
    moi = [c for c in kho if c.get("id") not in da_gap]
    if moi:
        gan_nhat = min(abs(_dk(c) - dk) for c in moi)
        return {**lam_giau_tn(random.choice([c for c in moi if abs(_dk(c) - dk) == gan_nhat])),
                "nguon": "kho GV (mức gần nhất)"}
    vong = [c for c in kho if c.get("id") != cau_hien_tai_id] or kho
    if vong:
        return {**lam_giau_tn(random.choice(vong)), "nguon": "kho GV (ôn lại)"}
    raise ValueError(f"Bài «{bai}» chưa có câu trắc nghiệm dùng được — nhờ GV bổ sung ở Kho đề.")


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
    # Hết kho -> ƯU TIÊN 1 accuracy: KHÔNG giao câu AI sinh chưa duyệt cho HS.
    # Sinh nháp để GV duyệt sau, rồi báo HS nhờ GV bổ sung (tránh bịa đáp án).
    raw = llm.chat_pro([
        {"role": "system", "content": prompts.prompt_ra_de(mon)},
        {"role": "user", "content": f"Ra 1 bài thuộc: {bai}, độ khó {do_kho}/3."},
    ], timeout=90)
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
    # Lưu vào kho để GV duyệt sau, nhưng KHÔNG giao ngay để giữ chính xác.
    kho_all.append({**cau, "cho_duyet": True})
    teacher.luu_bank(bai, kho_all, mon)
    raise ValueError(
        f"Bài «{bai}» đã hết câu duyệt — AI đã soạn nháp 1 câu chờ GV duyệt, "
        "bạn ôn câu cũ hoặc nhờ GV bổ sung nhé.")


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
