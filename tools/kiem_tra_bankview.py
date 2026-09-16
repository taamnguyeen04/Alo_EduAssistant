import glob
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.bank_view import tach_phuong_an, dap_an_dung, lam_dep

tot_tn = tach_ok = co_pa = 0
loi = []
for f in sorted(glob.glob("data/bank/*.json")):
    for c in json.load(open(f, encoding="utf-8")):
        if c.get("dang") != "TN":
            continue
        tot_tn += 1
        than, pas = tach_phuong_an(c.get("de", ""))
        if len(pas) >= 2:
            co_pa += 1
        if len(pas) >= 2 and dap_an_dung(c.get("dap_an", "")):
            tach_ok += 1
        elif len(pas) < 2:
            loi.append((c.get("id"), len(pas), (c.get("dap_an", "") or "")[:20]))

print(f"TN tach duoc A-D: {co_pa}/{tot_tn} | + dap an ro: {tach_ok}/{tot_tn}")
for lid, n, da in loi[:10]:
    print("  KHONG TACH:", lid, "pas:", n, "da:", da)

# Mau hien thi that
d = json.load(open(sorted(glob.glob("data/bank/*.json"))[0], encoding="utf-8"))
c = next(x for x in d if x.get("dang") == "TN")
than, pas = tach_phuong_an(c["de"])
print("THAN:", lam_dep(than))
for nhan, nd in pas:
    dau = "✅" if nhan == dap_an_dung(c["dap_an"]) else "  "
    print(f"{dau} {nhan}. {lam_dep(nd)}")
assert co_pa / max(tot_tn, 1) >= 0.8, "ty le tach A-D thap"
print("THAT BAI: khong")
