import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import re
import json

# ==========================================
# 1. CẤU HÌNH AI & BẢO MẬT (CHỐNG LỖI 404/429)
# ==========================================
API_KEY = st.secrets.get("GEMINI_API_KEY", "")

if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    st.error("❌ CHƯA CÓ API KEY! Hãy dán vào mục Secrets trên Streamlit Cloud.")
    st.stop()

@st.cache_resource
def get_model():
    # Tự động dò tìm model khả dụng, ưu tiên Flash để tiết kiệm Quota
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for target in ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']:
            for m_name in available_models:
                if target in m_name:
                    return genai.GenerativeModel(m_name)
        return genai.GenerativeModel(available_models[0])
    except Exception as e:
        st.error(f"Lỗi khởi tạo AI: {e}")
        return None

model = get_model()

# ==========================================
# 2. QUẢN LÝ DỮ LIỆU HỆ THỐNG
# ==========================================
if 'score' not in st.session_state: st.session_state.score = 0
if 'streak' not in st.session_state: st.session_state.streak = 0
if 'history' not in st.session_state: st.session_state.history = []
if 'current_data' not in st.session_state: st.session_state.current_data = None
if 'student_name' not in st.session_state: st.session_state.student_name = ""
if 'notes' not in st.session_state: st.session_state.notes = ""
if 'answered_questions' not in st.session_state: st.session_state.answered_questions = set()

# ==========================================
# 3. GIAO DIỆN CSS (70PX, 80PX, 750PX)
# ==========================================
st.set_page_config(page_title="SmartLens AI Pro", layout="wide", page_icon="🛡️")

