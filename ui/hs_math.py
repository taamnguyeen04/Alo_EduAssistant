import os
import urllib.parse
import streamlit as st
from core import curriculum, store, conversations, subjects, lop
from ui.theme import goto, chon_bai_va_di

LESSON_DIR = os.path.join("data", "lessons")

def _extract_yt_id(link):
    if "youtu.be/" in link:
        return link.split("youtu.be/")[1].split("?")[0]
    if "v=" in link:
        return urllib.parse.parse_qs(urllib.parse.urlparse(link).query).get("v", [""])[0]
    return ""

def _video_minh_hoa(title, mon):
    """Preset Manim đã render xong, gắn đúng Bài này (video hoặc hình PNG)."""
    if not os.path.isdir(LESSON_DIR):
        return []
    ra = []
    for ten in sorted(os.listdir(LESSON_DIR)):
        if not ten.endswith(".json"):
            continue
        d = store.doc_json(os.path.join(LESSON_DIR, ten), {})
        if d.get("mon", "toan11") != mon or d.get("bai") != title:
            continue
        if d.get("video_mp4") and os.path.exists(d["video_mp4"]):
            ra.append(d)
        elif d.get("hinh_png") and os.path.exists(d["hinh_png"]):
            ra.append(d)
    return ra


def render(sid, mon="toan11"):
    cfg = subjects.lay_mon(mon)
    hs = store.doc_hs(sid)

    nhom = curriculum.danh_sach_chuong(mon)
    if not nhom:
        # Môn chưa có dữ liệu: vẫn vào được trang, hiện trạng thái trống
        st.html(f"""
            <div style='text-align:center;padding:56px 24px;background:#ffffff;
                 border:1px solid #e2e8f0;border-radius:20px;box-shadow:0 4px 15px rgba(0,0,0,0.03);'>
                <div style='font-size:52px;margin-bottom:12px;'>{cfg.get('icon', '📚')}</div>
                <div style='font-size:24px;font-weight:800;color:#0f172a;margin-bottom:8px;'>
                    Môn {cfg.get('ten', '')} đang được soạn</div>
                <div style='font-size:15px;color:#64748b;margin-bottom:24px;'>Thầy sẽ cập nhật bài giảng,
                    video và bài tập trong thời gian tới.<br>Em quay lại sau nhé!</div>
            </div>
        """)
        st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
        if st.button("🏠 Về Trang chủ", key="btn_baihoc_home"):
            goto("🏠 Trang chủ")
            st.rerun()
        return

    # ── Thống kê nhanh ──
    so_da_xem = len(hs.get("video_da_xem", []))
    bai_hien = hs.get("bai_hien_tai") or "Chưa chọn"
    c1, c2 = st.columns([3, 1])
    with c1:
        tk = st.text_input("🔍 Tìm bài...", "", placeholder="Nhập tên bài hoặc từ khóa...")
    with c2:
        st.metric("Đã xem", so_da_xem)

    if bai_hien != "Chưa chọn":
        st.markdown(
            f"<div style='background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;"
            f"padding:8px 14px;font-size:0.88rem;color:#166534;margin-bottom:12px;'>"
            f"📖 Đang học: <strong>{bai_hien}</strong></div>",
            unsafe_allow_html=True,
        )

    for chuong, ds in nhom.items():
        loc = [v for v in ds if not tk.strip() or tk.strip().lower() in
               (v.get("title", "") + " ".join(v.get("content", []))).lower()]
        if not loc:
            continue
        da_xem_trong_chuong = sum(1 for v in loc if v.get("link") in hs.get("video_da_xem", []))
        label = f"📁 {chuong}  ({da_xem_trong_chuong}/{len(loc)} hoàn thành)"
        with st.expander(label, expanded=False):
            for v in loc:
                dang_hoc = hs.get("bai_hien_tai") == v.get("title")
                da_xem = v.get("link") in hs.get("video_da_xem", [])

                yt_id = _extract_yt_id(v.get("link", ""))
                thumb = f"https://img.youtube.com/vi/{yt_id}/hqdefault.jpg" if yt_id else "https://via.placeholder.com/320x180.png?text=Video"

                st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
                c_img, c_info = st.columns([1, 2.5])
                
                with c_img:
                    st.html(f"<img src='{thumb}' style='width:100%; border-radius:12px; border: 1px solid #e2e8f0; object-fit: cover; aspect-ratio: 16/9;'>")
                    
                with c_info:
                    # Badge trạng thái
                    badges = ""
                    if dang_hoc:
                        badges += "<span style='background:#dbeafe;color:#1d4ed8;border-radius:6px;padding:2px 8px;font-size:11.5px;font-weight:600;margin-right:8px;'>Đang học</span>"
                    if da_xem:
                        badges += "<span style='background:#dcfce7;color:#16a34a;border-radius:6px;padding:2px 8px;font-size:11.5px;font-weight:600;'>✓ Đã xem</span>"

                    if badges:
                        st.html(f"<div style='margin-bottom:6px;'>{badges}</div>")
                    st.html(f"<h4 style='color:#0f172a; margin:0 0 6px 0; font-size: 16px; font-weight: 700;'>{v.get('title')}</h4>")
                    
                    bullets = "".join([f"<li style='color:#64748b;font-size:13.5px;margin-bottom:2px;'>{y}</li>" for y in v.get("content", [])[:3]])
                    if bullets:
                        st.html(f"<ul style='margin-top:0; padding-left:20px; margin-bottom:12px;'>{bullets}</ul>")
                    
                    # Buttons
                    bc1, bc2, bc3 = st.columns([1.2, 1.2, 1.2])
                    with bc1:
                        st.link_button("▶ Xem video", v["link"], key=f"vid-{v['title']}", use_container_width=True)
                    with bc2:
                        if st.button("💬 Hỏi bài này", key=f"hoi-{v['title']}", type="primary", use_container_width=True):
                            st.session_state.cid = conversations.tao_cuoc(sid, bai=v["title"])
                            chon_bai_va_di(sid, v["title"], "🤖 Hỏi AI")
                            st.rerun()
                    with bc3:
                        if not da_xem:
                            if st.button("✓ Đánh dấu xem", key=f"xem-{v['title']}", use_container_width=True):
                                hs = store.doc_hs(sid)
                                if v["link"] not in hs.get("video_da_xem", []):
                                    hs["video_da_xem"].append(v["link"])
                                    store.luu_hs(sid, hs)
                                    st.rerun()

                them = lop.ds_hoclieu(v.get("title"))
                if them:
                    with st.expander(f"📎 Học liệu thêm ({len(them)})"):
                        for h in them:
                            st.markdown(f"**[{h['loai']}] {h['tieu_de']}**")
                            if h.get("mo_ta"):
                                st.caption(h["mo_ta"])
                            st.link_button("Mở", h["url"], key=f"hl-{h['id']}")
                for vd in _video_minh_hoa(v.get("title"), mon):
                    if vd.get("video_mp4"):
                        with st.expander(f"🎬 Video minh họa: {vd.get('ten', '')}", expanded=False):
                            st.video(vd["video_mp4"])
                    elif vd.get("hinh_png"):
                        with st.expander(f"🖼️ Hình minh họa: {vd.get('ten', '')}", expanded=False):
                            st.image(vd["hinh_png"])
                st.markdown("<hr style='margin:16px 0;border-color:#f1f5f9;'>", unsafe_allow_html=True)

