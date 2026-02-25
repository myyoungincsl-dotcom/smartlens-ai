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
        # Lấy danh sách tất cả các model mà Key của bạn được phép dùng
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Ưu tiên chọn các bản flash để có tốc độ nhanh
        for m in models:
            if '1.5-flash' in m: return genai.GenerativeModel(m)
        # Nếu không thấy, chọn model đầu tiên có sẵn
        return genai.GenerativeModel(models[0])
    except Exception as e:
        st.error(f"Không thể kết nối AI: {e}")
        return None

model = get_working_model()

# --- 2. QUẢN LÝ SESSION ---
if 'score' not in st.session_state: st.session_state.score = 0
if 'streak' not in st.session_state: st.session_state.streak = 0
if 'current_data' not in st.session_state: st.session_state.current_data = None
if 'student_name' not in st.session_state: st.session_state.student_name = ""
if 'name_confirmed' not in st.session_state: st.session_state.name_confirmed = False
if 'answered_questions' not in st.session_state: st.session_state.answered_questions = {}

# --- 3. GIAO DIỆN CSS (DESIGN HIỆN ĐẠI) ---
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
        background: #161b22; border-left: 8px solid #58a6ff; padding: 30px; border-radius: 15px; 
        border: 1px solid #30363d; line-height: 1.8; font-size: 18px; box-shadow: 5px 5px 15px rgba(0,0,0,0.3);
    }}
    .guide-box {{ background: #1c2128; padding: 15px; border-radius: 10px; border: 1px dashed #58a6ff; margin-bottom: 20px; }}
</style>
""", unsafe_allow_html=True)

# --- 4. HÀM XỬ LÝ PHÂN TÍCH (YÊU CẦU DÀI & SÂU) ---
def run_analysis(text):
    if not text or model is None: return
    # Giới hạn text đầu vào đủ để AI phân tích sâu mà không quá tải
    input_content = text[:3500].replace('"', "'")
    with st.spinner("🕵️ SmartLens đang thực hiện thẩm định đa chiều..."):
        try:
            prompt = f"""
            Hãy đóng vai một chuyên gia phân tích tư duy. Phân tích nội dung sau một cách CHI TIẾT và DÀI DÒNG:
            1. XÁC THỰC: Kiểm tra tính đúng đắn, logic của thông tin.
            2. PHẢN BIỆN: Chỉ ra các lỗ hổng hoặc góc nhìn bị bỏ qua.
            3. MỞ RỘNG: Đưa ra các bài học thực tế và liên hệ thực tiễn sâu sắc.
            Yêu cầu định dạng: Sử dụng <b>, <br>, <li> để trình bày cực kỳ chuyên nghiệp và dễ đọc.
            Sau đó tạo 3 câu hỏi trắc nghiệm tư duy sâu (A, B, C, D).
            TRẢ VỀ JSON:
            {{
                "verification": "nội dung phân tích chi tiết và dài dòng ở đây",
                "questions": [
                    {{"q": "câu hỏi", "options": ["A. x", "B. y", "C. z", "D. t"], "correct": "A"}}
                ]
            }}
            NỘI DUNG: {input_content}
            """
            response = model.generate_content(prompt)
            match = re.search(r"\{.*\}", response.text, re.DOTALL)
            if match:
                # Làm sạch chuỗi trước khi parse
                clean_json = match.group().replace('\n', ' ').replace('\r', '')
                st.session_state.current_data = json.loads(clean_json)
                st.session_state.answered_questions = {}
                st.rerun()
        except Exception as e:
            st.error(f"Lỗi AI: {e}. Thử lại với đoạn văn bản ngắn hơn chút nhé.")

# --- 5. SIDEBAR (KHÓA TÊN & ĐIỂM) ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🛡️ HÀNH TRÌNH</h2>", unsafe_allow_html=True)
    
    if not st.session_state.name_confirmed:
        name_input = st.text_input("Nhập tên học sinh:")
        if st.button("XÁC NHẬN", use_container_width=True):
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
        # Reset các ô nhập liệu bằng cách xóa query params hoặc rerun
        st.rerun()

# --- 6. GIAO DIỆN CHÍNH ---
st.markdown("<div class='main-title'>🛡️ SMARTLENS AI</div>", unsafe_allow_html=True)
left, right = st.columns([3.8, 1.2])

with right:
    st.markdown("### 📝 GHI CHÚ")
    st.text_area("", height=750, key="note_v4", placeholder="Ghi lại kiến thức tại đây...")

with left:
    tab1, tab2 = st.tabs(["📺 VIDEO YOUTUBE", "📝 VĂN BẢN TỰ CHỌN"])
    
    with tab1:
        st.markdown('<div class="guide-box">💡 <b>Hướng dẫn Video:</b> Copy link YouTube có phụ đề, dán vào đây và hệ thống sẽ tự động bóc tách lời thoại để thẩm định tri thức.</div>', unsafe_allow_html=True)
        url = st.text_input("Dán link YouTube:", key="yt_url")
        if st.button("🚀 PHÂN TÍCH VIDEO"):
            v_id = re.search(r"(?:v=|\/)([a-zA-Z0-9_-]{11})", url)
            if v_id:
                try:
                    ts = YouTubeTranscriptApi.get_transcript(v_id.group(1), languages=['vi', 'en'])
                    run_analysis(" ".join([i['text'] for i in ts]))
                except:
                    st.warning("⚠️ Video này không có phụ đề. Hãy dùng tab Văn Bản!")
            else: st.error("Link không hợp lệ!")
    
    with tab2:
        txt = st.text_area("Dán nội dung cần thẩm định:", height=250, key="txt_input")
        if st.button("🔍 THẨM ĐỊNH VĂN BẢN"):
            run_analysis(txt)

    if st.session_state.current_data:
        st.markdown("---")
        st.markdown("### 🕵️ PHÂN TÍCH CHUYÊN SÂU")
        st.markdown(f'<div class="check-box">{st.session_state.current_data.get("verification", "")}</div>', unsafe_allow_html=True)
        
        st.markdown("### ✍️ THỬ THÁCH TƯ DUY")
        for i, q in enumerate(st.session_state.current_data.get('questions', [])):
            st.write(f"**Câu {i+1}: {q['q']}**")
            ans = st.radio(f"Chọn đáp án cho câu {i+1}:", q['options'], key=f"ans_v4_{i}", index=None)
            
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
                    st.error("❌ Chưa đúng, hãy đọc kỹ lại phần phân tích!")
