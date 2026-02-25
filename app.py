import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import re
import json

# --- 1. CẤU HÌNH AI (CƠ CHẾ TỰ DÒ MODEL - CHỐNG 404) ---
API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    st.error("❌ THIẾU API KEY TRONG SECRETS!")
    st.stop()

@st.cache_resource
def get_working_model():
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for m in models:
            if '1.5-flash' in m: return genai.GenerativeModel(m)
        return genai.GenerativeModel(models[0])
    except Exception as e:
        st.error(f"Lỗi khởi tạo AI: {e}")
        return None

model = get_working_model()

# --- 2. QUẢN LÝ SESSION ---
if 'score' not in st.session_state: st.session_state.score = 0
if 'streak' not in st.session_state: st.session_state.streak = 0
if 'current_data' not in st.session_state: st.session_state.current_data = None
if 'student_name' not in st.session_state: st.session_state.student_name = ""
if 'name_confirmed' not in st.session_state: st.session_state.name_confirmed = False
if 'answered_questions' not in st.session_state: st.session_state.answered_questions = {}

# --- 3. GIAO DIỆN CSS ---
st.set_page_config(page_title="SmartLens AI Pro", layout="wide")
st.markdown(f"""
<style>
    .stApp {{ background-color: #0d1117; color: #c9d1d9; }}
    .main-title {{ font-size: 70px !important; color: #58a6ff !important; text-align: center; font-weight: 900; margin-bottom: 10px; }}
    .big-val {{ font-size: 80px !important; font-weight: 900 !important; text-align: center; margin: 0; line-height: 1; }}
    .score-color {{ color: #f2cc60 !important; }}
    .streak-color {{ color: #ff4b4b !important; }}
    .note-box textarea {{ height: 750px !important; background-color: #161b22 !important; color: #e6edf3 !important; border: 1px solid #30363d !important; border-radius: 15px; }}
    .check-box {{ 
        background: #161b22; border-left: 8px solid #58a6ff; padding: 25px; border-radius: 15px; 
        border: 1px solid #30363d; line-height: 1.7; font-size: 18px;
    }}
    .guide-box {{ background: #1c2128; padding: 15px; border-radius: 10px; border: 1px dashed #58a6ff; margin-bottom: 20px; }}
</style>
""", unsafe_allow_html=True)

# --- 4. HÀM PHÂN TÍCH (ĐỘ DÀI VỪA ĐỦ - ỔN ĐỊNH) ---
def run_analysis(text):
    if not text or model is None: return
    # Cắt văn bản đầu vào để tránh quá tải
    input_content = text[:2500].replace('"', "'")
    with st.spinner("🛡️ AI SmartLens đang thẩm định..."):
        try:
            # Prompt yêu cầu JSON sạch, không dư dấu phẩy
            prompt = f"""
            Phân tích nội dung sau theo 3 phần: Xác thực, Phản biện, Mở rộng. 
            Viết sâu sắc nhưng súc tích (khoảng 200-300 từ). Dùng <b> và <br>.
            Tạo 3 câu hỏi trắc nghiệm (A, B, C, D). 
            CHỈ TRẢ VỀ JSON:
            {{
                "verification": "nội dung phân tích",
                "questions": [
                    {{"q": "câu hỏi", "options": ["A. x", "B. y", "C. z", "D. t"], "correct": "A"}}
                ]
            }}
            NỘI DUNG: {input_content}
            """
            response = model.generate_content(prompt)
            match = re.search(r"\{.*\}", response.text, re.DOTALL)
            if match:
                # Xử lý chuỗi JSON để loại bỏ các ký tự gây lỗi thường gặp
                clean_json = match.group().replace('\n', ' ').replace('\r', '').strip()
                # Xử lý dấu phẩy thừa trước dấu đóng ngoặc (lỗi bạn gặp)
                clean_json = re.sub(r',\s*([\}\]])', r'\1', clean_json)
                st.session_state.current_data = json.loads(clean_json)
                st.session_state.answered_questions = {}
                st.rerun()
        except Exception as e:
            st.error(f"Lỗi xử lý dữ liệu: {e}. Vui lòng thử lại lần nữa.")

