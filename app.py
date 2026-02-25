import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import re
import json

# --- 1. CẤU HÌNH AI THÔNG MINH (CHỐNG LỖI 404 & 403) ---
API_KEY = st.secrets.get("GEMINI_API_KEY", "")

if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    st.error("❌ LỖI: Chưa có API Key trong Secrets!")
    st.stop()

@st.cache_resource
def get_working_model():
    """Hàm tự động dò tìm model để tránh lỗi 404 Version"""
    try:
        # Danh sách ưu tiên các model ổn định nhất
        priority_models = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        for target in priority_models:
            for m_name in available:
                if target in m_name:
                    return genai.GenerativeModel(m_name)
        return genai.GenerativeModel(available[0])
    except Exception as e:
        st.error(f"Không thể kết nối AI: {e}")
        return None

model = get_working_model()

# --- 2. QUẢN LÝ DỮ LIỆU ---
if 'score' not in st.session_state: st.session_state.score = 0
if 'streak' not in st.session_state: st.session_state.streak = 0
if 'history' not in st.session_state: st.session_state.history = []
if 'current_data' not in st.session_state: st.session_state.current_data = None
if 'student_name' not in st.session_state: st.session_state.student_name = ""
if 'answered' not in st.session_state: st.session_state.answered = set()

# --- 3. GIAO DIỆN CSS (70PX - 80PX - 750PX) ---
st.set_page_config(page_title="SmartLens AI Pro", layout="wide")
st.markdown(f"""
<style>
    .stApp {{ background-color: #0d1117; color: #c9d1d9; }}
    h1 {{ font-size: 70px !important; color: #58a6ff !important; text-align: center; font-weight: 900; line-height: 1.1; }}
    .streak-val {{ color: #ff4b4b !important; font-size: 80px !important; font-weight: 900 !important; text-align: center; margin: 0; }}
    .note-box textarea {{ height: 750px !important; background-color: #161b22 !important; color: #e6edf3 !important; border: 1px solid #30363d !important; }}
    .check-box {{ background-color: #161b22; border-left: 15px solid #0056b3; padding: 35px; border-radius: 15px; border: 1px solid #30363d; line-height: 1.8; font-size: 18px; }}
</style>
""", unsafe_allow_html=True)

# --- 4. HÀM XỬ LÝ (TỐI ƯU CHỐNG 504) ---
def run_analysis(text, title="Bài học"):
    if not text or model is None: return
    # Cắt cực ngắn (chỉ lấy 2000 ký tự) để tiết kiệm Token
    clean_text = text[:2000] 
    
    with st.spinner("Đang thẩm định (Ưu tiên tốc độ)..."):
        try:
            prompt = f"Phân tích tiếng Việt ngắn gọn + 3 câu hỏi JSON: {clean_text}"
            response = model.generate_content(prompt)
            
            if response:
                json_match = re.search(r"\{.*\}", response.text, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    st.session_state.current_data = data
                    st.session_state.history.append({"title": title[:20], "data": data})
                    st.rerun()
        except Exception as e:
            if "429" in str(e):
                st.error("⚠️ Hết lượt dùng miễn phí! Vui lòng thay API Key từ Gmail khác trong phần Secrets.")
            else:
                st.error(f"Lỗi hệ thống: {e}")

# --- 5. SIDEBAR ---
with st.sidebar:
    st.markdown("## 🛡️ SMARTLENS")
    if not st.session_state.student_name:
        st.session_state.student_name = st.text_input("👤 Tên học sinh:")
    else:
        st.markdown(f"Học sinh: **{st.session_state.student_name}**")

    st.markdown(f"""
        <div style="text-align: center; background: #161b22; padding: 20px; border-radius: 15px; border: 2px solid #58a6ff;">
            <p style="font-size: 14px; color: #8b949e;">ĐIỂM</p>
            <h1 style="color: #f2cc60; font-size: 50px !important; margin: 0;">{st.session_state.score}</h1>
            <p style="font-size: 14px; color: #8b949e;">CHUỖI LỬA</p>
            <p class="streak-val">{st.session_state.streak} 🔥</p>
        </div>
    """, unsafe_allow_html=True)

    if st.button("➕ BÀI HỌC MỚI", use_container_width=True, type="primary"):
        st.session_state.current_data = None
        st.rerun()
    
    st.markdown("---")
    st.write("📚 BÀI ĐÃ LƯU")
    for i, h in enumerate(st.session_state.history):
        if st.button(f"📖 {h['title']}", key=f"h_{i}", use_container_width=True):
            st.session_state.current_data = h['data']
            st.rerun()

# --- 6. GIAO DIỆN CHÍNH ---
st.markdown("<h1>🛡️ THẨM ĐỊNH CHUYÊN SÂU</h1>", unsafe_allow_html=True)
m_col, n_col = st.columns([3.8, 1.2])

with n_col:
    st.markdown("### 📝 GHI CHÚ (750px)")
    st.text_area("", height=750, key="notes_box", placeholder="Ghi chép tại đây...")

with m_col:
    t1, t2 = st.tabs(["📺 VIDEO", "📝 VĂN BẢN"])
    with t1:
        url = st.text_input("Link YouTube:")
        if st.button("🚀 PHÂN TÍCH", key="btn_yt"):
            v_id = re.search(r"(?:v=|\/)([a-zA-Z0-9_-]{11})", url)
            if v_id:
                try:
                    ts = YouTubeTranscriptApi.get_transcript(v_id.group(1), languages=['vi', 'en'])
                    run_analysis(" ".join([i['text'] for i in ts]), title=f"Video {v_id.group(1)}")
                except:
                    st.warning("⚠️ Không lấy được phụ đề. Hãy dùng Tab Văn Bản để dán nội dung!")
    with t2:
        txt_in = st.text_area("Dán nội dung:", height=300)
        if st.button("🔍 KIỂM CHỨNG", key="btn_txt"):
            run_analysis(txt_in, title="Văn bản")

    if st.session_state.current_data:
        d = st.session_state.current_data
        st.markdown("---")
        st.markdown(f'<div class="check-box">{d.get("verification", "")}</div>', unsafe_allow_html=True)
        
        st.markdown("### ✍️ THỬ THÁCH")
        for idx, q in enumerate(d.get('questions', [])):
            st.write(f"**{idx+1}. {q['q']}**")
            choice = st.radio(f"Chọn {idx+1}:", q['options'], key=f"q_{idx}", index=None)
            if choice and choice.startswith(q['correct']):
                if f"q_{idx}" not in st.session_state.answered:
                    st.session_state.score += 10
                    st.session_state.streak += 1
                    st.session_state.answered.add(f"q_{idx}")
                    st.rerun()
