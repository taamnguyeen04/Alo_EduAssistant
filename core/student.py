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

# ── Luyện trắc nghiệm: mức độ + trình độ riêng từng Bài ──
# 1 = Nhận biết, 2 = Thông hiểu, 3 = Vận dụng (khớp do_kho 1-3 trong bank).
MUC_DO_TN = {1: "Nhận biết", 2: "Thông hiểu", 3: "Vận dụng"}
# Điểm đệm thay đổi CHẬM: đúng +1 (VD +1.5), sai −1, "không biết" −0.5.
# Chỉ đổi level khi chạm ngưỡng VÀ đã làm đủ số câu tối thiểu.
DIEM_TN_DUNG = {1: 1.0, 2: 1.0, 3: 1.5}
DIEM_TN_SAI = -1.0
DIEM_TN_KHONG_BIET = -0.5
DIEM_TN_LAM_LAI_DUNG = 0.5
NGUONG_TN_LEN = 4.0
NGUONG_TN_XUONG = -3.0
SO_CAU_TN_TOI_THIEU = 6


def ten_muc_do(do_kho):
    """1 -> 'Nhận biết', 2 -> 'Thông hiểu', 3 -> 'Vận dụng'."""
    try:
        return MUC_DO_TN.get(int(do_kho), f"Mức {do_kho}")
    except (TypeError, ValueError):
        return "Thông hiểu"


def lay_trinh_do_bai(sid, bai):
    """Trình độ của 1 HS ở 1 Bài: {level, diem, so_cau}. Mặc định level 1."""
    hs = store.doc_hs(sid)
    kho = hs.get("trinh_do_bai") or {}
    thong = kho.get(bai or "") or {}
    try:
        level = int(thong.get("level", 1))
    except (TypeError, ValueError):
        level = 1
    level = max(1, min(3, level))
    try:
        diem = float(thong.get("diem", 0.0) or 0.0)
    except (TypeError, ValueError):
        diem = 0.0
    try:
        so_cau = int(thong.get("so_cau", 0) or 0)
    except (TypeError, ValueError):
        so_cau = 0
    return {"level": level, "diem": diem, "so_cau": so_cau}


def cap_nhat_trinh_do_bai(sid, bai, do_kho, ket_qua):
    """Cập nhật điểm đệm per-Bài sau mỗi câu TN.

    ket_qua: 'dung' | 'sai' | 'khong_biet' | 'lam_lai_dung' | 'lam_lai_sai'.
    Đổi level chậm: cần chạm ngưỡng điểm VÀ đủ số câu tối thiểu.
    Trả về (level_cu, level_moi).
    """
    try:
        dk = int(do_kho)
    except (TypeError, ValueError):
        dk = 2
    if ket_qua == "dung":
        delta = DIEM_TN_DUNG.get(dk, 1.0)
    elif ket_qua == "lam_lai_dung":
        delta = DIEM_TN_LAM_LAI_DUNG
    elif ket_qua == "khong_biet":
        delta = DIEM_TN_KHONG_BIET
    elif ket_qua in ("sai", "lam_lai_sai"):
        delta = DIEM_TN_SAI
    else:
        delta = 0.0
    hs = store.doc_hs(sid)
    kho = hs.get("trinh_do_bai") or {}
    thong = dict(kho.get(bai or "") or {})
    cu = lay_trinh_do_bai(sid, bai)["level"]
    diem = float(thong.get("diem", 0.0) or 0.0) + delta
    so_cau = int(thong.get("so_cau", 0) or 0) + 1
    moi = cu
    if so_cau >= SO_CAU_TN_TOI_THIEU:
        if diem >= NGUONG_TN_LEN and cu < 3:
            moi = cu + 1
            diem = 0.0
        elif diem <= NGUONG_TN_XUONG and cu > 1:
            moi = cu - 1
            diem = 0.0
    diem = max(NGUONG_TN_XUONG, min(NGUONG_TN_LEN, diem))
    kho[bai or ""] = {"level": moi, "diem": round(diem, 2), "so_cau": so_cau}
    hs["trinh_do_bai"] = kho
    store.luu_hs(sid, hs)
    return cu, moi


