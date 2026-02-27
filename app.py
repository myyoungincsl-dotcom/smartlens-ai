import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import re
import json

# --- 1. CẤU HÌNH AI (GIỮ NGUYÊN TUYỆT ĐỐI LOGIC CỦA BẠN) ---
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

# --- 3. HÀM TRỢ GIÚP CHI TIẾT ---
@st.dialog("🆘 CẨM NANG SỬ DỤNG SMARTLENS AI")
def show_detailed_help():
    st.markdown("""
    <div style="color: #c9d1d9 !important; font-family: sans-serif;">
        <h3 style="color: #58a6ff;">📺 PHÂN TÍCH VIDEO YOUTUBE</h3>
        <p>1. Dán đường link video vào ô nhập liệu ở Tab YouTube.<br>
        2. Nhấn nút <b>BẮT ĐẦU TRÍCH XUẤT</b> để AI quét phụ đề.<br>
        3. Nếu hệ thống báo lỗi <i>"Video không có phụ đề"</i>, hãy thực hiện quy trình <b>DownSub</b> bên dưới.</p>
        
        <h3 style="color: #58a6ff;">📥 QUY TRÌNH DOWNSUB (KHI LỖI PHỤ ĐỀ)</h3>
        <p><b>Bước 1:</b> Truy cập website <a href="https://downsub.com/" target="_blank" style="color: #58a6ff;">DownSub.com</a>.<br>
        <b>Bước 2:</b> Dán link YouTube của bạn vào ô tìm kiếm và nhấn <b>Download</b>.<br>
        <b>Bước 3:</b> Kéo xuống danh sách định dạng, tìm dòng <b>[TXT]</b> (thường ở đầu danh sách ngôn ngữ).<br>
        <b>Bước 4:</b> Nhấn Download file TXT đó về máy.<br>
        <b>Bước 5:</b> Mở file TXT, <b>Copy toàn bộ văn bản</b> và quay lại ứng dụng này.<br>
        <b>Bước 6:</b> Chọn Tab <b>📝 VĂN BẢN</b>, dán nội dung vào và nhấn <b>THẨM ĐỊNH TƯ DUY</b>.</p>
        
        <h3 style="color: #58a6ff;">📝 GHI CHÚ & HÀNH TRÌNH HỌC</h3>
        <p>- <b>Khung Ghi Chú:</b> Luôn nằm ở bên phải màn hình để bạn tóm tắt kiến thức ngay lập tức.<br>
        - <b>Thử thách:</b> Trả lời 3 câu hỏi trắc nghiệm để kiểm tra mức độ hiểu bài.<br>
        - <b>Điểm & Lửa:</b> Trả lời đúng nhận 10đ. Chuỗi lửa (Streak) thể hiện sự kiên trì của bạn, đừng để nó tắt nhé!</p>
    </div>
    """, unsafe_allow_html=True)

# --- 4. CSS TỔNG LỰC (ÉP MÀU ĐEN TOÀN DIỆN) ---
st.set_page_config(page_title="SmartLens AI Pro", layout="wide")

