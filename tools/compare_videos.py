import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
from docx import Document

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

d = Document("Tổng hợp nội dung Toán học 11.docx")
seen = []
for rel in d.part.rels.values():
    if "hyperlink" in rel.reltype and rel.target_ref not in seen:
        seen.append(rel.target_ref)

vd = json.load(open(os.path.join(BASE_DIR, "data", "video_data.json"), encoding="utf-8"))
vlinks = [v["link"] for v in vd]

print("docx unique links:", len(seen))
print("video_data links:", len(vlinks))
print("missing in video_data:", [u for u in seen if u not in vlinks] or "KHONG")
print("missing in docx:", [u for u in vlinks if u not in seen] or "KHONG")

# so sanh content theo tung bai
paras = [p.text for p in d.paragraphs]
for v in vd:
    title = v["title"]
    try:
        i = paras.index(title)
    except ValueError:
        print("KHONG THAY TRONG DOCX:", title)
        continue
    link = paras[i + 1] if i + 1 < len(paras) else ""
    nd = []
    j = i + 2
    if j < len(paras) and paras[j].strip().lower().startswith("n"):
        j += 1
    while j < len(paras) and not paras[j].startswith("Bài ") and not paras[j].startswith("CHƯƠNG"):
        if paras[j].strip():
            nd.append(paras[j].strip("· ").strip())
        j += 1
    ok_link = "OK" if v["link"] in link else "LECH:" + link[:60]
    ok_nd = "OK" if nd == v["content"] else f"LECH({len(nd)}vs{len(v['content'])})"
    print(f"{title[:35]:35s} link={ok_link} nd={ok_nd}")
