import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import manim_ai
from core import llm
from visuals import render as manim_render

GOOD = """from manim import *
class GeneratedScene(Scene):
    def construct(self):
        self.play(Write(Text("Xin chao", font_size=40)), run_time=1)
        self.wait(1)
"""

GOOD_CAMERA = """from manim import *
class GeneratedScene(MovingCameraScene):
    def construct(self):
        t = Text("Zoom vao day", font_size=36)
        self.play(Write(t), run_time=1)
        self.camera.frame.save_state()
        self.play(self.camera.frame.animate.scale(0.5).move_to(t), run_time=1)
        self.wait(1)
"""

# 1. Code độc hại / sai luật đều rớt (validator v2)
xau = [
    ("import os\n" + GOOD, "import os"),
    ("from manim import *\nimport subprocess\nclass GeneratedScene(Scene):\n    def construct(self):\n        pass",
     "import subprocess"),
    ("from manim import *\nclass GeneratedScene(Scene):\n    def construct(self):\n        open('x','w')", "open()"),
    ("from manim import *\nclass GeneratedScene(Scene):\n    def construct(self):\n        x = eval('1')", "eval()"),
    ("from manim import *\nclass Khac(Scene):\n    def construct(self):\n        pass", "sai tên class"),
    ("from manim import *\nclass GeneratedScene(Scene):\n    def construct(self):\n        while True:\n            pass", "while"),
    ("from manim import *\nclass GeneratedScene(Scene)\n    def construct(self):\n        pass", "syntax"),
    ("", "rỗng"),
    ("from manim import *\nclass GeneratedScene(Scene):\n    def construct(self):\n        pass\n" * 200, "quá dài/sai cấu trúc"),
    ("from manim import *\nimport numpy as np\nclass GeneratedScene(Scene):\n    def construct(self):\n        a = os.system('x')", "os.system"),
    # Luật mới của v2 (v1 cho lọt hoặc không kiểm tra)
    ("from manim import *\nclass GeneratedScene(Scene):\n    def construct(self):\n        self.add(ImageMobject('a.png'))", "ImageMobject đọc file"),
    ("from manim import *\nclass GeneratedScene(Scene):\n    def construct(self):\n        xs = list(range(100000))", "range() khổng lồ"),
    ("from manim import *\nclass GeneratedScene(Scene):\n    async def construct(self):\n        pass", "async construct"),
    ("from manim import *\nimport numpy as np\nclass GeneratedScene(Scene):\n    def construct(self):\n        a = np.load('x.npy')", "np.load đọc file"),
    ("from manim import *\nclass GeneratedScene(Circle):\n    def construct(self):\n        pass", "base lạ"),
]
for code, ten in xau:
    ok, ly_do = manim_ai.kiem_tra_code(code)
    assert not ok, f"LOT {ten}"
    print(f"PASS chan: {ten} ({ly_do[:60]})")

# 2. Code lành qua được (Scene thường + MovingCameraScene mới của v2)
for ten, code in [("scene thường", GOOD), ("moving camera", GOOD_CAMERA)]:
    ok, ly_do = manim_ai.kiem_tra_code(code)
    assert ok, f"{ten}: {ly_do}"
    print(f"PASS nhan code lanh ({ten})")

# 3. trich_code lấy đúng khối fence (python/py)
raw = "Giải thích dài dòng\n```python\n" + GOOD + "\n```\nthêm chữ"
assert manim_ai.trich_code(raw).strip() == GOOD.strip()
raw2 = "```py\n" + GOOD + "\n```"
assert manim_ai.trich_code(raw2).strip() == GOOD.strip()
print("PASS trich fence")

# 4. _trich_json đọc được storyboard lồng nhau, kể cả bọc ```json
PLAN_THAT = {
    "title": "Chao lop", "learning_goal": "HS thay chu chao",
    "output": "video", "scene_type": "Scene", "duration_target_sec": 10,
    "must_include": ["Text Xin chao"], "must_not_include": [],
    "style": {"background": "dark", "layout": "center", "color_semantics": {}},
    "manim_features": ["Write", "Text"],
    "steps": [{"id": 1, "purpose": "chao", "objects": ["Text"],
               "action": "hien chu o giua", "labels_or_math": ["Xin chao"],
               "camera": "none", "timing_sec": 2.0}],
    "final_frame": "Chu Xin chao o giua man hinh",
}
fenced = "```json\n" + json.dumps(PLAN_THAT, ensure_ascii=False) + "\n```"
assert manim_ai._trich_json("Xem storyboard nè:\n" + fenced + "\nxong") == PLAN_THAT
print("PASS trich json storyboard")

