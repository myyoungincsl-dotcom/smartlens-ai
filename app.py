import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import re
import json

# --- 1. CẤU HÌNH AI AN TOÀN ---
# Hệ thống sẽ ưu tiên lấy Key trong phần "Secrets" của Streamlit để tránh bị lộ (Leaked)
API_KEY = st.secrets.get("GEMINI_API_KEY", "")

if API_KEY:
    genai.configure(api_key=API_KEY)
    
else:
    st.error("❌ Chưa tìm thấy API Key trong phần Secrets của Streamlit!")

@st.cache_resource
def get_available_model():
    """Tự động dò tìm model đang hoạt động để tránh lỗi 404"""
    try:
        priority_list = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for target in priority_list:
            for model_name in available_models:
                if target in model_name:
                    return genai.GenerativeModel(model_name)
        return genai.GenerativeModel(available_models[0])
    except Exception as e:
        st.error(f"Lỗi kết nối AI: {e}")
        return None

model = get_available_model()

# --- 2. QUẢN LÝ DỮ LIỆU ---
if 'score' not in st.session_state: st.session_state.score = 0
if 'streak' not in st.session_state: st.session_state.streak = 0
if 'student_name' not in st.session_state: st.session_state.student_name = ""
if 'current_data' not in st.session_state: st.session_state.current_data = None
if 'answered_status' not in st.session_state: st.session_state.answered_status = {}
if 'notes' not in st.session_state: st.session_state.notes = ""
if 'manual_mode' not in st.session_state: st.session_state.manual_mode = False
if 'history' not in st.session_state: st.session_state.history = []

# --- 3. CSS GIAO DIỆN (70PX, 750PX, STREAK 80PX) ---
st.set_page_config(page_title="SmartLens AI Pro", layout="wide", page_icon="🛡️")
st.markdown(f"""
<style>
    .stApp {{ background-color: #0d1117; color: #c9d1d9; }}
    h1 {{ font-size: 70px !important; font-weight: 900 !important; color: #58a6ff !important; text-align: center; line-height: 1.1; }}
    .streak-val {{ color: #ff4b4b !important; font-size: 80px !important; font-weight: 900 !important; text-align: center; margin: 0; }}
    .note-box textarea {{ height: 750px !important; background-color: #161b22 !important; color: #e6edf3 !important; border: 1px solid #30363d !important; font-size: 16px !important; }}
    .check-box {{ background-color: #161b22; border-left: 15px solid #0056b3; padding: 35px; border-radius: 15px; border: 1px solid #30363d; line-height: 1.8; }}
</style>
""", unsafe_allow_html=True)

# --- 4. HÀM XỬ LÝ PHÂN TÍCH ---
def run_analysis(text, title="Bài học"):
    if not text or model is None: return
    with st.spinner("AI đang thẩm định tri thức..."):
        try:
            prompt = f"Phân tích tiếng Việt chuyên sâu (Xác thực, Phản biện, Mở rộng) + 5 câu hỏi trắc nghiệm JSON: {text[:4500]}"
            res = model.generate_content(prompt)
            match = re.search(r"\{.*\}", res.text, re.DOTALL)
            if match:
                data = json.loads(match.group())
                st.session_state.current_data = data
                st.session_state.history.append({"title": title[:25], "data": data})
                st.session_state.manual_mode = False
                st.session_state.answered_status = {}
                st.rerun()
        except Exception as e:
            st.error(f"Lỗi: {e}")

