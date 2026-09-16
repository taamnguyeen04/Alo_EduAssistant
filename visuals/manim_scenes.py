"""Preset Manim cho GV — CHỈ nhận tham số JSON qua biến môi trường.

Quy tắc an toàn (theo plan Phase 4f):
- Không sinh code Manim tự do. Mọi tham số đi qua MANIM_PRESET_JSON,
  được visuals/render.py kiểm tra trước khi gọi render.
- Chữ dùng Text (không dùng Tex) để khỏi phụ thuộc LaTeX trên máy GV.
- 3 preset bám Chương 1 + 9: đường tròn lượng giác, đồ thị hàm số,
  cát tuyến tiến về tiếp tuyến (định nghĩa đạo hàm).

Chạy tay (không qua app):
    set MANIM_PRESET_JSON={"angle_deg": 30}
    manim -qm visuals/manim_scenes.py UnitCircleScene
"""
import json
import math
import os

from manim import *

config.pixel_width = 854
config.pixel_height = 480  # 480p cho bản -ql nhanh


def doc_param():
    try:
        return json.loads(os.environ.get("MANIM_PRESET_JSON", "{}"))
    except Exception:
        return {}


class UnitCircleScene(Scene):
    """Đường tròn đơn vị: tia OM quét góc, chiếu sin/cos trực tiếp (Bài 1)."""

    def construct(self):
        p = doc_param()
        goc_do = float(p.get("angle_deg", 30)) % 360
        goc = math.radians(goc_do)
        R = 2.2

        duong_tron = Circle(radius=R, color=BLUE)
        truc_x = Line(LEFT * (R + 0.6), RIGHT * (R + 0.6), stroke_width=2)
        truc_y = Line(DOWN * (R + 0.6), UP * (R + 0.6), stroke_width=2)
        self.play(Create(duong_tron), Create(truc_x), Create(truc_y), run_time=1.2)
        self.play(Write(Text(f"Góc α = {goc_do:g}°", font="Arial", font_size=30).to_corner(UL)),
                  run_time=0.8)

        theta = ValueTracker(0.0)

        def tia():
            return Line(ORIGIN, R * np.array([math.cos(theta.get_value()),
                                              math.sin(theta.get_value()), 0]),
                        color=YELLOW, stroke_width=5)

        def diem_m():
            return Dot(R * np.array([math.cos(theta.get_value()),
                                     math.sin(theta.get_value()), 0]),
                       color=GREEN, radius=0.09)

        def cung():
            return Arc(radius=0.55, start_angle=0, angle=theta.get_value(),
                       color=YELLOW, stroke_width=4)

        def doan_sin():
            x = R * math.cos(theta.get_value())
            y = R * math.sin(theta.get_value())
            return Line(np.array([x, 0, 0]), np.array([x, y, 0]),
                        color=RED, stroke_width=5)

        def doan_cos():
            x = R * math.cos(theta.get_value())
            y = R * math.sin(theta.get_value())
            return Line(np.array([0, y, 0]), np.array([x, y, 0]),
                        color=BLUE_B, stroke_width=5)

        def nhan_sin():
            x = R * math.cos(theta.get_value())
            y = R * math.sin(theta.get_value())
            return Text(f"sin = {y / R:.2f}", font="Arial", font_size=24, color=RED
                        ).next_to(np.array([x, y / 2, 0]), RIGHT, buff=0.15)

        def nhan_cos():
            x = R * math.cos(theta.get_value())
            y = R * math.sin(theta.get_value())
            return Text(f"cos = {x / R:.2f}", font="Arial", font_size=24, color=BLUE_B
                        ).next_to(np.array([x / 2, y, 0]), UP, buff=0.15)

        self.add(always_redraw(tia), always_redraw(cung), always_redraw(diem_m),
                 always_redraw(doan_sin), always_redraw(doan_cos),
                 always_redraw(nhan_sin), always_redraw(nhan_cos))
        self.play(theta.animate.set_value(goc), run_time=4, rate_func=smooth)
        self.wait(2)


