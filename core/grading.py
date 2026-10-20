"""Chấm từng bước giải của HS."""
import json
import os
import re
from . import store
from . import llm
from . import prompts
from .student import tach_json_cuoi

ATTEMPT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "attempts")

_JSON_KEYS = ("dung_sai_tung_buoc", "sai_o_buoc", "goi_y_sua", "diem_yeu_moi")

# Tin nhắn xin gợi ý: có lời nhờ + KHÔNG có nội dung toán (số, =, toán tử, LaTeX)
_RE_NHO = re.compile(r"không biết|chưa biết|chưa hiểu|không hiểu|hướng dẫn|gợi ý|giúp|chỉ (cho |em |tôi |mình )?|bó tay|chịu|bắt đầu từ đâu|làm sao|như thế nào|hint", re.I)
_RE_TOAN = re.compile(r"[0-9=+\-*/^√π]|\\[a-z]+|\$|sin|cos|tan|log|lim|dx|dy")


def tach_json_cham(raw):
    """Tách JSON chấm bài: có fence thì dùng chung, không thì moi object chứa key chấm."""
    # Thử đường chuẩn trước; AI hay quên fence nên có đường moi regex dự phòng.
    tra_loi, data = tach_json_cuoi(raw)
    if isinstance(data, dict) and "dung_sai_tung_buoc" in data:
        return tra_loi, data
    m = re.search(r"\{[^{}]*\"dung_sai_tung_buoc\"[^{}]*\}", raw, re.S)
    if m:
        try:
            d = json.loads(m.group(0))
            phan_chat = raw[:m.start()].rstrip() or tra_loi
            return phan_chat, d
        except Exception:
            pass
    return tra_loi, {}


def lam_sach_goi_y(raw):
    """Xóa sạch mọi mảnh JSON rò rỉ để không bao giờ hiện lên màn hình."""
    t = re.sub(r"```json.*?```", " ", raw, flags=re.S)
    t = re.sub(r"```.*?```", " ", t, flags=re.S)
    t = re.sub(r"\{[^{}]*\"dung_sai_tung_buoc\"[^{}]*\}", " ", t)
    t = re.sub(r"\"(?:%s)\"\s*:\s*(?:\[[^\]]*\]|\"[^\"]*\"|[^,}\]]+)" % "|".join(_JSON_KEYS), " ", t)
    t = re.sub(r"[{}\[\]\"]", " ", t)
    t = " ".join(t.split())
    return t[:500] if t else "Mình chưa đọc được bài làm, bạn viết lại từng bước rõ hơn nhé."


def la_xin_goi_y(tin_nhan):
    """True khi HS nhờ hướng dẫn mà chưa nộp bước giải nào (đừng chấm sai oan)."""
    # Tin dài quá 300 ký tự coi như bài làm thật, không phải lời xin gợi ý.
    t = (tin_nhan or "").strip()
    if not t or len(t) > 300:
        return False
    return bool(_RE_NHO.search(t)) and not _RE_TOAN.search(t)


def goi_y_buoc_dau(sid, cau, mon="toan11"):
    """Chế độ gợi ý: hỏi Socrates đúng bước 1, không chấm, không lưu attempt rớt."""
    buoc1 = (cau.get("buoc_giai") or [""])[0]
    raw = llm.chat_pro([
        {"role": "system", "content": prompts.prompt_goi_y(mon)},
        {"role": "user", "content": (
            f"Đề: {cau.get('de')}\nBước chuẩn đầu tiên (MẬT, đừng đọc nguyên văn): {buoc1}\n"
            f"Lỗi hay gặp: {cau.get('loi_hay_gap')}\n"
            f"HS nhắn: em không biết làm, nhờ hướng dẫn. Hãy hỏi gợi mở đúng bước 1."
        )},
    ])
    tra_loi, _ = tach_json_cuoi(raw)
    return {"che_do": "goi_y", "goi_y": lam_sach_goi_y(raw) if not tra_loi.strip() else tra_loi.strip()}


