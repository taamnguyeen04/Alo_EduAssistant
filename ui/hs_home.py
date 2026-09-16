import os
import streamlit as st
import random
import base64
import urllib.parse
from core import store, subjects, curriculum
from ui import widgets
from ui.theme import goto, chon_bai_va_di

ATTEMPT_DIR = os.path.join("data", "attempts")

def _render_html(s):
    st.html(s)

@st.cache_data
def _get_base64_image(file_name):
    path = os.path.join("img", file_name)
    if not os.path.exists(path): return ""
    with open(path, "rb") as f:
        ext = file_name.split('.')[-1]
        if ext == 'jpg': ext = 'jpeg'
        return f"data:image/{ext};base64,{base64.b64encode(f.read()).decode()}"

def _extract_yt_id(link):
    if "youtu.be/" in link:
        return link.split("youtu.be/")[1].split("?")[0]
    if "v=" in link:
        return urllib.parse.parse_qs(urllib.parse.urlparse(link).query).get("v", [""])[0]
    return ""

def _attempts(sid):
    if not os.path.isdir(ATTEMPT_DIR):
        return []
    ds = []
    for ten in os.listdir(ATTEMPT_DIR):
        if ten.startswith(sid + "_") and ten.endswith(".json"):
            ds.append(store.doc_json(os.path.join(ATTEMPT_DIR, ten), {}))
    return ds

