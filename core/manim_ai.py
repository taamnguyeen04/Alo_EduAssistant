"""Manim AI v2 - Natural language -> pedagogical plan -> Manim code -> audit -> render.

Drop-in upgrade for the old manim_ai.py.

Main differences:
1) Do NOT jump directly from teacher prompt to code. First build a strict visual plan JSON.
2) Code generator receives the plan + a Manim capability guide.
3) A second AI pass audits fidelity, mathematical correctness, layout and animation quality.
4) Static AST validator allows advanced Manim scene types while blocking dangerous Python/file access.
5) Render errors can be repaired up to 2 times.
6) The same pipeline can generate MP4 video or a PNG final-frame illustration.

The public function sinh_video_tu_mo_ta keeps the old signature compatible.
"""
from __future__ import annotations

import ast
import json
import re
from typing import Any, Dict, List, Tuple

from . import llm

try:
    from . import prompts as _legacy_prompts
except Exception:  # pragma: no cover - optional compatibility
    _legacy_prompts = None

# In the real project this is visuals/render.py.
from visuals import render as manim_render

# ---------------------------------------------------------------------------
# Safety / static validation
# ---------------------------------------------------------------------------

_MODULE_OK = {"manim", "math", "numpy"}
_SCENE_BASE_OK = {
    "Scene",
    "MovingCameraScene",
    "TeachingScene",
    "ThreeDScene",
    "SpecialThreeDScene",
    "ZoomedScene",
    "LinearTransformationScene",
    "VectorScene",
}

# Preamble nền tảng: lớp TeachingScene có sẵn trong môi trường render cho code AI.
# - self.noi(text): dải thuyết minh ĐỘC QUYỀN ở đáy màn hình, câu sau tự thay câu trước
#   (chống chồng chữ theo cấu trúc, không cần kiểm tra vùng trống).
# - self.dan_nhan(obj, text, huong): nhãn ngắn gắn chuẩn bằng next_to, chữ gọn.
# AI KHÔNG được định nghĩa lại lớp này (validator bắt đúng 1 class GeneratedScene).
# Preamble cố ý tránh mọi tên trong danh sách cấm để code render nối vào vẫn sạch.
_PREAMBLE_DAY_HOC = """
from manim import *
import numpy as np

# Manim >= 0.21 đã xóa bí danh màu cũ MAGENTA/CYAN (giờ là PURE_MAGENTA/PURE_CYAN).
# Shim này giữ code AI cũ/chuẩn cũ vẫn render được; code mới nên dùng thẳng tên PURE_*.
try:
    MAGENTA
except NameError:
    MAGENTA = PURE_MAGENTA
try:
    CYAN
except NameError:
    CYAN = PURE_CYAN


class TeachingScene(MovingCameraScene):
    _VUNG_NOI_Y = -3.3
    _RONG_NOI_TOI_DA = 13.0

    def noi(self, text, mau=WHITE, co_chu=28):
        chu = Text(str(text), font="Arial", font_size=co_chu, color=mau)
        chu.set_max_width(self._RONG_NOI_TOI_DA)
        chu.move_to(DOWN * 3.3)
        try:
            cu = self._dong_noi
        except AttributeError:
            cu = None
        if cu is not None:
            self.play(FadeOut(cu, run_time=0.25))
        self._dong_noi = chu
        self.play(FadeIn(chu, run_time=0.35))

    def dan_nhan(self, doi_tuong, text, huong="right", mau=YELLOW, co_chu=24):
        # huong: "right"/"left"/"up"/"down"/"up_left"/... hoặc vector Manim
        # (DOWN+LEFT, UL, ...) — truyền thẳng cho next_to, không dùng làm key dict.
        if isinstance(huong, str):
            huong_map = {"right": RIGHT, "left": LEFT, "up": UP, "down": DOWN,
                         "up_left": UL, "up_right": UR,
                         "down_left": DL, "down_right": DR}
            huong = huong_map.get(huong, RIGHT)
        nhan = Text(str(text), font="Arial", font_size=co_chu, color=mau)
        nhan.next_to(doi_tuong, huong, buff=0.25)
        self.play(FadeIn(nhan, run_time=0.3))
        return nhan
""".strip()


def _ma_render(code: str) -> str:
    """Nối preamble TeachingScene trước code AI để render (code AI giữ nguyên để lưu)."""
    return _PREAMBLE_DAY_HOC + "\n\n" + (code or "").strip() + "\n"

_TEN_CAM = {
    "open", "exec", "eval", "compile", "__import__", "globals", "locals",
    "vars", "getattr", "setattr", "delattr", "hasattr", "input", "exit",
    "quit", "help", "breakpoint", "memoryview", "os", "sys", "subprocess",
    "socket", "pathlib", "shutil", "requests", "urllib", "http", "threading",
    "multiprocessing", "asyncio", "ctypes", "inspect", "importlib", "pickle",
    "system", "popen", "config",
}

# Block direct/indirect file/process/network entry points, including common numpy I/O.
_THUOC_TINH_CAM = {
    "system", "popen", "execl", "execle", "execlp", "execlpe", "execv",
    "execve", "execvp", "execvpe", "spawnl", "spawnle", "spawnlp", "spawnlpe",
    "spawnv", "spawnve", "spawnvp", "spawnvpe",
    "load", "save", "savez", "savez_compressed", "loadtxt", "savetxt",
    "open_memmap", "DataSource",
    "genfromtxt", "fromfile", "tofile", "memmap", "ctypeslib",
    "add_sound", "get_file_writer",
}

# These Manim mobjects accept file paths. Keep them out of generated code unless
# you later add a trusted asset service and explicit allow-listing.
_MANIM_DOI_TUONG_DOC_FILE_CAM = {
    "ImageMobject", "SVGMobject", "Code", "OpenGLImageMobject",
}

TOI_DA_CODE = 24000
TOI_DA_PLAY = 90
TOI_DA_RANGE_LITERAL = 1200


def trich_code(text: str) -> str:
    """Extract first fenced Python block; otherwise use the whole response."""
    m = re.search(r"```(?:python|py)\s*(.*?)```", text or "", re.S | re.I)
    if m:
        return m.group(1).strip()
    return (text or "").strip()


