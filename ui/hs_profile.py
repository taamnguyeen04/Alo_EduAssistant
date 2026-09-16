import os
import streamlit as st
from core import store, subjects, curriculum
from ui import widgets
from ui.theme import page_header

NGAY_TUAN = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
ATTEMPT_DIR = os.path.join("data", "attempts")

def _render_html(s):
    st.html(s)

def render(sid, mon="toan11"):
    cfg = subjects.lay_mon(mon)
    
    _render_html("""
        <style>
        .profile-header {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            border-radius: 20px; padding: 32px; color: white; display: flex; align-items: center; gap: 24px;
            margin-bottom: 32px; box-shadow: 0 10px 25px rgba(15,23,42,0.15);
        }
        .profile-avatar {
            width: 80px; height: 80px; background: #3b82f6; border-radius: 50%; color: #fff;
            display: flex; align-items: center; justify-content: center; font-size: 32px; font-weight: bold;
            box-shadow: 0 0 0 4px rgba(255,255,255,0.2);
        }
        .profile-header h1 {
            color: #fff !important;
        }
        .section-title {
            font-size: 18px; font-weight: 700; color: #1e293b; margin-bottom: 16px;
            padding-bottom: 8px; border-bottom: 2px solid #f1f5f9;
        }
        .stTextInput > div > div > input, .stSelectbox > div > div > div {
            background-color: #f8fafc !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 10px !important;
        }
        .stTextInput > div > div > input:focus, .stSelectbox > div > div > div:focus {
            border-color: #3b82f6 !important;
            box-shadow: 0 0 0 2px rgba(59,130,246,0.2) !important;
        }
        </style>
    """)

    hs = store.doc_hs(sid)
    ten = hs.get("ten", sid)
    lop = hs.get("lop", "11")
    
    _render_html(f"""
        <div class="profile-header">
            <div class="profile-avatar">{ten[0].upper() if ten else 'H'}</div>
            <div>
                <h1 style="margin: 0 0 4px 0; font-size: 32px; font-weight: 800; color: #ffffff;">Hồ sơ học tập</h1>
                <div style="color: #cbd5e1; font-size: 17px;">Mã học sinh: {sid} • Lớp {lop}</div>
            </div>
        </div>
    """)
    
    c1, c2 = st.columns([1.2, 1])
    with c1:
        _render_html("<div class='section-title'>👤 Thông tin cá nhân</div>")
        ten_new = st.text_input("Họ và tên", hs.get("ten", sid))
        
        c_lop, c_trinh = st.columns(2)
        with c_lop:
            lop_new = st.text_input("Lớp", hs.get("lop", "11"))
        with c_trinh:
            idx_trinh = ["yếu", "trung bình", "khá", "giỏi"].index(hs.get("trinh_do_toan", "trung bình")) if hs.get("trinh_do_toan", "trung bình") in ["yếu", "trung bình", "khá", "giỏi"] else 1
            trinh = st.selectbox(f"Trình độ {cfg['ten']}", ["yếu", "trung bình", "khá", "giỏi"], index=idx_trinh)
            
        pc = st.text_input("Cách học hiệu quả nhất (VD: thích ví dụ thực tế, học qua hình ảnh)", hs.get("phong_cach", ""))
        
        _render_html("<br><div class='section-title'>🎯 Điểm mạnh & Điểm yếu</div>")
        c_m, c_y = st.columns(2)
        with c_m:
            manh = st.text_area("Điểm mạnh môn toán", ", ".join(hs.get("manh", [])), height=100, placeholder="Tính toán nhanh, nhớ công thức...")
        with c_y:
            yeu = st.text_area("Điểm yếu môn toán", ", ".join(hs.get("yeu", [])), height=100, placeholder="Hay sai dấu, sợ hình học...")

    with c2:
        _render_html("<div class='section-title'>📅 Kế hoạch học tập</div>")
        ds_bai = [""] + [v["title"] for v in curriculum.load_videos(mon)] + ["ngoài chương trình"]
        bai_ht = hs.get("bai_hien_tai", "")
        idx_bai = ds_bai.index(bai_ht) if bai_ht in ds_bai else 0
        bai = st.selectbox("Bài đang học trên lớp", ds_bai, index=idx_bai)
        
        _render_html("<div style='margin-bottom:8px; font-size:14px; color:#334155; font-weight:600;'>Thời khóa biểu các môn</div>")
        tkb_cu = hs.get("tkb", {}) or {}
        tkb_moi = {}
        
        for i in range(0, 7, 2):
            c_d1, c_d2 = st.columns(2)
            with c_d1:
                ngay = NGAY_TUAN[i]
                tkb_moi[ngay] = st.text_input(ngay, ", ".join(tkb_cu.get(ngay, [])), placeholder="Toán, Lý...")
            with c_d2:
                if i + 1 < 7:
                    ngay2 = NGAY_TUAN[i + 1]
                    tkb_moi[ngay2] = st.text_input(ngay2, ", ".join(tkb_cu.get(ngay2, [])), placeholder="Văn, Anh...")
        
        _render_html("<br>")
        if st.button("Lưu", type="primary", use_container_width=True):
            hs.update({
                "ten": ten_new, "lop": lop_new, "trinh_do_toan": trinh, "phong_cach": pc,
                "manh": [x.strip() for x in manh.split(",") if x.strip()],
                "yeu": [x.strip() for x in yeu.split(",") if x.strip()],
                "bai_hien_tai": bai,
                "tkb": {n: [m.strip() for m in tkb_moi[n].split(",") if m.strip()]
                        for n in NGAY_TUAN if tkb_moi[n].strip()}
            })
            store.luu_hs(sid, hs)
            st.success("Đã lưu hồ sơ. AI sẽ cá nhân hóa bài giảng theo thiết lập này.")
            st.rerun()
