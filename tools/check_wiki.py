import glob
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIKI = os.path.join(base, "data", "wiki")
files = glob.glob(os.path.join(WIKI, "**", "*.md"), recursive=True)
links = []
for f in files:
    for m in re.finditer(r"\[\[([^\]]+)\]\]", open(f, encoding="utf-8").read()):
        links.append((f, m.group(1).split("|")[0]))
bad = [(f, t) for f, t in links
       if not os.path.exists(os.path.join(WIKI, t if t.endswith(".md") else t + ".md"))]
print("md files:", len(files), "| links:", len(links), "| broken:", len(bad))
for f, t in bad[:10]:
    print("GAY:", os.path.basename(f), "->", t)
# xem mau 1 concept + 1 source
print("---- concept mau ----")
first = sorted(os.listdir(os.path.join(WIKI, "concepts")))[0]
print(open(os.path.join(WIKI, "concepts", first), encoding="utf-8").read()[:700])