# --- 5. SIDEBAR ---
with st.sidebar:
    st.markdown("<h1 style='font-size: 40px !important;'>🛡️ SMARTLENS</h1>", unsafe_allow_html=True)
    if not st.session_state.student_name:
        name = st.text_input("👤 Tên học sinh:")
        if name: st.session_state.student_name = name; st.rerun()
    else:
        st.markdown(f"### Học sinh: **{st.session_state.student_name}**")

    st.markdown(f"""
        <div style="text-align: center; background: #161b22; padding: 20px; border-radius: 15px; border: 2px solid #0056b3; margin-top: 10px;">
            <p style="font-size: 14px; color: #8b949e;">ĐIỂM TÍCH LŨY</p>
            <h1 style="color: #f2cc60; font-size: 60px !important; margin: 0;">{st.session_state.score}</h1>
            <hr style="border: 0.5px solid #30363d;">
            <p style="font-size: 14px; color: #8b949e;">CHUỖI (STREAK)</p>
            <p class="streak-val">{st.session_state.streak} 🔥</p>
        </div>
    """, unsafe_allow_html=True)

    if st.button("➕ BÀI HỌC MỚI", use_container_width=True, type="primary"):
        st.session_state.current_data = None
        st.session_state.manual_mode = False
        st.rerun()

    st.markdown("---")
    st.markdown("### 📚 LỊCH SỬ BÀI HỌC")
    for i, item in enumerate(st.session_state.history):
        if st.button(f"📖 {item['title']}", key=f"h_{i}", use_container_width=True):
            st.session_state.current_data = item['data']
            st.rerun()

# --- 6. GIAO DIỆN CHÍNH ---
st.markdown("<h1>🛡️ THẨM ĐỊNH CHUYÊN SÂU</h1>", unsafe_allow_html=True)
m_col, n_col = st.columns([3.8, 1.2])

with n_col:
    st.markdown("### 📝 GHI CHÚ PHẢN BIỆN")
    st.session_state.notes = st.text_area("", value=st.session_state.notes, key="note_final", height=750)

with m_col:
    t1, t2 = st.tabs(["📺 KIỂM CHỨNG VIDEO", "📝 KIỂM CHỨNG VĂN BẢN"])
    
    with t1:
        url = st.text_input("Dán link YouTube:", placeholder="https://youtube.com/...")
        if st.button("🚀 PHÂN TÍCH VIDEO", type="primary"):
            v_match = re.search(r"(?:v=|\/)([a-zA-Z0-9_-]{11})", url)
            if v_match:
                try:
                    ts = YouTubeTranscriptApi.get_transcript(v_match.group(1), languages=['vi', 'en'])
                    run_analysis(" ".join([i['text'] for i in ts]), title=f"Video {v_match.group(1)}")
                except:
                    st.session_state.manual_mode = True
                    st.error("⚠️ YouTube không cấp phụ đề tự động.")

        if st.session_state.manual_mode:
            st.warning("👉 CÁCH DỰ PHÒNG: Lấy văn bản từ DownSub dán vào đây.")
            st.link_button("1. LẤY VĂN BẢN", f"https://downsub.com/?url={url}")
            manual_in = st.text_area("2. Dán nội dung vào đây:", height=150)
            if st.button("🔍 XÁC NHẬN PHÂN TÍCH"):
                run_analysis(manual_in, title="Dữ liệu thủ công")

    with t2:
        txt_in = st.text_area("Dán văn bản cần mổ xẻ:", height=300)
        if st.button("🔍 KIỂM CHỨNG NGAY", type="primary"):
            run_analysis(txt_in, title="Văn bản")

    if st.session_state.current_data:
        d = st.session_state.current_data
        st.markdown("---")
        st.markdown(f'<div class="check-box">{d.get("verification", "")}</div>', unsafe_allow_html=True)
        st.markdown("## ✍️ THỬ THÁCH TƯ DUY")
        for i, q in enumerate(d.get('questions', [])):
            st.write(f"**Câu {i+1}: {q['q']}**")
            ans = st.radio("Chọn:", q['options'], index=None, key=f"q_{i}")
            if ans and ans.startswith(q.get('correct', '')):
                if f"q_{i}" not in st.session_state.answered_status:
                    st.session_state.score += 10
                    st.session_state.streak += 1
                    st.session_state.answered_status[f"q_{i}"] = True
                    st.rerun()
                st.success("Chính xác! +10 điểm")
