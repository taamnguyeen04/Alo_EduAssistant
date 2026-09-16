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
    return t[:500] if t else "Thầy chưa đọc được bài làm, em viết lại từng bước rõ hơn nhé."


def la_xin_goi_y(tin_nhan):
    """True khi HS nhờ hướng dẫn mà chưa nộp bước giải nào (đừng chấm sai oan)."""
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
    # Lưu attempt
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
    # Tự lên/xuống trình độ theo 5 bài gần nhất
    from .student import tu_dong_cap_nhat_trinh_do
    cu, moi = tu_dong_cap_nhat_trinh_do(sid)
    if moi != cu:
        kq["trinh_do_moi"] = {"cu": cu, "moi": moi}
    return kq, raw
