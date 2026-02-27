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
        # Tự động lấy danh sách model để tránh lỗi 404 (sai tên model)
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Ưu tiên bản flash để tránh lỗi 429 (hết hạn mức)
        target = next((m for m in available_models if '1.5-flash' in m), available_models[0])
        return genai.GenerativeModel(target)
    except Exception as e:
        st.error(f"Lỗi AI: {e}")
        return None

model = get_working_model()

# --- 2. QUẢN LÝ SESSION ---
if 'score' not in st.session_state: st.session_state.score = 0
if 'streak' not in st.session_state: st.session_state.streak = 0
if 'current_data' not in st.session_state: st.session_state.current_data = None
if 'student_name' not in st.session_state: st.session_state.student_name = ""
if 'name_confirmed' not in st.session_state: st.session_state.name_confirmed = False
if 'answered_questions' not in st.session_state: st.session_state.answered_questions = {}

# --- 3. GIAO DIỆN CSS & SIDEBAR ---
st.set_page_config(page_title="SmartLens AI Pro", layout="wide")

with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🛡️ PROFILE</h2>", unsafe_allow_html=True)
    
    if not st.session_state.name_confirmed:
        name_input = st.text_input("Tên học sinh:")
        if st.button("XÁC NHẬN", use_container_width=True):
            if name_input:
                st.session_state.student_name = name_input
                st.session_state.name_confirmed = True
                st.rerun()
    else:
        st.markdown(f"<h3 style='text-align:center; color:#58a6ff;'>🌟 Chào {st.session_state.student_name}!</h3>", unsafe_allow_html=True)

    # CHỈ SỐ TO KHỔNG LỒ (120PX)
    st.markdown(f"""
        <div style="background: #161b22; padding: 25px; border-radius: 20px; border: 1px solid #30363d; text-align: center;">
            <p style="margin:0; font-size:16px; color:#8b949e; font-weight: bold;">ĐIỂM SỐ</p>
            <p style="font-size: 120px !important; font-weight: 900 !important; color: #f2cc60 !important; margin: 0; line-height: 1;">{st.session_state.score}</p>
            <div style="height:30px; border-bottom: 1px solid #30363d; margin-bottom: 20px;"></div>
            <p style="margin:0; font-size:16px; color:#8b949e; font-weight: bold;">CHUỖI LỬA</p>
            <p style="font-size: 120px !important; font-weight: 900 !important; color: #ff4b4b !important; margin: 0; line-height: 1;">{st.session_state.streak}🔥</p>
        </div>
    """, unsafe_allow_html=True)

# CSS Custom
st.markdown("""
<style>
    .stApp { background-color: #0d1117 !important; color: #c9d1d9; }
    .main-title { font-size: 65px !important; color: #58a6ff !important; text-align: center; font-weight: 900; }
    .guide-box { 
        background: #1c2128; padding: 20px; border-radius: 12px; 
        border: 1px dashed #58a6ff; margin-top: 15px; line-height: 1.6;
    }
    .check-box { 
        background: rgba(22, 27, 34, 0.9); border-left: 10px solid #58a6ff; 
        padding: 30px; border-radius: 20px; font-size: 19px;
    }
</style>
""", unsafe_allow_html=True)

# --- 4. HÀM PHÂN TÍCH ---
def run_analysis(text):
    if not text or model is None: return
    input_text = text[:2500].replace('"', "'")
    with st.spinner("🕵️ AI đang thẩm định nội dung..."):
        try:
            prompt = f"Phân tích phản biện nội dung sau (Xác thực, Phản biện, Ứng dụng). Trả về JSON: {{'verification': '...', 'questions': [{{'q': '...', 'options': ['A..','B..','C..','D..'], 'correct': 'A'}}]}}. Nội dung: {input_text}"
            response = model.generate_content(prompt)
            match = re.search(r"\{.*\}", response.text, re.DOTALL)
            if match:
                st.session_state.current_data = json.loads(match.group().replace('\n', ' '))
                st.session_state.answered_questions = {}
                st.rerun()
        except Exception as e:
            st.error(f"Lỗi: {e}")

# --- 5. GIAO DIỆN CHÍNH ---
st.markdown("<div class='main-title'>🛡️ SMARTLENS AI</div>", unsafe_allow_html=True)
left, right = st.columns([3.8, 1.2])

with left:
    tab1, tab2 = st.tabs(["📺 PHÂN TÍCH YOUTUBE", "📝 VĂN BẢN"])
    
    with tab1:
        url = st.text_input("Dán link video YouTube tại đây:")
        if st.button("🚀 BẮT ĐẦU TRÍCH XUẤT", use_container_width=True):
            v_id = re.search(r"(?:v=|\/)([a-zA-Z0-9_-]{11})", url)
            if v_id:
                try:
                    ts = YouTubeTranscriptApi.get_transcript(v_id.group(1), languages=['vi', 'en'])
                    run_analysis(" ".join([i['text'] for i in ts]))
                except:
                    st.error("❌ Lỗi: Video này không có phụ đề công khai!")
            else: st.warning("Vui lòng nhập link YouTube hợp lệ.")

        # CHỈ DẪN CHI TIẾT KHI GẶP LỖI
        st.markdown(f"""
        <div class="guide-box">
            <b>💡 CÁCH XỬ LÝ KHI VIDEO KHÔNG CÓ PHỤ ĐỀ:</b><br>
            1️⃣ Truy cập trang: <a href="https://downsub.com/" target="_blank" style="color:#58a6ff; font-weight:bold;">DownSub.com</a><br>
            2️⃣ Dán link YouTube vào đó và nhấn <b>Download</b>.<br>
            3️⃣ Tại mục <b>TXT</b>, chọn tải về hoặc Copy toàn bộ văn bản phụ đề.<br>
            4️⃣ Chuyển sang Tab <b>📝 VĂN BẢN</b> bên cạnh, dán nội dung vào và nhấn Thẩm định.
        </div>
        """, unsafe_allow_html=True)

    with tab2:
        txt = st.text_area("Dán nội dung văn bản vào đây:", height=250)
        if st.button("🔍 THẨM ĐỊNH TƯ DUY", use_container_width=True):
            run_analysis(txt)

    if st.session_state.current_data:
        st.markdown("---")
        st.markdown(f'<div class="check-box">{st.session_state.current_data.get("verification", "")}</div>', unsafe_allow_html=True)
        # (Phần hiển thị câu hỏi trắc nghiệm giữ nguyên như cũ...)
        for i, q in enumerate(st.session_state.current_data.get('questions', [])):
            st.write(f"**Câu {i+1}: {q['q']}**")
            is_locked = f"q_{i}" in st.session_state.answered_questions
            ans = st.radio(f"Đáp án {i+1}", q['options'], key=f"r_{i}", index=None, disabled=is_locked)
            if not is_locked and st.button(f"Nộp câu {i+1}", key=f"b_{i}"):
                if ans:
                    correct = ans.startswith(q['correct'])
                    st.session_state.answered_questions[f"q_{i}"] = correct
                    if correct:
                        st.session_state.score += 10
                        st.session_state.streak += 1
                        st.balloons()
                    else: st.session_state.streak = 0
                    st.rerun()