st.markdown("""
<style>
    /* 1. Ép đen toàn bộ nền App, Header và Toolbar */
    [data-testid="stAppViewContainer"], 
    [data-testid="stHeader"], 
    [data-testid="stToolbar"],
    .stApp {
        background-color: #0d1117 !important;
        color: #c9d1d9 !important;
    }

    /* 2. Ép đen Sidebar */
    [data-testid="stSidebar"], 
    [data-testid="stSidebarNav"] {
        background-color: #010409 !important;
        border-right: 1px solid #30363d !important;
    }

    /* 3. Lập trình lại TẤT CẢ các nút bấm */
    div.stButton > button {
        background-color: #21262d !important;
        color: #c9d1d9 !important;
        border: 1px solid #30363d !important;
        width: 100%;
        border-radius: 6px;
        font-weight: 600;
    }
    div.stButton > button:hover {
        background-color: #30363d !important;
        border-color: #8b949e !important;
        color: white !important;
    }
    div.stButton > button[kind="primary"] {
        background-color: #238636 !important;
        color: white !important;
        border: none !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #2ea043 !important;
    }

    /* 4. Fix màu chữ cho các thành phần mặc định */
    h1, h2, h3, h4, p, li, label, .stMarkdown, .stSubheader {
        color: #c9d1d9 !important;
    }
    .main-title {
        font-size: 60px !important;
        color: #58a6ff !important;
        text-align: center;
        font-weight: 900;
        margin-bottom: 20px;
    }

    /* 5. Ép màu các khung Custom */
    .metric-card {
        background-color: #161b22 !important;
        padding: 20px; border-radius: 15px;
        border: 1px solid #30363d !important;
        text-align: center;
        margin-bottom: 15px;
    }
    .check-box {
        background-color: #161b22 !important;
        border-left: 10px solid #58a6ff !important;
        padding: 25px; border-radius: 15px;
        border: 1px solid #30363d !important;
        color: #c9d1d9 !important;
    }

    /* 6. Ép màu cho Tabs và Inputs */
    .stTabs [data-baseweb="tab-list"] { background-color: transparent !important; }
    .stTabs [data-baseweb="tab"] { color: #8b949e !important; }
    .stTabs [aria-selected="true"] { color: #58a6ff !important; border-bottom-color: #58a6ff !important; }
    
    input, textarea {
        background-color: #0d1117 !important;
        color: white !important;
        border: 1px solid #30363d !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 5. SIDEBAR (PROFILE, ĐIỂM, HELP) ---
with st.sidebar:
    # Nút Hướng dẫn sử dụng
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
        st.markdown(f"<p style='text-align:center; color:#58a6ff;'>🌟 Chào <b>{st.session_state.student_name}</b>!</p>", unsafe_allow_html=True)

    # Khung Điểm & Lửa
    st.markdown(f"""
        <div class="metric-card">
            <p style="margin:0; font-size:14px; color:#8b949e;">ĐIỂM SỐ</p>
            <p style="font-size: 80px; font-weight: 900; color: #f2cc60; margin: 0; line-height: 1;">{st.session_state.score}</p>
            <hr style="border: 0.5px solid #30363d; margin: 20px 0;">
            <p style="margin:0; font-size:14px; color:#8b949e;">CHUỖI LỬA</p>
            <p style="font-size: 80px; font-weight: 900; color: #ff4b4b; margin: 0; line-height: 1;">{st.session_state.streak}🔥</p>
        </div>
    """, unsafe_allow_html=True)

    st.write("---")
    if st.button("➕ BÀI HỌC MỚI", use_container_width=True, type="primary"):
        st.session_state.current_data = None
        st.session_state.answered_questions = {}
        st.rerun()

# --- 6. HÀM PHÂN TÍCH (GIỮ NGUYÊN) ---
def run_analysis(text):
    if not text or model is None: return
    input_text = text[:2500].replace('"', "'")
    with st.spinner("🕵️ AI đang thẩm định nội dung..."):
        try:
            prompt = f"""Phân tích phản biện: 1.Xác thực 2.Phản biện 3.Ứng dụng. 
            Trả về JSON chuẩn: {{"verification": "html_content", "questions": [{{"q": "câu hỏi", "options": ["A..","B..","C..","D.."], "correct": "A"}}]}}
            Nội dung: {input_text}"""
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
    st.markdown("### 📝 GHI CHÚ <br><small style='color:#8b949e;'>(để ghi chép thông tin)</small>", unsafe_allow_html=True)
    st.text_area("ghi_chu", height=750, key="notes_fixed", label_visibility="collapsed", placeholder="Tóm tắt ý chính tại đây...")

with left:
    tab1, tab2 = st.tabs(["📺 YOUTUBE", "📝 VĂN BẢN"])
    
    with tab1:
        url = st.text_input("Dán link video YouTube tại đây:")
        if st.button("🚀 BẮT ĐẦU TRÍCH XUẤT", use_container_width=True):
            v_id = re.search(r"(?:v=|\/)([a-zA-Z0-9_-]{11})", url)
            if v_id:
                try:
                    ts = YouTubeTranscriptApi.get_transcript(v_id.group(1), languages=['vi', 'en'])
                    run_analysis(" ".join([i['text'] for i in ts]))
                except: st.error("❌ Video không có phụ đề! Hãy dùng DownSub.")
        
        st.markdown("""
        <div style="background:#010409; padding:15px; border-radius:10px; border:1px dashed #58a6ff; margin-top:15px; color:#c9d1d9;">
            <b>💡 Hướng dẫn nhanh:</b> Nếu lỗi, copy link qua <b>DownSub.com</b> tải file TXT rồi dán vào tab <b>VĂN BẢN</b>.
        </div>
        """, unsafe_allow_html=True)

    with tab2:
        txt = st.text_area("Dán nội dung văn bản (hoặc nội dung từ DownSub):", height=250)
        if st.button("🔍 THẨM ĐỊNH TƯ DUY", use_container_width=True):
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
                if st.session_state.answered_questions[q_id]: st.success(f"✅ Đúng! ({q['correct']})")
                else: st.error(f"❌ Sai! Đáp án đúng: {q['correct']}")