def _sua_escape_json(s: str) -> str:
    """Chữa backslash đơn của AI (LaTeX \\frac, \\sin...) thành \\\\ để json.loads nuốt được.

    Quy ước storyboard: backslash + chữ cái gần như luôn là lệnh LaTeX, không phải
    escape JSON. Chỉ giữ nguyên các escape thật: \\", \\\\, \\/ và \\uXXXX hợp lệ.
    Lookbehind (?<!\\\\) đảm bảo không "ăn" lại backslash đã nhân đôi ở bước trước.
    """
    s = re.sub(r'(?<!\\)\\u(?![0-9a-fA-F]{4})', r'\\\\u', s)  # \u hỏng mã hex
    s = re.sub(r'(?<!\\)\\(?!u[0-9a-fA-F]{4})([A-Za-z])', r'\\\\\1', s)  # \latex -> \\latex
    s = re.sub(r'(?<!\\)\\(?![\"\\/btnfru])', r'\\\\', s)  # escape lạ còn lại
    return s


def _loads_json_lenh(obj: str) -> Any:
    """json.loads có tự chữa escape đơn của AI."""
    try:
        return json.loads(obj)
    except json.JSONDecodeError:
        fixed = _sua_escape_json(obj)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError as e2:
            # Kèm đoạn text quanh điểm vỡ để GV/dev thấy đúng ký tự gây lỗi.
            pos = getattr(e2, "pos", None)
            if pos is not None:
                doan = fixed[max(0, pos - 80):pos + 80].replace("\n", "\\n")
                raise ValueError(f"JSON lỗi tại ký tự {pos} (quanh: ...{doan}...): {e2}")
            raise


def _trich_json(text: str) -> Dict[str, Any]:
    """Robustly extract one JSON object from an LLM response."""
    raw = (text or "").strip()
    ung_vien: List[str] = []
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.S | re.I)
    if fenced:
        ung_vien.append(fenced.group(1))
    a, b = raw.find("{"), raw.rfind("}")
    if a >= 0 and b > a:
        ung_vien.append(raw[a:b + 1])
    loi_cuoi: Exception = ValueError("AI phải trả về một JSON object.")
    for ung in ung_vien:
        try:
            obj = _loads_json_lenh(ung)
            if isinstance(obj, dict):
                return obj
            loi_cuoi = ValueError("AI phải trả về một JSON object.")
        except Exception as e:  # thử ứng viên tiếp theo
            loi_cuoi = e
    raise ValueError(f"Không đọc được JSON từ AI: {loi_cuoi}")


def _ten_goi(node: ast.Call) -> str:
    """Best-effort call name for checks and metrics."""
    f = node.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return ""


# Dấu tiếng Việt đặc trưng (ă â đ ê ô ơ ư + nguyên âm bỏ dấu): font mặc định
# của Manim không có, phải ép font="Arial" nếu không sẽ hiện ô vuông □.
_CHU_TIENG_VIET = re.compile(r"[À-ÿĀ-ƱẠ-ỹ]")


def _thieu_font_tieng_viet(call: ast.Call) -> bool:
    """Text/Paragraph chứa chữ Việt có dấu nhưng không truyền font=."""
    if any(kw.arg == "font" for kw in call.keywords):
        return False
    chuoi = [a.value for a in call.args
             if isinstance(a, ast.Constant) and isinstance(a.value, str)]
    chuoi += [kw.value.value for kw in call.keywords
              if kw.arg == "text" and isinstance(kw.value, ast.Constant)
              and isinstance(kw.value.value, str)]
    return any(_CHU_TIENG_VIET.search(s) for s in chuoi)
_DOI_TUONG_NHAN_CHU = {"Text", "Paragraph", "MathTex", "Tex"}
_ANIM_XOA = {"FadeOut", "Uncreate", "Unwrite", "FadeTransform"}


def kiem_tra_bo_cuc(code: str) -> List[str]:
    """Lint bố cục tĩnh, KHÔNG chặn render: heuristic bắt 3 mùi rối hình phổ biến.

    1. Nhồi >= 3 nhãn trong một lệnh add/play (phải reveal nối tiếp).
    2. Nhiều chữ (> 6) nhưng không có animation xóa (chữ tồn đọng chồng nhau).
    3. Chữ thuyết minh không qua self.noi() (caption bar độc quyền).
    4. Lệch đơn vị: vừa coords_to_point vừa Circle(radius=số cứng).
    """
    canh_bao: List[str] = []
    try:
        tree = ast.parse(code or "")
    except SyntaxError:
        return canh_bao
    so_chu = 0
    co_xoa = False
    co_noi = False
    nhoi_nhat = 0
    dung_truc = False
    tron_cung = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        ten = _ten_goi(node)
        if ten in _DOI_TUONG_NHAN_CHU:
            so_chu += 1
        if ten in _ANIM_XOA:
            co_xoa = True
        if ten == "coords_to_point":
            dung_truc = True
        if ten == "Circle":
            ban_kinh_cung = [kw.value for kw in node.keywords if kw.arg == "radius"]
            if node.args and isinstance(node.args[0], ast.Constant):
                ban_kinh_cung = ban_kinh_cung + [node.args[0]]
            if any(isinstance(v, ast.Constant) and isinstance(v.value, (int, float))
                   for v in ban_kinh_cung):
                tron_cung = True
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "noi":
                co_noi = True
            if node.func.attr in {"add", "play"}:
                dem = sum(1 for a in node.args
                          if isinstance(a, ast.Call) and _ten_goi(a) in _DOI_TUONG_NHAN_CHU)
                nhoi_nhat = max(nhoi_nhat, dem)
    if nhoi_nhat >= 3:
        canh_bao.append(
            f"Một lệnh hiện {nhoi_nhat} nhãn cùng lúc — nên reveal từng cái "
            "(Write/FadeIn nối tiếp, nhãn cũ hide trước khi thêm mới).")
    if so_chu > 6 and not co_xoa:
        canh_bao.append(
            f"Tạo {so_chu} đối tượng chữ nhưng không thấy FadeOut/Uncreate — "
            "nguy cơ chữ tồn đọng chồng lên nhau.")
    if so_chu >= 3 and not co_noi:
        canh_bao.append(
            "Chữ thuyết minh nên qua self.noi() (caption bar độc quyền) thay vì Text rải rác.")
    if dung_truc and tron_cung:
        canh_bao.append(
            "Vừa dùng coords_to_point (đơn vị Axes) vừa Circle(radius=số cứng) "
            "(đơn vị màn hình) — điểm M sẽ lệch khỏi đường tròn; phải "
            "Circle(radius=axes.x_axis.get_unit_size()).")
    return canh_bao


