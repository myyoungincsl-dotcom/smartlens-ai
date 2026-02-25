import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import re
import json

# --- 1. CẤU HÌNH AI (TỰ ĐỘNG DÒ MODEL) ---
API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    st.error("❌ THIẾU API KEY TRONG SECRETS!")
    st.stop()

@st.cache_resource
def get_working_model():
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for m in models:
            if '1.5-flash' in m: return genai.GenerativeModel(m)
        return genai.GenerativeModel(models[0])
    except: return None

model = get_working_model()

# --- 2. QUẢN LÝ SESSION ---
if 'score' not in st.session_state: st.session_state.score = 0
if 'streak' not in st.session_state: st.session_state.streak = 0
if 'current_data' not in st.session_state: st.session_state.current_data = None
if 'student_name' not in st.session_state: st.session_state.student_name = ""
if 'name_confirmed' not in st.session_state: st.session_state.name_confirmed = False
if 'answered_questions' not in st.session_state: st.session_state.answered_questions = {}

# --- 3. SIDEBAR (PROFILE & TÙY CHỈNH GIAO DIỆN) ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🛡️ PROFILE</h2>", unsafe_allow_html=True)
    
    if not st.session_state.name_confirmed:
        name_input = st.text_input("Tên học sinh:")
        if st.button("XÁC NHẬN", use_container_width=True):
            if name_input:
                st.session_state.student_name = name_input
                st.session_state.name_confirmed = True
                st.rerun()
    else:
        st.markdown(f"<h3 style='text-align:center; color:#58a6ff;'>🌟 Chào {st.session_state.student_name}!</h3>", unsafe_allow_html=True)
        if st.button("Đổi tên"):
            st.session_state.name_confirmed = False
            st.rerun()

    st.markdown(f"""
        <div style="background: #161b22; padding: 20px; border-radius: 20px; border: 1px solid #30363d; text-align: center;">
            <p style="margin:0; font-size:14px; color:#8b949e;">ĐIỂM SỐ</p>
            <p style="font-size: 80px !important; font-weight: 900 !important; color: #f2cc60 !important; margin: 0;">{st.session_state.score}</p>
            <div style="height:15px"></div>
            <p style="margin:0; font-size:14px; color:#8b949e;">CHUỖI LỬA</p>
            <p style="font-size: 80px !important; font-weight: 900 !important; color: #ff4b4b !important; margin: 0;">{st.session_state.streak} 🔥</p>
        </div>
    """, unsafe_allow_html=True)

    if st.button("➕ BÀI HỌC MỚI", use_container_width=True, type="primary"):
        st.session_state.current_data = None
        st.session_state.answered_questions = {}
        st.rerun()

    # --- PHẦN TÙY CHỈNH GIAO DIỆN ---
    st.write("---")
    st.markdown("🎨 **TÙY CHỈNH GIAO DIỆN**")
    user_bg_color = st.color_picker("Màu nền App:", "#0d1117")
    user_font_size = st.slider("Cỡ chữ phân tích (px):", 14, 40, 18)

# --- 4. GIAO DIỆN CSS (KẾT HỢP TÙY CHỈNH) ---
st.markdown(f"""
<style>
    .stApp {{ background-color: {user_bg_color} !important; color: #c9d1d9; }}
    .main-title {{ font-size: 70px !important; color: #58a6ff !important; text-align: center; font-weight: 900; margin-bottom: 10px; }}
    .note-box textarea {{ height: 750px !important; background-color: #161b22 !important; color: #e6edf3 !important; border: 1px solid #30363d !important; border-radius: 15px; }}
    
    /* Ô PHÂN TÍCH CHÍNH - CỠ CHỮ ĐƯỢC KẾT NỐI VỚI SLIDER */
    .check-box {{ 
        background: rgba(22, 27, 34, 0.8); 
        border-left: 8px solid #58a6ff; 
        padding: 25px; 
        border-radius: 15px; 
        border: 1px solid #30363d; 
        line-height: 1.6;
        font-size: {user_font_size}px !important;
    }}
    .guide-box {{ background: #1c2128; padding: 15px; border-radius: 10px; border: 1px dashed #58a6ff; margin-bottom: 20px; }}
</style>
""", unsafe_allow_html=True)

