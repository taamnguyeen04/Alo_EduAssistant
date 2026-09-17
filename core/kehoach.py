"""Kế hoạch học tập theo mục tiêu từng giai đoạn + thời khóa biểu.

Luồng:
  HS đặt mục tiêu điểm (0-10) cho từng môn ở 4 giai đoạn GK1/CK1/GK2/CK2
  (Hồ sơ) -> fingerprint(mục tiêu + TKB) đổi -> AI sinh lại kế hoạch tuần
  (JSON: mỗi ngày 2-4 việc) -> Trang chủ hiện nổi bật "Kế hoạch hôm nay".

LLM lỗi/mất mạng -> dùng kế hoạch nền (suy từ TKB) để không bao giờ trắng.
"""
import datetime
import hashlib
import json

from . import store, subjects, tkb as tkb_core

GIAI_DOAN = ["GK1", "CK1", "GK2", "CK2"]
TEN_GIAI_DOAN = {"GK1": "Giữa kỳ 1", "CK1": "Cuối kỳ 1",
                 "GK2": "Giữa kỳ 2", "CK2": "Cuối kỳ 2"}
NGAY_TUAN = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
TEN_NGAY = {"T2": "Thứ 2", "T3": "Thứ 3", "T4": "Thứ 4", "T5": "Thứ 5",
            "T6": "Thứ 6", "T7": "Thứ 7", "CN": "Chủ nhật"}


def ma_hom_nay():
    """Mã ngày hôm nay theo NGAY_TUAN (T2..CN)."""
    return NGAY_TUAN[datetime.date.today().weekday()]


def muc_tieu(hs):
    """{giai_đoạn: {mã_môn: điểm}} — chỉ giữ điểm > 0."""
    # Điểm 0 nghĩa là chưa đặt nên bỏ để prompt AI gọn.
    raw = hs.get("muc_tieu_giai_doan", {}) or {}
    kq = {}
    for gd in GIAI_DOAN:
        g = raw.get(gd, {}) or {}
        loc = {}
        for ma, diem in g.items():
            try:
                d = float(diem)
            except (TypeError, ValueError):
                continue
            if ma in subjects.MON_HOC and d > 0:
                loc[ma] = round(min(d, 10), 1)
        if loc:
            kq[gd] = loc
    return kq


def mon_trong_ngay(hs, ma_ngay):
    """Các môn học ở trường trong 1 ngày (theo TKB file/tay), giữ thứ tự, không trùng."""
    tkb = tkb_core.chuan_hoa_tkb(hs.get("tkb", {}))
    lich = (tkb.get("lich") or {}).get(ma_ngay, {}) or {}
    mons, thay = [], set()
    for buoi in ("sáng", "chiều", "tối"):
        tiet_map = lich.get(buoi, {}) or {}
        for t in sorted(tiet_map, key=lambda x: (int(x) if str(x).isdigit() else 99, str(x))):
            mon = str(tiet_map[t]).strip()
            if mon and mon not in thay:
                thay.add(mon)
                mons.append(mon)
    return mons


def fingerprint(hs):
    """Dấu vân tay mục tiêu + TKB. Đổi 1 trong 2 -> AI phải chạy lại."""
    # Hash mục tiêu + lịch TKB: đổi 1 trong 2 là vân tay đổi theo.
    tkb = tkb_core.chuan_hoa_tkb(hs.get("tkb", {}))
    payload = {"muc_tieu": muc_tieu(hs), "tkb": tkb.get("lich", {})}
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def can_tao_lai(hs):
    kh = hs.get("ke_hoach", {}) or {}
    return (not isinstance(kh, dict) or not (kh.get("tuan") or {})
            or kh.get("fingerprint") != fingerprint(hs))


def _prompt_ke_hoach(ten, mt, tkb_lich):
    dong_mt = []
    for gd in GIAI_DOAN:
        if gd in mt:
            ds = ", ".join(f"{subjects.MON_HOC[m]['ten']} {d}" for m, d in mt[gd].items())
            dong_mt.append(f"- {TEN_GIAI_DOAN[gd]}: {ds}")
    txt_mt = "\n".join(dong_mt) if dong_mt else "(chưa đặt)"
    dong_tkb = []
    for n in NGAY_TUAN:
        lich_n = tkb_lich.get(n, {}) or {}
        mons = []
        for buoi in ("sáng", "chiều", "tối"):
            for t in sorted((lich_n.get(buoi) or {}),
                            key=lambda x: (int(x) if str(x).isdigit() else 99, str(x))):
                m = str((lich_n[buoi])[t]).strip()
                if m and m not in mons:
                    mons.append(m)
        if mons:
            dong_tkb.append(f"- {TEN_NGAY[n]}: {', '.join(mons)}")
    txt_tkb = "\n".join(dong_tkb) if dong_tkb else "(chưa có thời khóa biểu)"
    return (
        "Bạn là trợ lý học tập cho học sinh Việt Nam lớp 11, tên em là " + (ten or "em") + ".\n"
        "MỤC TIÊU ĐIỂM (thang 10) EM ĐẶT:\n" + txt_mt + "\n"
        "THỜI KHÓA BIỂU Ở TRƯỜNG:\n" + txt_tkb + "\n"
        "Hãy lập KẾ HOẠCH TỰ HỌC 1 TUẦN, mỗi ngày 2-4 việc ngắn gọn, cụ thể "
        "(môn nào, làm gì, bao lâu), ưu tiên môn sắp học ở trường hôm sau và "
        "môn em đặt mục tiêu cao. Toàn bộ tiếng Việt.\n"
        "CHỈ trả về đúng 1 JSON (không giải thích, không markdown fence):\n"
        '{"tuan": {"T2": ["việc 1", "việc 2"], "T3": [], "T4": [], "T5": [], '
        '"T6": [], "T7": [], "CN": []}, '
        '"trong_tam": "1 câu trọng tâm tuần này", '
        '"loi_nhan": "1 câu động viên ngắn"}'
    )


