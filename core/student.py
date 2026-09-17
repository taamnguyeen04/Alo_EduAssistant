"""Logic HS: chat Socrates + tách JSON + lưu hồ sơ (có nối kho bank/wiki)."""
import json
import re
from . import store
from . import subjects
from . import llm
from . import prompts
from . import curriculum
from . import knowledge
from . import conversations

TRINH_DO = ["yếu", "trung bình", "khá", "giỏi"]
DIEM_LEN_TRINH = 5    # đúng ròng +5 -> lên 1 bậc
DIEM_XUONG_TRINH = -5  # sai ròng -5 -> xuống 1 bậc


def tu_dong_cap_nhat_trinh_do(sid, dung_het):
    """Điểm đệm trình độ: mỗi bài chấm xong đúng +1, sai -1 (bù trừ lẫn nhau).
    Chạm +5 (ròng) -> lên 1 bậc, chạm -5 (ròng) -> xuống 1 bậc, rồi reset về 0.
    Đúng/sai xen kẽ thì điểm quanh quẩn gần 0 nên bậc ổn định, không nhảy liên tục.
    Trả về (cu, moi); bằng nhau = chưa đổi bậc."""
    hs = store.doc_hs(sid)
    cu = hs.get("trinh_do_toan", "trung bình")
    if cu not in TRINH_DO:
        cu = "trung bình"
    try:
        diem = int(hs.get("diem_trinh_do", 0) or 0)
    except (TypeError, ValueError):
        diem = 0
    diem += 1 if dung_het else -1
    idx = TRINH_DO.index(cu)
    moi = cu
    if diem >= DIEM_LEN_TRINH and idx < len(TRINH_DO) - 1:
        moi = TRINH_DO[idx + 1]
        diem = 0
    elif diem <= DIEM_XUONG_TRINH and idx > 0:
        moi = TRINH_DO[idx - 1]
        diem = 0
    diem = max(DIEM_XUONG_TRINH, min(DIEM_LEN_TRINH, diem))
    hs["diem_trinh_do"] = diem
    if moi != cu:
        hs["trinh_do_toan"] = moi
    store.luu_hs(sid, hs)
    return cu, moi


def ghi_nhan_video(sid, link, tu_dong=False, nguong_tu_dong=3):
    """Đánh dấu đã xem (tay) hoặc đếm lượt gợi ý (tự động sau N lần).
    Trả về True nếu video vừa vào danh sách đã xem."""
    if not link:
        return False
    hs = store.doc_hs(sid)
    if link in hs.get("video_da_xem", []):
        return False
    if not tu_dong:
        hs.setdefault("video_da_xem", []).append(link)
        store.luu_hs(sid, hs)
        return True
    dem = hs.get("video_goi_y_count", {})
    dem[link] = int(dem.get(link, 0)) + 1
    hs["video_goi_y_count"] = dem
    if dem[link] >= nguong_tu_dong:
        hs.setdefault("video_da_xem", []).append(link)
        store.luu_hs(sid, hs)
        return True
    store.luu_hs(sid, hs)
    return False


def tach_json_cuoi(raw):
    """Tách (phần chat, dict JSON cuối). Không có JSON -> ({}, raw)."""
    if not raw:
        return "", {}
    if not isinstance(raw, str):
        raw = str(raw)
    if "```json" not in raw:
        return raw, {}
    try:
        tra_loi = raw[: raw.rfind("```json")].rstrip()
        json_str = raw.split("```json", 1)[1].split("```", 1)[0]
        return tra_loi, json.loads(json_str)
    except Exception:
        return raw, {}


def tach_diem_yeu(raw):
    tra_loi, data = tach_json_cuoi(raw)
    return tra_loi, data.get("weaknesses", []) if isinstance(data, dict) else []


_MAU_CHU_TRUNG = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")

# Thuật ngữ toán tiếng Trung hay bị DeepSeek/Qwen nhả lẫn -> nghĩa tiếng Việt
TRUNG_VIET = {
    "奇函数": "hàm số lẻ",
    "偶函数": "hàm số chẵn",
    "定义域": "tập xác định",
    "值域": "tập giá trị",
    "正弦": "sin",
    "余弦": "cos",
    "正切": "tan",
    "周期": "chu kỳ",
    "对称": "đối xứng",
    "函数": "hàm số",
    "单调": "đơn điệu",
    "递增": "đồng biến",
    "递减": "nghịch biến",
    "奇": "lẻ",
    "偶": "chẵn",
}


def co_chu_trung(text):
    """True nếu còn chữ Hán (CJK) trong câu trả lời."""
    return bool(text and _MAU_CHU_TRUNG.search(text))


