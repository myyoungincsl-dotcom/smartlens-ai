import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import re
import json

# --- 1. CẤU HÌNH AI (KHẮC PHỤC 404 & 429) ---
API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    st.error("❌ THIẾU API KEY TRONG SECRETS!")
    st.stop()

@st.cache_resource
def get_working_model():
    try:
        # Tự động lấy danh sách model để tránh lỗi 404
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Ưu tiên bản 1.5-flash để tránh lỗi 429
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

# --- 3. ĐỊNH NGHĨA HÀM TRỢ GIÚP (Sửa màu chữ) ---
@st.dialog("🆘 HƯỚNG DẪN CHI TIẾT")
def help_modal():
    # Sử dụng thẻ span và color !important để ép màu chữ trắng trong dialog
    st.markdown("""
    <div style="color: white !important;">
    <h3 style="color: #58a6ff !important;">🛡️ Cách hoạt động</h3>
    <p>1. <b>Tab YouTube:</b> Phân tích video. Nếu lỗi phụ đề, dùng DownSub.</p>
    <p>2. <b>Tab Văn bản:</b> Dán nội dung trực tiếp để thẩm định.</p>
    
    <h3 style="color: #58a6ff !important;">📺 Cách dùng DownSub</h3>
    <ol>
        <li>Truy cập <a href="https://downsub.com/" target="_blank" style="color:#58a6ff; font-weight:bold;">DownSub.com</a>.</li>
        <li>Dán link YouTube vào và nhấn <b>Download</b>.</li>
        <li>Tìm mục <b>[TXT]</b> và tải về.</li>
        <li>Copy nội dung dán vào tab <b>VĂN BẢN</b>.</li>
    </ol>
    
    <h3 style="color: #58a6ff !important;">📝 Ghi chú</h3>
    <p>Sử dụng ô bên phải để ghi chép kiến thức.</p>
    </div>
    """, unsafe_allow_html=True)

# --- 4. GIAO DIỆN SIDEBAR (RESET NÚT TRẮNG) ---
st.set_page_config(page_title="SmartLens AI Pro", layout="wide")

with st.sidebar:
    # Nút HELP (Lập trình lại màu)
    if st.button("❓ TRỢ GIÚP (HELP)", use_container_width=True):
        help_modal()
        
    st.markdown("<h2 style='text-align: center; color: white !important;'>🛡️ PROFILE</h2>", unsafe_allow_html=True)
    
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

    # KHỐI ĐIỂM SỐ (ÉP ĐEN)
    st.markdown(f"""
        <div style="background-color: #161b22 !important; padding: 25px; border-radius: 20px; border: 1px solid #30363d !important; text-align: center;">
            <p style="margin:0; font-size:16px; color:#8b949e !important; font-weight: bold;">ĐIỂM SỐ</p>
            <p style="font-size: 120px !important; font-weight: 900 !important; color: #f2cc60 !important; margin: 0; line-height: 1;">{st.session_state.score}</p>
            <div style="height:30px; border-bottom: 1px solid #30363d !important; margin-bottom: 20px;"></div>
            <p style="margin:0; font-size:16px; color:#8b949e !important; font-weight: bold;">CHUỖI LỬA</p>
            <p style="font-size: 120px !important; font-weight: 900 !important; color: #ff4b4b !important; margin: 0; line-height: 1;">{st.session_state.streak}🔥</p>
        </div>
    """, unsafe_allow_html=True)

    st.write("---")
    # NÚT BÀI HỌC MỚI (Lập trình lại màu)
    if st.button("➕ BÀI HỌC MỚI", use_container_width=True, type="primary"):
        st.session_state.current_data = None
        st.session_state.answered_questions = {}
        st.rerun()

    st.markdown("<p style='color: white !important;'>🎨 <b>TÙY CHỈNH</b></p>", unsafe_allow_html=True)
    bg_color = st.color_picker("Màu nền App:", "#0d1117")