# 4b. JSON vỡ vì backslash LaTeX đơn (\frac, \sin, \neq) vẫn đọc được
vo = ('{"title": "t", "learning_goal": "g", "output": "video", '
      '"scene_type": "Scene", "steps": [{"id": 1, "labels_or_math": '
      '["$\\frac{1}{2}$", "$x \\neq \\sin\\beta$"]}]}')
doc = manim_ai._trich_json(vo)
assert doc["steps"][0]["labels_or_math"][0] == "$\\frac{1}{2}$", doc
assert doc["steps"][0]["labels_or_math"][1] == "$x \\neq \\sin\\beta$", doc
vo2 = '{"a": "x \\q b", "steps": [{"id": 1}]}'  # escape lạ \q
assert manim_ai._trich_json(vo2)["a"] == "x \\q b"
print("PASS trich json chua backslash don LaTeX")

# 4c. Planner vỡ JSON lần 1 -> tự thử lại lần 2 (mock), không văng lỗi ra UI
dem = {"n": 0}
GOOD_PLAN_TXT = json.dumps(PLAN_THAT, ensure_ascii=False)
VO_PLAN_TXT = GOOD_PLAN_TXT.replace("Xin chao", "Xin $\\chao \\frac{a}{b}$", 1)


def gia_plan(msgs, timeout=60):
    dem["n"] += 1
    if dem["n"] == 1:
        return "{hong json"  # vỡ hẳn, chữa escape cũng không cứu được
    return GOOD_PLAN_TXT


llm.chat = gia_plan
plan2 = manim_ai.lap_ke_hoach("mô tả thử", bai="Bài 1", output="video")
assert plan2["steps"] and dem["n"] == 2, dem
print("PASS planner tu thu lai sau JSON vo")

# 5. Render thật 1 scene ngắn (pipeline code->mp4 + previews của render v2)
r = manim_render.render_code(GOOD, quality="l", timeout=300, preview_count=2)
assert r["mp4"] and os.path.getsize(r["mp4"]) > 5000, r["log"][-300:]
assert isinstance(r.get("previews"), list)
print("PASS render that:", os.path.basename(r["mp4"]), os.path.getsize(r["mp4"]),
      "bytes, previews:", len(r.get("previews") or []))

# 6-8. End-to-end với LLM mock (không tốn token): planner -> coder -> critic
AUDIT_OK = {"needs_revision": False,
            "scores": {"prompt_fidelity": 5, "subject_correctness": 5,
                       "visual_layout": 4, "animation_pedagogy": 4, "manim_power": 3},
            "issues": [], "summary": "Dat."}


def mock_router(code_lan1):
    state = {"coder": 0}

    def gia(msgs, timeout=60):
        system = msgs[0]["content"] if msgs else ""
        if "```python" in system:  # coder / sửa code
            state["coder"] += 1
            code = code_lan1 if state["coder"] == 1 else GOOD
            return "```python\n" + code + "\n```"
        if "reviewer" in system.lower():  # critic
            return json.dumps(AUDIT_OK, ensure_ascii=False)
        return json.dumps(PLAN_THAT, ensure_ascii=False)  # planner

    return gia, state


# 6. Gen ok ngay lần 1
gia6, st6 = mock_router(GOOD)
llm.chat = gia6
kq = manim_ai.sinh_video_tu_mo_ta("video chào lớp", bai="Bài 1", quality="l", timeout=300)
assert kq["mp4"] and kq["code"].strip() == GOOD.strip(), kq["log"][-300:]
assert kq.get("plan", {}).get("steps"), "thiếu storyboard trong kết quả"
assert "audit" in kq, "thiếu audit trong kết quả"
assert st6["coder"] == 1, st6
print("PASS flow mock lan 1 (plan + critic + cache)")

