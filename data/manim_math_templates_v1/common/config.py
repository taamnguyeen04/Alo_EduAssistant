import json, math, os
ENV_KEY = 'MANIM_TEMPLATE_JSON'

def load_params():
    try:
        v = json.loads(os.environ.get(ENV_KEY, '{}'))
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}

def number(p, key, default, lo=None, hi=None):
    try: v = float(p.get(key, default))
    except (TypeError, ValueError): v = float(default)
    if not math.isfinite(v): v = float(default)
    if lo is not None: v = max(lo, v)
    if hi is not None: v = min(hi, v)
    return v

def integer(p, key, default, lo=None, hi=None): return int(round(number(p, key, default, lo, hi)))
def boolean(p, key, default=False):
    v = p.get(key, default)
    if isinstance(v, str): return v.strip().lower() in {'1','true','yes','y','on'}
    return bool(v)
def choice(p, key, default, allowed):
    v = str(p.get(key, default)); return v if v in set(allowed) else default
