import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import re
import json
import time

# --- 1. CẤU HÌNH AI (GIẢI QUYẾT TRIỆT ĐỂ LỖI 429) ---
API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    st.error("❌ THIẾU API KEY TRONG SECRETS!")
    st.stop()

@st.cache_resource
def get_working_model():
    # Sử dụng gemini-1.5-flash để có hạn mức (quota) cao nhất, tránh lỗi 429 triệt để
    try:
        return genai.GenerativeModel('gemini-1.5-flash')
    except:
        return None

model = get_working_model()

# --- 2. QUẢN LÝ SESSION ---
if 'score' not in st.session_state: st.session_state.score = 0
if 'streak' not in st.session_state: st.session_state.streak = 0
if 'current_data' not in st.session_state: st.session_state.current_data = None
if 'student_name' not in st.session_state: st.session_state.student_name = ""
if 'name_confirmed' not in st.session_state: st.session_state.name_confirmed = False
if 'answered_questions' not in st.session_state: st.session_state.answered_questions = {}

# --- 3. GIAO DIỆN CSS & SIDEBAR ---
st.set_page_config(page_title="SmartLens AI Pro", layout="wide")

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

    # ĐIỂM SỐ & CHUỖI LỬA TO ĐÙNG (120PX)
    st.markdown(f"""
        <div style="background: #161b22; padding: 25px; border-radius: 20px; border: 1px solid #30363d; text-align: center;">
            <p style="margin:0; font-size:18px; color:#8b949e; font-weight: bold;">ĐIỂM SỐ</p>
            <p style="font-size: 120px !important; font-weight: 900 !important; color: #f2cc60 !important; margin: 0; line-height: 1;">{st.session_state.score}</p>
            <div style="height:30px; border-bottom: 1px solid #30363d; margin-bottom: 20px;"></div>
            <p style="margin:0; font-size:18px; color:#8b949e; font-weight: bold;">CHUỖI LỬA</p>
            <p style="font-size: 120px !important; font-weight: 900 !important; color: #ff4b4b !important; margin: 0; line-height: 1;">{st.session_state.streak}🔥</p>
        </div>
    """, unsafe_allow_html=True)

    if st.button("➕ BÀI HỌC MỚI", use_container_width=True, type="primary"):
        st.session_state.current_data = None
        st.session_state.answered_questions = {}
        st.rerun()

    st.write("---")
    st.markdown("🎨 **TÙY CHỈNH**")
    bg_color = st.color_picker("Màu nền App:", "#0d1117")

st.markdown(f"""
<style>
    .stApp {{ background-color: {bg_color} !important; color: #c9d1d9; }}
    .main-title {{ font-size: 70px !important; color: #58a6ff !important; text-align: center; font-weight: 900; margin-bottom: 10px; }}
    .check-box {{ 
        background: rgba(22, 27, 34, 0.9); border-left: 10px solid #58a6ff; padding: 30px; border-radius: 20px; 
        border: 1px solid #30363d; line-height: 1.7; font-size: 18px;
    }}
    .guide-box {{ background: #1c2128; padding: 15px; border-radius: 10px; border: 1px dashed #58a6ff; margin-bottom: 20px; }}
</style>
""", unsafe_allow_html=True)

# --- 4. HÀM PHÂN TÍCH (CÓ XỬ LÝ LỖI QUOTA) ---
def run_analysis(text):
    if not text or model is None: return
    input_content = text[:2500].replace('"', "'")
    
    with st.spinner("🕵️ SmartLens AI đang làm việc..."):
        try:
            prompt = f"""
            Đóng vai chuyên gia tư duy phản biện. Phân tích nội dung sau theo cấu trúc chuyên nghiệp:
            1. 🛡️ XÁC THỰC LOGIC. 2. 🔍 PHẢN BIỆN LỖ HỔNG. 3. 💡 ỨNG DỤNG MỞ RỘNG.
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
        except Exception as e:
            if "429" in str(e):
                st.error("⚠️ Hệ thống AI đang bận (Lỗi Quota). Vui lòng đợi 10 giây rồi nhấn lại nhé!")
            else:
                st.error(f"Lỗi: {e}")

# --- 5. GIAO DIỆN CHÍNH ---
st.markdown("<div class='main-title'>🛡️ SMARTLENS AI</div>", unsafe_allow_html=True)
left, right = st.columns([3.8, 1.2])

with right:
    st.markdown("### 📝 GHI CHÚ")
    st.text_area("", height=750, key="notes_fixed", placeholder="Ghi chú...")

with left:
    tab1, tab2 = st.tabs(["📺 VIDEO YOUTUBE", "📝 VĂN BẢN"])
    
    with tab1:
        st.markdown('<div class="guide-box">Dán link YouTube có phụ đề vào đây.</div>', unsafe_allow_html=True)
        url = st.text_input("Nhập link video:", key="yt_url")
        if st.button("🚀 BẮT ĐẦU PHÂN TÍCH"):
            v_id = re.search(r"(?:v=|\/)([a-zA-Z0-9_-]{11})", url)
            if v_id:
                try:
                    ts = YouTubeTranscriptApi.get_transcript(v_id.group(1), languages=['vi', 'en'])
                    run_analysis(" ".join([i['text'] for i in ts]))
                except: st.error("Video không có phụ đề!")
    
    with tab2:
        txt = st.text_area("Dán văn bản cần thẩm định:", height=250, key="txt_input")
        if st.button("🔍 THẨM ĐỊNH TƯ DUY"): run_analysis(txt)

    if st.session_state.current_data:
        st.markdown("---")
        st.markdown(f'<div class="check-box">{st.session_state.current_data.get("verification", "")}</div>', unsafe_allow_html=True)
        
        st.markdown("### ✍️ THỬ THÁCH")
        for i, q in enumerate(st.session_state.current_data.get('questions', [])):
            st.write(f"**Câu {i+1}: {q['q']}**")
            is_locked = f"q_{i}" in st.session_state.answered_questions
            ans = st.radio(f"Đáp án {i+1}:", q['options'], key=f"radio_{i}", index=None, disabled=is_locked)
            
            if not is_locked:
                if st.button(f"Nộp đáp án {i+1}", key=f"btn_{i}"):
                    if ans:
                        is_correct = ans.startswith(q['correct'])
                        st.session_state.answered_questions[f"q_{i}"] = is_correct
                        if is_correct:
                            st.session_state.score += 10
                            st.session_state.streak += 1
                            st.balloons()
                        else: st.session_state.streak = 0
                        st.rerun()
            else:
                if st.session_state.answered_questions[f"q_{i}"]:
                    st.success(f"✅ Đúng! Đáp án: {q['correct']}")
                else: st.error(f"❌ Sai! Đáp án đúng: {q['correct']}")