def cham_tung_buoc(sid, cau, cac_buoc_hs, mon="toan11"):
    """cau: dict từ exercises.ra_bai. cac_buoc_hs: list[str] mỗi bước 1 ô.
    Trả về dict {dung_sai_tung_buoc, sai_o_buoc, goi_y_sua, diem_yeu_moi, dung_het} và lưu attempt."""
    buoc_txt = "\n".join(f"Bước {i+1}: {b}" for i, b in enumerate(cac_buoc_hs))
    hs = store.doc_hs(sid)
    raw = llm.chat_pro([
        {"role": "system", "content": prompts.prompt_cham(mon)},
        {"role": "user", "content": (
            f"Đề: {cau.get('de')}\nĐáp án: {cau.get('dap_an')}\n"
            f"Bước chuẩn: {cau.get('buoc_giai')}\n"
            f"Lỗi hay gặp (đối chiếu): {cau.get('loi_hay_gap')}\n"
            f"Điểm yếu đã biết của HS (đừng ghi trùng): {hs.get('weaknesses')}\n"
            f"Bài làm HS:\n{buoc_txt}\nHãy chấm từng bước."
        )},
    ])
    _, data = tach_json_cham(raw)
    if not isinstance(data, dict):
        data = {}
    goi_y = data.get("goi_y_sua", "")
    if not isinstance(goi_y, str) or not goi_y.strip() or any(k in goi_y for k in _JSON_KEYS):
        goi_y = lam_sach_goi_y(raw)
    ds_dung = data.get("dung_sai_tung_buoc", [])
    if not isinstance(ds_dung, list):
        ds_dung = []
    ds_dung = [bool(x) for x in ds_dung]
    yeu_moi = data.get("diem_yeu_moi", [])
    if not isinstance(yeu_moi, list):
        yeu_moi = []
    yeu_moi = [str(w).strip() for w in yeu_moi if str(w).strip()]
    kq = {
        "che_do": "cham",
        "dung_sai_tung_buoc": ds_dung,
        "sai_o_buoc": data.get("sai_o_buoc", None),
        "goi_y_sua": goi_y,
        "diem_yeu_moi": yeu_moi,
    }
    kq["dung_het"] = bool(kq["dung_sai_tung_buoc"]) and all(kq["dung_sai_tung_buoc"])
    # Lưu attempt ngay để làm bằng chứng báo cáo + chống giao lặp về sau.
    os.makedirs(ATTEMPT_DIR, exist_ok=True)
    store.ghi_json(os.path.join(ATTEMPT_DIR, f"{sid}_{cau.get('id')}.json"), {
        "sid": sid, "cau_id": cau.get("id"), "bai": cau.get("bai"),
        "de": cau.get("de"), "cac_buoc": cac_buoc_hs, **kq,
    })
    # Cập nhật điểm yếu HS
    if kq["diem_yeu_moi"]:
        hs = store.doc_hs(sid)
        da_co = {w.lower() for w in hs.get("weaknesses", [])}
        for w in kq["diem_yeu_moi"]:
            w = (w or "").strip()
            if w and w.lower() not in da_co:
                hs["weaknesses"].append(w)
                da_co.add(w.lower())
        store.luu_hs(sid, hs)
    # Điểm đệm trình độ: đúng +1 / sai -1, đủ ±5 ròng mới đổi bậc
    from .student import tu_dong_cap_nhat_trinh_do
    cu, moi = tu_dong_cap_nhat_trinh_do(sid, kq["dung_het"], mon)
    if moi != cu:
        kq["trinh_do_moi"] = {"cu": cu, "moi": moi}
    return kq, raw


# ── Luyện tự luận: chấm qua ảnh chụp vở ─────────────────────────────

def _luu_attempt_tl(sid, cau, dung_het, loai="tu_luan_anh"):
    """Lưu attempt tự luận (bằng chứng chống giao lặp + báo cáo)."""
    os.makedirs(ATTEMPT_DIR, exist_ok=True)
    store.ghi_json(os.path.join(ATTEMPT_DIR, f"{sid}_{cau.get('id')}.json"), {
        "sid": sid, "cau_id": cau.get("id"), "bai": cau.get("bai"),
        "de": cau.get("de"), "dang": "TL", "loai": loai,
        "dung": bool(dung_het), "dung_het": bool(dung_het),
        "do_kho": cau.get("do_kho", 1),
    })