def render(sid, mon="toan11"):
    hs = store.doc_hs(sid)
    cfg = subjects.lay_mon(mon)
    ten = hs.get("ten", sid)
    lop = hs.get("lop", "11")
    atts = _attempts(sid)
    
    # Custom CSS for modern UI
    _render_html("""
        <style>
        .ed-card {
            background: white; border-radius: 20px; border: 1px solid #e2e8f0;
            box-shadow: 0 4px 15px rgba(0,0,0,0.03); transition: all 0.3s ease;
            overflow: hidden; margin-bottom: 24px;
        }
        .ed-card:hover {
            transform: translateY(-4px); box-shadow: 0 12px 25px rgba(0,0,0,0.08);
        }
        .vid-card {
            background: white; border-radius: 16px; border: 1px solid #e2e8f0;
            overflow: hidden; transition: all 0.3s ease; height: 100%;
        }
        .vid-card:hover {
            transform: translateY(-4px); box-shadow: 0 12px 25px rgba(0,0,0,0.08);
        }
        .ai-card {
            background: linear-gradient(145deg, #ffffff, #f8fafc); border: 1px solid #e2e8f0;
            border-radius: 20px; padding: 24px; box-shadow: 0 8px 20px rgba(0,0,0,0.03);
            height: 100%;
        }
        .btn-overlay div[data-testid="stButton"] button {
            width: 100%; border-radius: 12px; font-weight: 600;
        }
        </style>
    """)

    # ── 1. HERO / WELCOME SECTION ──
    bai_hien_tai = hs.get("bai_hien_tai", "Chưa chọn bài")
    progress = random.randint(30, 80) if bai_hien_tai != "Chưa chọn bài" else 0
    
    _render_html(f"""
        <div style='background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); border-radius: 24px; padding: 40px; color: white; display: flex; align-items: center; justify-content: space-between; margin-bottom: 40px; box-shadow: 0 10px 30px rgba(37,99,235,0.2);'>
            <div style='flex: 1;'>
                <div style='font-size: 16px; font-weight: 600; color: #bfdbfe; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px;'>Học sinh lớp {lop}</div>
                <h1 style='font-size: 36px; font-weight: 800; margin: 0 0 16px 0; color: white;'>Xin chào, {ten}! 👋</h1>
                <div style='display: flex; gap: 16px; margin-bottom: 32px;'>
                    <div style='background: rgba(255,255,255,0.15); padding: 8px 16px; border-radius: 12px; font-weight: 600; backdrop-filter: blur(10px);'>🔥 7 ngày liên tục</div>
                    <div style='background: rgba(255,255,255,0.15); padding: 8px 16px; border-radius: 12px; font-weight: 600; backdrop-filter: blur(10px);'>🎯 Mục tiêu: Chinh phục {cfg['ten']}</div>
                </div>
                
                <div style='background: rgba(0,0,0,0.2); padding: 24px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.1); max-width: 500px;'>
                    <div style='font-size: 14px; font-weight: 600; color: #93c5fd; margin-bottom: 8px;'>TIẾP TỤC BÀI HỌC • {cfg['ten']}</div>
                    <h3 style='font-size: 20px; font-weight: 700; margin: 0 0 16px 0; color: white;'>{bai_hien_tai}</h3>
                    <div style='display: flex; align-items: center; gap: 12px; margin-bottom: 8px;'>
                        <div style='flex: 1; background: rgba(255,255,255,0.2); height: 8px; border-radius: 4px;'>
                            <div style='background: #60a5fa; height: 8px; border-radius: 4px; width: {progress}%;'></div>
                        </div>
                        <div style='font-size: 14px; font-weight: 600;'>{progress}%</div>
                    </div>
                </div>
            </div>
            <div style='width: 140px; margin-left: 20px; display: flex; flex-direction: column; gap: 12px;'>
            </div>
        </div>
    """)
    
    # Overlay for Hero button
    _render_html("<div style='margin-top:-104px; margin-left:calc(100% - 170px); position:relative; z-index:10; width:140px;' class='btn-overlay'>")
    if st.button("Tiếp tục học →", type="primary", key="btn_hero_tieptuc"):
        goto("📚 Bài học")
        st.rerun()
    _render_html("</div>")
    _render_html("<div style='height: 80px'></div>")

    # ── 2. CÁC MÔN HỌC CỦA BẠN ──
    _render_html("<h2 style='font-size:22px; font-weight:800; color:#0f172a; margin-bottom:24px;'>📚 Các môn học của bạn</h2>")
    ds_mon = subjects.MON_HOC
    
    # Display in rows of 4
    mon_keys = list(ds_mon.keys())
    for i in range(0, len(mon_keys), 4):
        cols = st.columns(4)
        for j in range(4):
            if i + j < len(mon_keys):
                ma = mon_keys[i + j]
                m = ds_mon[ma]
                with cols[j]:
                    img_b64 = _get_base64_image(m.get("img", "toan11.png"))
                    bai_count = len(curriculum.load_videos(ma)) if m.get("co_du_lieu") else 0
                    is_active = (ma == mon)
                    active_border = "border: 2px solid #3b82f6;" if is_active else ""
                    
                    _render_html(f"""
                        <div class='ed-card' style='{active_border}'>
                            <div style="height: 120px; background-image: url('{img_b64}'); background-size: cover; background-position: center;"></div>
                            <div style='padding: 16px;'>
                                <h4 style='margin: 0 0 8px 0; font-size: 16px; font-weight: 700; color: #1e293b;'>{m['icon']} {m['ten']}</h4>
                                <div style='font-size: 13px; color: #64748b; margin-bottom: 16px;'>{bai_count} bài học { "• Đang học" if is_active else "" }</div>
                            </div>
                        </div>
                    """)
                    _render_html("<div style='margin-top:-64px; padding: 0 16px 16px 16px;' class='btn-overlay'>")
                    if st.button("Vào học", key=f"btn_mon_{ma}", use_container_width=True):
                        st.session_state.mon = ma
                        st.rerun()
                    _render_html("</div>")
    
    _render_html("<div style='height: 32px'></div>")

    # ── 3 & 4. VIDEO & AI GỢI Ý ──
    c_vid, c_ai = st.columns([1.5, 1])
    
    with c_vid:
        _render_html("<h2 style='font-size:22px; font-weight:800; color:#0f172a; margin-bottom:24px;'>🎥 Video bài giảng</h2>")
        videos = curriculum.load_videos(mon)
        if videos:
            vcols = st.columns(2)
            for idx, v in enumerate(videos[:2]):
                with vcols[idx]:
                    yt_id = _extract_yt_id(v.get("link", ""))
                    thumb = f"https://img.youtube.com/vi/{yt_id}/hqdefault.jpg" if yt_id else "https://via.placeholder.com/300x169.png?text=No+Thumbnail"
                    
                    _render_html(f"""
                        <div class='vid-card'>
                            <div style="position: relative;">
                                <img src="{thumb}" style="width: 100%; height: 140px; object-fit: cover;">
                                <div style="position: absolute; bottom: 8px; right: 8px; background: rgba(0,0,0,0.8); color: white; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 600;">15:00</div>
                            </div>
                            <div style='padding: 16px;'>
                                <div style='font-size: 12px; font-weight: 600; color: #3b82f6; margin-bottom: 4px;'>{cfg['ten']} • {v.get('chapter', 'Chương 1')}</div>
                                <div style='font-size: 14px; font-weight: 700; color: #1e293b; line-height: 1.4; height: 40px; overflow: hidden;'>{v.get('title', 'Bài giảng')}</div>
                            </div>
                        </div>
                    """)
                    _render_html("<div style='margin-top:-16px; padding: 0 16px 16px 16px;' class='btn-overlay'>")
                    if st.button("Xem video", key=f"btn_vid_{idx}", use_container_width=True):
                        goto("📚 Bài học")
                        st.rerun()
                    _render_html("</div>")
        else:
            st.info(f"Môn {cfg['ten']} chưa có video.")

    with c_ai:
        _render_html("<h2 style='font-size:22px; font-weight:800; color:#0f172a; margin-bottom:24px;'>🤖 AI gợi ý cho em</h2>")
        _render_html("""
            <div class='ai-card'>
                <div style='display: flex; gap: 12px; margin-bottom: 20px;'>
                    <div style='background: #dcfce7; color: #166534; padding: 8px 12px; border-radius: 12px; flex: 1;'>
                        <div style='font-size: 12px; font-weight: 700; margin-bottom: 4px;'>ĐIỂM MẠNH ✅</div>
                        <div style='font-size: 13px; font-weight: 500;'>Tính toán cẩn thận</div>
                    </div>
                    <div style='background: #fee2e2; color: #991b1b; padding: 8px 12px; border-radius: 12px; flex: 1;'>
                        <div style='font-size: 12px; font-weight: 700; margin-bottom: 4px;'>CẦN CẢI THIỆN ⚠</div>
                        <div style='font-size: 13px; font-weight: 500;'>Nhầm dấu (-)</div>
                    </div>
                </div>
                <div style='background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px;'>
                    <div style='font-size: 14px; font-weight: 700; color: #1e293b; margin-bottom: 12px;'>Kế hoạch tiếp theo:</div>
                    <div style='display: flex; align-items: center; gap: 8px; margin-bottom: 8px; font-size: 13px; color: #475569;'>
                        <span style='background: #f1f5f9; padding: 4px; border-radius: 6px;'>▶</span> Ôn lại bài Công thức lượng giác
                    </div>
                    <div style='display: flex; align-items: center; gap: 8px; margin-bottom: 16px; font-size: 13px; color: #475569;'>
                        <span style='background: #f1f5f9; padding: 4px; border-radius: 6px;'>✏</span> Làm 5 bài tập nhận biết
                    </div>
                </div>
            </div>
        """)
        _render_html("<div style='margin-top:-64px; padding: 0 24px; position:relative; z-index:10;' class='btn-overlay'>")
        if st.button("Làm bài tập AI", type="primary", use_container_width=True):
            goto("✏ Luyện tập")
            st.rerun()
        _render_html("</div>")

    _render_html("<div style='height: 32px'></div>")

    # ── 3b. VIỆC GV GIAO + NHÓM HỌC ──
    from core import lop as lop_core
    _render_html("<h2 style='font-size:22px; font-weight:800; color:#0f172a; margin-bottom:24px;'>📌 Việc GV giao & Nhóm học</h2>")
    c_job, c_grp = st.columns([1.5, 1])
    with c_job:
        viec = [g for g in lop_core.viec_cua_hs(sid) if g.get("trang_thai") != "xong"][:5]
        if viec:
            items = "".join(
                f"<div style='display:flex;justify-content:space-between;align-items:center;"
                f"padding:10px 0;border-bottom:1px solid #f1f5f9;font-size:14px;'>"
                f"<span style='font-weight:600;color:#1e293b;'>{g.get('bai','')}</span>"
                f"<span style='font-size:12px;color:{'#dc2626' if g.get('trang_thai')=='qua_han' else '#64748b'};'>"
                f"hạn {g.get('han','—')}</span></div>" for g in viec)
            _render_html(f"<div class='ed-card' style='padding: 20px;'>{items}</div>")
        else:
            _render_html("<div class='ed-card' style='padding: 20px; color:#64748b; font-size:14px;'>"
                         "Không có việc tồn đọng. 🎉</div>")
    with c_grp:
        nhom = lop_core.nhom_cua_hs(sid)[:3]
        if nhom:
            for n in nhom:
                tv = n.get("thanh_vien", [])
                # Hiện tên kèm mã để em biết mình đúng nhóm
                ten_tv = []
                for m in tv:
                    try:
                        h = store.doc_hs(m)
                        ten_tv.append(f"{h.get('ten', m)} ({m})")
                    except Exception:
                        ten_tv.append(m)
                items = "".join(
                    f"<div style='padding:6px 0;font-size:13px;color:#334155;'>👤 {t}</div>"
                    for t in ten_tv)
                with st.container(border=True):
                    st.markdown(f"👥 **{n.get('id', '')}** — {n.get('muc_tieu') or 'Nhóm học'}")
                    st.caption(f"📖 {n.get('bai', '')} • Cùng: {', '.join(tv)}")
                    st.markdown(items, unsafe_allow_html=True)
                    if st.button("✏ Luyện bài nhóm", key=f"luyen-nhom-{n.get('id', '')}",
                                 type="primary", use_container_width=True):
                        # Đặt Bài hiện tại = Bài của nhóm rồi nhảy sang Luyện tập
                        chon_bai_va_di(sid, n.get("bai", ""), "✏ Luyện tập")
                        st.rerun()
        else:
            _render_html("<div class='ed-card' style='padding: 20px; color:#64748b; font-size:14px;'>"
                         f"Chưa vào nhóm nào (mã của em: <b>{sid}</b>).<br>"
                         "GV ghép theo <b>Bài đang học</b> — kiểm tra:<br>"
                         "1) GV đã bấm <b>Tạo nhóm</b> chưa (mới Gợi ý thì chưa thấy),<br>"
                         "2) Mã đăng nhập có khớp mã trong nhóm không,<br>"
                         "3) Bài đang học ở Hồ sơ có khớp Bài của nhóm không.</div>")

    _render_html("<div style='height: 32px'></div>")

    # ── 5 & 6. BÀI TẬP VÀ HOẠT ĐỘNG ──
    c_prac, c_act = st.columns([1.5, 1])
    
    with c_prac:
        _render_html("<h2 style='font-size:22px; font-weight:800; color:#0f172a; margin-bottom:24px;'>✏ Bài tập đề xuất</h2>")
        _render_html("""
            <div class='ed-card' style='padding: 20px;'>
                <div style='display: flex; justify-content: space-between; align-items: center; padding-bottom: 16px; border-bottom: 1px solid #f1f5f9; margin-bottom: 16px;'>
                    <div style='display: flex; align-items: center; gap: 16px;'>
                        <div style='background: #fefce8; color: #ca8a04; width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 18px;'>⭐</div>
                        <div>
                            <div style='font-weight: 600; color: #1e293b; font-size: 15px;'>Rút gọn biểu thức lượng giác</div>
                            <div style='font-size: 13px; color: #64748b;'>10 câu • 15 phút</div>
                        </div>
                    </div>
                    <div style='font-weight: 600; color: #3b82f6; font-size: 14px;'>Khuyên làm</div>
                </div>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <div style='display: flex; align-items: center; gap: 16px;'>
                        <div style='background: #fefce8; color: #ca8a04; width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 18px;'>⭐⭐</div>
                        <div>
                            <div style='font-weight: 600; color: #1e293b; font-size: 15px;'>Bài tập nâng cao phương trình</div>
                            <div style='font-size: 13px; color: #64748b;'>5 câu • 10 phút</div>
                        </div>
                    </div>
                </div>
            </div>
        """)
        _render_html("<div style='margin-top:-64px; margin-left: calc(100% - 120px); padding-right: 20px; position:relative; z-index:10; width:120px;' class='btn-overlay'>")
        if st.button("Làm ngay", key="prac_1"):
            goto("✏ Luyện tập")
            st.rerun()
        _render_html("</div>")

    with c_act:
        _render_html("<h2 style='font-size:22px; font-weight:800; color:#0f172a; margin-bottom:24px;'>🕒 Gần đây</h2>")
        hoat_dong = [
            ("🎥 Đã xem", "Công thức lượng giác", "Hôm nay"),
            ("✏ Hoàn thành", "Bài tập cơ bản", "Hôm qua"),
            ("💬 Hỏi AI", "Giải thích sin cos", "2 ngày trước")
        ]
        html_hd = "<div class='ed-card' style='padding: 24px; height: 100%;'>"
        for loai, title, time in hoat_dong:
            html_hd += f"""
            <div style='display: flex; gap: 16px; margin-bottom: 20px;'>
                <div style='width: 2px; background: #e2e8f0; position: relative;'>
                    <div style='position: absolute; top: 6px; left: -4px; width: 10px; height: 10px; border-radius: 50%; background: #3b82f6;'></div>
                </div>
                <div>
                    <div style='font-size: 12px; font-weight: 700; color: #3b82f6; margin-bottom: 2px;'>{loai}</div>
                    <div style='font-weight: 600; color: #1e293b; font-size: 14px; margin-bottom: 2px;'>{title}</div>
                    <div style='font-size: 12px; color: #64748b;'>{time}</div>
                </div>
            </div>
            """
        html_hd += "</div>"
        _render_html(html_hd)