# --- 5. CSS TỔNG LỰC (KHÓA DARK MODE & LẬP TRÌNH NÚT BẤM) ---
st.markdown(f"""
<style>
    /* Ép nền tối cho toàn App */
    .stApp {{ background-color: {bg_color} !important; color: #c9d1d9; }}
    
    /* Ép tất cả văn bản trong main area thành màu sáng */
    h1, h2, h3, p, span, li, label, .stMarkdown, .stSubheader, .stAlert {{ color: #c9d1d9 !important; }}
    
    .main-title {{ font-size: 65px !important; color: #58a6ff !important; text-align: center; font-weight: 900; margin-bottom: 10px; }}
    
    /* Ép khung báo cáo luôn tối */
    .check-box {{ 
        background-color: #1c2128 !important; border-left: 10px solid #58a6ff !important; 
        padding: 30px; border-radius: 20px; font-size: 19px; border: 1px solid #30363d !important;
        color: #c9d1d9 !important;
    }}
    
    .guide-box {{ background-color: #161b22 !important; padding: 20px; border-radius: 12px; border: 1px dashed #58a6ff !important; margin-top: 15px; color: #c9d1d9 !important; }}

    /* ========================================================== */
    /* 🔴🔴🔴 LẬP TRÌNH LẠI CÁC NÚT BẤM (FIX MÀU TRẮNG) 🔴🔴🔴 */
    /* ========================================================== */
    
    /* 1. ĐỊNH DẠNG NÚT BẤM CƠ BẢN (st.button thường) */
    div.stButton > button {{
        background-color: #161b22 !important; /* Nền xám đen */
        color: white !important; /* Chữ trắng */
        border: 1px solid #30363d !important; /* Viền xám */
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
    }}
    
    /* Hiệu ứng di chuột vào (Hover) */
    div.stButton > button:hover {{
        border-color: #58a6ff !important; /* Viền xanh */
        color: #58a6ff !important; /* Chữ xanh */
        background-color: #1c2128 !important; /* Nền tối hơn */
    }}

    /* 2. ĐỊNH DẠNG NÚT TYPE="PRIMARY" (Nút Bài học mới) */
    div.stButton > button[kind="primary"] {{
        background-color: #21262d !important; /* Nền tối khác một chút */
        border: 1px solid #30363d !important;
        color: #58a6ff !important; /* Ép chữ xanh cho nút chính */
    }}
    
    /* Hover của nút Primary */
    div.stButton > button[kind="primary"]:hover {{
        background-color: #238636 !important; /* Hover ra màu xanh lá chuẩn GitHub */
        color: white !important; /* Chữ trắng khi hover */
        border-color: #2ea043 !important;
    }}
    
    /* Sửa ô nhập text/textarea (Fix chữ đen trên nền đen) */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {{
        color: white !important;
        background-color: #0d1117 !important;
        border-color: #30363d !important;
    }}
</style>
""", unsafe_allow_html=True)

# --- 6. HÀM PHÂN TÍCH ---
def run_analysis(text):
    if not text or model is None: return
    input_text = text[:2500].replace('"', "'")
    with st.spinner("🕵️ AI đang thẩm định nội dung..."):
        try:
            prompt = f"""Phân tích phản biện nội dung này. Trả về JSON: {{"verification": "html_content", "questions": [{{'q': '...', 'options': ['A..','B..','C..','D..'], 'correct': 'A'}}]}}. Nội dung: {input_text}"""
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
    # Thêm câu chú thích của bạn
    st.markdown("### 📝 GHI CHÚ <br><small style='color:#8b949e !important;'>(để ghi chép thông tin)</small>", unsafe_allow_html=True)
    st.text_area("", height=750, key="notes_fixed", placeholder="Ví dụ: Video này nói về tư duy phản biện...")

with left:
    tab1, tab2 = st.tabs(["📺 PHÂN TÍCH YOUTUBE", "📝 VĂN BẢN"])
    
    with tab1:
        url = st.text_input("Dán link YouTube tại đây:")
        # Nút Trích xuất (Dùng Kind thường để ăn màu nền tối)
        if st.button("🚀 BẮT ĐẦU TRÍCH XUẤT", use_container_width=True):
            v_id = re.search(r"(?:v=|\/)([a-zA-Z0-9_-]{11})", url)
            if v_id:
                try:
                    ts = YouTubeTranscriptApi.get_transcript(v_id.group(1), languages=['vi', 'en'])
                    run_analysis(" ".join([i['text'] for i in ts]))
                except: st.error("❌ Video không có phụ đề!")
        
        # Hướng dẫn DownSub chi tiết
        st.markdown(f"""
        <div class="guide-box">
            <b style="color:#58a6ff !important;">🆘 HƯỚNG DẪN DOWNSUB CHI TIẾT:</b><br>
            1. Truy cập <a href="https://downsub.com/" target="_blank" style="color:#58a6ff; font-weight:bold;">DownSub.com</a>.<br>
            2. Dán link video vào và nhấn <b>Download</b>.<br>
            3. Tìm mục <b>[TXT]</b> và tải về (hoặc Copy toàn bộ văn bản).<br>
            4. Dán vào tab <b>📝 VĂN BẢN</b> bên cạnh để phân tích.
        </div>
        """, unsafe_allow_html=True)

    with tab2:
        txt = st.text_area("Dán nội dung văn bản:", height=250)
        # Nút Thẩm định
        if st.button("🔍 THẨM ĐỊNH TƯ DUY", use_container_width=True): run_analysis(txt)

    if st.session_state.current_data:
        st.markdown("---")
        # Khung phân tích (Cố định màu trong CSS)
        st.markdown(f'<div class="check-box">{st.session_state.current_data.get("verification", "")}</div>', unsafe_allow_html=True)
        
        st.markdown("### ✍️ THỬ THÁCH")
        for i, q in enumerate(st.session_state.current_data.get('questions', [])):
            st.write(f"**Câu {i+1}: {q['q']}**")
            q_id = f"q_{i}"
            is_locked = q_id in st.session_state.answered_questions
            ans = st.radio(f"Chọn đáp án câu {i+1}:", q['options'], key=f"r_{i}", index=None, disabled=is_locked)
            
            if not is_locked:
                # Nút nộp đáp án
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
                # HIỂN THỊ KẾT QUẢ ĐÚNG SAI
                if st.session_state.answered_questions[q_id]:
                    st.success(f"✅ Chính xác! Đáp án đúng là {q['correct']}")
                else:
                    st.error(f"❌ Sai rồi! Đáp án đúng: {q['correct']}")