def _range_literal_qua_lon(node: ast.Call) -> bool:
    if not isinstance(node.func, ast.Name) or node.func.id != "range":
        return False
    vals: List[int] = []
    for a in node.args[:3]:
        if isinstance(a, ast.Constant) and isinstance(a.value, int):
            vals.append(a.value)
        elif isinstance(a, ast.UnaryOp) and isinstance(a.op, ast.USub) and isinstance(a.operand, ast.Constant) and isinstance(a.operand.value, int):
            vals.append(-a.operand.value)
        else:
            return False
    if not vals:
        return False
    if len(vals) == 1:
        span = abs(vals[0])
    elif len(vals) >= 2:
        span = abs(vals[1] - vals[0])
    else:
        span = 0
    return span > TOI_DA_RANGE_LITERAL


def kiem_tra_code(code: str) -> Tuple[bool, str]:
    """Static safety + minimum-quality checks before render."""
    code = (code or "").strip()
    if not code:
        return False, "Code rỗng."
    if len(code) > TOI_DA_CODE:
        return False, f"Code quá dài ({len(code)} ký tự), tối đa {TOI_DA_CODE}."

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Lỗi cú pháp Python dòng {e.lineno}: {e.msg}."

    top_classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    if len(top_classes) != 1 or top_classes[0].name != "GeneratedScene":
        return False, "Phải có đúng 1 class top-level tên GeneratedScene."

    scene_cls = top_classes[0]
    if len(scene_cls.bases) != 1 or not isinstance(scene_cls.bases[0], ast.Name):
        return False, "GeneratedScene phải kế thừa đúng 1 scene class của Manim."
    base_name = scene_cls.bases[0].id
    if base_name not in _SCENE_BASE_OK:
        return False, f"Scene base không cho phép: {base_name}."

    construct = next(
        (n for n in scene_cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "construct"),
        None,
    )
    if construct is None:
        return False, "GeneratedScene phải có method construct(self)."

    play_count = 0
    add_count = 0

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                mods = [(a.name or "").split(".")[0] for a in node.names]
            else:
                mods = [(node.module or "").split(".")[0]]
            for m in mods:
                if m not in _MODULE_OK:
                    return False, f"Cấm import module: {m}."

        elif isinstance(node, (ast.While, ast.AsyncFor, ast.AsyncWith, ast.Await, ast.Yield, ast.YieldFrom,
                               ast.AsyncFunctionDef)):
            return False, f"Cấm cấu trúc: {type(node).__name__}."

        elif isinstance(node, ast.Name):
            if node.id in _TEN_CAM or node.id.startswith("__"):
                return False, f"Cấm dùng tên: {node.id}."
            if node.id in _MANIM_DOI_TUONG_DOC_FILE_CAM:
                return False, f"Cấm đối tượng có thể đọc file: {node.id}."

        elif isinstance(node, ast.Attribute):
            if node.attr in _THUOC_TINH_CAM or node.attr.startswith("__"):
                return False, f"Cấm truy cập thuộc tính: {node.attr}."

        elif isinstance(node, ast.Call):
            call_name = _ten_goi(node)
            if call_name in _MANIM_DOI_TUONG_DOC_FILE_CAM:
                return False, f"Cấm đối tượng có thể đọc file: {call_name}."
            if call_name == "plot" and any(kw.arg == "t_range" for kw in node.keywords):
                return False, ("Axes.plot() trong Manim 0.21 dùng x_range=[u, v, bước] "
                               "(VD: x_range=[0, TAU, 0.1]), không dùng t_range=; "
                               "t_range chỉ dành cho ParametricFunction().")
            if call_name in {"Text", "Paragraph"} and _thieu_font_tieng_viet(node):
                return False, ('Text tiếng Việt có dấu thiếu font="Arial" '
                               "(font mặc định render ra ô vuông □ trắng).")
            if _range_literal_qua_lon(node):
                return False, f"range() literal quá lớn; tối đa khoảng {TOI_DA_RANGE_LITERAL} bước."
            if isinstance(node.func, ast.Attribute) and node.func.attr == "play":
                play_count += 1
            if isinstance(node.func, ast.Attribute) and node.func.attr == "add":
                add_count += 1

    if play_count > TOI_DA_PLAY:
        return False, f"Quá nhiều self.play ({play_count}), tối đa {TOI_DA_PLAY}."
    if play_count == 0 and add_count == 0:
        return False, "Scene không có self.play() hoặc self.add(); có thể tạo ra khung rỗng."

    return True, ""


# ---------------------------------------------------------------------------
# Prompting: planner -> coder -> critic
# ---------------------------------------------------------------------------