def cham_tu_luan_qua_anh(sid, cau, hinh_data_urls, mon="toan11"):
    """Chấm bài TỰ LUẬN qua ảnh chụp vở HS (tối đa 3 ảnh).

    Gửi đề + đáp án + bước chuẩn (MẬT) + ảnh bài làm cho LLM vision
    (PRO), chấm từng bước theo prompt_cham, lưu attempt + điểm yếu.
    Trả về dict {dung_sai_tung_buoc, sai_o_buoc, goi_y_sua, diem_yeu_moi,
    dung_het, tra_loi} + raw.
    """
    from .student import them_diem_yeu
    hs = store.doc_hs(sid)
    hinh_list = [u for u in (hinh_data_urls or []) if u][:3]
    if not hinh_list:
        raise ValueError("Bạn chụp ảnh bài giải trong vở rồi tải lên nhé.")
    parts = [{
        "type": "text",
        "text": (
            f"Đề: {cau.get('de')}\nĐáp án: {cau.get('dap_an')}\n"
            f"Bước chuẩn: {cau.get('buoc_giai')}\n"
            f"Lỗi hay gặp (đối chiếu): {cau.get('loi_hay_gap')}\n"
            f"Điểm yếu đã biết của HS (đừng ghi trùng): {hs.get('weaknesses')}\n"
            "Trên là đề + đáp án chuẩn (MẬT). Dưới là ảnh bài làm trong vở "
            "của HS. Hãy đọc chữ trong ảnh rồi chấm từng bước."
        ),
    }]
    for url in hinh_list:
        parts.append({"type": "image_url", "image_url": {"url": url}})
    raw = llm.chat_pro([
        {"role": "system", "content": prompts.prompt_cham(mon)},
        {"role": "user", "content": parts},
    ])
    tra_loi, data = tach_json_cham(raw)
    if not isinstance(data, dict):
        data = {}
    goi_y = data.get("goi_y_sua", "")
    if not isinstance(goi_y, str) or not goi_y.strip() or any(k in goi_y for k in _JSON_KEYS):
        goi_y = lam_sach_goi_y(raw)
    ds_dung = data.get("dung_sai_tung_buoc", [])
    if not isinstance(ds_dung, list):
        ds_dung = []
    ds_dung = [bool(x) for x in ds_dung]
    yeu_moi = [str(w).strip() for w in (data.get("diem_yeu_moi", []) or [])
               if str(w).strip()]
    dung_het = bool(ds_dung) and all(ds_dung)
    _luu_attempt_tl(sid, cau, dung_het)
    diem_yeu_da_luu = them_diem_yeu(sid, yeu_moi) if yeu_moi else []
    return {"che_do": "cham_tl_anh", "dung_sai_tung_buoc": ds_dung,
            "sai_o_buoc": data.get("sai_o_buoc", None),
            "goi_y_sua": goi_y or tra_loi.strip(),
            "diem_yeu_moi": diem_yeu_da_luu or yeu_moi,
            "dung_het": dung_het, "tra_loi": tra_loi.strip()}, raw


# ── Luyện trắc nghiệm A-E ─────────────────────────────────────────────

def _luu_attempt_tn(sid, cau, chon, dung, loai):
    """Lưu attempt trắc nghiệm (bằng chứng chống giao lặp + báo cáo)."""
    os.makedirs(ATTEMPT_DIR, exist_ok=True)
    store.ghi_json(os.path.join(ATTEMPT_DIR, f"{sid}_{cau.get('id')}.json"), {
        "sid": sid, "cau_id": cau.get("id"), "bai": cau.get("bai"),
        "de": cau.get("de"), "dang": "TN", "loai": loai,
        "chon": chon, "dung": bool(dung),
        "dung_het": bool(dung), "do_kho": cau.get("do_kho", 1),
    })


def cham_trac_nghiem(sid, cau, chon, mon="toan11"):
    """Chấm 1 câu TN đã làm giàu (exercises.lam_giau_tn). Chấm local tuyệt đối.

    chon: 'A'..'D'. Trả về dict {dung, dap_an_dung, giai_thich, diem_yeu_moi,
    trinh_do_moi?} và lưu attempt + điểm yếu + trình độ per-Bài.
    """
    from .student import cap_nhat_trinh_do_bai, them_diem_yeu, ten_muc_do
    chon = (chon or "").strip().upper()
    dap_dung = (cau.get("dung") or "").strip().upper()
    dung = bool(chon) and chon == dap_dung
    loai = "binh_thuong"
    _luu_attempt_tn(sid, cau, chon, dung, loai)
    diem_yeu_moi = []
    if not dung:
        # Điểm yếu = lỗi hay gặp đã curated của chính câu này (không tốn LLM,
        # không bịa). Kho TN hiện chưa ghi lỗi/dạng cho câu parse được nên
        # fallback theo Bài+mức — vẫn gom nhóm được ở báo cáo GV.
        yeu = list(cau.get("loi_hay_gap") or [])
        if not yeu:
            if cau.get("dang_phan"):
                yeu = [f"sai dạng {cau.get('dang_phan')} ({ten_muc_do(cau.get('do_kho', 2))})"]
            else:
                yeu = [f"làm sai mức {ten_muc_do(cau.get('do_kho', 1))} — {cau.get('bai', '')}"]
        diem_yeu_moi = them_diem_yeu(sid, yeu)
    cu, moi = cap_nhat_trinh_do_bai(sid, cau.get("bai"), cau.get("do_kho", 1),
                                    "dung" if dung else "sai")
    kq = {"che_do": "cham_tn", "dung": dung, "chon": chon,
          "dap_an_dung": dap_dung, "diem_yeu_moi": diem_yeu_moi}
    if moi != cu:
        kq["trinh_do_moi"] = {"cu": ten_muc_do(cu), "moi": ten_muc_do(moi),
                              "level_cu": cu, "level_moi": moi}
    return kq


