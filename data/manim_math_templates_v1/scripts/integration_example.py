"""Khung tích hợp template-first vào pipeline AI hiện tại."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def load_catalog(): return json.loads((ROOT/'template_catalog.json').read_text(encoding='utf-8'))
def build_matcher_payload(user_prompt):
    return {'system':(ROOT/'ai_prompts'/'template_matcher_system.txt').read_text(encoding='utf-8'),'user':{'prompt':user_prompt,'catalog':load_catalog()}}
def should_use_template(match):
    return bool(match.get('template_id')) and float(match.get('confidence',0))>=0.65 and not bool(match.get('fallback_required',False))
