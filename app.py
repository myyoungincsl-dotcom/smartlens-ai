import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import re
import json

# --- 1. CẤU HÌNH AI THÔNG MINH (CHỐNG LỖI 404 & 429) ---
API_KEY = st.secrets.get("GEMINI_API_KEY", "")

if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    st.error("❌ CHƯA CÓ API KEY TRONG SECRETS!")
    st.stop()

@st.cache_resource
def get_working_model():
    """Tự động tìm model khả dụng để tránh lỗi 404 Version"""
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for target in ['gemini-1.5-flash', 'gemini-1.5-pro', 'models/gemini-1.5-flash']:
            for m_name in available_models:
                if target in m_name:
                    return genai.GenerativeModel(m_name)
        return genai.GenerativeModel(available_models[0])
    except Exception as e:
        st.error(f"Lỗi khởi tạo AI: {e}")
        return None

model = get_working_model()

# --- 2. QUẢN LÝ SESSION (ĐIỂM, TÊN, LỊCH SỬ) ---
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
    .main-title {{ font-size: 70px !important; color: #58a6ff !important; text-align: center; font-weight: 900; line-height: 1.1; margin-bottom: 20px; }}
    .streak-val {{ color: #ff4b4b !important; font-size: 80px !important; font-weight: 900 !important; text-align: center; margin: 0; }}
    .note-box textarea {{ height: 750px !important; background-color: #161b22 !important; color: #e6edf3 !important; border: 1px solid #30363d !important; }}
    .check-box {{ background-color: #161b22; border-left: 10px solid #58a6ff; padding: 25px; border-radius: 15px; border: 1px solid #30363d; line-height: 1.8; font-size: 18px; }}
</style>
""", unsafe_allow_html=True)

# --- 4. HÀM PHÂN TÍCH CHI TIẾT ---
def run_analysis(text, title="Bài học"):
    if not text or model is None: return
    # Cắt 3000 ký tự để AI phản hồi nhanh & sâu nhất
    clean_text = text[:3000]
    with st.spinner("🛡️ SmartLens đang phân tích chi tiết..."):
        try:
            prompt = f"""
            Hãy đóng vai chuyên gia thẩm định. Phân tích nội dung sau một cách CHI TIẾT, DÀI DÒNG:
            1. XÁC THỰC (Đúng/Sai). 2. PHẢN BIỆN (Góc nhìn khác). 3. MỞ RỘNG (Ứng dụng).
            Yêu cầu: Viết nội dung sâu sắc, dùng <b> và <br> để định dạng.
            Sau đó tạo 3 câu hỏi trắc nghiệm. 
            TRẢ VỀ JSON THUẦN TÚY:
            {{
                "verification": "phân tích cực kỳ dài và chi tiết ở đây",
                "questions": [
                    {{"q": "Câu hỏi", "options": ["A", "B", "C", "D"], "correct": "A"}}
                ]
            }}
            NỘI DUNG: {clean_text}
            """
            response = model.generate_content(prompt)
            json_match = re.search(r"\{.*\}", response.text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                st.session_state.current_data = data
                st.session_state.history.append({"title": title[:25], "data": data})
                st.session_state.answered_questions = set()
                st.rerun()
        except Exception as e:
            st.error(f"Lỗi AI: {e}")

# --- 5. SIDEBAR (NHẬP TÊN, ĐIỂM, BÀI HỌC MỚI, LỊCH SỬ) ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🛡️ PROFILE</h2>", unsafe_allow_html=True)
    st.session_state.student_name = st.text_input("👤 Nhập tên học sinh:", value=st.session_state.student_name)
    
    st.markdown(f"""
        <div style="background: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; text-align: center;">
            <p style="margin:0; font-size:12px;">ĐIỂM SỐ</p>
            <h1 style="color:#f2cc60; margin:0; font-size:50px !important;">{st.session_state.score}</h1>
            <p style="margin:0; font-size:12px;">CHUỖI LỬA</p>
            <p class="streak-val" style="font-size:40px !important;">{st.session_state.streak} 🔥</p>
        </div>
    """, unsafe_allow_html=True)

    st.write("---")
    if st.button("➕ BÀI HỌC MỚI", use_container_width=True, type="primary"):
        st.session_state.current_data = None
        st.rerun()
    
    st.write("📚 LỊCH SỬ BÀI HỌC")
    for i, h in enumerate(reversed(st.session_state.history)):
        if st.button(f"📖 {h['title']}...", key=f"h_{i}", use_container_width=True):
            st.session_state.current_data = h['data']
            st.rerun()

# --- 6. GIAO DIỆN CHÍNH ---
st.markdown("<div class='main-title'>🛡️ SMARTLENS AI</div>", unsafe_allow_html=True)

left, right = st.columns([3.8, 1.2])

with right:
    st.markdown("### 📝 GHI CHÚ (750px)")
    st.text_area("", height=750, placeholder="Ghi chép tại đây...", key="notes_area", label_visibility="collapsed")

with left:
    if st.session_state.student_name:
        st.write(f"Chào mừng học sinh: **{st.session_state.student_name}**")
        
    t1, t2 = st.tabs(["📺 VIDEO", "📝 VĂN BẢN"])
    with t1:
        url = st.text_input("Dán link YouTube:")
        if st.button("🚀 PHÂN TÍCH VIDEO"):
            v_id = re.search(r"(?:v=|\/)([a-zA-Z0-9_-]{11})", url)
            if v_id:
                try:
                    ts = YouTubeTranscriptApi.get_transcript(v_id.group(1), languages=['vi', 'en'])
                    run_analysis(" ".join([i['text'] for i in ts]), title=f"Video {v_id.group(1)}")
                except: st.warning("Không lấy được phụ đề. Hãy dùng Tab Văn Bản!")
    with t2:
        txt = st.text_area("Dán nội dung:", height=250)
        if st.button("🔍 THẨM ĐỊNH NGAY"):
            run_analysis(txt, title="Văn bản")

    if st.session_state.current_data:
        d = st.session_state.current_data
        st.markdown("---")
        st.markdown("### 🕵️ KẾT QUẢ PHÂN TÍCH")
        st.markdown(f'<div class="check-box">{d.get("verification", "")}</div>', unsafe_allow_html=True)
        
        st.markdown("### ✍️ THỬ THÁCH")
        for i, q in enumerate(d.get('questions', [])):
            st.write(f"**{i+1}. {q['q']}**")
            ans = st.radio(f"Chọn {i+1}:", q['options'], key=f"q_{i}", index=None)
            if ans and ans.startswith(q['correct']):
                if f"done_{i}" not in st.session_state.answered_questions:
                    st.session_state.score += 10
                    st.session_state.streak += 1
                    st.session_state.answered_questions.add(f"done_{i}")
                    st.success("Đúng rồi! +10 điểm")
                    st.rerun()
