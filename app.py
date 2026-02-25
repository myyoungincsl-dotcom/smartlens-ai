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
    st.error("❌ CHƯA CÓ API KEY TRONG SECRETS!")
    st.stop()

@st.cache_resource
def get_model():
    try:
        return genai.GenerativeModel('gemini-1.5-flash')
    except: return None

model = get_model()

# --- 2. QUẢN LÝ SESSION ---
if 'score' not in st.session_state: st.session_state.score = 0
if 'streak' not in st.session_state: st.session_state.streak = 0
if 'current_data' not in st.session_state: st.session_state.current_data = None
if 'student_name' not in st.session_state: st.session_state.student_name = ""
if 'answered_questions' not in st.session_state: st.session_state.answered_questions = {}

# --- 3. GIAO DIỆN CSS (DESIGN MỚI) ---
st.set_page_config(page_title="SmartLens AI Pro", layout="wide")
st.markdown(f"""
<style>
    .stApp {{ background-color: #0d1117; color: #c9d1d9; }}
    .main-title {{ font-size: 70px !important; color: #58a6ff !important; text-align: center; font-weight: 900; text-shadow: 2px 2px 10px #58a6ff44; }}
    .big-val {{ font-size: 80px !important; font-weight: 900 !important; text-align: center; margin: 0; line-height: 1; }}
    .score-color {{ color: #f2cc60 !important; }}
    .streak-color {{ color: #ff4b4b !important; }}
    .note-box textarea {{ height: 750px !important; background-color: #161b22 !important; color: #e6edf3 !important; border: 1px solid #30363d !important; border-radius: 15px; }}
    .check-box {{ 
        background: linear-gradient(145deg, #1c2128, #161b22);
        border-left: 8px solid #58a6ff; padding: 25px; border-radius: 15px; 
        border: 1px solid #30363d; line-height: 1.6; font-size: 17px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }}
    .stButton>button {{ border-radius: 10px; font-weight: bold; transition: 0.3s; }}
    .stButton>button:hover {{ transform: scale(1.02); box-shadow: 0 5px 15px #58a6ff44; }}
</style>
""", unsafe_allow_html=True)

# --- 4. HÀM XỬ LÝ (PHÂN TÍCH NGẮN GỌN) ---
def run_analysis(text, title="Bài học"):
    if not text or model is None: return
    with st.spinner("🛡️ Đang thẩm định..."):
        try:
            prompt = f"""
            Phân tích ngắn gọn (Dưới 300 từ) nội dung sau theo 3 phần: Xác thực, Phản biện, Mở rộng.
            Sử dụng <b> và <br> để trình bày đẹp.
            Sau đó tạo 3 câu hỏi trắc nghiệm A, B, C, D.
            TRẢ VỀ JSON:
            {{
                "verification": "nội dung phân tích",
                "questions": [{{"q": "câu hỏi", "options": ["A. x", "B. y", "C. z", "D. t"], "correct": "A"}}]
            }}
            NỘI DUNG: {text[:2500]}
            """
            response = model.generate_content(prompt)
            match = re.search(r"\{.*\}", response.text, re.DOTALL)
            if match:
                st.session_state.current_data = json.loads(match.group())
                st.session_state.answered_questions = {}
                st.rerun()
        except Exception as e:
            st.error(f"Lỗi AI: {e}")

# --- 5. SIDEBAR (LƯU TÊN & ĐIỂM TO) ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>👤 HỌC SINH</h2>", unsafe_allow_html=True)
    
    # Cơ chế lưu tên ổn định hơn
    name_input = st.text_input("Nhập tên và nhấn Enter:", value=st.session_state.student_name)
    if name_input != st.session_state.student_name:
        st.session_state.student_name = name_input
        st.success("Đã lưu tên!")

    st.markdown(f"""
        <div style="background: #161b22; padding: 20px; border-radius: 20px; border: 1px solid #30363d; text-align: center; margin-top: 10px;">
            <p style="margin:0; font-size:14px; color:#8b949e;">ĐIỂM SỐ</p>
            <p class="big-val score-color">{st.session_state.score}</p>
            <div style="height:10px"></div>
            <p style="margin:0; font-size:14px; color:#8b949e;">CHUỖI LỬA</p>
            <p class="big-val streak-color">{st.session_state.streak} 🔥</p>
        </div>
    """, unsafe_allow_html=True)

    st.write("---")
    # Nút RESET hoàn toàn
    if st.button("➕ BÀI HỌC MỚI", use_container_width=True, type="primary"):
        st.session_state.current_data = None
        st.session_state.answered_questions = {}
        st.rerun()

# --- 6. GIAO DIỆN CHÍNH ---
st.markdown("<div class='main-title'>🛡️ SMARTLENS AI</div>", unsafe_allow_html=True)
left, right = st.columns([3.8, 1.2])

with right:
    st.markdown("### 📝 GHI CHÚ")
    st.text_area("", height=750, key="notes_area", placeholder="Hệ thống ghi chú...")

with left:
    if st.session_state.student_name:
        st.markdown(f"🚩 Đang học: **{st.session_state.student_name}**")
    
    t1, t2 = st.tabs(["📺 VIDEO", "📝 VĂN BẢN"])
    with t1:
        url = st.text_input("Link YouTube:", key="yt_url")
        if st.button("🚀 PHÂN TÍCH"):
            v_id = re.search(r"(?:v=|\/)([a-zA-Z0-9_-]{11})", url)
            if v_id:
                try:
                    ts = YouTubeTranscriptApi.get_transcript(v_id.group(1), languages=['vi', 'en'])
                    run_analysis(" ".join([i['text'] for i in ts]))
                except: st.warning("Hãy dùng Tab Văn Bản!")
    with t2:
        txt = st.text_area("Nội dung:", height=200, key="txt_input")
        if st.button("🔍 THẨM ĐỊNH"): run_analysis(txt)

    if st.session_state.current_data:
        st.markdown("---")
        st.markdown(f'<div class="check-box">{st.session_state.current_data.get("verification", "")}</div>', unsafe_allow_html=True)
        
        st.markdown("### ✍️ THỬ THÁCH TRẮC NGHIỆM")
        for i, q in enumerate(st.session_state.current_data.get('questions', [])):
            st.write(f"**Câu {i+1}: {q['q']}**")
            ans = st.radio(f"Chọn đáp án cho câu {i+1}:", q['options'], key=f"ans_{i}", index=None)
            
            # Hiển thị Đúng/Sai rõ ràng
            if ans:
                is_correct = ans.startswith(q['correct'])
                if is_correct:
                    st.success(f"✅ CHÍNH XÁC! Đáp án là {q['correct']}")
                    if f"q_{i}" not in st.session_state.answered_questions:
                        st.session_state.score += 10
                        st.session_state.streak += 1
                        st.session_state.answered_questions[f"q_{i}"] = True
                        st.balloons()
                        st.rerun()
                else:
                    st.error(f"❌ CHƯA ĐÚNG! Hãy thử chọn lại nhé.")