_MANIM_CAPABILITY_GUIDE = r"""
Use Manim Community stable APIs and choose the strongest tool that improves pedagogy, not merely decoration.

Scene classes:
- Scene: normal 2D.
- MovingCameraScene: zoom/pan/focus on small details; animate self.camera.frame.
- TeachingScene: SUBCLASS of MovingCameraScene, ALWAYS AVAILABLE in the render
  environment (do NOT define it). Inherit it for Scene/MovingCameraScene storyboards
  to get self.noi(text) exclusive caption bar and self.dan_nhan(obj, text, huong).
- ZoomedScene: inset magnifier / local detail.
- ThreeDScene / SpecialThreeDScene: 3D axes, surfaces, solids, camera orientation/rotation.
- LinearTransformationScene / VectorScene: vector spaces and linear transforms when genuinely relevant.

High-value primitives:
- Geometry: Dot, LabeledDot, Line, DashedLine, Arrow, Vector, DoubleArrow, Circle, Arc,
  Angle, RightAngle, Polygon, Rectangle, RoundedRectangle, Brace, BraceBetweenPoints,
  SurroundingRectangle, TangentLine.
- Graphing: Axes, NumberPlane, PolarPlane, ComplexPlane, NumberLine, ParametricFunction,
  ImplicitFunction, graph plotting helpers, get_area(), get_secant_slope_group() when compatible.
- Dynamic: ValueTracker, DecimalNumber, Variable, always_redraw, TracedPath, updaters,
  MoveAlongPath.
- Transform: Transform, ReplacementTransform, TransformFromCopy, TransformMatchingTex,
  TransformMatchingShapes, FadeTransform, MoveToTarget.
- Attention: Indicate, Circumscribe, Flash, FocusOn, ApplyWave, Wiggle, ShowPassingFlash.
- Sequencing: AnimationGroup, LaggedStart, Succession.
- 3D: ThreeDAxes, Surface, Sphere, Cube, Prism, Cone, Cylinder, Dot3D, Arrow3D, Line3D.
- Fields: ArrowVectorField, StreamLines when the concept actually needs a field.

Pedagogical motion rules:
1. Every animation must communicate a conceptual change: reveal, compare, transform, trace,
   measure, project, focus or conclude.
2. Prefer Transform/TransformMatchingTex when one mathematical state becomes another.
3. Use ValueTracker + always_redraw for continuously changing quantities.
4. Use TracedPath when trajectory/history is conceptually important.
5. Use camera movement only when it helps attention or scale; do not create gratuitous motion.
6. Never overcrowd the frame. Reserve top ~12% for a title only if a title is useful.
7. Keep labels attached to their objects and avoid overlaps. Use VGroup/arrange/next_to/to_edge.
8. Use semantic colors consistently across the whole scene (same quantity = same color).
9. Vietnamese prose uses Text/Paragraph. Mathematical notation uses MathTex if LaTeX is available;
   otherwise use Text with Unicode-friendly notation.
10. For 3D, set a meaningful camera orientation and use ambient rotation only when it improves
    spatial understanding.
11. Keep the final frame readable for at least ~1 second.
"""


def _legacy_context(mon: str) -> str:
    if _legacy_prompts is None:
        return ""
    try:
        return str(_legacy_prompts.prompt_sinh_manim(mon) or "")
    except Exception:
        return ""


def _system_planner(mon: str, output: str, latex_ok: bool) -> str:
    return f"""
Bạn là chuyên gia thiết kế trực quan sư phạm và storyboard cho giáo viên.
Nhiệm vụ: chuyển mô tả tự nhiên thành một kế hoạch hình/video RẤT SÁT yêu cầu trước khi viết code.
Không viết Python. Chỉ trả về 1 JSON object hợp lệ, không markdown.
Mọi backslash trong text/LaTeX phải viết GẤP ĐÔI ("\\\\frac", "\\\\sin", "\\\\neq");
backslash đơn làm JSON vỡ và storyboard bị hủy.

Ưu tiên theo thứ tự:
1) Trung thành tuyệt đối với các đối tượng, công thức, số liệu, thứ tự và ý đồ mà giáo viên mô tả.
2) Đúng kiến thức và đúng quan hệ không gian/toán học.
3) Dễ nhìn trên màn chiếu 16:9, tránh chữ chồng nhau.

LUẬT REVEAL TỪNG BƯỚC (bắt buộc, chống rối hình):
- Mỗi step chỉ giới thiệu đúng 1 ý chính, theo trình tự: tạo đối tượng → giải thích
  → nhấn mạnh → biến đổi → kết luận. KHÔNG bao giờ hiện mọi nhãn/công thức cùng lúc.
- Tối đa 5 nhãn cùng hiện trong một frame (hình đơn giản: tối đa 3).
- Mỗi step phải có "caption": đúng 1 câu thuyết minh ngắn (hiện ở dải dưới màn hình,
  step sau thay step trước). Chữ giải thích KHÔNG đặt rải rác quanh hình.
- Mỗi step phải có "hide": liệt kê đối tượng/nhãn tạm sẽ ẩn đi cuối bước sau khi
  đã làm xong nhiệm vụ (tránh tồn đọng chữ cũ chồng lên hình mới).
- Công thức chỉ xuất hiện SAU đối tượng trực quan mà nó giải thích.
4) Chuyển động phải giải thích kiến thức, không làm màu.
5) Chọn đúng loại Scene để tận dụng Manim.

Đầu ra đang cần: {output}.
Môn/ngữ cảnh: {mon}.
LaTeX/MathTex khả dụng: {latex_ok}.

JSON bắt buộc có cấu trúc:
{{
  "title": "...",
  "learning_goal": "...",
  "output": "video|image",
  "scene_type": "Scene|MovingCameraScene|ThreeDScene|SpecialThreeDScene|ZoomedScene|LinearTransformationScene|VectorScene",
  "duration_target_sec": 20,
  "must_include": ["các chi tiết bắt buộc phải xuất hiện"],
  "must_not_include": ["các chi tiết không nên tự ý thêm"],
  "style": {{
    "background": "dark|light",
    "layout": "mô tả bố cục",
    "color_semantics": {{"đối tượng/đại lượng": "vai trò màu"}}
  }},
  "manim_features": ["ValueTracker", "MovingCameraScene", "TransformMatchingTex", "..."],
  "steps": [
    {{
      "id": 1,
      "purpose": "mục đích sư phạm của bước",
      "objects": ["đối tượng phải có"],
      "action": "thứ gì xuất hiện/biến đổi/di chuyển và theo quan hệ nào",
      "labels_or_math": ["chữ/công thức chính xác cần hiện"],
      "caption": "1 câu thuyết minh hiện ở dải dưới (bước sau thay bước trước)",
      "hide": ["nhãn/đối tượng tạm sẽ ẩn cuối bước"],
      "camera": "none|zoom/pan/orbit + mục tiêu",
      "timing_sec": 2.0
    }}
  ],
  "final_frame": "mô tả chính xác khung hình cuối"
}}

Nếu mô tả thiếu một giá trị không thiết yếu, chọn mặc định hợp lý nhưng ghi rõ trong plan.
Không tự thêm định lý, công thức, số liệu hay kết luận mà giáo viên không yêu cầu.
""".strip()


