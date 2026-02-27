import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import re
import json

# --- 1. CẤU HÌNH AI (GIỮ NGUYÊN TUYỆT ĐỐI) ---
API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    st.error("❌ THIẾU API KEY!")
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

# --- 3. HÀM TRỢ GIÚP (FIX LỖI HIỂN THỊ) ---
@st.dialog("🆘 HƯỚNG DẪN SỬ DỤNG CHI TIẾT")
def show_help():
    st.markdown("""
    <div style="color: #c9d1d9;">
        <h3 style="color: #58a6ff;">📺 PHÂN TÍCH YOUTUBE</h3>
        <p>1. Dán link -> Nhấn <b>TRÍCH XUẤT PHỤ ĐỀ</b>.<br>
        2. Sau khi xong, nhấn <b>THẨM ĐỊNH VIDEO</b> để AI làm việc.</p>
        <h3 style="color: #58a6ff;">📥 QUY TRÌNH DOWNSUB (KHI LỖI)</h3>
        <p>Truy cập <b>DownSub.com</b> -> Tải file <b>[TXT]</b> -> Copy chữ dán vào tab <b>VĂN BẢN</b>.</p>
        <h3 style="color: #58a6ff;">📝 GHI CHÚ & ĐIỂM SỐ</h3>
        <p>- Ô ghi chú bên phải tự dài ra theo nội dung viết.<br>
        - Trả lời đúng nhận 10đ. Sai sẽ bị mất chuỗi lửa!</p>
    </div>
    """, unsafe_allow_html=True)

# --- 4. CSS TỔNG LỰC (KHÓA ĐEN TOÀN DIỆN & Ô GHI CHÚ CO GIÃN) ---
st.set_page_config(page_title="SmartLens AI Pro", layout="wide")

st.markdown("""
<style>
    /* Ép đen toàn bộ nền, header và thanh công cụ */
    [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stToolbar"], .stApp {
        background-color: #0d1117 !important;
        color: #c9d1d9 !important;
    }
    [data-testid="stSidebar"] { 
        background-color: #010409 !important; 
        border-right: 1px solid #30363d !important; 
    }

    /* Lập trình lại nút bấm */
    div.stButton > button {
        background-color: #21262d !important; 
        color: #c9d1d9 !important;
        border: 1px solid #30363d !important; 
        width: 100%; 
        border-radius: 6px;
    }
    div.stButton > button:hover { 
        background-color: #30363d !important; 
        border-color: #8b949e !important; 
    }
    div.stButton > button[kind="primary"] { 
        background-color: #238636 !important; 
        color: white !important; 
    }

    /* Khung điểm số bé lại tinh tế */
    .metric-card {
        background-color: #161b22 !important; 
        padding: 12px; 
        border-radius: 10px;
        border: 1px solid #30363d !important; 
        text-align: center; 
        margin-bottom: 8px;
    }
    
    /* Ô ghi chú tự co giãn */
    .stTextArea textarea {
        height: auto !important;
        min-height: 100px !important;
        background-color: #0d1117 !important;
        color: white !important;
        border: 1px solid #30363d !important;
    }

    .check-box {
        background-color: #161b22 !important; 
        border-left: 10px solid #58a6ff !important;
        padding: 20px; border-radius: 12px; 
        border: 1px solid #30363d !important;
    }
    
    .main-title { font-size: 50px !important; color: #58a6ff !important; text-align: center; font-weight: 900; }
    h1, h2, h3, p, label, .stMarkdown { color: #c9d1d9 !important; }
</style>
""", unsafe_allow_html=True)

# --- 5. SIDEBAR ---
with st.sidebar:
    if st.button("❓ TRỢ GIÚP (HELP)"):
        show_help()
        
    st.markdown("<h2 style='text-align: center;'>🛡️ PROFILE</h2>", unsafe_allow_html=True)
    
    if not st.session_state.name_confirmed:
        name_input = st.text_input("Tên học sinh:")
        if st.button("XÁC NHẬN"):
            if name_input:
                st.session_state.student_name = name_input
                st.session_state.name_confirmed = True
                st.rerun()
    else:
        st.markdown(f"<p style='text-align:center; color:#58a6ff;'>🌟 <b>{st.session_state.student_name}</b></p>", unsafe_allow_html=True)

    # Khung điểm & chuỗi bé lại
    st.markdown(f"""
        <div class="metric-card">
            <p style="margin:0; font-size:11px; color:#8b949e;">ĐIỂM SỐ</p>
            <p style="font-size: 35px; font-weight: 900; color: #f2cc60; margin: 0;">{st.session_state.score}</p>
            <hr style="border: 0.5px solid #30363d; margin: 8px 0;">
            <p style="margin:0; font-size:11px; color:#8b949e;">CHUỖI LỬA</p>
            <p style="font-size: 35px; font-weight: 900; color: #ff4b4b; margin: 0;">{st.session_state.streak}🔥</p>
        </div>
    """, unsafe_allow_html=True)

    if st.button("➕ BÀI HỌC MỚI", type="primary"):
        st.session_state.current_data = None
        st.session_state.answered_questions = {}
        st.rerun()