def sua_chu_trung(text):
    """Thay thuật ngữ Hán hay gặp bằng tiếng Việt (lưới an toàn cuối)."""
    if not text:
        return text
    for k in sorted(TRUNG_VIET, key=len, reverse=True):
        if k in text:
            text = text.replace(k, " " + TRUNG_VIET[k] + " ")
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def _khoi_cau_tham_khao(cau_list):
    """Render câu bank cho prompt NỘI BỘ (kèm đáp án để AI định hướng, cấm tiết lộ)."""
    khoi = []
    for c in cau_list:
        khoi.append(
            f"[{c.get('id')}] ({c.get('bai')} | {c.get('dang_phan') or c.get('dang')} | khó {c.get('do_kho')})\n"
            f"Đề: {c.get('de')}\nĐáp án (MẬT): {c.get('dap_an')}\n"
            f"Bước chuẩn (MẬT): {c.get('buoc_giai')}\nLỗi hay gặp: {c.get('loi_hay_gap')}"
        )
    return "\n---\n".join(khoi)


def _loc_id_hop_le(ids, mon="toan11"):
    """Chỉ giữ mã câu có thật trong bank (chống AI bịa ID)."""
    hop = []
    for cid in (ids or []):
        c = knowledge.tim_cau_theo_id(cid, mon)
        if c and c.get("chat_luong") == "ok" and c["id"] not in hop:
            hop.append(c["id"])
    return hop