def _system_coder(mon: str, output: str, latex_ok: bool) -> str:
    legacy = _legacy_context(mon)
    return f"""
Bạn là kỹ sư Manim Community chuyên tạo học liệu trực quan chất lượng cao.
Bạn nhận STORYBOARD JSON đã được duyệt. Hãy triển khai đúng storyboard, không tự đổi nội dung.

YÊU CẦU ĐẦU RA:
- Chỉ trả đúng 1 khối ```python ...```.
- Chỉ có đúng 1 top-level class tên GeneratedScene.
- GeneratedScene kế thừa đúng scene_type trong storyboard.
- Có construct(self).
- Chỉ import từ manim, math, numpy.
- Không đọc/ghi file, không mạng, không subprocess, không ImageMobject/SVGMobject/Code.
- Không dùng while.
- Code tự chứa hoàn toàn, deterministic, không cần asset ngoài.
- Không dùng config để thay đổi output path.
- Mọi mảng tọa độ numpy KẾT HỢP với hằng/véc-tơ Manim (ORIGIN, UP, RIGHT,
  get_center(), ...) BẮT BUỘC có đúng 3 phần tử [x, y, 0]. Viết
  np.array([np.cos(a), np.sin(a), 0]), KHÔNG bao giờ np.array([np.cos(a), np.sin(a)]).
  Quy tắc này áp dụng cho mọi phép +, -, * với điểm Manim.
- Màu Manim 0.21: MAGENTA và CYAN đã bị xóa, chỉ dùng PURE_MAGENTA/PURE_CYAN
  (hoặc RED, BLUE, YELLOW, GREEN, ORANGE, PINK, PURPLE, TEAL, GOLD, MAROON,
  WHITE, BLACK — các tên này vẫn còn). Không dùng tên màu nào khác khi chưa chắc chắn.
- Mọi Text()/Paragraph() chứa TIẾNG VIỆT CÓ DẤU bắt buộc thêm font="Arial"
  (font mặc định thiếu dấu tiếng Việt, render ra ô vuông □ trắng).
  Text chỉ có ASCII/Greek (Ox, O, α) thì không cần.
- Vẽ đồ thị trên Axes/NumberPlane: dùng axes.plot(f, x_range=[u, v, bước])
  (VD: x_range=[0, TAU, 0.1]). TUYỆT ĐỐI KHÔNG truyền t_range= cho .plot()
  (gây TypeError trên Manim 0.21); t_range chỉ dành cho ParametricFunction().
  Đường tròn/quỹ đạo tham số: dùng Circle() hoặc ParametricFunction(
  lambda t: axes.coords_to_point(np.cos(t), np.sin(t)), t_range=[0, TAU]),
  không dùng axes.plot với hàm trả về mảng.
- THỐNG NHẤT ĐƠN VỊ (luật sắt): trong một scene, mọi đối tượng hình học phải dùng
  chung MỘT hệ tọa độ. Nếu đã dùng Axes/coords_to_point thì CẤM Circle(radius=số cứng),
  Dot(tọa độ tay), Line(ORIGIN, ...) theo đơn vị màn hình. Công thức chuẩn:
    don_vi = axes.x_axis.get_unit_size()
    goc = axes.coords_to_point(0, 0, 0)
    tron = Circle(radius=don_vi).move_to(goc)
    M = Dot(axes.coords_to_point(1, 0, 0))
  (điểm M(cos α; sin α) lúc này CHẮC CHẮN nằm trên đường tròn vì cùng đơn vị).
- Video/hình tỷ lệ mặc định 16:9.
- Nếu output=image, xây bố cục hoàn chỉnh ở final frame; animation có thể tối thiểu.
- Nếu output=video, bám timing tương đối của storyboard, tránh thời lượng chờ dài vô ích.
- LaTeX khả dụng: {latex_ok}. Nếu False, tuyệt đối không dùng Tex/MathTex.

BỐ CỤC & CHẤT LƯỢNG:
- Không để text/formula vượt khung, chồng nhau hoặc che đồ thị.
- Với công thức biến đổi, ưu tiên TransformMatchingTex nếu LaTeX khả dụng.

VISUAL PEDAGOGY RULES (bắt buộc, ưu tiên hơn mọi mặc định):
1. Never show all explanations at once. Mỗi thời điểm chỉ phục vụ đúng 1 ý của storyboard.
2. Maximum visible labels cùng lúc: hình đơn giản <= 3, hình toán <= 5.
3. Mọi câu chữ thuyết minh (caption của storyboard) BẮT BUỘC qua self.noi("..."):
   dải dưới màn hình, câu sau tự thay câu trước. Cấm đặt chữ giải thích rải rác quanh hình.
4. Nhãn toán (tên điểm, công thức ngắn) gắn trực tiếp lên đối tượng bằng
   self.dan_nhan(obj, "...", huong=...), không tự đặt tọa độ tay. huong nhận
   "right"/"left"/"up"/"down" hoặc vector Manim (DOWN+LEFT, UL...).
5. Không hiện công thức trước đối tượng trực quan mà nó giải thích.
6. Trình tự chuẩn mỗi bước: tạo đối tượng → self.noi() giải thích → nhấn mạnh
   (Indicate/Circumscribe) → biến đổi → self.noi() kết luận.
7. Nhãn/đối tượng tạm trong storyboard "hide" phải FadeOut ngay khi xong nhiệm vụ,
   không để tồn đọng sang bước sau.
8. Dải dưới màn hình (vùng caption) là vùng cấm: không đặt đồ thị/điểm/nhãn nào
   ở đó (giữ mọi đối tượng toán ở phía trên y = -2.5).
9. Trước khi thêm nhãn mới, kiểm tra storyboard xem nhãn cũ nào đã hide; nếu frame
   đã đủ 5 nhãn thì phải ẩn bớt trước khi thêm.
10. Khi storyboard yêu cầu scene_type Scene hoặc MovingCameraScene, hãy kế thừa
    TeachingScene (đã có sẵn trong môi trường render, KHÔNG định nghĩa lại) để có
    self.noi()/self.dan_nhan(). Các scene_type khác giữ nguyên.
- Với đại lượng thay đổi liên tục, ưu tiên ValueTracker + always_redraw/DecimalNumber.
- Với quỹ đạo, dùng TracedPath khi phù hợp.
- Với chi tiết nhỏ, cân nhắc MovingCameraScene/ZoomedScene đúng theo storyboard.
- Với 3D, dùng ThreeDAxes/Surface/solid + camera orientation hợp lý.
- Không tạo title/card/decoration nếu không giúp học nội dung.

{_MANIM_CAPABILITY_GUIDE}

Ngữ cảnh cũ của dự án (chỉ tham khảo; storyboard mới là nguồn sự thật):
{legacy[:5000]}
""".strip()


