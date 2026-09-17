import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import store, student

SID = "test_hs_phase3"
fails = []


def check(name, cond, info=""):
    print(("PASS " if cond else "FAIL ") + name, info)
    if not cond:
        fails.append(name)


def don():
    try:
        os.remove(store.duong_dan_hs(SID))
    except OSError:
        pass
    att = os.path.join("data", "attempts")
    if os.path.isdir(att):
        for t in os.listdir(att):
            if t.startswith(SID + "_"):
                os.remove(os.path.join(att, t))


don()

# 1. Hồ sơ lưu đủ trường mới (yeu, tkb, bai_hien_tai)
hs = store.doc_hs(SID)
hs.update({"yeu": ["sợ hình không gian"], "tkb": {"T2": ["Toán", "Văn"]}, "bai_hien_tai": "Bài 1. X"})
store.luu_hs(SID, hs)
hs2 = store.doc_hs(SID)
check("hs-luu-truong-moi", hs2["yeu"] == ["sợ hình không gian"] and hs2["tkb"] == {"T2": ["Toán", "Văn"]}
      and hs2["bai_hien_tai"] == "Bài 1. X")

# 2. Điểm đệm trình độ: đúng +1/sai -1, đủ +5 ròng mới lên 1 bậc
store.luu_hs(SID, {**store.doc_hs(SID), "trinh_do_toan": "trung bình", "diem_trinh_do": 0})
for _ in range(4):
    cu, moi = student.tu_dong_cap_nhat_trinh_do(SID, True)
check("4-dung-chua-len", (cu, moi) == ("trung bình", "trung bình")
      and store.doc_hs(SID)["diem_trinh_do"] == 4)
cu, moi = student.tu_dong_cap_nhat_trinh_do(SID, False)
check("1-sai-tru-ve-3", (cu, moi) == ("trung bình", "trung bình")
      and store.doc_hs(SID)["diem_trinh_do"] == 3)
for _ in range(2):
    cu, moi = student.tu_dong_cap_nhat_trinh_do(SID, True)
check("du-5-rong-len-kha", (cu, moi) == ("trung bình", "khá")
      and store.doc_hs(SID)["diem_trinh_do"] == 0)
check("tu-len-luu", store.doc_hs(SID)["trinh_do_toan"] == "khá")

# 3. Đủ -5 ròng mới xuống 1 bậc
for _ in range(4):
    cu, moi = student.tu_dong_cap_nhat_trinh_do(SID, False)
check("4-sai-chua-xuong", (cu, moi) == ("khá", "khá"))
cu, moi = student.tu_dong_cap_nhat_trinh_do(SID, False)
check("tu-xuong-trinh-do", (cu, moi) == ("khá", "trung bình"))

# 4. Đúng/sai xen kẽ quanh 0 thì giữ nguyên bậc
store.luu_hs(SID, {**store.doc_hs(SID), "trinh_do_toan": "trung bình", "diem_trinh_do": 0})
for kq in (True, False, True, True, False, False, True):
    cu, moi = student.tu_dong_cap_nhat_trinh_do(SID, kq)
check("xen-ke-giu-nguyen", (cu, moi) == ("trung bình", "trung bình")
      and store.doc_hs(SID)["diem_trinh_do"] == 1)

# 5. Video: tay vào ngay; tự động sau 3 lần gợi ý
check("video-tay", student.ghi_nhan_video(SID, "linkA") is True)
check("video-tay-luu", "linkA" in store.doc_hs(SID)["video_da_xem"])
check("video-goi-lan1", student.ghi_nhan_video(SID, "linkB", tu_dong=True) is False)
check("video-goi-lan2", student.ghi_nhan_video(SID, "linkB", tu_dong=True) is False)
check("video-goi-lan3", student.ghi_nhan_video(SID, "linkB", tu_dong=True) is True)
check("video-goi-luu", "linkB" in store.doc_hs(SID)["video_da_xem"])

# 6. Đổi trình độ -> context chat đổi theo (AI đọc hồ sơ mỗi lượt)
bat = {}
orig = student.llm.chat


def gia_chat(msgs):
    bat["system"] = msgs[0]["content"]
    return "ok\n```json\n{\"weaknesses\": [], \"bai_de_xuat\": [], \"can_cu_bank_ids\": [], \"bai_hien_tai\": \"\", \"video_goi_y\": \"\", \"muc_do_hieu\": \"tot\"}\n```"


student.llm.chat = gia_chat
hs = store.doc_hs(SID)
hs["trinh_do_toan"] = "giỏi"
store.luu_hs(SID, hs)
student.hs_chat(SID, "sin là gì")
check("prompt-theo-trinh-do", "trình độ=giỏi" in bat.get("system", ""), bat.get("system", "")[:60])
student.llm.chat = orig

don()
print("---")
print("THAT BAI:", fails if fails else "khong co")
sys.exit(1 if fails else 0)