# 7. Coder hỏng lần 1 (import os) -> validator bắt -> tự sửa -> ra GOOD
BAD = "from manim import *\nimport os\nclass GeneratedScene(Scene):\n    def construct(self):\n        pass"
gia7, st7 = mock_router(BAD)
llm.chat = gia7
kq = manim_ai.sinh_video_tu_mo_ta("video chào lớp", bai="Bài 1", quality="l", timeout=300)
assert kq["mp4"], kq["log"][-300:]
assert kq["code"].strip() == GOOD.strip(), "bản sửa phải ra code GOOD"
assert st7["coder"] == 2, st7
print("PASS tu sua sau validator lan 2")

# 9. Prompt coder khóa luật tọa độ 3 phần tử (lỗi broadcast (3,) vs (2,))
src_ai = open("core/manim_ai.py", encoding="utf-8").read()
assert "[x, y, 0]" in src_ai
print("PASS prompt khoa toa do 3 phan tu")

# 10. Vòng sửa broadcast: log lỗi shape -> prompt sửa có cheat-sheet + cấm trả rỗng,
#     code sửa được render (mock), kết quả giữ code mới
CODE_2D = ("from manim import *\nimport numpy as np\n"
           "class GeneratedScene(Scene):\n"
           "    def construct(self):\n"
           "        d = np.array([np.cos(0.5), np.sin(0.5)])\n"
           "        t = Text('x', font_size=24)\n"
           "        t.move_to(ORIGIN + d * 0.4)\n"
           "        self.add(t)\n"
           "        self.wait(0.5)\n")
bat = {}
orig_render = manim_render.render_code


def gia_render(code, quality="l", timeout=300, **kw):
    if "np.cos(0.5), np.sin(0.5)])" in code:
        return {"mp4": "", "cached": False,
                "log": "ValueError: operands could not be broadcast together with shapes (3,) (2,)"}
    return {"mp4": "VID.mp4", "cached": False, "log": "Render xong."}


manim_render.render_code = gia_render


def gia_sua(msgs, timeout=60):
    bat["user"] = msgs[-1]["content"]
    return "```python\n" + GOOD + "\n```"


llm.chat = gia_sua
plan_gia = {"output": "video", "steps": [{"id": 1}], "scene_type": "Scene"}
code_sua = manim_ai.sua_code_theo_log(plan_gia, CODE_2D, "broadcast shapes (3,) (2,)", "mô tả", "toan11", 60)
assert code_sua.strip() == GOOD.strip(), "sua phai tra full code GOOD"
assert "KHÔNG TRỐNG" in bat["user"], "prompt sua thieu cam tra rong"
assert "broadcast" in bat["user"], "prompt sua thieu cheat-sheet"
manim_render.render_code = orig_render  # trả lại render thật cho các test sau
print("PASS sua theo log broadcast (prompt + full code)")

# 11. trich_code rỗng -> kiem_tra_code báo đúng bệnh (UI hiển thị được)
ok, ly_do = manim_ai.kiem_tra_code(manim_ai.trich_code("xin lỗi, tôi không làm được"))
assert not ok and ly_do, ly_do
print("PASS trich rong -> validator bao ro:", ly_do[:60])

# 12. Visual Director v3: TeachingScene qua validator, tự định nghĩa lại thì rớt
GOOD_TEACH = """from manim import *
class GeneratedScene(TeachingScene):
    def construct(self):
        self.noi("Day la duong tron don vi")
        c = Circle(radius=2)
        self.play(Create(c), run_time=1)
        self.dan_nhan(c, "R = 1", huong="right")
        self.noi("Ket luan")
        self.wait(1)
"""
ok, ly_do = manim_ai.kiem_tra_code(GOOD_TEACH)
assert ok, f"TeachingScene phai qua validator: {ly_do}"
print("PASS validator nhan TeachingScene")
DINH_NGHIA_LAI = ("from manim import *\nclass TeachingScene(MovingCameraScene):\n    pass\n"
                  "class GeneratedScene(TeachingScene):\n    def construct(self):\n        pass")