def _system_critic() -> str:
    return """
Bạn là reviewer Manim + chuyên gia sư phạm. So sánh MÔ TẢ GỐC, STORYBOARD và CODE.
Không viết lại code. Chỉ trả 1 JSON object hợp lệ, không markdown:
{
  "needs_revision": true,
  "scores": {
    "prompt_fidelity": 0,
    "subject_correctness": 0,
    "visual_layout": 0,
    "animation_pedagogy": 0,
    "manim_power": 0
  },
  "issues": [
    {"severity":"critical|major|minor", "problem":"...", "fix":"..."}
  ],
  "summary":"..."
}
Mỗi score từ 0 đến 5.
needs_revision=true nếu có critical/major issue, hoặc prompt_fidelity < 4,
subject_correctness < 4, visual_layout < 3, animation_pedagogy < 3.
Không phạt code vì không dùng hiệu ứng cầu kỳ nếu hiệu ứng đó không cần thiết về sư phạm.

KIỂM BỐ CỤC (quyết định visual_layout, hãy đếm thật trên CODE):
- Đếm mọi Text/Paragraph/MathTex/Tex được tạo: cùng hiện > 5 cái mà không có
  FadeOut/Uncreate/FadeTransform tương ứng => major issue "too many simultaneous labels",
  visual_layout tối đa 2.
- Một lệnh self.add()/self.play() nhồi >= 3 nhãn cùng lúc => major issue
  "labels must be revealed sequentially", visual_layout tối đa 2.
- Câu chữ thuyết minh/diễn giải KHÔNG qua self.noi() (caption bar độc quyền) mà đặt
  rải rác bằng Text/move_to/next_to => major issue "narration must use caption bar".
- Nhãn đặt bằng tọa độ tay (move_to với số cứng) gần đối tượng khác => minor, gợi ý
  dùng self.dan_nhan() hoặc next_to/arrange.
- Nhãn tạm trong storyboard "hide" nhưng code không FadeOut => major issue
  "temporary annotation never removed".
- Lệch đơn vị tọa độ: code vừa dùng coords_to_point (đơn vị Axes) vừa dùng
  Circle(radius=số cứng)/Dot/Line tọa độ tay (đơn vị màn hình) => major issue
  "mixed coordinate systems", subject_correctness tối đa 2. Đúng phải là
  Circle(radius=axes.x_axis.get_unit_size()).move_to(axes.coords_to_point(0,0,0)).
""".strip()


def _goi_llm(system: str, user: str, timeout: int, task: str = "flash") -> str:
    """Gọi LLM theo task (prod: planner/coder/sửa=FLASH, critic/audit=PRO).

    Đi qua llm.chat_theo_task để mock llm.chat cũ trong tools/kiem_tra_*
    vẫn chặn được (wrapper gọi đúng chat(messages, timeout=timeout)).
    """
    return llm.chat_theo_task(
        task,
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        timeout=timeout,
    )


def _capabilities() -> Dict[str, Any]:
    try:
        cap = manim_render.get_capabilities()
        if isinstance(cap, dict):
            return cap
    except Exception:
        pass
    return {"latex": False, "manim": None, "ffmpeg": None}


def _doc_plan(raw: str, output: str) -> Dict[str, Any]:
    plan = _trich_json(raw)

    # Normalize critical fields to prevent the planner from escaping the contract.
    plan["output"] = output
    if plan.get("scene_type") not in _SCENE_BASE_OK:
        plan["scene_type"] = "MovingCameraScene" if output == "video" else "Scene"
    steps = plan.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError("Storyboard AI không có steps.")
    if len(steps) > 24:
        plan["steps"] = steps[:24]
    return plan


def lap_ke_hoach(mo_ta: str, bai: str = "", mon: str = "toan11", output: str = "video", timeout: int = 180) -> Dict[str, Any]:
    cap = _capabilities()
    latex_ok = bool(cap.get("latex"))
    system = _system_planner(mon, output, latex_ok)
    user = f"Bài/chủ đề: {bai or '(chung)'}\nMô tả gốc của giáo viên:\n{mo_ta}"
    raw = _goi_llm(system, user, timeout)
    try:
        return _doc_plan(raw, output)
    except ValueError:
        # Planner hay vỡ JSON vì backslash LaTeX đơn: cho 1 cơ hội sửa.
        user2 = user + ("\n\nLần trước JSON SAI CÚ PHÁP (thường do backslash đơn "
                        "trong LaTeX). Trả lại ĐÚNG 1 JSON object hợp lệ, mọi backslash "
                        "viết gấp đôi (\\\\frac, \\\\sin), không markdown.")
        return _doc_plan(_goi_llm(system, user2, timeout), output)


def sinh_code_tu_ke_hoach(plan: Dict[str, Any], mo_ta: str, bai: str = "", mon: str = "toan11", timeout: int = 180) -> str:
    cap = _capabilities()
    latex_ok = bool(cap.get("latex"))
    user = (
        f"MÔ TẢ GỐC:\n{mo_ta}\n\n"
        f"BÀI/CHỦ ĐỀ: {bai or '(chung)'}\n\n"
        "STORYBOARD JSON:\n" + json.dumps(plan, ensure_ascii=False, indent=2)
    )
    raw = _goi_llm(_system_coder(mon, plan.get("output", "video"), latex_ok), user, timeout)
    return trich_code(raw)


def danh_gia_code(plan: Dict[str, Any], code: str, mo_ta: str, timeout: int = 180) -> Dict[str, Any]:
    user = (
        f"MÔ TẢ GỐC:\n{mo_ta}\n\n"
        "STORYBOARD:\n" + json.dumps(plan, ensure_ascii=False, indent=2) +
        "\n\nCODE:\n```python\n" + code + "\n```"
    )
    try:
        return _trich_json(_goi_llm(_system_critic(), user, timeout, task="pro"))
    except Exception as e:
        # Audit failure should not destroy a valid generation pipeline.
        return {
            "needs_revision": False,
            "scores": {},
            "issues": [],
            "summary": f"Không parse được audit: {e}",
        }