def them_diem_yeu(sid, ds_moi):
    """Thêm điểm yếu vào hồ sơ (khử trùng không phân biệt hoa/thường)."""
    ds_moi = [str(w or "").strip() for w in (ds_moi or []) if str(w or "").strip()]
    if not ds_moi:
        return []
    hs = store.doc_hs(sid)
    da_co = {w.lower() for w in hs.get("weaknesses", [])}
    them = []
    for w in ds_moi:
        if w.lower() not in da_co:
            hs["weaknesses"].append(w)
            da_co.add(w.lower())
            them.append(w)
    if them:
        store.luu_hs(sid, hs)
    return them


def lay_trinh_do(data_hoac_sid, mon="toan11"):
    """Trình độ chung per-môn (đọc trinh_do_mon, fallback file cũ trinh_do_toan)."""
    data = store.doc_hs(data_hoac_sid) if isinstance(data_hoac_sid, str) else (data_hoac_sid or {})
    per = data.get("trinh_do_mon") or {}
    if isinstance(per, dict) and per.get(mon) in TRINH_DO:
        return per[mon]
    cu = data.get("trinh_do_toan", "trung bình")
    return cu if cu in TRINH_DO else "trung bình"


def _lay_diem_trinh_do(data, mon="toan11"):
    per = data.get("diem_trinh_do_mon") or {}
    if isinstance(per, dict) and isinstance(per.get(mon), (int, float)):
        return int(per[mon])
    try:
        return int(data.get("diem_trinh_do", 0) or 0)
    except (TypeError, ValueError):
        return 0


def tu_dong_cap_nhat_trinh_do(sid, dung_het, mon="toan11"):
    """Điểm đệm trình độ per-môn: mỗi bài chấm xong đúng +1, sai -1 (bù trừ lẫn nhau).
    Chạm +5 (ròng) -> lên 1 bậc, chạm -5 (ròng) -> xuống 1 bậc, rồi reset về 0.
    Đúng/sai xen kẽ thì điểm quanh quẩn gần 0 nên bậc ổn định, không nhảy liên tục.
    Ghi cả khóa per-môn mới + khóa legacy (môn mặc định) để file/test cũ vẫn đọc được.
    Trả về (cu, moi); bằng nhau = chưa đổi bậc."""
    hs = store.doc_hs(sid)
    cu = lay_trinh_do(hs, mon)
    diem = _lay_diem_trinh_do(hs, mon)
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
    per_diem = hs.get("diem_trinh_do_mon") or {}
    if not isinstance(per_diem, dict):
        per_diem = {}
    per_diem[mon] = diem
    hs["diem_trinh_do_mon"] = per_diem
    if moi != cu:
        per_td = hs.get("trinh_do_mon") or {}
        if not isinstance(per_td, dict):
            per_td = {}
        per_td[mon] = moi
        hs["trinh_do_mon"] = per_td
    if mon == subjects.MON_MAC_DINH:  # dual-write cho file/test cũ
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


_RE_LATEX_DISPLAY = re.compile(r"\\\[(.+?)\\\]", re.S)
_RE_LATEX_INLINE_PAREN = re.compile(r"\\\((.+?)\\\)", re.S)


def chuan_hoa_latex(text):
    """Đổi \\[...\\] -> $$...$$, \\(...\\) -> $...$ để st.markdown render KaTeX.

    Streamlit chỉ render $...$/$$...$$; model hay nhả \\[ \\] khiến markdown
    hiểu \\[ là escape nên hiện ngoặc vuông + backslash như ảnh lỗi.
    """
    if not text:
        return text
    text = _RE_LATEX_DISPLAY.sub(r"$$\1$$", text)
    text = _RE_LATEX_INLINE_PAREN.sub(r"$\1$", text)
    return text


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