def _tach_json(text):
    s = (text or "").strip()
    if s.startswith("```"):
        s = re_sub_fence(s)
    try:
        return json.loads(s)
    except Exception:
        pass
    i, j = s.find("{"), s.rfind("}")
    if 0 <= i < j:
        try:
            return json.loads(s[i:j + 1])
        except Exception:
            return None
    return None


def re_sub_fence(s):
    lines = s.split("\n")
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines)


def _ke_hoach_nen(hs):
    """Kế hoạch nền khi AI lỗi: suy thẳng từ TKB + mục tiêu."""
    mt = muc_tieu(hs)
    tuan = {}
    for n in NGAY_TUAN:
        mons = mon_trong_ngay(hs, n)
        if not mons:
            tuan[n] = ["Nghỉ ngơi, đọc sách 20 phút 📖"] if n == "CN" else []
            continue
        viec = [f"Tối: ôn lại {', '.join(mons[:3])} đã học hôm nay (30 phút) 📝"]
        if len(mons) > 1:
            viec.append(f"Làm 3-5 bài tập {mons[0]} ⏱ 20 phút")
        tuan[n] = viec
    trong_tam = ""
    if mt:
        gd = next(iter(mt))
        ds = ", ".join(f"{subjects.MON_HOC[m]['ten']} {d}" for m, d in mt[gd].items())
        trong_tam = f"Hướng tới {TEN_GIAI_DOAN[gd]}: {ds} 🎯"
    return {"tuan": tuan, "trong_tam": trong_tam or "Học đều mỗi ngày một ít 🌱",
            "loi_nhan": "Mỗi ngày tiến một bước nhỏ là đủ! 💪", "nguon": "nen"}


def tao_ke_hoach(sid):
    """Sinh (lại) kế hoạch AI cho HS, lưu vào hồ sơ, trả về dict kế hoạch."""
    from . import llm
    hs = store.doc_hs(sid)
    mt = muc_tieu(hs)
    tkb_lich = (tkb_core.chuan_hoa_tkb(hs.get("tkb", {})).get("lich") or {})
    kh = None
    try:
        raw = llm.chat_flash(
            [{"role": "user", "content": _prompt_ke_hoach(hs.get("ten", ""), mt, tkb_lich)}],
            timeout=60,
        )
        data = _tach_json(raw)
        if isinstance(data, dict) and isinstance(data.get("tuan"), dict):
            tuan = {}
            for n in NGAY_TUAN:
                vs = data["tuan"].get(n, []) or []
                tuan[n] = [str(v).strip() for v in vs if str(v).strip()][:4]
            kh = {"tuan": tuan,
                  "trong_tam": str(data.get("trong_tam", "")).strip(),
                  "loi_nhan": str(data.get("loi_nhan", "")).strip(),
                  "nguon": "ai"}
    except Exception:
        kh = None
    if not kh:
        # AI lỗi/mất mạng thì dùng kế hoạch nền để hôm nào cũng có việc.
        kh = _ke_hoach_nen(hs)
    hs = store.doc_hs(sid)  # đọc tươi, tránh ghi đè thay đổi khác
    kh["fingerprint"] = fingerprint(hs)
    kh["cap_nhat"] = datetime.datetime.now().isoformat(timespec="minutes")
    hs["ke_hoach"] = kh
    store.luu_hs(sid, hs)
    return kh


def nhac_hom_nay(hs):
    """Gói hiển thị cho Trang chủ: {ma_ngay, ten_ngay, mon_truong, viec, trong_tam, loi_nhan, cap_nhat}."""
    ma = ma_hom_nay()
    kh = hs.get("ke_hoach", {}) or {}
    tuan = kh.get("tuan", {}) or {}
    return {
        "ma_ngay": ma,
        "ten_ngay": TEN_NGAY[ma],
        "mon_truong": mon_trong_ngay(hs, ma),
        "viec": [str(v) for v in (tuan.get(ma, []) or [])],
        "trong_tam": kh.get("trong_tam", ""),
        "loi_nhan": kh.get("loi_nhan", ""),
        "cap_nhat": kh.get("cap_nhat", ""),
        "nguon": kh.get("nguon", ""),
    }