# --- 5. SIDEBAR (KHÓA TÊN & ĐIỂM) ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🛡️ HÀNH TRÌNH</h2>", unsafe_allow_html=True)
    
    if not st.session_state.name_confirmed:
        name_input = st.text_input("Nhập tên học sinh:")
        if st.button("XÁC NHẬN TÊN", use_container_width=True):
            if name_input:
                st.session_state.student_name = name_input
                st.session_state.name_confirmed = True
                st.rerun()
    else:
        st.markdown(f"<h3 style='text-align:center; color:#58a6ff;'>🌟 Chào {st.session_state.student_name}!</h3>", unsafe_allow_html=True)
        if st.button("ĐỔI TÊN"):
            st.session_state.name_confirmed = False
            st.rerun()

    st.markdown(f"""
        <div style="background: #161b22; padding: 20px; border-radius: 20px; border: 1px solid #30363d; text-align: center;">
            <p style="margin:0; font-size:14px; color:#8b949e;">ĐIỂM SỐ</p>
            <p class="big-val score-color">{st.session_state.score}</p>
            <div style="height:15px"></div>
            <p style="margin:0; font-size:14px; color:#8b949e;">CHUỖI LỬA</p>
            <p class="big-val streak-color">{st.session_state.streak} 🔥</p>
        </div>
    """, unsafe_allow_html=True)

    st.write("---")
    if st.button("➕ BÀI HỌC MỚI", use_container_width=True, type="primary"):
        st.session_state.current_data = None
        st.session_state.answered_questions = {}
        st.rerun()

# --- 6. GIAO DIỆN CHÍNH ---
st.markdown("<div class='main-title'>🛡️ SMARTLENS AI</div>", unsafe_allow_html=True)
left, right = st.columns([3.8, 1.2])

with right:
    st.markdown("### 📝 GHI CHÚ")
    st.text_area("", height=750, key="notes_fixed", placeholder="Ghi chép tại đây...")

with left:
    tab1, tab2 = st.tabs(["📺 VIDEO YOUTUBE", "📝 VĂN BẢN"])
    
    with tab1:
        st.markdown('<div class="guide-box">💡 <b>Cách dùng:</b> Copy link YouTube có phụ đề, dán vào đây để AI bóc tách nội dung và thẩm định thông tin.</div>', unsafe_allow_html=True)
        url = st.text_input("Link video:", key="yt_url_key")
        if st.button("🚀 PHÂN TÍCH VIDEO"):
            v_id = re.search(r"(?:v=|\/)([a-zA-Z0-9_-]{11})", url)
            if v_id:
                try:
                    ts = YouTubeTranscriptApi.get_transcript(v_id.group(1), languages=['vi', 'en'])
                    run_analysis(" ".join([i['text'] for i in ts]))
                except:
                    st.warning("⚠️ Video không có phụ đề. Vui lòng dán văn bản vào tab bên cạnh!")
    
    with tab2:
        txt = st.text_area("Nội dung cần thẩm định:", height=250, key="txt_input_key")
        if st.button("🔍 THẨM ĐỊNH VĂN BẢN"):
            run_analysis(txt)

    if st.session_state.current_data:
        st.markdown("---")
        st.markdown(f'<div class="check-box">{st.session_state.current_data.get("verification", "")}</div>', unsafe_allow_html=True)
        
        st.markdown("### ✍️ THỬ THÁCH TƯ DUY")
        for i, q in enumerate(st.session_state.current_data.get('questions', [])):
            st.write(f"**Câu {i+1}: {q['q']}**")
            ans = st.radio(f"Chọn đáp án câu {i+1}:", q['options'], key=f"ans_fixed_{i}", index=None)
            
            if ans:
                if ans.startswith(q['correct']):
                    st.success("✅ Chính xác! +10 điểm.")
                    if f"q_{i}" not in st.session_state.answered_questions:
                        st.session_state.score += 10
                        st.session_state.streak += 1
                        st.session_state.answered_questions[f"q_{i}"] = True
                        st.balloons()
                        st.rerun()
                else:
                    st.error("❌ Chưa chính xác. Hãy xem kỹ lại phần phân tích!")
