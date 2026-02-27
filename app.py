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

# --- 3. ĐỊNH NGHĨA HÀM TRỢ GIÚP (FIX LỖI NÚT ẤN) ---
@st.dialog("🆘 HƯỚNG DẪN CHI TIẾT")
def show_help_content():
    st.markdown("""
    ### 🛡️ SmartLens AI hoạt động như thế nào?
    1. **Tab YouTube:** Phân tích video. Nếu hệ thống báo lỗi phụ đề, hãy dùng công cụ hỗ trợ DownSub.
    2. **Tab Văn bản:** Dán trực tiếp nội dung bạn đọc được để AI thẩm định tư duy phản biện.
    3. **Thử thách:** Sau khi phân tích, trả lời đúng nhận **10 điểm**. Trả lời sai Chuỗi lửa về 0!
    
    ### 📺 Cách dùng DownSub (Chi tiết)
    * **Bước 1:** Truy cập [DownSub.com](https://downsub.com).
    * **Bước 2:** Dán link YouTube vào và nhấn **Download**.
    * **Bước 3:** Kéo xuống phần **[TXT]**, nhấn nút **Download**.
    * **Bước 4:** Copy toàn bộ chữ trong file vừa tải, dán vào tab **VĂN BẢN** của App.
    
    ### 📝 Ghi chú (để ghi chép thông tin)
    * Ô bên phải dùng để tóm tắt lại kiến thức. Dữ liệu này giúp bạn ghi nhớ sâu hơn và không bị mất khi làm trắc nghiệm.
    """)

# --- 4. GIAO DIỆN SIDEBAR ---
st.set_page_config(page_title="SmartLens AI Pro", layout="wide")

with st.sidebar:
    # Nút Help mới (Sửa lỗi không hiện)
    if st.button("❓ TRỢ GIÚP (HELP)", use_container_width=True):
        show_help_content()
        
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

    # FIX LIGHT MODE: Ép màu nền đen và chữ sáng cho khung điểm
    st.markdown(f"""
        <div style="background-color: #161b22 !important; padding: 20px; border-radius: 15px; border: 2px solid #30363d !important; text-align: center;">
            <p style="margin:0; font-size:14px; color:#8b949e !important; font-weight: bold;">ĐIỂM SỐ</p>
            <p style="font-size: 80px !important; font-weight: 900 !important; color: #f2cc60 !important; margin: 0; line-height: 1;">{st.session_state.score}</p>
            <hr style="border: 1px solid #30363d !important; margin: 15px 0;">
            <p style="margin:0; font-size:14px; color:#8b949e !important; font-weight: bold;">CHUỖI LỬA</p>
            <p style="font-size: 80px !important; font-weight: 900 !important; color: #ff4b4b !important; margin: 0; line-height: 1;">{st.session_state.streak}🔥</p>
        </div>
    """, unsafe_allow_html=True)

    st.write("---")
    if st.button("➕ BÀI HỌC MỚI", use_container_width=True, type="primary"):
        st.session_state.current_data = None
        st.session_state.answered_questions = {}
        st.rerun()

    bg_color = st.color_picker("Chọn màu nền App:", "#0d1117")

# --- 5. CSS TỔNG LỰC (KHÓA MÀU) ---
st.markdown(f"""
<style>
    .stApp {{ background-color: {bg_color} !important; }}
    /* Ép tất cả văn bản trong main area thành màu sáng */
    .stApp, .stMarkdown, p, h1, h2, h3, label {{ color: #c9d1d9 !important; }}
    .main-title {{ font-size: 60px !important; color: #58a6ff !important; text-align: center; font-weight: 900; padding-bottom: 20px; }}
    
    /* Fix khung báo cáo bị trắng */
    .check-box {{ 
        background-color: #161b22 !important; 
        border-left: 10px solid #58a6ff !important; 
        padding: 25px; border-radius: 15px; 
        border: 1px solid #30363d !important;
        color: #c9d1d9 !important;
        margin-bottom: 20px;
    }}
    
    /* Fix khung Downsub */
    .guide-box {{ 
        background-color: #1c2128 !important; 
        padding: 15px; border-radius: 10px; 
        border: 1px dashed #58a6ff !important; 
        color: #c9d1d9 !important;
    }}
</style>
""", unsafe_allow_html=True)

# --- 6. HÀM PHÂN TÍCH (Giữ nguyên) ---
def run_analysis(text):
    if not text or model is None: return
    input_text = text[:2500].replace('"', "'")
    with st.spinner("🕵️ AI đang thẩm định nội dung..."):
        try:
            prompt = f"Phân tích phản biện nội dung này. Trả về JSON: {{'verification': 'html_content', 'questions': [{{'q': '...', 'options': ['A..','B..','C..','D..'], 'correct': 'A'}}]}}. Nội dung: {input_text}"
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
    st.text_area("", height=650, key="notes_fixed", placeholder="Ví dụ: Video này nói về tư duy phản biện...")

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
        
        st.markdown(f"""
        <div class="guide-box">
            <b style="color:#58a6ff;">🆘 HƯỚNG DẪN DOWNSUB CHI TIẾT:</b><br>
            1. Truy cập <a href="https://downsub.com/" target="_blank" style="color:#58a6ff; font-weight:bold;">DownSub.com</a>.<br>
            2. Dán link video vào và nhấn <b>Download</b>.<br>
            3. Tìm mục <b>[TXT]</b> và tải về (hoặc Copy).<br>
            4. Dán vào tab <b>VĂN BẢN</b> bên cạnh để phân tích.
        </div>
        """, unsafe_allow_html=True)

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
                else: st.error(f"❌ Sai! Đáp án đúng: {q['correct']}")
