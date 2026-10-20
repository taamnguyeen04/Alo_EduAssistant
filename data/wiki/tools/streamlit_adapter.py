"""Streamlit helpers for rendering this LLM Wiki.

The source DOCX contains legacy MathType/OLE equations. In JSON/Markdown they are
preserved as local SVG assets, referenced either by Markdown image syntax or by
HTML <img src="assets/..."> tags emitted by Pandoc. This module renders BOTH
forms, while leaving ordinary Markdown/LaTeX to st.markdown().

Usage:
    from tools.streamlit_adapter import render_md_with_assets, render_question
    render_question(st, question, kb_root)
"""
from pathlib import Path
import re
from typing import Any, Dict, Iterable, Tuple

# Capture Markdown image or HTML img whose src is inside assets/.
_TOKEN_RE = re.compile(
    r"!\[(?P<alt>[^\]]*)\]\((?P<mdsrc>assets/[^)]+)\)"
    r"|<img\b[^>]*\bsrc=[\"'](?P<htmlsrc>assets/[^\"']+)[\"'][^>]*>",
    flags=re.IGNORECASE,
)


def _render_asset(st, root: Path, rel: str, caption: str | None = None) -> None:
    asset = (root / rel).resolve()
    try:
        asset.relative_to(root.resolve())
    except ValueError:
        st.warning(f"Unsafe asset path ignored: {rel}")
        return
    if not asset.exists():
        st.warning(f"Missing asset: {rel}")
        return
    # Streamlit accepts local image paths, including SVG in current releases.
    # If a deployment changes that behavior, the source SVG remains directly
    # accessible and can be converted to PNG without altering the question data.
    st.image(str(asset), caption=caption or None)


def render_md_with_assets(st, markdown_text: str, kb_root) -> None:
    """Render Markdown/LaTeX plus local source-faithful equation/image assets."""
    root = Path(kb_root)
    text = markdown_text or ""
    pos = 0
    for m in _TOKEN_RE.finditer(text):
        before = text[pos:m.start()]
        if before.strip():
            st.markdown(before)
        rel = m.group("mdsrc") or m.group("htmlsrc")
        _render_asset(st, root, rel, m.group("alt"))
        pos = m.end()
    tail = text[pos:]
    if tail.strip():
        st.markdown(tail)


def render_question(st, question: Dict[str, Any], kb_root, show_solution: bool = False) -> None:
    """Reference renderer for a normalized question JSON object."""
    render_md_with_assets(st, question.get("prompt_md") or question.get("stem_md", ""), kb_root)

    qtype = question.get("question_type")
    if qtype == "multiple_choice_single":
        for opt in question.get("options", []):
            st.markdown(f"**{opt.get('key', '')}.**")
            render_md_with_assets(st, opt.get("content_md", ""), kb_root)
    elif qtype == "true_false":
        for item in question.get("statements", []):
            st.markdown(f"**{item.get('key', '')})**")
            render_md_with_assets(st, item.get("content_md", ""), kb_root)

    if show_solution:
        st.markdown("### Đáp án")
        st.write(question.get("correct_answer"))
        solution = question.get("solution_md", "")
        if solution.strip():
            st.markdown("### Lời giải")
            render_md_with_assets(st, solution, kb_root)
