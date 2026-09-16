"""Template-first video: khớp mô tả GV -> template có sẵn + slot -> render.

Luồng: chon_template(mo_ta) --khớp--> dien_slot() -> render_template()
                                        --trượt--> trả None để pipeline sinh tự do.
Không tốn token LLM: matcher chạy bằng từ khóa trên manifest (topics,
intent_patterns, best_for, not_for). LLM matcher/adapter trong pack
(ai_prompts/) để dành khi cần độ phủ cao hơn.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK_DIR = os.path.join(BASE_DIR, "data", "manim_math_templates_v1")
TEMPLATES_DIR = os.path.join(PACK_DIR, "templates")
CACHE_DIR = os.path.join(BASE_DIR, "data", "videos_template")

NGUONG_KHOP = 4.0  # điểm tối thiểu để dùng template thay vì sinh tự do


def _doc_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def tai_catalog():
    path = os.path.join(PACK_DIR, "template_catalog.json")
    if not os.path.exists(path):
        return []
    try:
        data = _doc_json(path)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _chuan_hoa(s):
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def cham_diem(mo_ta, muc):
    """Chấm khớp mô tả với 1 template: trúng not_for bị phạt nặng."""
    mo = _chuan_hoa(mo_ta)
    if not mo:
        return 0.0
    diem = 0.0
    for cum in muc.get("topics", []) + muc.get("best_for", []):
        c = _chuan_hoa(cum)
        if c and (c in mo or mo in c):
            diem += 2.0
    for cum in muc.get("intent_patterns", []):
        c = _chuan_hoa(cum)
        if c and (c in mo or mo in c):
            diem += 3.0
    for cum in muc.get("not_for", []):
        c = _chuan_hoa(cum)
        if c and (c in mo or mo in c):
            diem -= 6.0
    return diem


def chon_template(mo_ta):
    """Trả (muc_catalog, diem) tốt nhất, hoặc (None, 0.0) nếu không đủ ngưỡng."""
    tot, diem_tot = None, 0.0
    for muc in tai_catalog():
        d = cham_diem(mo_ta, muc)
        if d > diem_tot:
            tot, diem_tot = muc, d
    if tot is None or diem_tot < NGUONG_KHOP:
        return None, 0.0
    return tot, diem_tot


def _trich_goc(mo_ta):
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:°|do|độ)", _chuan_hoa(mo_ta))
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except ValueError:
            return None
    m = re.search(r"g[óo]c\s+(\d+(?:[.,]\d+)?)", _chuan_hoa(mo_ta))
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except ValueError:
            return None
    return None


def _trich_ham(mo_ta, allowed):
    mo = _chuan_hoa(mo_ta).replace(" ", "")
    for ham in allowed:
        if ham.replace(" ", "") in mo:
            return ham
    # biến thể viết thường gặp: "sinx" -> "sin(x)"
    if "sin(x)" in allowed and "sinx" in mo:
        return "sin(x)"
    if "cos(x)" in allowed and "cosx" in mo:
        return "cos(x)"
    return None


def dien_slot(mo_ta, muc):
    """Điền slot từ mô tả + default manifest, có kẹp min/max và allowed."""
    slots = (muc.get("slots") or {})
    params = {}
    for ten, dinh_nghia in slots.items():
        loai = dinh_nghia.get("type", "number")
        mac_dinh = dinh_nghia.get("default")
        if loai == "boolean":
            params[ten] = bool(mac_dinh)
        elif loai == "choice":
            params[ten] = mac_dinh
        else:
            try:
                params[ten] = float(mac_dinh)
            except (TypeError, ValueError):
                params[ten] = mac_dinh
    # trích xuất thông minh theo tên slot quen thuộc
    if "angle_deg" in slots:
        goc = _trich_goc(mo_ta)
        if goc is not None:
            params["angle_deg"] = goc
    if "cycles" in slots and re.search(r"\b2\s*(chu k|vòng|vong|cycles?)", _chuan_hoa(mo_ta)):
        params["cycles"] = 2
    for ten, dinh_nghia in slots.items():
        if dinh_nghia.get("type") == "choice" and isinstance(dinh_nghia.get("allowed"), list):
            ham = _trich_ham(mo_ta, dinh_nghia["allowed"])
            if ham is not None:
                params[ten] = ham
    # kẹp giá trị theo manifest (giống common/config.py của pack)
    for ten, dinh_nghia in slots.items():
        loai = dinh_nghia.get("type")
        if loai == "number" and isinstance(params.get(ten), (int, float)):
            v = float(params[ten])
            lo, hi = dinh_nghia.get("min"), dinh_nghia.get("max")
            if isinstance(lo, (int, float)):
                v = max(lo, v)
            if isinstance(hi, (int, float)):
                v = min(hi, v)
            if dinh_nghia.get("nonzero") and v == 0:
                v = float(dinh_nghia.get("default") or 1)
            params[ten] = v
        elif loai == "choice":
            allowed = dinh_nghia.get("allowed") or []
            if params.get(ten) not in allowed:
                params[ten] = dinh_nghia.get("default")
    return params


def _khoa_cache(template_id, version, params, quality):
    raw = json.dumps({"t": template_id, "v": version, "p": params, "q": quality},
                     ensure_ascii=False, sort_keys=True)
    return f"{template_id}_{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]}.mp4"


def render_template(template_id, params, quality="l", timeout=600):
    """Render 1 template qua scripts/render_template.py, có cache theo params."""
    catalog = {m.get("template_id"): m for m in tai_catalog()}
    muc = catalog.get(template_id)
    if muc is None:
        return {"mp4": "", "log": f"Không có template {template_id}.", "cached": False}
    manifest_path = os.path.join(TEMPLATES_DIR, template_id, "manifest.json")
    try:
        manifest = _doc_json(manifest_path)
    except Exception as e:
        return {"mp4": "", "log": f"Manifest lỗi: {e}", "cached": False}
    version = manifest.get("version", "1.0.0")
    scene_class = manifest.get("scene_class", "")

    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, _khoa_cache(template_id, version, params, quality))
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 5000:
        return {"mp4": cache_path, "log": "Dùng video template đã render trước đó.",
                "cached": True}

    media_dir = tempfile.mkdtemp(prefix="manim_tpl_")
    cmd = [sys.executable, os.path.join(PACK_DIR, "scripts", "render_template.py"),
           template_id, "--params", json.dumps(params, ensure_ascii=False),
           "--quality", quality, "--media-dir", media_dir]
    # Windows: console mặc định cp1252 làm tiến trình con nổ khi log có chữ Việt.
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        hoan_tat = subprocess.run(cmd, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=timeout,
                                  env=env)
    except subprocess.TimeoutExpired:
        shutil.rmtree(media_dir, ignore_errors=True)
        return {"mp4": "", "log": f"Render template {template_id} quá {timeout}s.", "cached": False}
    if hoan_tat.returncode != 0:
        tail = (hoan_tat.stderr or hoan_tat.stdout or "")[-1500:]
        shutil.rmtree(media_dir, ignore_errors=True)
        return {"mp4": "", "log": f"Render template {template_id} lỗi: {tail}", "cached": False}
    mp4 = ""
    if scene_class:
        for root, _ds, files in os.walk(media_dir):
            if f"{scene_class}.mp4" in files:
                mp4 = os.path.join(root, f"{scene_class}.mp4")
                break
    if not mp4 or not os.path.exists(mp4):
        shutil.rmtree(media_dir, ignore_errors=True)
        return {"mp4": "", "log": f"Không tìm thấy mp4 của {scene_class}.", "cached": False}
    try:
        shutil.copyfile(mp4, cache_path)
    except OSError as e:
        shutil.rmtree(media_dir, ignore_errors=True)
        return {"mp4": "", "log": f"Không lưu được cache: {e}", "cached": False}
    shutil.rmtree(media_dir, ignore_errors=True)
    return {"mp4": cache_path, "log": f"Render template {template_id} xong.", "cached": False}


def sinh_video_template(mo_ta, quality="l", timeout=600):
    """Thử đường template: khớp -> (template_id, params) + render; trượt -> template None."""
    muc, diem = chon_template(mo_ta)
    if muc is None:
        return {"mp4": "", "log": "Không có template phù hợp.", "cached": False,
                "template": None, "params": {}, "diem": 0.0}
    params = dien_slot(mo_ta, muc)
    kq = render_template(muc["template_id"], params, quality=quality, timeout=timeout)
    kq.update({"template": muc["template_id"], "params": params, "diem": diem,
               "ten_vi": muc.get("name_vi", "")})
    return kq