def _can_sua(audit: Dict[str, Any]) -> bool:
    if bool(audit.get("needs_revision")):
        return True
    for issue in audit.get("issues") or []:
        if isinstance(issue, dict) and issue.get("severity") in {"critical", "major"}:
            return True
    return False


def _goi_code_co_thu_lai(system: str, user: str, timeout: int) -> str:
    """Gọi LLM lấy code; model free đôi khi trả về rỗng nên nhắc và thử lại 1 lần."""
    code = trich_code(_goi_llm(system, user, timeout))
    if code.strip():
        return code
    return trich_code(_goi_llm(
        system,
        user + "\n\nLần trước bạn trả về TRỐNG. Bắt buộc trả FULL code trong "
               "đúng 1 khối ```python, không giải thích.",
        timeout))


def sua_code_theo_audit(plan: Dict[str, Any], code: str, audit: Dict[str, Any], mo_ta: str, mon: str, timeout: int) -> str:
    cap = _capabilities()
    latex_ok = bool(cap.get("latex"))
    user = (
        f"MÔ TẢ GỐC:\n{mo_ta}\n\n"
        "STORYBOARD:\n" + json.dumps(plan, ensure_ascii=False, indent=2) +
        "\n\nAUDIT:\n" + json.dumps(audit, ensure_ascii=False, indent=2) +
        "\n\nCODE HIỆN TẠI:\n```python\n" + code + "\n```\n\n"
        "Sửa TỐI THIỂU nhưng đầy đủ các lỗi audit. Không thay đổi nội dung đúng. Chỉ trả 1 khối ```python."
    )
    return _goi_code_co_thu_lai(_system_coder(mon, plan.get("output", "video"), latex_ok), user, timeout)


def sua_code_theo_log(plan: Dict[str, Any], code: str, log: str, mo_ta: str, mon: str, timeout: int) -> str:
    cap = _capabilities()
    latex_ok = bool(cap.get("latex"))
    user = (
        f"MÔ TẢ GỐC:\n{mo_ta}\n\n"
        "STORYBOARD:\n" + json.dumps(plan, ensure_ascii=False, indent=2) +
        "\n\nCODE BỊ LỖI:\n```python\n" + code + "\n```\n\n"
        f"LOG LỖI:\n{(log or '')[-3500:]}\n\n"
        "Sửa đúng nguyên nhân lỗi render nhưng vẫn bám storyboard. "
        "Bắt buộc trả lời KHÔNG TRỐNG, chỉ 1 khối ```python (kể cả khi chỉ sửa 1 dòng, vẫn trả FULL code).\n\n"
        + _CHEAT_SHEET_LOI
    )
    return _goi_code_co_thu_lai(_system_coder(mon, plan.get("output", "video"), latex_ok), user, timeout)


# ---------------------------------------------------------------------------
# Public orchestration
# ---------------------------------------------------------------------------

_CHEAT_SHEET_LOI = """
LỖI RENDER HAY GẶP (kiểm tra trước khi trả code):
1. "operands could not be broadcast together with shapes (3,) (2,)": mảng
   numpy 2 phần tử cộng với điểm Manim 3D. Sửa: mọi np.array tọa độ phải có
   đúng 3 phần tử [x, y, 0].
2. DecimalNumber.set_value / move_to lỗi kiểu: chỉ truyền float, không truyền
   mobject hay mảng.
3. Updater nhận đúng 1 tham số (mobject, hoặc mobject + dt); không dùng biến
   ngoài đã bị xóa; remove_updater đúng hàm đã add.
4. Text tiếng Việt: dùng font hỗ trợ Unicode đầy đủ, không để ký tự □.
5. add_updater + play trên cùng mobject: đảm bảo updater không ghi đè lẫn nhau.
6. NameError màu (MAGENTA/CYAN is not defined): Manim 0.21 đã xóa 2 bí danh này,
   dùng PURE_MAGENTA/PURE_CYAN. Mọi tên màu khác chỉ dùng trong danh sách an toàn
   của prompt coder.
7. TypeError "got multiple values for 't_range'" ở axes.plot: đổi sang
   x_range=[u, v, bước]; t_range chỉ dùng cho ParametricFunction().
8. Chữ tiếng Việt hiện ô vuông □ trắng: Text/Paragraph có dấu thiếu
   font="Arial". Thêm font="Arial" cho MỌI chữ Việt có dấu.
""".strip()


