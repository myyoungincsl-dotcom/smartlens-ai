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

# --- 3. HÀM TRỢ GIÚP (ĐÃ FIX LỖI HIỂN THỊ CHỮ) ---
@st.dialog("🆘 CẨM NANG SỬ DỤNG SMARTLENS AI")
def show_detailed_help():
    st.subheader("📺 PHÂN TÍCH VIDEO YOUTUBE")
    st.write("1. Dán đường link video vào ô nhập liệu ở Tab YouTube.")
    st.write("2. Nhấn nút **BẮT ĐẦU TRÍCH XUẤT** để AI quét phụ đề.")
    st.divider()
    st.subheader("📥 QUY TRÌNH DOWNSUB (KHI LỖI PHỤ ĐỀ)")
    st.write("• Truy cập **DownSub.com** -> Dán link -> Tải file **[TXT]**.")
    st.write("• Copy văn bản -> Dán vào Tab **VĂN BẢN** -> Thẩm định.")
    st.divider()
    st.subheader("📝 GHI CHÚ & HÀNH TRÌNH HỌC")
    st.write("- Trả lời đúng nhận **10đ**. Chuỗi lửa sẽ tắt nếu trả lời sai!")

# --- 4. CSS TỔNG LỰC (FIX Ô NHẬP LIỆU TRẮNG) ---
st.set_page_config(page_title="SmartLens AI Pro", layout="wide")

st.markdown("""
<style>
    /* 1. Ép đen nền toàn App */
    [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stToolbar"], .stApp {
        background-color: #0d1117 !important;
        color: #c9d1d9 !important;
    }

    /* 2. Ép đen Sidebar */
    [data-testid="stSidebar"] {
        background-color: #010409 !important;
        border-right: 1px solid #30363d !important;
    }

    /* 3. FIX Ô NHẬP LIỆU: Tên học sinh, Link Youtube, Văn bản */
    input[type="text"], textarea, [data-baseweb="input"] {
        background-color: #161b22 !important;
        color: white !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
    }
    
    /* Đảm bảo chữ trong ô nhập liệu không bị đen trên nền đen */
    input, textarea {
        color: white !important;
        -webkit-text-fill-color: white !important;
    }

    /* 4. Lập trình nút bấm */
    div.stButton > button {
        background-color: #21262d !important;
        color: #c9d1d9 !important;
        border: 1px solid #30363d !important;
        border-radius: 6px;
    }
    div.stButton > button[kind="primary"] {
        background-color: #238636 !important;
        color: white !important;
    }

    /* 5. Khung Điểm & Lửa (Bé lại) */
    .metric-card {
        background-color: #161b22 !important;
        padding: 15px; border-radius: 12px;
        border: 1px solid #30363d !important;
        text-align: center; margin-bottom: 10px;
    }
    .metric-value { font-size: 35px !important; font-weight: 900; line-height: 1; }

    .main-title { font-size: 50px !important; color: #58a6ff !important; text-align: center; font-weight: 900; }
    
    /* Tabs */
    .stTabs [data-baseweb="tab"] { color: #8b949e !important; }
    .stTabs [aria-selected="true"] { color: #58a6ff !important; }
</style>
""", unsafe_allow_html=True)

# --- 5. SIDEBAR ---
with st.sidebar:
    if st.button("❓ TRỢ GIÚP (HELP)", use_container_width=True):
        show_detailed_help()
        
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

    st.markdown(f"""
        <div class="metric-card">
            <p style="margin:0; font-size:12px; color:#8b949e;">ĐIỂM SỐ</p>
            <p class="metric-value" style="color: #f2cc60;">{st.session_state.score}</p>
            <hr style="border: 0.5px solid #30363d; margin: 10px 0;">
            <p style="margin:0; font-size:12px; color:#8b949e;">CHUỖI LỬA</p>
            <p class="metric-value" style="color: #ff4b4b;">{st.session_state.streak}🔥</p>
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
    with st.spinner("🕵️ AI đang thẩm định..."):
        try:
            prompt = f"Phân tích phản biện. Trả về JSON chuẩn: {{'verification': 'html_content', 'questions': [{{'q': '...', 'options': [], 'correct': ''}}]}} Nội dung: {input_text}"
            response = model.generate_content(prompt)
            match = re.search(r"\{.*\}", response.text, re.DOTALL)
            if match:
                st.session_state.current_data = json.loads(match.group().replace('\n', ' '))
                st.session_state.answered_questions = {}
                st.rerun()
        except Exception as e: st.error(f"Lỗi AI: {e}")

# --- 7. GIAO DIỆN CHÍNH ---
st.markdown("<div class='main-title'>🛡️ SMARTLENS AI</div>", unsafe_allow_html=True)
left, right = st.columns([3.8, 1.2])

with right:
    st.markdown("### 📝 GHI CHÚ", unsafe_allow_html=True)
    st.text_area("ghi_chu", key="notes_fixed", label_visibility="collapsed", placeholder="Tự co giãn khi viết...")

with left:
    tab1, tab2 = st.tabs(["📺 YOUTUBE", "📝 VĂN BẢN"])
    
    with tab1:
        url = st.text_input("Dán link video YouTube:")
        if st.button("🚀 BẮT ĐẦU TRÍCH XUẤT", use_container_width=True):
            v_id = re.search(r"(?:v=|\/)([a-zA-Z0-9_-]{11})", url)
            if v_id:
                try:
                    ts = YouTubeTranscriptApi.get_transcript(v_id.group(1), languages=['vi', 'en'])
                    run_analysis(" ".join([i['text'] for i in ts]))
                except: st.error("❌ Video không có phụ đề!")

    with tab2:
        txt = st.text_area("Dán nội dung văn bản:", height=250)
        if st.button("🔍 THẨM ĐỊNH TƯ DUY", use_container_width=True):
            run_analysis(txt)

    if st.session_state.current_data:
        st.markdown("---")
        st.markdown(f'<div style="background:#161b22; border-left:10px solid #58a6ff; padding:25px; border-radius:15px; border:1px solid #30363d;">{st.session_state.current_data.get("verification", "")}</div>', unsafe_allow_html=True)
        
        st.markdown("### ✍️ THỬ THÁCH")
        for i, q in enumerate(st.session_state.current_data.get('questions', [])):
            st.write(f"**Câu {i+1}: {q['q']}**")
            ans = st.radio(f"Chọn đáp án:", q['options'], key=f"r_{i}", index=None, disabled=f"q_{i}" in st.session_state.answered_questions)
            
            if f"q_{i}" not in st.session_state.answered_questions:
                if st.button(f"Nộp đáp án {i+1}", key=f"b_{i}"):
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
                if st.session_state.answered_questions[f"q_{i}"]: st.success(f"✅ Đúng! ({q['correct']})")
                else: st.error(f"❌ Sai! Đáp án: {q['correct']}")
