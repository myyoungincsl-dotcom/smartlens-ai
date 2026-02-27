import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import re
import json

# --- 1. CẤU HÌNH AI (Giữ nguyên logic của bạn) ---
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

# Hàm Dialog cho nút Help
@st.dialog("🆘 HƯỚNG DẪN SỬ DỤNG CHI TIẾT")
def help_modal():
    st.markdown("""
    ### 🛡️ SmartLens AI hoạt động như thế nào?
    1. **Tab YouTube:** Phân tích video. Nếu hệ thống báo lỗi phụ đề, hãy dùng công cụ hỗ trợ (Xem bên dưới).
    2. **Tab Văn bản:** Dán trực tiếp nội dung bạn đọc được để AI thẩm định tư duy phản biện.
    3. **Thử thách:** Sau khi phân tích, bạn sẽ nhận được 3 câu hỏi. Trả lời đúng nhận **10 điểm** và tăng **Chuỗi lửa**. Trả lời sai Chuỗi lửa sẽ tắt!
    
    ### 📺 Cách dùng DownSub (Khi YouTube báo lỗi)
    * **Bước 1:** Truy cập [DownSub.com](https://downsub.com).
    * **Bước 2:** Dán link YouTube vào và nhấn **Download**.
    * **Bước 3:** Kéo xuống phần **TXT**, nhấn nút **Download** hoặc **Copy**.
    * **Bước 4:** Quay lại Tab **VĂN BẢN** của SmartLens, dán vào và nhấn **Thẩm định**.
    
    ### 📝 Ghi chú thông tin
    * Sử dụng ô bên phải để tóm tắt lại kiến thức AI vừa phân tích. Dữ liệu này giúp bạn ghi nhớ sâu hơn và không bị mất khi bạn làm trắc nghiệm.
    """)

with st.sidebar:
    # Nút Help đặt ngay đầu Sidebar cho dễ thấy
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

    # KHỐI ĐIỂM (Cố định màu nền đen để chống Light Mode)
    st.markdown(f"""
        <div style="background-color: #161b22 !important; padding: 25px; border-radius: 20px; border: 1px solid #30363d !important; text-align: center;">
            <p style="margin:0; font-size:16px; color:#8b949e !important; font-weight: bold;">ĐIỂM SỐ</p>
            <p style="font-size: 100px !important; font-weight: 900 !important; color: #f2cc60 !important; margin: 0; line-height: 1;">{st.session_state.score}</p>
            <div style="height:30px; border-bottom: 1px solid #30363d !important; margin-bottom: 20px;"></div>
            <p style="margin:0; font-size:16px; color:#8b949e !important; font-weight: bold;">CHUỖI LỬA</p>
            <p style="font-size: 100px !important; font-weight: 900 !important; color: #ff4b4b !important; margin: 0; line-height: 1;">{st.session_state.streak}🔥</p>
        </div>
    """, unsafe_allow_html=True)

    st.write("---")
    if st.button("➕ BÀI HỌC MỚI", use_container_width=True, type="primary"):
        st.session_state.current_data = None
        st.session_state.answered_questions = {}
        st.rerun()

    st.markdown("🎨 **TÙY CHỈNH GIAO DIỆN**")
    bg_color = st.color_picker("Chọn màu nền App:", "#0d1117")

# --- 4. ÁP DỤNG CSS TRIỆT ĐỂ (CHỐNG LIGHT MODE) ---
st.markdown(f"""
<style>
    /* Ép nền tối cho toàn bộ App */
    .stApp {{ background-color: {bg_color} !important; color: #c9d1d9 !important; }}
    
    /* Ép tất cả các văn bản Markdown phải có màu sáng */
    .stMarkdown p, .stMarkdown li, .stMarkdown h3, .stMarkdown label {{ color: #c9d1d9 !important; }}
    
    .main-title {{ font-size: 65px !important; color: #58a6ff !important; text-align: center; font-weight: 900; }}
    
    /* Ép khung phân tích luôn là màu tối chuẩn của GitHub/Dark Mode */
    .check-box {{ 
        background-color: #161b22 !important; 
        border-left: 10px solid #58a6ff !important; 
        padding: 30px; border-radius: 20px; font-size: 19px; 
        border: 1px solid #30363d !important;
        color: #c9d1d9 !important;
    }}
    
    /* Khung hướng dẫn Downsub */
    .guide-box {{ 
        background-color: #0d1117 !important; 
        padding: 20px; border-radius: 12px; 
        border: 1px dashed #58a6ff !important; 
        margin-top: 15px;
        color: #c9d1d9 !important;
    }}
    
    /* Ép màu cho Sidebar */
    [data-testid="stSidebar"] {{ background-color: #0d1117 !important; }}
</style>
""", unsafe_allow_html=True)

# --- 5. HÀM PHÂN TÍCH (Giữ nguyên logic của bạn) ---
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

# --- 6. GIAO DIỆN CHÍNH ---
st.markdown("<div class='main-title'>🛡️ SMARTLENS AI</div>", unsafe_allow_html=True)
left, right = st.columns([3.8, 1.2])

with right:
    st.markdown("### 📝 GHI CHÚ <br><small>(để ghi chép thông tin)</small>", unsafe_allow_html=True)
    st.text_area("", height=750, key="notes_fixed", placeholder="Ghi lại kiến thức tại đây...")

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
            else: st.warning("Link không hợp lệ.")

        st.markdown(f"""
        <div class="guide-box">
            <b>🆘 HƯỚNG DẪN DOWNSUB CHI TIẾT:</b><br>
            1. Truy cập <a href="https://downsub.com/" target="_blank" style="color:#58a6ff; font-weight:bold;">DownSub.com</a>.<br>
            2. Dán link video vào ô tìm kiếm và nhấn <b>Download</b>.<br>
            3. Tìm mục <b>[TXT]</b> và nhấn vào nút Download bên cạnh ngôn ngữ bạn muốn.<br>
            4. Mở file vừa tải, <b>Copy toàn bộ chữ</b> và dán vào tab <b>VĂN BẢN</b> bên cạnh để phân tích.
        </div>
        """, unsafe_allow_html=True)

    with tab2:
        txt = st.text_area("Dán nội dung văn bản (hoặc phụ đề từ DownSub):", height=250)
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