def sinh_hoc_lieu_tu_mo_ta(
    mo_ta: str,
    bai: str = "",
    mon: str = "toan11",
    output: str = "video",
    quality: str = "l",
    timeout: int = 300,
    che_do: str = "quality",
    so_vong_sua_render: int = 2,
    dung_template: bool = True,
) -> Dict[str, Any]:
    """Generate Manim video or still image.

    Returns a rich dict:
      video: {mp4, code, log, cached, plan, audit, previews}
      image: {png, code, log, cached, plan, audit}

    che_do:
      - quality: planner -> coder -> critic -> optional revision -> render
      - fast:    planner -> coder -> render (skip critic)

    dung_template (chỉ output video): thử khớp template có sẵn trước
      (nhanh, ổn định, không tốn token); trượt mới sinh tự do.
    """
    mo_ta = (mo_ta or "").strip()
    if not mo_ta:
        return {"mp4": "", "png": "", "code": "", "log": "GV chưa nhập mô tả.", "cached": False}
    if output not in {"video", "image"}:
        return {"mp4": "", "png": "", "code": "", "log": "output chỉ nhận 'video' hoặc 'image'.", "cached": False}
    if quality not in {"l", "m", "h", "p", "k"}:
        return {"mp4": "", "png": "", "code": "", "log": "quality chỉ nhận 'l', 'm', 'h', 'p' hoặc 'k'.", "cached": False}
    if che_do not in {"fast", "quality"}:
        che_do = "quality"

    # Keep individual LLM calls below the render timeout. The project's llm.chat
    # already owns its own network/API timeout.
    llm_timeout = min(max(int(timeout), 30), 300)

    ghi_chu_tpl = ""
    if output == "video" and dung_template:
        try:
            from core import manim_template as _tpl
            kq_tpl = _tpl.sinh_video_template(mo_ta, quality=quality, timeout=timeout)
        except Exception as e:
            kq_tpl = {"mp4": "", "log": f"Lỗi đường template: {e}", "cached": False,
                      "template": None, "params": {}, "diem": 0.0}
        if kq_tpl.get("mp4"):
            nguon = " (video render trước đó, dùng lại ngay)." if kq_tpl.get("cached") else "."
            kq_tpl["png"] = ""
            kq_tpl["code"] = ""
            kq_tpl["plan"] = {"template": kq_tpl.get("template"), "params": kq_tpl.get("params")}
            kq_tpl["audit"] = {"needs_revision": False, "scores": {},
                               "issues": [], "summary": "Template đã duyệt, không cần audit."}
            kq_tpl["log"] = (f"Dùng template {kq_tpl.get('template')} "
                             f"({kq_tpl.get('ten_vi', '')}) cho mô tả này" + nguon).strip()
            return kq_tpl
        ghi_chu_tpl = kq_tpl.get("log", "")

    try:
        plan = lap_ke_hoach(mo_ta, bai=bai, mon=mon, output=output, timeout=llm_timeout)
    except Exception as e:
        return {"mp4": "", "png": "", "code": "", "log": f"Không tạo được storyboard: {e}", "cached": False}

    try:
        code = sinh_code_tu_ke_hoach(plan, mo_ta, bai=bai, mon=mon, timeout=llm_timeout)
    except Exception as e:
        return {"mp4": "", "png": "", "code": "", "plan": plan, "log": f"AI không sinh được code: {e}", "cached": False}

    ok, reason = kiem_tra_code(code)
    if not ok:
        # Treat validator failure as a repairable code issue before first render.
        audit = {
            "needs_revision": True,
            "scores": {},
            "issues": [{"severity": "critical", "problem": reason, "fix": "Sửa code để qua static validator."}],
            "summary": "Static validator thất bại.",
        }
        try:
            code = sua_code_theo_audit(plan, code, audit, mo_ta, mon, llm_timeout)
            ok, reason = kiem_tra_code(code)
        except Exception as e:
            return {"mp4": "", "png": "", "code": code, "plan": plan, "audit": audit,
                    "log": f"Code không đạt kiểm tra và sửa thất bại: {e}", "cached": False}
        if not ok:
            return {"mp4": "", "png": "", "code": code, "plan": plan, "audit": audit,
                    "log": f"Code không đạt kiểm tra: {reason}", "cached": False}
    else:
        audit = {"needs_revision": False, "scores": {}, "issues": [], "summary": "Chưa audit."}

    if che_do == "quality":
        audit = danh_gia_code(plan, code, mo_ta, timeout=llm_timeout)
        if _can_sua(audit):
            try:
                revised = sua_code_theo_audit(plan, code, audit, mo_ta, mon, llm_timeout)
                ok2, reason2 = kiem_tra_code(revised)
                if ok2:
                    code = revised
                else:
                    audit.setdefault("issues", []).append({
                        "severity": "minor",
                        "problem": f"Bản sửa audit không qua validator: {reason2}",
                        "fix": "Giữ lại code trước audit để render.",
                    })
            except Exception as e:
                audit.setdefault("issues", []).append({
                    "severity": "minor",
                    "problem": f"Không áp dụng được bản sửa audit: {e}",
                    "fix": "Giữ lại code đã hợp lệ.",
                })

    def render_now(current_code: str) -> Dict[str, Any]:
        ma_day_du = _ma_render(current_code)
        if output == "image":
            return manim_render.render_code_still(ma_day_du, quality=quality, timeout=timeout)
        return manim_render.render_code(ma_day_du, quality=quality, timeout=timeout, preview_count=4)

    kq = render_now(code)
    key = "png" if output == "image" else "mp4"

    repair_logs: List[str] = []
    for _ in range(max(0, min(int(so_vong_sua_render), 3))):
        if kq.get(key):
            break
        repair_logs.append(kq.get("log", ""))
        try:
            code2 = sua_code_theo_log(plan, code, kq.get("log", ""), mo_ta, mon, llm_timeout)
        except Exception as e:
            kq["log"] = (kq.get("log", "") + f"\nAI sửa theo log thất bại: {e}").strip()
            break
        ok2, reason2 = kiem_tra_code(code2)
        if not ok2:
            goi_y = (" AI trả về rỗng 2 lần liên tiếp — GV bấm dựng lại để thử tiếp."
                     if reason2 == "Code rỗng." else "")
            kq["log"] = (kq.get("log", "") + f"\nBản sửa không qua validator: {reason2}." + goi_y).strip()
            break
        code = code2
        kq = render_now(code)

    result = {**kq, "code": code, "plan": plan, "audit": audit}
    if repair_logs and result.get(key):
        result["log"] = f"Render ban đầu lỗi; AI đã sửa thành công sau {len(repair_logs)} vòng."
    canh_bao_bo_cuc = kiem_tra_bo_cuc(code) if result.get(key) else []
    if canh_bao_bo_cuc:
        result["log"] = (result.get("log", "")
                         + "\nLưu ý bố cục (video vẫn chạy, nên gọn hơn lần sau): "
                         + " | ".join(canh_bao_bo_cuc)).strip()
    if ghi_chu_tpl:
        result["log"] = f"[{ghi_chu_tpl} Chuyển sang sinh tự do.] " + result.get("log", "")
    return result


def sinh_video_tu_mo_ta(
    mo_ta: str,
    bai: str = "",
    mon: str = "toan11",
    quality: str = "l",
    timeout: int = 300,
    che_do: str = "quality",
    dung_template: bool = True,
) -> Dict[str, Any]:
    """Backward-compatible API for the existing website."""
    return sinh_hoc_lieu_tu_mo_ta(
        mo_ta=mo_ta,
        bai=bai,
        mon=mon,
        output="video",
        quality=quality,
        timeout=timeout,
        che_do=che_do,
        dung_template=dung_template,
    )


def sinh_hinh_tu_mo_ta(
    mo_ta: str,
    bai: str = "",
    mon: str = "toan11",
    quality: str = "m",
    timeout: int = 300,
    che_do: str = "quality",
) -> Dict[str, Any]:
    """New API: natural language -> polished Manim final-frame PNG."""
    return sinh_hoc_lieu_tu_mo_ta(
        mo_ta=mo_ta,
        bai=bai,
        mon=mon,
        output="image",
        quality=quality,
        timeout=timeout,
        che_do=che_do,
    )