st.markdown(f"""
<style>
    /* Nền tối chuyên nghiệp */
    .stApp {{ background-color: #0d1117; color: #c9d1d9; }}
    
    /* Tiêu đề chính 70px */
    .main-title {{ font-size: 70px !important; color: #58a6ff !important; text-align: center; font-weight: 900; line-height: 1.1; margin-bottom: 20px; }}
    
    /* Chỉ số Streak 80px */
    .streak-val {{ color: #ff4b4b !important; font-size: 80px !important; font-weight: 900 !important; text-align: center; margin: 0; }}
    
    /* Ô ghi chú 750px height */
    .note-box textarea {{ height: 750px !important; background-color: #161b22 !important; color: #e6edf3 !important; border: 1px solid #30363d !important; border-radius: 10px; }}
    
    /* Khung thẩm định */
    .check-box {{ background-color: #161b22; border-left: 10px solid #58a6ff; padding: 25px; border-radius: 15px; border: 1px solid #30363d; line-height: 1.8; font-size: 18px; }}
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {{ background-color: #161b22 !important; border-right: 1px solid #30363d; }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. HÀM XỬ LÝ LOGIC CHÍNH
# ==========================================
def process_content(text, title="Bài học"):
    if not text or model is None: return
    # Giới hạn 3000 ký tự để tránh lỗi 504 Deadline Exceeded
    input_text = text[:3000]
    
    with st.spinner("🛡️ AI SmartLens đang thẩm định tri thức..."):
        try:
            prompt = f"""
            Bạn là chuyên gia thẩm định thông tin. Phân tích nội dung sau bằng tiếng Việt:
            1. Xác thực: Đúng hay sai? 2. Phản biện: Các góc nhìn khác? 3. Mở rộng: Bài học thực tế?
            Viết nội dung phân tích rõ ràng, dùng <b> và <br> để định dạng.
            Sau đó tạo 3 câu hỏi trắc nghiệm (A, B, C, D).
            TRẢ VỀ JSON THUẦN TÚY:
            {{
                "verification": "nội dung phân tích",
                "questions": [
                    {{"q": "Câu hỏi", "options": ["A. x", "B. y", "C. z", "D. t"], "correct": "A"}}
                ]
            }}
            Nội dung: {input_text}
            """
            response = model.generate_content(prompt)
            # Trích xuất JSON
            json_match = re.search(r"\{.*\}", response.text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                st.session_state.current_data = data
                st.session_state.history.append({"title": title[:20], "data": data})
                st.session_state.answered_questions = set()
                st.rerun()
        except Exception as e:
            if "429" in str(e):
                st.error("⚠️ Hết lượt dùng (Quota Exceeded)! Hãy thay API Key mới trong Secrets.")
            else:
                st.error(f"Lỗi AI: {e}")

# ==========================================
# 5. SIDEBAR (PROFILE & ĐIỂM SỐ)
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #58a6ff;'>🛡️ SMARTLENS AI</h2>", unsafe_allow_html=True)
    
    # Nhập tên học sinh
    st.session_state.student_name = st.text_input("👤 Tên học sinh:", value=st.session_state.student_name)
    
    # Bảng điểm & Streak
    st.markdown(f"""
        <div style="text-align: center; background: #0d1117; padding: 20px; border-radius: 15px; border: 2px solid #30363d; margin-top: 10px;">
            <p style="font-size: 14px; color: #8b949e; margin: 0;">ĐIỂM TÍCH LŨY</p>
            <h1 style="color: #f2cc60; font-size: 55px !important; margin: 0;">{st.session_state.score}</h1>
            <hr style="border: 0.5px solid #30363d;">
            <p style="font-size: 14px; color: #8b949e; margin: 0;">CHUỖI LỬA</p>
            <p class="streak-val">{st.session_state.streak} 🔥</p>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("➕ BÀI HỌC MỚI", use_container_width=True, type="primary"):
        st.session_state.current_data = None
        st.rerun()

    st.markdown("---")
    st.write("📚 LỊCH SỬ THẨM ĐỊNH")
    for i, item in enumerate(reversed(st.session_state.history)):
        if st.button(f"📖 {item['title']}...", key=f"hist_{i}", use_container_width=True):
            st.session_state.current_data = item['data']
            st.rerun()

# ==========================================
# 6. KHU VỰC CHÍNH (MAIN CONTENT)
# ==========================================
st.markdown("<div class='main-title'>🛡️ THẨM ĐỊNH CHUYÊN SÂU</div>", unsafe_allow_html=True)

left_col, right_col = st.columns([3.8, 1.2])

with right_col:
    st.markdown("### 📝 GHI CHÚ BÀI HỌC")
    # Ô ghi chú cao 750px
    st.session_state.notes = st.text_area("", value=st.session_state.notes, placeholder="Ghi lại những điều tâm đắc...", key="note_area", label_visibility="collapsed")

with left_col:
    tab_yt, tab_text = st.tabs(["📺 KIỂM CHỨNG YOUTUBE", "📝 KIỂM CHỨNG VĂN BẢN"])
    
    with tab_yt:
        url = st.text_input("Dán đường link YouTube vào đây:", placeholder="https://www.youtube.com/watch?v=...")
        if st.button("🚀 BẮT ĐẦU PHÂN TÍCH VIDEO", type="primary", use_container_width=True):
            video_id_match = re.search(r"(?:v=|\/)([a-zA-Z0-9_-]{11})", url)
            if video_id_match:
                try:
                    video_id = video_id_match.group(1)
                    transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['vi', 'en'])
                    full_text = " ".join([t['text'] for t in transcript_list])
                    process_content(full_text, title=f"Video {video_id}")
                except Exception:
                    st.warning("⚠️ Không thể lấy phụ đề tự động. Bạn hãy lấy văn bản từ Downsub.com rồi dán vào Tab Văn Bản nhé!")
            else:
                st.error("Link YouTube không hợp lệ!")

    with tab_text:
        input_txt = st.text_area("Dán nội dung bài báo hoặc kiến thức cần kiểm chứng:", height=250)
        if st.button("🔍 KIỂM CHỨNG KIẾN THỨC", type="primary", use_container_width=True):
            process_content(input_txt, title="Văn bản tự nhập")

    # Hiển thị kết quả thẩm định
    if st.session_state.current_data:
        data = st.session_state.current_data
        st.markdown("---")
        st.markdown("### 🕵️ KẾT QUẢ THẨM ĐỊNH AI")
        st.markdown(f"""<div class="check-box">{data.get('verification', 'Đang cập nhật...')}</div>""", unsafe_allow_html=True)
        
        st.markdown("### ✍️ THỬ THÁCH TƯ DUY")
        for i, q in enumerate(data.get('questions', [])):
            st.write(f"**Câu hỏi {i+1}: {q['q']}**")
            # Trắc nghiệm
            choice = st.radio(f"Chọn đáp án đúng cho câu {i+1}:", q['options'], key=f"quest_{i}", index=None)
            
            if choice:
                if choice.startswith(q['correct']):
                    if f"q_{i}" not in st.session_state.answered_questions:
                        st.session_state.score += 10
                        st.session_state.streak += 1
                        st.session_state.answered_questions.add(f"q_{i}")
                        st.success("🎉 Chính xác! Bạn được cộng 10 điểm.")
                        st.balloons()
                        st.rerun()
                else:
                    st.error("❌ Sai rồi, hãy suy nghĩ thêm một chút!")