def sinh_cau_dan_dat(sid, cau, mon="toan11"):
    """Sinh 2-3 câu TN con dẫn dắt khi HS chọn 'Em không biết'.

    Trả về (ds_cau_con, diem_yeu_phat_hien). Mỗi câu con:
    {de, phuong_an[4], dap_an A-D, giai_thich}. LLM hỏng thì fallback
    dùng bước chuẩn có sẵn để luồng không bao giờ kẹt.
    """
    from .student import tach_json_cuoi, them_diem_yeu
    hs = store.doc_hs(sid)
    try:
        raw = llm.chat_pro([
            {"role": "system", "content": prompts.prompt_dan_dat_tn(mon)},
            {"role": "user", "content": (
                f"Đề gốc: {cau.get('de')}\nĐáp án đúng (MẬT): {cau.get('dung')}\n"
                f"Bước chuẩn (MẬT): {cau.get('buoc_giai')}\n"
                f"Lỗi hay gặp: {cau.get('loi_hay_gap')}\n"
                f"Điểm yếu đã biết của HS (đừng ghi trùng): {hs.get('weaknesses')}\n"
                f"Hãy ra câu con dẫn dắt."
            )},
        ])
        _, data = tach_json_cuoi(raw)
        cons = data.get("cau_con", []) if isinstance(data, dict) else []
        yeu = data.get("diem_yeu", []) if isinstance(data, dict) else []
        hop = []
        for cc in cons:
            if not isinstance(cc, dict):
                continue
            pa = cc.get("phuong_an") or []
            da = str(cc.get("dap_an", "")).strip().upper()
            if len(pa) == 4 and da in ("A", "B", "C", "D") and str(cc.get("de", "")).strip():
                hop.append({"de": str(cc["de"]).strip(),
                            "phuong_an": [str(x) for x in pa],
                            "dap_an": da,
                            "giai_thich": str(cc.get("giai_thich", "") or "").strip()})
            if len(hop) >= 3:
                break
        if hop:
            return hop, them_diem_yeu(sid, yeu)
    except Exception:
        pass
    # Fallback không LLM: mỗi bước chuẩn thành 1 mốc gợi mở đọc-hiểu.
    buocs = [str(b or "").strip() for b in (cau.get("buoc_giai") or []) if str(b or "").strip()]
    hop = [{"de": f"Bước dẫn dắt {i + 1}: {b}",
            "phuong_an": ["Đã hiểu bước này", "Chưa rõ bước này",
                          "Cần ví dụ thêm", "Bỏ qua bước này"],
            "dap_an": "A", "giai_thich": b} for i, b in enumerate(buocs[:3])]
    if not hop:
        hop = [{"de": "Bạn còn nhớ kiến thức nền của bài này không?",
                "phuong_an": ["Nhớ rõ", "Nhớ mang máng", "Quên gần hết", "Chưa học bao giờ"],
                "dap_an": "A", "giai_thich": ""}]
    from .student import ten_muc_do as _ten_muc
    return hop, them_diem_yeu(sid, list(cau.get("loi_hay_gap") or [])
                              or [f"cần dẫn dắt mức {_ten_muc(cau.get('do_kho', 1))} — {cau.get('bai', '')}"])


def cham_lam_lai(sid, cau, chon, diem_yeu_con=None, mon="toan11"):
    """Chấm lần chọn lại duy nhất sau dẫn dắt. Đúng bù nhẹ, sai không trừ thêm."""
    from .student import cap_nhat_trinh_do_bai, them_diem_yeu
    chon = (chon or "").strip().upper()
    dap_dung = (cau.get("dung") or "").strip().upper()
    dung = bool(chon) and chon == dap_dung
    _luu_attempt_tn(sid, cau, chon, dung, "lam_lai")
    moi_them = them_diem_yeu(sid, diem_yeu_con)
    cu, moi = cap_nhat_trinh_do_bai(sid, cau.get("bai"), cau.get("do_kho", 1),
                                    "lam_lai_dung" if dung else "lam_lai_sai")
    from .student import ten_muc_do
    kq = {"che_do": "lam_lai", "dung": dung, "chon": chon,
          "dap_an_dung": dap_dung, "diem_yeu_moi": moi_them}
    if moi != cu:
        kq["trinh_do_moi"] = {"cu": ten_muc_do(cu), "moi": ten_muc_do(moi),
                              "level_cu": cu, "level_moi": moi}
    return kq


def ghi_nhan_khong_biet(sid, cau, mon="toan11"):
    """Ghi attempt 'không biết' + trừ điểm đệm nhẹ (chưa chấm đúng/sai)."""
    from .student import cap_nhat_trinh_do_bai
    _luu_attempt_tn(sid, cau, "E", False, "khong_biet")
    return cap_nhat_trinh_do_bai(sid, cau.get("bai"), cau.get("do_kho", 1), "khong_biet")
