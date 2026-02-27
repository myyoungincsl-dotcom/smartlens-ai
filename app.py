import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import re
import json

# --- 1. CẤU HÌNH AI ---
API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    st.error("❌ THIẾU API KEY TRONG SECRETS!")
    st.stop()

@st.cache_resource
def get_working_model():
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target = next((m for m in available_models if '1.5-flash' in m), available_models[0])
        return genai.GenerativeModel(target)
    except: return None

model = get_working_model()

# --- 2. QUẢN LÝ SESSION ---
if 'score' not in st.session_state: st.session_state.score = 0
if 'streak' not in st.session_state: st.session_state.streak = 0
if 'current_data' not in st.session_state: st.session_state.current_data = None
if 'student_name' not in st.session_state: st.session_state.student_name = ""
if 'name_confirmed' not in st.session_state: st.session_state.name_confirmed = False
if 'answered_questions' not in st.session_state: st.session_state.answered_questions = {}

# --- 3. GIAO DIỆN SIDEBAR ---
st.set_page_config(page_title="SmartLens AI Pro", layout="wide")

with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #58a6ff !important;'>🛡️ PROFILE</h2>", unsafe_allow_html=True)
    
    if not st.session_state.name_confirmed:
        name_input = st.text_input("Tên học sinh:")
        if st.button("XÁC NHẬN", use_container_width=True):
            if name_input:
                st.session_state.student_name = name_input
                st.session_state.name_confirmed = True
                st.rerun()
    else:
        st.markdown(f"<h3 style='text-align:center; color:#58a6ff !important;'>🌟 Chào {st.session_state.student_name}!</h3>", unsafe_allow_html=True)
        if st.button("Đổi tên"):
            st.session_state.name_confirmed = False
            st.rerun()

    # KHỐI ĐIỂM SỐ (FIX LỖI LIGHT MODE)
    st.markdown(f"""
        <div style="background-color: #161b22 !important; padding: 25px; border-radius: 20px; border: 1px solid #30363d !important; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.5);">
            <p style="margin:0; font-size:16px; color:#8b949e !important; font-weight: bold;">ĐIỂM SỐ</p>
            <p style="font-size: 120px !important; font-weight: 900 !important; color: #f2cc60 !important; margin: 0; line-height: 1;">{st.session_state.score}</p>
            <div style="height:30px; border-bottom: 1px solid #30363d !important; margin-bottom: 20px;"></div>
            <p style="margin:0; font-size:16px; color:#8b949e !important; font-weight: bold;">CHUỖI LỬA</p>
            <p style="font-size: 120px !important; font-weight: 900 !important; color: #ff4b4b !important; margin: 0; line-height: 1;">{st.session_state.streak}🔥</p>
        </div>
    """, unsafe_allow_html=True)

    st.write("---")
    
    # NÚT HELP MỚI
    if st.button("❓ TRỢ GIÚP (HELP)", use_container_width=True):
        st.dialog("HƯỚNG DẪN SỬ DỤNG SMARTLENS AI")

    @st.dialog("HƯỚNG DẪN SỬ DỤNG SMARTLENS AI")
    def show_help():
        st.markdown("""
        ### 📺 1. Cách phân tích Video YouTube
        * Dán link YouTube vào ô nhập. Nếu video có phụ đề, nhấn **Bắt đầu trích xuất**.
        * **Nếu báo lỗi phụ đề:** 1. Truy cập [DownSub.com](https://downsub.com/).
            2. Dán link video vào DownSub, tải file **TXT**.
            3. Copy nội dung TXT đó, chuyển sang tab **VĂN BẢN** trong SmartLens và dán vào.

        ### 📝 2. Cách sử dụng Ghi chú
        * Ô bên phải dùng để bạn ghi lại những ý tưởng quan trọng khi đang xem báo cáo của AI. 
        * Ghi chú này sẽ **không bị mất** khi bạn trả lời câu hỏi.

        ### ✍️ 3. Làm thử thách trắc nghiệm
        * Mỗi bài phân tích sẽ có 3 câu hỏi. Trả lời đúng bạn được **+10 điểm** và tăng **Chuỗi lửa**. 
        * Trả lời sai, Chuỗi lửa sẽ về 0!

        ### 🎨 4. Chỉnh màu
        * Dùng ô chọn màu ở dưới cùng Sidebar để đổi màu nền theo sở thích của bạn.
        """)

    if st.button("➕ BÀI HỌC MỚI", use_container_width=True, type="primary"):
        st.session_state.current_data = None
        st.session_state.answered_questions = {}
        st.rerun()

    bg_color = st.color_picker("Chọn màu nền App:", "#0d1117")

