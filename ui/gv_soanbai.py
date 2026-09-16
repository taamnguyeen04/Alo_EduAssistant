"""Gộp trang GV: Soạn bài trực quan (P4f) + Học liệu bổ sung (P4b).

Giữ nguyên logic 2 module cũ, chỉ gom chung 1 tab bằng st.tabs.
"""
import streamlit as st
from ui import gv_lesson, gv_hoclieu


def render(mon="toan11"):
    tab1, tab2 = st.tabs(["Soạn bài trực quan", "Học liệu bổ sung"])
    with tab1:
        gv_lesson.render(mon)
    with tab2:
        gv_hoclieu.render(mon)