# --- 6. HÀM PHÂN TÍCH ---
def run_analysis(text):
    if not text or model is None: return
    input_text = text[:2500].replace('"', "'")
    with st.spinner("🕵️ AI đang làm việc..."):
        try:
            prompt = f"Phân tích phản biện. Trả về JSON chuẩn: {{'verification': 'html', 'questions': [{{'q':'','options':[],'correct':''}}]}} Nội dung: {input_text}"
            response = model.generate_content(prompt)
            match = re.search(r"\{.*\}", response.text, re.DOTALL)
            if match:
                st.session_state.current_data = json.loads(match.group().replace('\n', ' '))
                st.session_state.answered_questions = {}
                st.rerun()
        except Exception as e: st.error(f"Lỗi: {e}")

# --- 7. GIAO DIỆN CHÍNH ---
st.markdown("<div class='main-title'>🛡️ SMARTLENS AI</div>", unsafe_allow_html=True)
left, right = st.columns([3.8, 1.2])

with right:
    st.markdown("### 📝 GHI CHÚ <br><small style='color:#8b949e;'>(ghi chép thông tin)</small>", unsafe_allow_html=True)
    # Ô ghi chú co giãn linh hoạt
    st.text_area("notes_area", key="notes_fixed", label_visibility="collapsed", placeholder="Nhập tại đây, ô sẽ tự mở rộng...")

with left:
    tab1, tab2 = st.tabs(["📺 YOUTUBE", "📝 VĂN BẢN"])
    
    with tab1:
        url = st.text_input("Link video YouTube:")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🚀 TRÍCH XUẤT PHỤ ĐỀ"):
                v_id = re.search(r"(?:v=|\/)([a-zA-Z0-9_-]{11})", url)
                if v_id:
                    try:
                        ts = YouTubeTranscriptApi.get_transcript(v_id.group(1), languages=['vi', 'en'])
                        st.session_state.temp_text = " ".join([i['text'] for i in ts])
                        st.success("Xong! Hãy nhấn nút Thẩm định kế bên.")
                    except: st.error("Video không có phụ đề!")
        with c2:
            if st.button("🔍 THẨM ĐỊNH VIDEO"):
                if 'temp_text' in st.session_state:
                    run_analysis(st.session_state.temp_text)
                else: st.warning("Cần trích xuất phụ đề trước!")

    with tab2:
        txt = st.text_area("Dán nội dung:", height=200)
        if st.button("🔍 THẨM ĐỊNH VĂN BẢN"):
            run_analysis(txt)

    if st.session_state.current_data:
        st.markdown("---")
        st.markdown(f'<div class="check-box">{st.session_state.current_data.get("verification", "")}</div>', unsafe_allow_html=True)
        
        st.markdown("### ✍️ THỬ THÁCH")
        for i, q in enumerate(st.session_state.current_data.get('questions', [])):
            st.write(f"**Câu {i+1}: {q['q']}**")
            q_id = f"q_{i}"
            is_locked = q_id in st.session_state.answered_questions
            ans = st.radio(f"Chọn đáp án:", q['options'], key=f"r_{i}", index=None, disabled=is_locked)
            
            if not is_locked and st.button(f"Nộp đáp án {i+1}", key=f"b_{i}"):
                if ans:
                    is_correct = ans.startswith(q['correct'])
                    st.session_state.answered_questions[q_id] = is_correct
                    if is_correct:
                        st.session_state.score += 10
                        st.session_state.streak += 1
                        st.balloons()
                    else: st.session_state.streak = 0
                    st.rerun()
            elif is_locked:
                if st.session_state.answered_questions[q_id]: st.success(f"✅ Đúng! ({q['correct']})")
                else: st.error(f"❌ Sai! Đáp án: {q['correct']}")