ok, ly_do = manim_ai.kiem_tra_code(DINH_NGHIA_LAI)
assert not ok, "AI khong duoc dinh nghia lai TeachingScene"
print("PASS chan AI dinh nghia lai TeachingScene")

# 13. Preamble + TeachingScene render thật ra mp4 (caption thay nhau, không nổ)
r = manim_render.render_code(manim_ai._ma_render(GOOD_TEACH), quality="l", timeout=300)
assert r["mp4"] and os.path.getsize(r["mp4"]) > 5000, r["log"][-300:]
print("PASS render TeachingScene + caption bar:", os.path.basename(r["mp4"]))

# 13b. Shim mau legacy (Manim 0.21): MAGENTA/CYAN van render duoc
MAU_CU = """from manim import *
class GeneratedScene(TeachingScene):
    def construct(self):
        c = Circle(radius=2, color=MAGENTA)
        self.play(Create(c), run_time=0.5)
        d = Dot(color=CYAN)
        self.play(FadeIn(d), run_time=0.5)
        self.wait(0.5)
"""
ok, ly_do = manim_ai.kiem_tra_code(MAU_CU)
assert ok, f"code mau cu phai qua validator: {ly_do}"
r = manim_render.render_code(manim_ai._ma_render(MAU_CU), quality="l", timeout=300)
assert r["mp4"] and os.path.getsize(r["mp4"]) > 5000, r["log"][-300:]
print("PASS shim MAGENTA/CYAN render that:", os.path.basename(r["mp4"]))

# 14. Lint bố cục: code nhồi nhãn bị bắt, code gọn im lặng
ROI = """from manim import *
class GeneratedScene(Scene):
    def construct(self):
        self.add(Text("M(cos a; sin a)"), Text("x=cos a"), Text("y=sin a"),
                 Text("R=1"), Text("I(1;0)"), Text("a=60"), Text("ghi chu"))
        self.wait(1)
"""
cb = manim_ai.kiem_tra_bo_cuc(ROI)
assert len(cb) >= 2, cb
print("PASS lint bat code roi:", len(cb), "canh bao")
assert manim_ai.kiem_tra_bo_cuc(GOOD) == [], "code gon khong duoc canh bao"
assert manim_ai.kiem_tra_bo_cuc(GOOD_TEACH) == [], "code TeachingScene chuan khong duoc canh bao"
print("PASS lint im lang voi code gon")

# 15. Prompt có đủ luật Visual Director (planner reveal + coder + critic layout)
src = open("core/manim_ai.py", encoding="utf-8").read()
for cum in ["VISUAL PEDAGOGY RULES", "self.noi(", '"caption"', '"hide"',
            "Maximum visible labels", "narration must use caption bar",
            "too many simultaneous labels"]:
    assert cum in src, f"thieu luat: {cum}"
# 16. dan_nhan nhận cả vector (DOWN+LEFT) lẫn chuỗi ("right") — lỗi unhashable cũ
HUONG = """from manim import *
class GeneratedScene(TeachingScene):
    def construct(self):
        o = Dot(ORIGIN, color=WHITE)
        self.add(o)
        self.dan_nhan(o, "O", huong=DOWN + LEFT)
        self.dan_nhan(o, "O2", huong="right")
        self.wait(0.5)
"""
ok, ly_do = manim_ai.kiem_tra_code(HUONG)
assert ok, f"dan_nhan vector phai qua validator: {ly_do}"
r = manim_render.render_code(manim_ai._ma_render(HUONG), quality="l", timeout=300)
assert r["mp4"] and os.path.getsize(r["mp4"]) > 5000, r["log"][-300:]
print("PASS dan_nhan vector + chuoi render that:", os.path.basename(r["mp4"]))

# 17. Vòng sửa gặp AI trả rỗng -> tự thử lại 1 lần rồi mới chịu thua
dem_rong = {"n": 0}


def gia_rong(msgs, timeout=60):
    dem_rong["n"] += 1
    if dem_rong["n"] == 1:
        return "   "
    return "```python\n" + GOOD + "\n```"


llm.chat = gia_rong
code_lai = manim_ai._goi_code_co_thu_lai("system", "user", 60)
assert code_lai.strip() == GOOD.strip() and dem_rong["n"] == 2, dem_rong
print("PASS tu thu lai khi AI tra rong")

