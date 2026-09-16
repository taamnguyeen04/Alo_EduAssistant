"""Gộp trang GV: Lớp học (P4c) + Giao bài (P4a).

Giữ nguyên logic 2 module cũ, chỉ gom chung 1 tab theo 2 mục.
"""
import streamlit as st
from ui import gv_lop, gv_giaobai


def render(mon="toan11"):
    # Mỗi module cũ đã có page_header riêng làm tiêu đề mục.
    gv_lop.render(mon)
    st.divider()
    gv_giaobai.render(mon)
