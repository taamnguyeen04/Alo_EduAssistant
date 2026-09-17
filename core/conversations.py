"""Nhiều đoạn chat cho mỗi HS (mỗi Bài/thắc mắc 1 luồng riêng).

- Điểm yếu, trình độ, bài đề xuất vẫn lưu CHUNG ở hồ sơ (AI đọc hết).
- Chỉ tin nhắn mới tách theo cuộc, để hỏi đáp từng Bài cho dễ theo dõi.
- data["history"] phẳng được giữ nguyên làm sổ tổng (báo cáo GV, trang chủ không vỡ).
"""
import time
from . import store


def _chuyen_lich_su_cu(data):
    """Lần đầu dùng: gom history phẳng cũ thành 1 cuộc 'Đoạn chat cũ'."""
    # Chạy 1 lần duy nhất cho file HS cũ chưa có key conversations.
    if "conversations" not in data:
        data["conversations"] = []
        if data.get("history"):
            data["conversations"].append({
                "id": "cuoc-cu",
                "tieu_de": "Đoạn chat cũ",
                "bai": data.get("bai_hien_tai", ""),
                "messages": list(data["history"]),
            })
    return data["conversations"]


def ds_cuoc(sid):
    data = store.doc_hs(sid)
    return _chuyen_lich_su_cu(data)


def lay_cuoc(sid, cid):
    for c in ds_cuoc(sid):
        if c["id"] == cid:
            return c
    return None


def tao_cuoc(sid, bai="", cau_mo_dau=""):
    data = store.doc_hs(sid)
    ds = _chuyen_lich_su_cu(data)
    # id theo mili-giây nên tạo 2 cuộc liên tiếp cũng không trùng.
    cid = f"cuoc-{int(time.time() * 1000)}"
    ten_bai = (bai or "").replace("Bài ", "B").split(".")[0].strip() or "Tự do"
    ds.insert(0, {
        "id": cid,
        "tieu_de": f"{ten_bai}: {(cau_mo_dau or 'Thắc mắc mới')[:32]}",
        "bai": bai,
        "messages": [],
    })
    store.luu_hs(sid, data)
    return cid


def xoa_cuoc(sid, cid):
    data = store.doc_hs(sid)
    ds = _chuyen_lich_su_cu(data)
    data["conversations"] = [c for c in ds if c["id"] != cid]
    store.luu_hs(sid, data)


def them_tin_nhan(sid, cid, role, content):
    """Ghi 1 tin vào cuộc đang mở + sổ tổng history."""
    # Ghi song song 2 nơi: cuộc mở để chat theo Bài, sổ tổng để báo cáo GV.
    data = store.doc_hs(sid)
    ds = _chuyen_lich_su_cu(data)
    for c in ds:
        if c["id"] == cid:
            c["messages"].append({"role": role, "content": content})
            # Tự đặt tên cuộc theo câu hỏi đầu tiên
            if role == "user" and len(c["messages"]) == 1:
                ten_bai = (c.get("bai") or "").replace("Bài ", "B").split(".")[0].strip() or "Tự do"
                c["tieu_de"] = f"{ten_bai}: {content[:32]}"
            break
    data.setdefault("history", []).append({"role": role, "content": content})
    store.luu_hs(sid, data)