_RE_TINH_TOAN = re.compile(r"[0-9]|sin|cos|tan|log|lim|√|π|\+|\-|\*|/|\^|=|dx|dy", re.I)


def _can_audit(cau_text, hinh_list, tham_khao):
    """True khi nên chạy vòng verify: có ảnh / ngoài bank / câu dài tính toán."""
    if hinh_list:
        return True
    if not tham_khao:
        return True
    t = (cau_text or "").strip()
    return len(t) > 60 and bool(_RE_TINH_TOAN.search(t))


def hs_chat(sid, cau_hoi, cid=None, mon="toan11", hinh_data_urls=None):
    """Hỏi đáp Socrates 1 lượt: nạp ngữ cảnh cuộc chat → tìm video/câu bank/wiki
    làm ngữ cảnh → gọi LLM → tách JSON ẩn → lưu điểm yếu/đề xuất vào hồ sơ HS.
    Trả về (tra_loi, extra{diem_yeu, bai_de_xuat, cau_goi_y, can_cu, video}).
    hinh_data_urls: list data URI ảnh (data:image/...;base64,...) để hỏi qua ảnh."""
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
    # Lọc ngữ cảnh gửi LLM: chỉ giữ text (bỏ base64 cũ cho nhẹ token).
    ngu_canh_sach = []
    for m in ngu_canh:
        c = m.get("content", "")
        if isinstance(c, list):  # tin multimodal cũ -> chỉ giữ phần text
            txt = " ".join(p.get("text", "") for p in c
                           if isinstance(p, dict) and p.get("type") == "text")
            ngu_canh_sach.append({"role": m.get("role", "user"), "content": txt})
        else:
            ngu_canh_sach.append({"role": m.get("role", "user"), "content": c})
    ngu_canh = ngu_canh_sach[-20:]  # chặn 20 tin gần nhất (ảnh tốn token)
    cau_text = (cau_hoi or "").strip()
    hinh_list = [u for u in (hinh_data_urls or []) if u]
    if hinh_list:
        parts = []
        if cau_text:
            parts.append({"type": "text", "text": cau_text})
        else:
            parts.append({"type": "text",
                          "text": "Mình gửi ảnh bài toán. Bạn xem ảnh rồi dẫn dắt mình từng bước nhỏ, đừng đọc đáp án ngay."})
            cau_text = cau_text or "Giải bài trong ảnh"
        for url in hinh_list[:3]:  # tối đa 3 ảnh/lượt (đỡ tràn token)
            parts.append({"type": "image_url", "image_url": {"url": url}})
        tin_moi = {"role": "user", "content": parts}
    else:
        tin_moi = {"role": "user", "content": cau_text}

    # Tìm video khớp câu hỏi (fallback bài hiện tại).
    video = curriculum.tim_bai(cau_text, data.get("bai_hien_tai", ""), mon)
    goi_y = curriculum.goi_y_video(video) if video else None
    bai = (video or {}).get("title", "") or data.get("bai_hien_tai", "")

    # Nhặt tối đa 4 câu bank đạt chuẩn làm tham khảo nội bộ (đáp án chỉ vào
    # prompt, cấm AI tiết lộ): ưu tiên đúng Bài, vét thêm ngoài Bài, kèm câu
    # theo điểm yếu cũ.
    tham_khao = knowledge.tim_cau_lien_quan(cau_text, bai=bai or None, n=2, mon=mon)
    if len(tham_khao) < 3:
        tham_khao += [c for c in knowledge.tim_cau_lien_quan(cau_text, n=3, mon=mon)
                      if c["id"] not in {c2["id"] for c2 in tham_khao}][: 3 - len(tham_khao)]
    theo_yeu = knowledge.cau_theo_diem_yeu(data.get("weaknesses", [])[:3], bai=bai or None, n=1, mon=mon)
    for c in theo_yeu:
        if c["id"] not in {c2["id"] for c2 in tham_khao} and len(tham_khao) < 4:
            tham_khao.append(c)

    # Đọc lý thuyết chuẩn wiki/wiki + concepts C1_Bx_Kxx + lỗi sai điển hình.
    # Ưu tiên hệ mới (syllabus map); rỗng thì fallback stub cũ, không chặn chat.
    wiki_bai, concepts_ghep, lesson_id = ("", "", "")
    if bai or cau_text:
        try:
            wiki_bai, concepts_ghep, lesson_id = knowledge.doc_ly_thuyet(
                bai or "", cau_text, mon=mon)
        except Exception:
            wiki_bai, concepts_ghep, lesson_id = ("", "", "")
    concept_cu = ""
    if not concepts_ghep and bai:
        try:
            concept_cu = knowledge.doc_concept(bai, mon=mon) or ""
        except Exception:
            concept_cu = ""
    loi_sai = knowledge.loi_sai_cua_bai(bai, mon=mon) if bai else []

    mon_ho_tro = [subjects.MON_HOC[m]["ten"] for m in data.get("mon_can_ho_tro", []) if m in subjects.MON_HOC]
    # Dựng context nội bộ (hồ sơ + video + concept + lỗi sai + câu tham khảo).
    context = (
        f"[Hồ sơ HS: trình độ={lay_trinh_do(data, mon)}, "
        f"điểm yếu đã biết={data.get('weaknesses')}, "
        f"bài hiện tại={data.get('bai_hien_tai')}, phong cách={data.get('phong_cach')}, "
        f"môn cần hỗ trợ={mon_ho_tro or 'chưa rõ'}, mục tiêu={data.get('muc_tieu') or 'chưa rõ'}, "
        f"tự học mỗi ngày={data.get('gio_tu_hoc') or 'chưa rõ'}]\n"
    )
    if goi_y:
        context += f"[VIDEO: {goi_y['title']} | {goi_y['link']} | ý chính: {'; '.join(goi_y['tom_tat'])}]\n"
    else:
        context += "[VIDEO: không có]\n"
    if wiki_bai:
        context += (f"[LÝ THUYẾT CHUẨN (wiki {lesson_id}, source_grounded sách "
                    f"Kết nối tri thức — lấy đây làm chuẩn công thức/ĐK, "
                    f"ưu tiên hơn trí nhớ model):\n{wiki_bai}]\n")
    if concepts_ghep:
        context += f"[CONCEPTS LIÊN QUAN (công thức cốt lõi để giải):\n{concepts_ghep}]\n"
    elif concept_cu:
        context += f"[KHÁI NIỆM GỐC (wiki):\n{concept_cu}]\n"
    if loi_sai:
        context += f"[LỖI SAI ĐIỂN HÌNH Bài này: {'; '.join(loi_sai)}]\n"
    if tham_khao:
        context += (f"[CÂU THAM KHẢO từ kho GV — chỉ gợi ý đúng các mã ID này, "
                    f"TUYỆT ĐỐI KHÔNG tiết lộ đáp án/bước chuẩn:\n{_khoi_cau_tham_khao(tham_khao)}]\n")
    else:
        context += "[CÂU THAM KHẢO: không có — bai_de_xuat để rỗng]\n"

    # Gọi LLM 2 pha (accuracy trước, dễ hiểu sau) + ép tiếng Việt.
    msgs = [
        {"role": "system", "content": prompts.prompt_hs(mon) + "\n" + context
         + "\nYÊU CẦU BẮT BUỘC: LUÔN trả lời toàn bộ bằng tiếng Việt, "
           "TUYỆT ĐỐI không dùng chữ Trung Quốc. Công thức CHỈ dùng "
           "$...$ hoặc $$...$$, CẤM \\[ \\] và \\( \\)."},
        *ngu_canh, tin_moi,
    ]
    raw = llm.chat_pro(msgs, timeout=90)
    # Vòng audit ưu tiên 1: chỉ chạy ở prod + câu khó (có ảnh / ngoài bank /
    # câu dài tính toán) để kiểm tra lại số học + công thức bằng PRO temp 0.0.
    if llm.che_do() == "prod" and _can_audit(cau_text, hinh_list, tham_khao):
        try:
            raw = llm.audit_dap_an([
                {"role": "system", "content": (
                    "Bạn là kiểm tra viên toán lớp 11. Ưu tiên CHÍNH XÁC tuyệt đối. "
                    "Nhận: câu hỏi HS + câu trả lời AI + CÂU THAM KHẢO bank (mật, là chuẩn). "
                    "Nhiệm vụ: kiểm tra lại công thức, ĐK, dấu, đơn vị độ/radian, số học từng bước. "
                    "Nếu đúng: trả NGUYÊN VĂN không sửa. Nếu sai: sửa tối thiểu cho đúng, "
                    "giữ nguyên giọng dễ hiểu + khung Chốt→Bước→Ví dụ→Hỏi, giữ nguyên khối ```json cuối. "
                    "Chỉ viết tiếng Việt, công thức LaTeX $...$.")},
                {"role": "user", "content": (
                    f"Câu hỏi HS: {cau_text}\n\nCâu trả lời cần kiểm:\n{raw}\n\n"
                    f"Ngữ cảnh bank/w debes (mật):\n{context}")},
            ])
        except Exception:
            pass  # audit rớt thì giữ bản đầu, không bao giờ chặn HS
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
    tra_loi = chuan_hoa_latex(sua_chu_trung(tra_loi))
    if not isinstance(extra, dict):
        extra = {}
    diem_yeu = [sua_chu_trung(w) for w in (extra.get("weaknesses", []) or [])]
    bai_de_xuat = _loc_id_hop_le(extra.get("bai_de_xuat", []) or [], mon)
    can_cu = _loc_id_hop_le(extra.get("can_cu_bank_ids", []) or [], mon)
    bai_hien_tai = extra.get("bai_hien_tai", "") or ""
    video_goi_y = extra.get("video_goi_y", "") or ""

    # Lưu hội thoại vào cuộc mở + sổ tổng (đọc tươi để khỏi ghi đè);
    # ép Bài về đúng cuộc (AI không được đổi giữa chừng).
    # Lưu bản text gọn (không lưu base64) để JSON HS không phình.
    noi_dung_luu = cau_text + (f" [đã gửi {len(hinh_list)} ảnh]" if hinh_list else "")
    if cid:
        conversations.them_tin_nhan(sid, cid, "user", noi_dung_luu)
        conversations.them_tin_nhan(sid, cid, "assistant", tra_loi)
        data = store.doc_hs(sid)
        # Giữ đúng Bài của cuộc đang mở, AI không được đổi giữa chừng
        for c in data.get("conversations", []):
            if c["id"] == cid and c.get("bai"):
                bai_hien_tai = c["bai"]
                break
    else:
        data["history"].append({"role": "user", "content": noi_dung_luu})
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
    # Kho thiếu đúng dạng (bai_de_xuat rỗng) mà có mẫu soạn sẵn theo công thức
    # chuẩn -> tự soạn tối đa 3 bài, lưu chờ GV duyệt, giao ngay cho HS.
    cau_tu_soan = []
    if not bai_de_xuat:
        try:
            from . import tu_soan as _tu_soan
            cau_tu_soan = _tu_soan.lay_cau_tu_soan(
                cau_text, lesson_id, bai or bai_hien_tai, mon) or []
            if cau_tu_soan:
                _tu_soan.luu_cho_duyet(cau_tu_soan, bai or bai_hien_tai or
                                       "Bài 4. Phương trình lượng giác", mon)
        except Exception:
            cau_tu_soan = []
    return tra_loi, {"diem_yeu": diem_yeu, "bai_de_xuat": bai_de_xuat,
                     "cau_goi_y": [c for c in cau_goi_y if c],
                     "cau_tu_soan": cau_tu_soan,
                     "can_cu": can_cu, "video": goi_y}
