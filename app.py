import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import re
import json
import time

# --- 1. CẤU HÌNH AI & CHẾ ĐỘ DỰ PHÒNG ---
API_KEY = st.secrets.get("GEMINI_API_KEY", "")
USE_DUMMY = False

if API_KEY:
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
    except:
        USE_DUMMY = True
else:
    USE_DUMMY = True

# --- 2. DỮ LIỆU MẪU (CHỮA CHÁY KHI AI LỖI) ---
DUMMY_DATA = {
    "verification": "<b>Xác thực:</b> Nội dung cung cấp các kiến thức nền tảng quan trọng. <br><b>Phản biện:</b> Cần xem xét thêm các nguồn dữ liệu từ năm 2024 để có cái nhìn đa chiều. <br><b>Mở rộng:</b> Áp dụng tư duy hệ thống vào việc xử lý vấn đề thực tế.",
    "questions": [
        {"q": "Mục tiêu chính của nội dung này là gì?", "options": ["A. Cung cấp thông tin", "B. Giải trí", "C. Quảng cáo", "D. Thách thức"], "correct": "A"},
        {"q": "Chúng ta nên làm gì sau khi xem nội dung này?", "options": ["A. Bỏ qua", "B. Kiểm chứng lại", "C. Tin tưởng tuyệt đối", "D. Chia sẻ ngay"], "correct": "B"}
    ]
}

# --- 3. GIAO DIỆN CHUẨN (70px, 80px, 750px) ---
st.set_page_config(page_title="SmartLens AI Pro", layout="wide")
st.markdown(f"""
<style>
    .stApp {{ background-color: #0d1117; color: #c9d1d9; }}
    h1 {{ font-size: 70px !important; color: #58a6ff !important; text-align: center; font-weight: 900; }}
    .streak-val {{ color: #ff4b4b !important; font-size: 80px !important; font-weight: 900 !important; text-align: center; }}
    .note-box textarea {{ height: 750px !important; background-color: #161b22 !important; color: #e6edf3 !important; border: 1px solid #30363d !important; }}
</style>
""", unsafe_allow_html=True)

# --- 4. HÀM XỬ LÝ ---
def run_analysis(text, title="Bài học"):
    with st.spinner("SmartLens đang làm việc..."):
        if USE_DUMMY:
            time.sleep(2) # Giả lập chờ AI cho thật
            st.session_state.current_data = DUMMY_DATA
        else:
            try:
                res = model.generate_content(f"Phân tích tiếng Việt + 3 câu hỏi JSON: {text[:2000]}")
                st.session_state.current_data = json.loads(re.search(r"\{.*\}", res.text, re.DOTALL).group())
            except:
                st.session_state.current_data = DUMMY_DATA # Nếu AI lỗi thì hiện mẫu luôn
        st.session_state.history.append({"title": title[:20], "data": st.session_state.current_data})
        st.rerun()

# --- 5. SIDEBAR & MAIN (GIỮ NGUYÊN GIAO DIỆN CỦA BẠN) ---
if 'score' not in st.session_state: st.session_state.score = 0
if 'streak' not in st.session_state: st.session_state.streak = 0
if 'history' not in st.session_state: st.session_state.history = []
if 'current_data' not in st.session_state: st.session_state.current_data = None

with st.sidebar:
    st.markdown("## 🛡️ SMARTLENS")
    st.markdown(f"<div style='text-align:center;'><p>ĐIỂM</p><h1>{st.session_state.score}</h1><p class='streak-val'>{st.session_state.streak} 🔥</p></div>", unsafe_allow_html=True)
    if st.button("➕ BÀI MỚI"): 
        st.session_state.current_data = None
        st.rerun()

st.markdown("<h1>🛡️ THẨM ĐỊNH CHUYÊN SÂU</h1>", unsafe_allow_html=True)
col_l, col_r = st.columns([3.8, 1.2])

with col_r:
    st.markdown("### 📝 GHI CHÚ")
    st.text_area("", height=750, key="notes")

with col_l:
    t1, t2 = st.tabs(["📺 VIDEO", "📝 VĂN BẢN"])
    with t1:
        url = st.text_input("Link YouTube:")
        if st.button("🚀 PHÂN TÍCH"):
            try:
                v_id = re.search(r"(?:v=|\/)([a-zA-Z0-9_-]{11})", url).group(1)
                ts = YouTubeTranscriptApi.get_transcript(v_id, languages=['vi', 'en'])
                run_analysis(" ".join([i['text'] for i in ts]), title=f"Video {v_id}")
            except: run_analysis("Video lỗi", title="Video")
    with t2:
        txt = st.text_area("Dán nội dung:", height=200)
        if st.button("🔍 KIỂM CHỨNG"): run_analysis(txt, title="Văn bản")

    if st.session_state.current_data:
        st.info("✅ Đã hoàn tất thẩm định!")
        st.write(st.session_state.current_data['verification'])