# --- 5. HÀM PHÂN TÍCH ---
def run_analysis(text):
    if not text or model is None: return
    input_content = text[:2800].replace('"', "'")
    with st.spinner("🕵️ SmartLens đang thẩm định tư duy..."):
        try:
            prompt = f"""
            Đóng vai chuyên gia tư duy phản biện. Phân tích SÂU SẮC, ĐA CHIỀU (250 từ) nội dung sau.
            Dùng <b> và <br>. Tạo 3 câu hỏi trắc nghiệm JSON.
            TRẢ VỀ JSON:
            {{
                "verification": "nội dung phân tích",
                "questions": [{{"q": "câu hỏi", "options": ["A. x", "B. y", "C. z", "D. t"], "correct": "A"}}]
            }}
            NỘI DUNG: {input_content}
            """
            response = model.generate_content(prompt)
            match = re.search(r"\{.*\}", response.text, re.DOTALL)
            if match:
                clean_json = re.sub(r',\s*([\}\]])', r'\1', match.group().replace('\n', ' '))
                st.session_state.current_data = json.loads(clean_json)
                st.session_state.answered_questions = {}
                st.rerun()
        except: st.error("Lỗi AI. Vui lòng thử lại!")

# --- 6. GIAO DIỆN CHÍNH ---
st.markdown("<div class='main-title'>🛡️ SMARTLENS AI</div>", unsafe_allow_html=True)
left, right = st.columns([3.8, 1.2])

with right:
    st.markdown("### 📝 GHI CHÚ")
    st.text_area("", height=750, key="notes_fixed_v2", placeholder="Ghi chú tại đây (750px)...")

with left:
    tab1, tab2 = st.tabs(["📺 VIDEO YOUTUBE", "📝 VĂN BẢN"])
    
    with tab1:
        st.markdown(f"""
        <div class="guide-box">
        <b>📺 Hướng dẫn Video:</b> Dán link YouTube có phụ đề.<br>
        <i>* Mẹo:</i> Nếu video báo lỗi, hãy dùng <a href="https://downsub.com/" target="_blank" style="color:#58a6ff; font-weight:bold;">DownSub.com</a> để lấy văn bản, sau đó dán vào tab <b>📝 VĂN BẢN</b>.
        </div>
        """, unsafe_allow_html=True)
        url = st.text_input("Nhập link video:", key="yt_input")
        if st.button("🚀 BẮT ĐẦU PHÂN TÍCH"):
            v_id = re.search(r"(?:v=|\/)([a-zA-Z0-9_-]{11})", url)
            if v_id:
                try:
                    ts = YouTubeTranscriptApi.get_transcript(v_id.group(1), languages=['vi', 'en'])
                    run_analysis(" ".join([i['text'] for i in ts]))
                except: st.error("Video không có phụ đề! Hãy dùng DownSub.com.")
    
    with tab2:
        txt = st.text_area("Dán nội dung cần thẩm định:", height=250, key="txt_input")
        if st.button("🔍 THẨM ĐỊNH TƯ DUY"): run_analysis(txt)

    if st.session_state.current_data:
        st.markdown("---")
        # PHẦN NÀY SẼ THAY ĐỔI CỠ CHỮ THEO THANH TRƯỢT
        st.markdown(f'<div class="check-box">{st.session_state.current_data.get("verification", "")}</div>', unsafe_allow_html=True)
        
        st.markdown("### ✍️ THỬ THÁCH")
        for i, q in enumerate(st.session_state.current_data.get('questions', [])):
            st.write(f"**Câu {i+1}: {q['q']}**")
            ans = st.radio(f"Chọn đáp án {i+1}:", q['options'], key=f"ans_f_{i}", index=None)
            if ans and ans.startswith(q['correct']):
                if f"q_{i}" not in st.session_state.answered_questions:
                    st.session_state.score += 10
                    st.session_state.streak += 1
                    st.session_state.answered_questions[f"q_{i}"] = True
                    st.balloons()
                    st.rerun()