class FunctionGraphScene(Scene):
    """Đồ thị y = a·f(bx+c)+d, chấm chạy dọc đồ thị + đọc tọa độ (Bài 3)."""

    def construct(self):
        import numpy as np

        p = doc_param()
        ten = str(p.get("func", "sin"))
        a = float(p.get("a", 1.0))
        b = float(p.get("b", 1.0))
        c = float(p.get("c", 0.0))
        d = float(p.get("d", 0.0))
        f = {"sin": np.sin, "cos": np.cos, "tan": np.tan}[ten]

        axes = Axes(x_range=[-7, 7, 1], y_range=[-4.5, 4.5, 1],
                    x_length=10, y_length=5.2,
                    axis_config={"include_tip": True}).shift(DOWN * 0.4)
        self.play(Create(axes), run_time=1)
        self.play(Write(Text(f"y = {a:g}·{ten}({b:g}x+{c:g})+{d:g}", font="Arial",
                             font_size=28).to_corner(UL)), run_time=0.8)

        def y_cua(x):
            with np.errstate(divide="ignore", invalid="ignore"):
                v = a * f(b * x + c) + d
            return np.clip(v, -4.4, 4.4)

        do_thi = axes.plot(y_cua, x_range=[-7, 7], color=YELLOW)
        self.play(Create(do_thi), run_time=2)

        t = ValueTracker(-6.0)

        def cham_chay():
            return Dot(axes.c2p(t.get_value(), y_cua(t.get_value())),
                       color=RED, radius=0.09)

        def toa_do():
            x = t.get_value()
            return Text(f"({x:.2f} ; {y_cua(x):.2f})", font="Arial", font_size=24
                        ).next_to(axes.c2p(x, y_cua(x)), UP, buff=0.15)

        self.add(always_redraw(cham_chay), always_redraw(toa_do))
        self.play(t.animate.set_value(6.0), run_time=5, rate_func=linear)
        self.wait(1.5)


class DerivativeScene(Scene):
    """Cát tuyến tiến về tiếp tuyến khi h → 0 (định nghĩa đạo hàm, Bài 31)."""

    def construct(self):
        import numpy as np

        p = doc_param()
        bieu_thuc = str(p.get("expr", "x**2"))
        a = float(p.get("a", 1.0))
        h0 = max(float(p.get("h0", 2.0)), 0.3)

        def f(x):
            if bieu_thuc == "x**3":
                return x ** 3
            if bieu_thuc == "sin(x)":
                return np.sin(x)
            return x ** 2

        nhan_f = {"x**2": "x²", "x**3": "x³", "sin(x)": "sin x"}.get(bieu_thuc, bieu_thuc)
        lo, hi = a - 3.0, a + 3.0
        axes = Axes(x_range=[lo, hi, 1], y_range=[-1, max(f(hi), f(lo), 2) + 1, 1],
                    x_length=10, y_length=5.2,
                    axis_config={"include_tip": True}).shift(DOWN * 0.4)
        self.play(Create(axes), run_time=1)
        self.play(Write(Text(f"y = {nhan_f}  tại x = {a:g}", font="Arial", font_size=28).to_corner(UL)),
                  run_time=0.8)

        do_thi = axes.plot(f, x_range=[lo, hi], color=YELLOW)
        self.play(Create(do_thi), run_time=1.5)

        h = ValueTracker(h0)
        fa = float(f(a))

        def cat_tuyen():
            hh = max(h.get_value(), 1e-6)
            fb = float(f(a + hh))
            x1, x2 = a - 2.5, a + 2.5
            y1 = fa + (fb - fa) / hh * (x1 - a)
            y2 = fa + (fb - fa) / hh * (x2 - a)
            return Line(axes.c2p(x1, y1), axes.c2p(x2, y2),
                        color=ORANGE, stroke_width=4)

        def nhan_doc():
            hh = max(h.get_value(), 1e-6)
            fb = float(f(a + hh))
            return Text(f"h = {hh:.2f}   dốc ≈ {(fb - fa) / hh:.2f}", font="Arial",
                        font_size=26, color=ORANGE).to_corner(UR)

        self.add(always_redraw(cat_tuyen), always_redraw(nhan_doc))
        self.play(h.animate.set_value(0.15), run_time=5, rate_func=smooth)

        # Chốt tiếp tuyến
        e = 1e-5
        dd = (float(f(a + e)) - float(f(a - e))) / (2 * e)
        x1, x2 = a - 2.5, a + 2.5
        tiep = Line(axes.c2p(x1, fa + dd * (x1 - a)),
                    axes.c2p(x2, fa + dd * (x2 - a)), color=RED, stroke_width=5)
        self.play(Create(tiep),
                  Write(Text(f"Tiếp tuyến, f'({a:g}) ≈ {dd:.2f}", font="Arial",
                            font_size=26, color=RED).to_corner(DR)),
                  run_time=1.5)
        self.wait(2)
