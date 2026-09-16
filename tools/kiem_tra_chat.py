import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import student, store

# Mock LLM: tra Socrates + JSON co ID that + ID bia
fake = """Trước hết em nhớ $\\pi$ rad $= 180^\\circ$ nhé. Vậy $315^\\circ$ bằng mấy $\\pi$?
```json
{"weaknesses": ["đổi độ sang radian còn chậm"], "bai_de_xuat": ["B1-TN-007", "BIA-999"], "can_cu_bank_ids": ["B1-TN-007"], "bai_hien_tai": "Bài 1. Giá trị lượng giác của góc lượng giác", "video_goi_y": "", "muc_do_hieu": "trung_binh"}
```"""
student.llm.chat = lambda msgs: fake

sid = "test_tmp_e2e"
tra_loi, extra = student.hs_chat(sid, "doi 315 do sang radian thế nào ạ")

ok = True


def check(name, cond, info=""):
    global ok
    print(("PASS " if cond else "FAIL ") + name, info)
    if not cond:
        ok = False


check("e2e_json_tach", "315" in tra_loi and "```json" not in tra_loi)
check("e2e_weakness", extra["diem_yeu"] == ["đổi độ sang radian còn chậm"], str(extra["diem_yeu"]))
check("e2e_idx_loc", extra["bai_de_xuat"] == ["B1-TN-007"], str(extra["bai_de_xuat"]))
check("e2e_cau_goi_y", len(extra["cau_goi_y"]) == 1 and extra["cau_goi_y"][0]["id"] == "B1-TN-007")
check("e2e_video", extra["video"] is not None and "youtu" in (extra["video"] or {}).get("link", ""))
hs = store.doc_hs(sid)
check("e2e_luu_hs", hs["bai_de_xuat"] == ["B1-TN-007"] and len(hs["weaknesses"]) == 1)
check("e2e_history", len(hs["history"]) == 2)

# lay cau theo id
from core import exercises
c = exercises.lay_cau_theo_id(sid, "B1-TN-007")
check("e2e_lay_cau", c and c["id"] == "B1-TN-007" and c["nguon"] == "kho GV")
check("e2e_lay_cau_ao", exercises.lay_cau_theo_id(sid, "KHONG-CO") is None)

os.remove(store.duong_dan_hs(sid))
print("THAT BAI: khong" if ok else "THAT BAI: co")
sys.exit(0 if ok else 1)
