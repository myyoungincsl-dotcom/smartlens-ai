import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import re
import json

# --- 1. CẤU HÌNH AI (SỬA LỖI 404 & QUOTA) ---
API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    st.error("❌ THIẾU API KEY TRONG SECRETS!")
    st.stop()

@st.cache_resource
def get_working_model():
    try:
        # Lấy danh sách các model khả dụng để tránh gọi sai tên dẫn đến lỗi 404
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Chiến thuật: Tìm bản Flash trước để có Quota cao nhất, nếu không có thì lấy model đầu tiên
        selected_model_name = None
        for m in available_models:
            if '1.5-flash' in m:
                selected_model_name = m
                break
        
        if not selected_model_name:
            selected_model_name = available_models[0]
            
        return genai.GenerativeModel(selected_model_name)
    except Exception as e:
        st.error(f"Lỗi khởi tạo AI: {e}")
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

    # HIỂN THỊ ĐIỂM & CHUỖI SIÊU TO (100PX)
    st.markdown(f"""
        <div style="background: #161b22; padding: 25px; border-radius: 20px; border: 1px solid #30363d; text-align: center;">
            <p style="margin:0; font-size:14px; color:#8b949e; font-weight: bold;">ĐIỂM SỐ</p>
            <p style="font-size: 100px !important; font-weight: 900 !important; color: #f2cc60 !important; margin: 0; line-height: 1;">{st.session_state.score}</p>
            <div style="height:25px"></div>
            <p style="margin:0; font-size:14px; color:#8b949e; font-weight: bold;">CHUỖI LỬA</p>
            <p style="font-size: 100px !important; font-weight: 900 !important; color: #ff4b4b !important; margin: 0; line-height: 1;">{st.session_state.streak}🔥</p>
        </div>
    """, unsafe_allow_html=True)

    if st.button("➕ BÀI HỌC MỚI", use_container_width=True, type="primary"):
        st.session_state.current_data = None
        st.session_state.answered_questions = {}
        st.rerun()

    st.write("---")
    bg_color = st.color_picker("Màu nền App:", "#0d1117")

# Áp dụng CSS
st.markdown(f"""
<style>
    .stApp {{ background-color: {bg_color} !important; color: #c9d1d9; }}
    .main-title {{ font-size: 70px !important; color: #58a6ff !important; text-align: center; font-weight: 900; margin-bottom: 10px; }}
    .check-box {{ 
        background: rgba(22, 27, 34, 0.8); border-left: 8px solid #58a6ff; padding: 25px; border-radius: 15px; 
        border: 1px solid #30363d; line-height: 1.7; font-size: 18px;
    }}
    .guide-box {{ background: #1c2128; padding: 15px; border-radius: 10px; border: 1px dashed #58a6ff; margin-bottom: 20px; }}
</style>
""", unsafe_allow_html=True)

# --- 4. HÀM PHÂN TÍCH ---
def run_analysis(text):
    if not text or model is None: return
    input_content = text[:2500].replace('"', "'")
    with st.spinner("🕵️ SmartLens đang thẩm định tư duy..."):
        try:
            prompt = f"""
            Phân tích chuyên sâu tư duy phản biện (Xác thực, Phản biện, Ứng dụng).
            Dùng <b> và <br>. Trả về JSON chuẩn:
            {{
                "verification": "nội dung phân tích",
                "questions": [
                    {{"q": "câu hỏi", "options": ["A. x", "B. y", "C. z", "D. t"], "correct": "A"}}
                ]
            }}
            NỘI DUNG: {input_content}
            """
            response = model.generate_content(prompt)
            match = re.search(r"\{.*\}", response.text, re.DOTALL)
            if match:
                st.session_state.current_data = json.loads(match.group().replace('\n', ' '))
                st.session_state.answered_questions = {}
                st.rerun()
        except Exception as e:
            if "429" in str(e):
                st.error("⚠️ Hết hạn mức (Quota). Hãy đợi 1 phút rồi thử lại nhé!")
            else:
                st.error(f"Lỗi: {e}")

# --- 5. GIAO DIỆN CHÍNH ---
st.markdown("<div class='main-title'>🛡️ SMARTLENS AI</div>", unsafe_allow_html=True)
left, right = st.columns([3.8, 1.2])

with right:
    st.markdown("### 📝 GHI CHÚ")
    st.text_area("", height=750, key="notes_v_final", placeholder="Ghi chú...")

with left:
    tab1, tab2 = st.tabs(["📺 YOUTUBE", "📝 VĂN BẢN"])
    with tab1:
        url = st.text_input("Nhập link video:")
        if st.button("🚀 PHÂN TÍCH"):
            v_id = re.search(r"(?:v=|\/)([a-zA-Z0-9_-]{11})", url)
            if v_id:
                try:
                    ts = YouTubeTranscriptApi.get_transcript(v_id.group(1), languages=['vi', 'en'])
                    run_analysis(" ".join([i['text'] for i in ts]))
                except: st.error("Không lấy được phụ đề!")
    
    with tab2:
        txt = st.text_area("Dán nội dung:", height=250)
        if st.button("🔍 THẨM ĐỊNH"): run_analysis(txt)

    if st.session_state.current_data:
        st.markdown(f'<div class="check-box">{st.session_state.current_data.get("verification", "")}</div>', unsafe_allow_html=True)
        for i, q in enumerate(st.session_state.current_data.get('questions', [])):
            st.write(f"**Câu {i+1}: {q['q']}**")
            is_locked = f"q_{i}" in st.session_state.answered_questions
            ans = st.radio(f"Đáp án {i+1}:", q['options'], key=f"radio_{i}", index=None, disabled=is_locked)
            if not is_locked and st.button(f"Nộp {i+1}", key=f"btn_{i}"):
                if ans:
                    correct = ans.startswith(q['correct'])
                    st.session_state.answered_questions[f"q_{i}"] = correct
                    if correct:
                        st.session_state.score += 10
                        st.session_state.streak += 1
                        st.balloons()
                    else: st.session_state.streak = 0
                    st.rerun()
            elif is_locked:
                if st.session_state.answered_questions[f"q_{i}"]: st.success("✅ Đúng!")
                else: st.error(f"❌ Sai! Đáp án là {q['correct']}")