# --- 4. ÁP DỤNG CSS (ÉP DARK MODE) ---
st.markdown(f"""
<style>
    /* Ép nền tối cho toàn App bất kể Windows Mode */
    .stApp {{ background-color: {bg_color} !important; color: #c9d1d9 !important; }}
    
    /* Ép màu cho các text mặc định của Streamlit */
    .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{ color: #c9d1d9 !important; }}
    
    .main-title {{ font-size: 65px !important; color: #58a6ff !important; text-align: center; font-weight: 900; }}
    
    /* Ép khung báo cáo luôn tối */
    .check-box {{ 
        background-color: #1c2128 !important; 
        border-left: 10px solid #58a6ff !important; 
        padding: 30px; border-radius: 20px; font-size: 19px; 
        border: 1px solid #30363d !important;
        color: #c9d1d9 !important;
    }}
    
    .guide-box {{ 
        background-color: #161b22 !important; padding: 20px; 
        border-radius: 12px; border: 1px dashed #58a6ff !important; 
        margin-top: 15px; color: #c9d1d9 !important;
    }}
</style>
""", unsafe_allow_html=True)

# --- 5. HÀM PHÂN TÍCH ---
def run_analysis(text):
    if not text or model is None: return
    input_text = text[:2500].replace('"', "'")
    with st.spinner("🕵️ AI đang thẩm định nội dung..."):
        try:
            prompt = f"""Phân tích phản biện chuyên sâu. Trả về JSON: {{"verification": "html_content", "questions": [{{'q': '...', 'options': ['A..','B..','C..','D..'], 'correct': 'A'}}]}}. Nội dung: {input_text}"""
            response = model.generate_content(prompt)
            match = re.search(r"\{.*\}", response.text, re.DOTALL)
            if match:
                st.session_state.current_data = json.loads(match.group().replace('\n', ' '))
                st.session_state.answered_questions = {}
                st.rerun()
        except Exception as e: st.error(f"Lỗi AI: {e}")

# --- 6. GIAO DIỆN CHÍNH ---
st.markdown("<div class='main-title'>🛡️ SMARTLENS AI</div>", unsafe_allow_html=True)
left, right = st.columns([3.8, 1.2])

with right:
    st.markdown("### 📝 GHI CHÚ")
    st.text_area("", height=750, key="notes_fixed")

with left:
    tab1, tab2 = st.tabs(["📺 PHÂN TÍCH YOUTUBE", "📝 VĂN BẢN"])
    
    with tab1:
        url = st.text_input("Dán link YouTube tại đây:")
        if st.button("🚀 BẮT ĐẦU TRÍCH XUẤT", use_container_width=True):
            v_id = re.search(r"(?:v=|\/)([a-zA-Z0-9_-]{11})", url)
            if v_id:
                try:
                    ts = YouTubeTranscriptApi.get_transcript(v_id.group(1), languages=['vi', 'en'])
                    run_analysis(" ".join([i['text'] for i in ts]))
                except: st.error("❌ Video không có phụ đề!")
    
    with tab2:
        txt = st.text_area("Dán nội dung văn bản:", height=250)
        if st.button("🔍 THẨM ĐỊNH TƯ DUY", use_container_width=True): run_analysis(txt)

    if st.session_state.current_data:
        st.markdown("---")
        st.markdown(f'<div class="check-box">{st.session_state.current_data.get("verification", "")}</div>', unsafe_allow_html=True)
        
        st.markdown("### ✍️ THỬ THÁCH")
        for i, q in enumerate(st.session_state.current_data.get('questions', [])):
            st.write(f"**Câu {i+1}: {q['q']}**")
            q_id = f"q_{i}"
            is_locked = q_id in st.session_state.answered_questions
            ans = st.radio(f"Chọn đáp án câu {i+1}:", q['options'], key=f"r_{i}", index=None, disabled=is_locked)
            
            if not is_locked:
                if st.button(f"Nộp đáp án {i+1}", key=f"b_{i}"):
                    if ans:
                        is_correct = ans.startswith(q['correct'])
                        st.session_state.answered_questions[q_id] = is_correct
                        if is_correct:
                            st.session_state.score += 10
                            st.session_state.streak += 1
                            st.balloons()
                        else: st.session_state.streak = 0
                        st.rerun()
            else:
                if st.session_state.answered_questions[q_id]:
                    st.success(f"✅ Chính xác! Đáp án là {q['correct']}")
                else:
                    st.error(f"❌ Sai rồi! Đáp án đúng: {q['correct']}")
