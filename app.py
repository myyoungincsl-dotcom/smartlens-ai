import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import re
import json

# --- 1. CẤU HÌNH AI & FIX LỖI 404 ---
API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    st.error("❌ CHƯA CÓ API KEY TRONG SECRETS!")
    st.stop()

@st.cache_resource
def get_working_model():
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for target in ['gemini-1.5-flash', 'gemini-1.5-pro', 'models/gemini-1.5-flash']:
            for m_name in available_models:
                if target in m_name: return genai.GenerativeModel(m_name)
        return genai.GenerativeModel(available_models[0])
    except: return None

model = get_working_model()

# --- 2. QUẢN LÝ SESSION ---
if 'score' not in st.session_state: st.session_state.score = 0
if 'streak' not in st.session_state: st.session_state.streak = 0
if 'history' not in st.session_state: st.session_state.history = []
if 'current_data' not in st.session_state: st.session_state.current_data = None
if 'student_name' not in st.session_state: st.session_state.student_name = ""
if 'answered_questions' not in st.session_state: st.session_state.answered_questions = set()

# --- 3. GIAO DIỆN CSS (70PX - 80PX - 750PX) ---
st.set_page_config(page_title="SmartLens AI Pro", layout="wide")
st.markdown(f"""
<style>
    .stApp {{ background-color: #0d1117; color: #c9d1d9; }}
    .main-title {{ font-size: 70px !important; color: #58a6ff !important; text-align: center; font-weight: 900; }}
    .streak-val {{ color: #ff4b4b !important; font-size: 80px !important; font-weight: 900 !important; text-align: center; }}
    .note-box textarea {{ height: 750px !important; background-color: #161b22 !important; color: #e6edf3 !important; border: 1px solid #30363d !important; }}
    .check-box {{ background-color: #161b22; border-left: 10px solid #58a6ff; padding: 25px; border-radius: 15px; border: 1px solid #30363d; line-height: 1.8; font-size: 18px; }}
</style>
""", unsafe_allow_html=True)

# --- 4. HÀM PHÂN TÍCH CHỐNG LỖI JSON ---
def run_analysis(text, title="Bài học"):
    if not text or model is None: return
    clean_text = text[:3000].replace('"', "'") # Thay dấu ngoặc kép để tránh lỗi JSON
    with st.spinner("🛡️ SmartLens đang phân tích sâu..."):
        try:
            prompt = f"""
            Đóng vai chuyên gia thẩm định. Phân tích CHI TIẾT, DÀI DÒNG nội dung này bằng tiếng Việt.
            Yêu cầu: 1. Xác thực. 2. Phản biện. 3. Mở rộng. (Dùng <b> và <br> để định dạng).
            Tạo 3 câu hỏi trắc nghiệm (A, B, C, D).
            TRẢ VỀ DUY NHẤT ĐỊNH DẠNG JSON (Không thêm bớt chữ gì ngoài JSON):
            {{
                "verification": "nội dung dài",
                "questions": [
                    {{"q": "Câu hỏi", "options": ["A. x", "B. y", "C. z", "D. t"], "correct": "A"}}
                ]
            }}
            NỘI DUNG: {clean_text}
            """
            response = model.generate_content(prompt)
            # Dùng regex để bóc tách JSON chính xác nhất
            match = re.search(r"\{.*\}", response.text, re.DOTALL)
            if match:
                clean_json = match.group().replace('\n', ' ').replace('\r', '')
                data = json.loads(clean_json)
                st.session_state.current_data = data
                st.session_state.history.append({"title": title[:20], "data": data})
                st.session_state.answered_questions = set()
                st.rerun()
        except Exception as e:
            st.error(f"Lỗi AI: {e}. AI trả về định dạng không chuẩn, vui lòng thử lại.")

# --- 5. SIDEBAR ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🛡️ PROFILE</h2>", unsafe_allow_html=True)
    st.session_state.student_name = st.text_input("👤 Tên học sinh:", value=st.session_state.student_name)
    st.markdown(f"<div style='background: #161b22; padding: 10px; border-radius: 10px; text-align: center;'><p>ĐIỂM: {st.session_state.score}</p><p class='streak-val' style='font-size:35px !important;'>{st.session_state.streak} 🔥</p></div>", unsafe_allow_html=True)
    if st.button("➕ BÀI HỌC MỚI", use_container_width=True, type="primary"):
        st.session_state.current_data = None
        st.rerun()
    st.write("📚 LỊCH SỬ")
    for i, h in enumerate(reversed(st.session_state.history)):
        if st.button(f"📖 {h['title']}...", key=f"h_{i}", use_container_width=True):
            st.session_state.current_data = h['data']
            st.rerun()

# --- 6. GIAO DIỆN CHÍNH ---
st.markdown("<div class='main-title'>🛡️ SMARTLENS AI</div>", unsafe_allow_html=True)
left, right = st.columns([3.8, 1.2])

with right:
    st.markdown("### 📝 GHI CHÚ (750px)")
    st.text_area("", height=750, key="notes_area", label_visibility="collapsed")

with left:
    t1, t2 = st.tabs(["📺 VIDEO", "📝 VĂN BẢN"])
    with t1:
        url = st.text_input("Link YouTube:")
        if st.button("🚀 PHÂN TÍCH VIDEO"):
            v_id = re.search(r"(?:v=|\/)([a-zA-Z0-9_-]{11})", url)
            if v_id:
                try:
                    ts = YouTubeTranscriptApi.get_transcript(v_id.group(1), languages=['vi', 'en'])
                    run_analysis(" ".join([i['text'] for i in ts]), title=f"Video {v_id.group(1)}")
                except: st.warning("Hãy dùng Tab Văn Bản!")
    with t2:
        txt = st.text_area("Dán nội dung:", height=250)
        if st.button("🔍 THẨM ĐỊNH"): run_analysis(txt, title="Văn bản")

    if st.session_state.current_data:
        st.markdown(f'<div class="check-box">{st.session_state.current_data.get("verification", "")}</div>', unsafe_allow_html=True)
        for i, q in enumerate(st.session_state.current_data.get('questions', [])):
            st.write(f"**{i+1}. {q['q']}**")
            ans = st.radio(f"Chọn {i+1}:", q['options'], key=f"q_{i}", index=None)
            if ans and ans.startswith(q['correct']):
                if f"d_{i}" not in st.session_state.answered_questions:
                    st.session_state.score += 10
                    st.session_state.streak += 1
                    st.session_state.answered_questions.add(f"d_{i}")
                    st.rerun()