llm.chat = lambda msgs, timeout=60: "   "
assert manim_ai._goi_code_co_thu_lai("system", "user", 60) == ""
# 18. Validator bắt axes.plot(t_range=) — API cũ gây TypeError trên Manim 0.21
PLOT_CU = ("from manim import *\nimport numpy as np\nclass GeneratedScene(Scene):\n"
           "    def construct(self):\n"
           "        ax = Axes()\n"
           "        c = ax.plot(lambda t: np.array([np.cos(t), np.sin(t), 0]), t_range=[0, 1])\n"
           "        self.add(ax, c)\n")
ok, ly_do = manim_ai.kiem_tra_code(PLOT_CU)
assert not ok and "x_range" in ly_do, ly_do
print("PASS validator chan plot(t_range=):", ly_do[:70])
PLOT_MOI = ("from manim import *\nclass GeneratedScene(Scene):\n"
            "    def construct(self):\n"
            "        ax = Axes(x_range=[-3, 3, 1], y_range=[-1, 9, 1])\n"
            "        c = ax.plot(lambda x: x**2, x_range=[-2, 2, 0.1], color=YELLOW)\n"
            "        self.play(Create(ax), Create(c), run_time=1)\n"
            "        self.wait(0.5)\n")
ok, ly_do = manim_ai.kiem_tra_code(PLOT_MOI)
assert ok, f"plot(x_range=) phai qua: {ly_do}"
r = manim_render.render_code(manim_ai._ma_render(PLOT_MOI), quality="l", timeout=300)
assert r["mp4"] and os.path.getsize(r["mp4"]) > 5000, r["log"][-300:]
# 19. Validator bắt Text Việt thiếu font="Arial" (ô vuông trắng), ASCII/Greek tha
TIEU_DE_THIEU = ("from manim import *\nclass GeneratedScene(Scene):\n"
                 "    def construct(self):\n"
                 '        t = Text("Đường tròn lượng giác", font_size=36)\n'
                 "        self.add(t)\n")
ok, ly_do = manim_ai.kiem_tra_code(TIEU_DE_THIEU)
assert not ok and "Arial" in ly_do, ly_do
print("PASS validator chan Text Viet thieu font:", ly_do[:60])
TIEU_DE_DU = TIEU_DE_THIEU.replace('font_size=36', 'font="Arial", font_size=36')
ok, ly_do = manim_ai.kiem_tra_code(TIEU_DE_DU)
assert ok, f"Text Viet co Arial phai qua: {ly_do}"
ASCII_OK = ("from manim import *\nclass GeneratedScene(Scene):\n"
            "    def construct(self):\n"
            '        self.add(Text("Ox"), Text("O"), Text("\\u03b1"))\n')
ok, ly_do = manim_ai.kiem_tra_code(ASCII_OK)
assert ok, f"Text ASCII/Greek khong can Arial: {ly_do}"
# 20. Lint bắt lệch đơn vị: coords_to_point + Circle(radius=số cứng)
LECH = ("from manim import *\nclass GeneratedScene(Scene):\n"
        "    def construct(self):\n"
        "        ax = Axes(x_range=[-1.5, 1.5, 0.5], y_range=[-1.5, 1.5, 0.5])\n"
        "        tron = Circle(radius=1.0, color=BLUE).move_to(ORIGIN)\n"
        "        M = Dot(ax.coords_to_point(1, 0, 0))\n"
        "        self.add(ax, tron, M)\n")
cb = manim_ai.kiem_tra_bo_cuc(LECH)
assert any("get_unit_size" in w for w in cb), cb
print("PASS lint bat lech don vi toa do")
CHUAN = LECH.replace("Circle(radius=1.0, color=BLUE).move_to(ORIGIN)",
                     "Circle(radius=ax.x_axis.get_unit_size(), color=BLUE).move_to(ax.coords_to_point(0, 0, 0))")
assert not any("get_unit_size" in w for w in manim_ai.kiem_tra_bo_cuc(CHUAN)), CHUAN
print("PASS lint im lang voi don vi thong nhat")
print("THAT BAI: khong")
