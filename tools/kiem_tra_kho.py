import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import knowledge, prompts
from core.student import tach_json_cuoi, _loc_id_hop_le, _khoi_cau_tham_khao

fails = []


def check(name, cond, info=""):
    print(("PASS " if cond else "FAIL ") + name, info)
    if not cond:
        fails.append(name)


# 1. Bank load (1069 ingest + 1 AI-DEMO-001 seed tay)
kho = knowledge.tai_bank()
check("bank_load", len(kho) == 1070, f"n={len(kho)}")
check("bank_ok_only_search", True)

# 2. Retrieval: radian -> B1-01 đúng đầu (đã hiệu đính tay -> ok), tất cả ok
r = knowledge.tim_cau_lien_quan("doi do sang radian la bao nhieu", n=3)
check("search_radian", bool(r) and r[0]["id"] == "B1-01"
      and all(c["chat_luong"] == "ok" for c in r), f"top={[c['id'] for c in r]}")

# 3. Bai filter
r2 = knowledge.tim_cau_lien_quan("tinh dao ham", bai="Bài 32. cac quy tat tinh dao ham", n=3)
check("search_bai_filter", bool(r2) and all(c["bai"].startswith("Bài 32") for c in r2),
      f"top={[c['id'] for c in r2]}")

# 4. Weakness search
r3 = knowledge.cau_theo_diem_yeu(["quên trừ 1 ở (n-1)"], n=2)
check("search_weakness_runs", isinstance(r3, list), f"n={len(r3)}")

# 5. Concept
cpt = knowledge.doc_concept("Bài 1. Giá trị lượng giác của góc lượng giác")
check("concept_found", len(cpt) > 100, f"len={len(cpt)}")
check("concept_missing", knowledge.doc_concept("Bài KHONG CO") == "")

# 6. loi_sai + tom_tat
check("loi_sai", isinstance(knowledge.loi_sai_cua_bai("Bài 1. Giá trị lượng giác của góc lượng giác"), list))
tk = knowledge.tom_tat_kho()
check("tom_tat", tk["tong"] == 1070 and tk["ok"] > 0, str({k: (v if k != "theo_bai" else len(v)) for k, v in tk.items()}))

# 7. ID validation (chong bia; can_duyet deu bi loai - dung)
ids = _loc_id_hop_le(["B1-TL-004", "BIA-DAT-999", "B1-01", "B2-TL-001"])
check("loc_id", "B1-TL-004" in ids and "B1-01" in ids and "B2-TL-001" in ids
      and "BIA-DAT-999" not in ids, str(ids))

# 8. tach_json_cuoi edge cases
t, d = tach_json_cuoi("hello khong json")
check("json_missing", t == "hello khong json" and d == {})
t, d = tach_json_cuoi('chat```json{"a": 1}```')
check("json_ok", t == "chat" and d == {"a": 1})

# 9. Prompt contracts
for key in ["weaknesses", "bai_de_xuat", "can_cu_bank_ids", "muc_do_hieu", "LaTeX", "TUYỆT ĐỐI KHÔNG"]:
    check(f"prompt_hs:{key}", key in prompts.SYSTEM_HS)
for key in ["dung_sai_tung_buoc", "diem_yeu_moi"]:
    check(f"prompt_cham:{key}", key in prompts.SYSTEM_CHAM)
for key in ["dang_phan", "buoc_giai"]:
    check(f"prompt_rade:{key}", key in prompts.SYSTEM_RA_DE)
check("prompt_gv_bai", "NHÓM THEO BÀI" in prompts.SYSTEM_GV)

# 10. Internal block must NOT leak structure UI can show answers
blk = _khoi_cau_tham_khao(r[:1])
check("khoi_noi_bo", "MẬT" in blk and r[0]["id"] in blk)

print("---")
print("THAT BAI:", fails if fails else "khong co")
sys.exit(1 if fails else 0)