def hs_chat(sid, cau_hoi, cid=None, mon="toan11"):
    """Hỏi đáp Socrates 1 lượt: nạp ngữ cảnh cuộc chat → tìm video/câu bank/wiki
    làm ngữ cảnh → gọi LLM → tách JSON ẩn → lưu điểm yếu/đề xuất vào hồ sơ HS.
    Trả về (tra_loi, extra{diem_yeu, bai_de_xuat, cau_goi_y, can_cu, video})."""
    data = store.doc_hs(sid)
    ngu_canh = list(data.get("history", []))
    if cid:
        # Nạp ngữ cảnh đúng cuộc đang mở; khóa Bài theo cuộc để AI bám đúng.
        cuoc = conversations.lay_cuoc(sid, cid)
        if cuoc is None:  # cuộc đã bị xóa giữa chừng
            cid = conversations.tao_cuoc(sid, bai=data.get("bai_hien_tai", ""))
            cuoc = conversations.lay_cuoc(sid, cid)
        ngu_canh = list(cuoc.get("messages", []))
        if cuoc.get("bai"):
            data["bai_hien_tai"] = cuoc["bai"]
    tin_moi = {"role": "user", "content": cau_hoi}

    # Tìm video khớp câu hỏi (fallback bài hiện tại).
    video = curriculum.tim_bai(cau_hoi, data.get("bai_hien_tai", ""), mon)
    goi_y = curriculum.goi_y_video(video) if video else None
    bai = (video or {}).get("title", "") or data.get("bai_hien_tai", "")

    # Nhặt tối đa 4 câu bank đạt chuẩn làm tham khảo nội bộ (đáp án chỉ vào
    # prompt, cấm AI tiết lộ): ưu tiên đúng Bài, vét thêm ngoài Bài, kèm câu
    # theo điểm yếu cũ.
    tham_khao = knowledge.tim_cau_lien_quan(cau_hoi, bai=bai or None, n=2, mon=mon)
    if len(tham_khao) < 3:
        tham_khao += [c for c in knowledge.tim_cau_lien_quan(cau_hoi, n=3, mon=mon)
                      if c["id"] not in {c2["id"] for c2 in tham_khao}][: 3 - len(tham_khao)]
    theo_yeu = knowledge.cau_theo_diem_yeu(data.get("weaknesses", [])[:3], bai=bai or None, n=1, mon=mon)
    for c in theo_yeu:
        if c["id"] not in {c2["id"] for c2 in tham_khao} and len(tham_khao) < 4:
            tham_khao.append(c)

    # Đọc concept wiki + lỗi sai điển hình của Bài để AI nhắc trước khi HS vấp.
    concept = knowledge.doc_concept(bai, mon=mon) if bai else ""
    loi_sai = knowledge.loi_sai_cua_bai(bai, mon=mon) if bai else []

    mon_ho_tro = [subjects.MON_HOC[m]["ten"] for m in data.get("mon_can_ho_tro", []) if m in subjects.MON_HOC]
    # Dựng context nội bộ (hồ sơ + video + concept + lỗi sai + câu tham khảo).
    context = (
        f"[Hồ sơ HS: trình độ={data.get('trinh_do_toan')}, "
        f"điểm yếu đã biết={data.get('weaknesses')}, "
        f"bài hiện tại={data.get('bai_hien_tai')}, phong cách={data.get('phong_cach')}, "
        f"môn cần hỗ trợ={mon_ho_tro or 'chưa rõ'}, mục tiêu={data.get('muc_tieu') or 'chưa rõ'}, "
        f"tự học mỗi ngày={data.get('gio_tu_hoc') or 'chưa rõ'}]\n"
    )
    if goi_y:
        context += f"[VIDEO: {goi_y['title']} | {goi_y['link']} | ý chính: {'; '.join(goi_y['tom_tat'])}]\n"
    else:
        context += "[VIDEO: không có]\n"
    if concept:
        context += f"[KHÁI NIỆM GỐC (wiki):\n{concept}]\n"
    if loi_sai:
        context += f"[LỖI SAI ĐIỂN HÌNH Bài này: {'; '.join(loi_sai)}]\n"
    if tham_khao:
        context += (f"[CÂU THAM KHẢO từ kho GV — chỉ gợi ý đúng các mã ID này, "
                    f"TUYỆT ĐỐI KHÔNG tiết lộ đáp án/bước chuẩn:\n{_khoi_cau_tham_khao(tham_khao)}]\n")
    else:
        context += "[CÂU THAM KHẢO: không có — bai_de_xuat để rỗng]\n"

    # Gọi LLM kèm luật Socrates + ép tiếng Việt (lẫn chữ Hán thì bắt viết lại).
    msgs = [
        {"role": "system", "content": prompts.prompt_hs(mon) + "\n" + context
         + "\nYÊU CẦU BẮT BUỘC: LUÔN trả lời toàn bộ bằng tiếng Việt, "
           "TUYỆT ĐỐI không dùng chữ Trung Quốc."},
        *ngu_canh, tin_moi,
    ]
    raw = llm.chat_pro(msgs)
    # Lẫn chữ Hán thì bắt viết lại 1 lần.
    if co_chu_trung(raw):
        raw = llm.chat_pro(msgs + [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": (
                "Viết lại câu trả lời trên HOÀN TOÀN bằng tiếng Việt, "
                "không dùng chữ Trung Quốc.")},
        ])
    # Tách phần chat khỏi JSON ẩn; lọc bỏ ID bịa/không đạt chuẩn.
    tra_loi, extra = tach_json_cuoi(raw)
    tra_loi = sua_chu_trung(tra_loi)
    if not isinstance(extra, dict):
        extra = {}
    diem_yeu = [sua_chu_trung(w) for w in (extra.get("weaknesses", []) or [])]
    bai_de_xuat = _loc_id_hop_le(extra.get("bai_de_xuat", []) or [], mon)
    can_cu = _loc_id_hop_le(extra.get("can_cu_bank_ids", []) or [], mon)
    bai_hien_tai = extra.get("bai_hien_tai", "") or ""
    video_goi_y = extra.get("video_goi_y", "") or ""

    # Lưu hội thoại vào cuộc mở + sổ tổng (đọc tươi để khỏi ghi đè);
    # ép Bài về đúng cuộc (AI không được đổi giữa chừng).
    if cid:
        conversations.them_tin_nhan(sid, cid, "user", cau_hoi)
        conversations.them_tin_nhan(sid, cid, "assistant", tra_loi)
        data = store.doc_hs(sid)
        # Giữ đúng Bài của cuộc đang mở, AI không được đổi giữa chừng
        for c in data.get("conversations", []):
            if c["id"] == cid and c.get("bai"):
                bai_hien_tai = c["bai"]
                break
    else:
        data["history"].append({"role": "user", "content": cau_hoi})
        data["history"].append({"role": "assistant", "content": tra_loi})
    # Cộng dồn điểm yếu mới (khử trùng, không phân biệt hoa/thường).
    da_co = {w.lower() for w in data.get("weaknesses", [])}
    for w in diem_yeu:
        w = (w or "").strip()
        if w and w.lower() not in da_co:
            data["weaknesses"].append(w)
            da_co.add(w.lower())
    if bai_de_xuat:
        data["bai_de_xuat"] = bai_de_xuat
    if bai_hien_tai:
        data["bai_hien_tai"] = bai_hien_tai
    if video_goi_y or (goi_y and goi_y["link"] not in data.get("video_da_xem", [])):
        # Đếm lượt gợi ý video (tới lần 3 mà chưa xem thì auto đánh dấu).
        link = video_goi_y or (goi_y["link"] if goi_y else "")
        if link and link not in data.get("video_da_xem", []):
            dem = data.get("video_goi_y_count", {})
            dem[link] = int(dem.get(link, 0)) + 1
            data["video_goi_y_count"] = dem
            if dem[link] >= 3:
                data.setdefault("video_da_xem", []).append(link)
    store.luu_hs(sid, data)
    cau_goi_y = [knowledge.tim_cau_theo_id(x, mon) for x in bai_de_xuat]
    return tra_loi, {"diem_yeu": diem_yeu, "bai_de_xuat": bai_de_xuat,
                     "cau_goi_y": [c for c in cau_goi_y if c],
                     "can_cu": can_cu, "video": goi_y}
