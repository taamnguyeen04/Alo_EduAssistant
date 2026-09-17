"""Manim renderer v2.

Compatible with the old visuals/render.py API, plus:
- AI scenes may inherit advanced Manim Scene subclasses.
- quality l/m/h.
- final-frame PNG rendering for static teaching visuals.
- optional MP4 preview-frame extraction for UI / future vision audit.
- capability detection (Manim version, LaTeX, FFmpeg).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENES_FILE = os.path.join(BASE_DIR, "visuals", "manim_scenes.py")
CACHE_DIR = os.path.join(BASE_DIR, "data", "visuals")

PRESETS = {
    "duong_tron": {"scene": "UnitCircleScene", "bai": "Bài 1. Giá trị lượng giác của góc lượng giác"},
    "do_thi": {"scene": "FunctionGraphScene", "bai": "Bài 3. Hàm số lượng giác"},
    "tiep_tuyen": {"scene": "DerivativeScene", "bai": "Bài 31. Định nghĩa và ý nghĩa đạo hàm"},
}

CODE_VERSION = 4
_HAM_OK = {"sin", "cos", "tan", "cot"}
_BIEU_THUC_OK = {
    "x**2": "x**2", "x^2": "x**2",
    "x**3": "x**3", "x^3": "x**3",
    "sin(x)": "sin(x)",
}
_QUALITY_OK = {"l", "m", "h", "p", "k"}


def _so(x, mac_dinh, nho_nhat, lon_nhat):
    try:
        v = float(x)
    except (TypeError, ValueError):
        v = float(mac_dinh)
    if v != v or v in (float("inf"), float("-inf")):
        v = float(mac_dinh)
    return min(max(v, nho_nhat), lon_nhat)


def validate(preset, params):
    if preset not in PRESETS:
        raise ValueError(f"Preset lạ: {preset}")
    p = params or {}
    if preset == "duong_tron":
        return {"angle_deg": _so(p.get("angle_deg", 30), 30, 0, 720)}
    if preset == "do_thi":
        ham = str(p.get("func", p.get("ham", "sin")))
        if ham not in _HAM_OK:
            raise ValueError(f"Hàm lạ: {ham}")
        return {
            "func": ham,
            "a": _so(p.get("a", 1), 1, -5, 5),
            "b": _so(p.get("b", 1), 1, -5, 5),
            "c": _so(p.get("c", 0), 0, -10, 10),
            "d": _so(p.get("d", 0), 0, -10, 10),
        }
    bt = _BIEU_THUC_OK.get(str(p.get("expr", p.get("bieu_thuc", "x**2"))).replace(" ", ""))
    if not bt:
        raise ValueError("Biểu thức chỉ nhận: x^2, x^3, sin(x)")
    return {
        "expr": bt,
        "a": _so(p.get("a", 1), 1, -5, 5),
        "h0": _so(p.get("h0", p.get("h", 2.0)), 2.0, 0.3, 3.0),
    }


def _ffmpeg_exe() -> Optional[str]:
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return exe
    except Exception:
        pass
    return shutil.which("ffmpeg")


def _ffmpeg_env() -> Dict[str, str]:
    env = dict(os.environ)
    exe = _ffmpeg_exe()
    if exe:
        env["IMAGEIO_FFMPEG_EXE"] = exe
        env["PATH"] = os.path.dirname(exe) + os.pathsep + env.get("PATH", "")
    return env


def _manim_cmd() -> List[str]:
    # Preserve the original Windows-first project convention.
    candidates = [
        os.path.join(BASE_DIR, "venv", "Scripts", "manim.exe"),
        os.path.join(BASE_DIR, ".venv", "Scripts", "manim.exe"),
        os.path.join(BASE_DIR, "venv", "bin", "manim"),
        os.path.join(BASE_DIR, ".venv", "bin", "manim"),
    ]
    for exe in candidates:
        if os.path.exists(exe):
            return [exe]
    return [sys.executable, "-m", "manim"]


def get_capabilities() -> Dict[str, Any]:
    version = None
    try:
        import manim
        version = getattr(manim, "__version__", None)
    except Exception:
        pass
    latex_cmd = shutil.which("latex") or shutil.which("pdflatex") or shutil.which("xelatex")
    return {
        "manim": version,
        "latex": bool(latex_cmd and shutil.which("dvisvgm")),
        "latex_exe": latex_cmd,
        "dvisvgm": shutil.which("dvisvgm"),
        "ffmpeg": _ffmpeg_exe(),
        "quality": ["l", "m", "h", "p", "k"],
    }


def _find_outputs(tmp: str, ext: str) -> List[str]:
    found: List[str] = []
    suffix = "." + ext.lower().lstrip(".")
    for root, _, files in os.walk(tmp):
        for f in files:
            if f.lower().endswith(suffix):
                path = os.path.join(root, f)
                if os.path.getsize(path) > 0:
                    found.append(path)
    found.sort(key=os.path.getsize, reverse=True)
    return found


def _render_file(
    py_file: str,
    scene: str,
    quality: str,
    timeout: int,
    tmp: str,
    env_extra: Optional[Dict[str, str]] = None,
    mode: str = "video",
) -> Dict[str, Any]:
    """Render one scene into a temp media directory."""
    if quality not in _QUALITY_OK:
        raise ValueError("quality chỉ nhận 'l', 'm', 'h', 'p' hoặc 'k'")
    if mode not in {"video", "still"}:
        raise ValueError("mode chỉ nhận 'video' hoặc 'still'")

    env = _ffmpeg_env()
    if env_extra:
        env.update(env_extra)

    cmd = _manim_cmd() + [f"-q{quality}", "--media_dir", tmp]
    if mode == "still":
        cmd += ["-s"]
        ext = "png"
    else:
        cmd += ["--format=mp4"]
        ext = "mp4"
    cmd += [py_file, scene]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        return {
            "mp4": "", "png": "", "cached": False,
            "log": f"Render quá {timeout}s nên đã dừng. Hãy thử quality 'l' hoặc rút gọn scene.",
        }

    outputs = _find_outputs(tmp, ext)
    if proc.returncode != 0 or not outputs:
        combined = ((proc.stderr or "") + "\n" + (proc.stdout or "")).strip()
        return {
            "mp4": "", "png": "", "cached": False,
            "log": "Render lỗi:\n" + combined[-3500:],
        }

    key = "png" if mode == "still" else "mp4"
    return {key: outputs[0], "cached": False, "log": "Render xong."}


def _cache_key(payload: Dict[str, Any]) -> str:
    # Hash toàn bộ tham số: cùng tham số thì cùng tên file cache.
    return hashlib.sha1(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


_V1_CODE_VERSION = 3  # phiên bản cache của visuals/render.py cũ (key 12 ký tự)


def _nhan_cache_cu(ten_file_moi: str, payload_cu: Dict[str, Any], tien_to: str) -> Optional[str]:
    """Nhận cache từ bản render v1 để khỏi render lại lãng phí.

    Trả về đường dẫn file mới nếu adopt thành công, ngược lại None.
    Chỉ đọc file .mp4 trong CACHE_DIR, không đụng gì khác.
    """
    try:
        key_cu = hashlib.sha1(
            json.dumps(payload_cu, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()[:12]
        duong_cu = os.path.join(CACHE_DIR, f"{tien_to}_{key_cu}.mp4")
        if os.path.exists(duong_cu) and os.path.getsize(duong_cu) > 0:
            shutil.copyfile(duong_cu, ten_file_moi)
            return ten_file_moi
    except Exception:
        pass
    return None


def _extract_preview_frames(mp4: str, cache_prefix: str, count: int = 4) -> List[str]:
    """Extract evenly sampled JPEG previews. Failure is non-fatal."""
    count = max(0, min(int(count), 8))
    if not mp4 or count <= 0:
        return []
    ffmpeg = _ffmpeg_exe()
    if not ffmpeg:
        return []

    # Use ffprobe if available for accurate duration; otherwise use a safe fps filter.
    preview_dir = os.path.join(CACHE_DIR, "previews")
    os.makedirs(preview_dir, exist_ok=True)
    pattern = os.path.join(preview_dir, f"{cache_prefix}_%02d.jpg")

    # thumbnail selects representative frames while keeping the command simple and robust.
    # fps=1/3 gives a useful spread for common short teaching clips; limit output count.
    cmd = [
        ffmpeg, "-y", "-i", mp4,
        "-vf", "fps=1/3,scale=640:-2",
        "-frames:v", str(count),
        pattern,
    ]
    try:
        subprocess.run(cmd, capture_output=True, timeout=45, errors="replace")
    except Exception:
        return []

    out = [os.path.join(preview_dir, f"{cache_prefix}_{i:02d}.jpg") for i in range(1, count + 1)]
    return [p for p in out if os.path.exists(p) and os.path.getsize(p) > 0]


def render(preset, params, quality="l", timeout=300):
    """Render a trusted preset (backward compatible)."""
    # Preset khóa sẵn nên chỉ kẹp tham số số, không sợ code bẩn.
    if quality not in _QUALITY_OK:
        raise ValueError("quality chỉ nhận 'l', 'm', 'h', 'p' hoặc 'k'")
    sach = validate(preset, params)
    key = _cache_key({"p": preset, "q": quality, "v": CODE_VERSION, **sach})
    os.makedirs(CACHE_DIR, exist_ok=True)
    mp4 = os.path.join(CACHE_DIR, f"{preset}_{key}.mp4")
    # Có cache thì trả ngay để lần 2 không tốn vài phút render lại.
    if os.path.exists(mp4) and os.path.getsize(mp4) > 0:
        return {"mp4": mp4, "cached": True, "log": "Lấy từ cache, không render lại."}
    if _nhan_cache_cu(mp4, {"p": preset, "q": quality, "v": _V1_CODE_VERSION, **sach}, preset):
        return {"mp4": mp4, "cached": True, "log": "Nhận cache từ phiên bản trước, không render lại."}

    tmp = tempfile.mkdtemp(prefix="manim_preset_")
    try:
        kq = _render_file(
            SCENES_FILE,
            PRESETS[preset]["scene"],
            quality,
            timeout,
            tmp,
            {"MANIM_PRESET_JSON": json.dumps(sach, ensure_ascii=False)},
            mode="video",
        )
        if not kq.get("mp4"):
            return kq
        shutil.copyfile(kq["mp4"], mp4)
        return {"mp4": mp4, "cached": False, "log": "Render xong."}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def render_code(code, quality="l", timeout=300, ten="ai_tu_do", preview_count=0):
    """Render AI-generated Manim code after external AST validation."""
    # Code AI phải qua kiem_tra_code() trước khi tới đây — hàm này chỉ render.
    if quality not in _QUALITY_OK:
        raise ValueError("quality chỉ nhận 'l', 'm', 'h', 'p' hoặc 'k'")
    key = _cache_key({"c": code, "q": quality, "v": CODE_VERSION, "mode": "video"})
    os.makedirs(CACHE_DIR, exist_ok=True)
    mp4 = os.path.join(CACHE_DIR, f"{ten}_{key}.mp4")

    if os.path.exists(mp4) and os.path.getsize(mp4) > 0:
        previews = _extract_preview_frames(mp4, key, preview_count)
        return {"mp4": mp4, "cached": True, "log": "Lấy từ cache, không render lại.", "previews": previews}
    if _nhan_cache_cu(mp4, {"c": code, "q": quality, "v": _V1_CODE_VERSION}, ten):
        previews = _extract_preview_frames(mp4, key, preview_count)
        return {"mp4": mp4, "cached": True, "log": "Nhận cache từ phiên bản trước.", "previews": previews}

    tmp = tempfile.mkdtemp(prefix="manim_ai_")
    try:
        py_file = os.path.join(tmp, "scene_ai.py")
        with open(py_file, "w", encoding="utf-8") as f:
            f.write(code)
        kq = _render_file(py_file, "GeneratedScene", quality, timeout, tmp, mode="video")
        if not kq.get("mp4"):
            return {**kq, "previews": []}
        shutil.copyfile(kq["mp4"], mp4)
        previews = _extract_preview_frames(mp4, key, preview_count)
        return {"mp4": mp4, "cached": False, "log": "Render xong.", "previews": previews}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def render_code_still(code, quality="m", timeout=300, ten="ai_hinh"):
    """Render the final frame of GeneratedScene as PNG."""
    if quality not in _QUALITY_OK:
        raise ValueError("quality chỉ nhận 'l', 'm', 'h', 'p' hoặc 'k'")
    key = _cache_key({"c": code, "q": quality, "v": CODE_VERSION, "mode": "still"})
    os.makedirs(CACHE_DIR, exist_ok=True)
    png = os.path.join(CACHE_DIR, f"{ten}_{key}.png")

    if os.path.exists(png) and os.path.getsize(png) > 0:
        return {"png": png, "cached": True, "log": "Lấy hình từ cache, không render lại."}

    tmp = tempfile.mkdtemp(prefix="manim_still_")
    try:
        py_file = os.path.join(tmp, "scene_ai.py")
        with open(py_file, "w", encoding="utf-8") as f:
            f.write(code)
        kq = _render_file(py_file, "GeneratedScene", quality, timeout, tmp, mode="still")
        if not kq.get("png"):
            return kq
        shutil.copyfile(kq["png"], png)
        return {"png": png, "cached": False, "log": "Render hình xong."}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
