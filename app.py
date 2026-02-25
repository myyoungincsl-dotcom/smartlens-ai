import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import re
import json

# --- 1. CẤU HÌNH AI BẢO MẬT ---
# Lấy Key từ Settings -> Secrets của Streamlit
API_KEY = st.secrets.get("GEMINI_API_KEY", "")

if API_KEY:
    genai.configure(api_key=API_KEY)
    # Dùng Flash để nhanh và bền (ít bị lỗi Quota)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("❌ LỖI: Chưa có API Key trong Secrets. Hãy dán GEMINI_API_KEY vào Settings của Streamlit Cloud.")
    st.stop()

# --- 2. QUẢN LÝ TRẠNG THÁI ---
if 'score' not in st.session_state: st.session_state.score = 0
if 'streak' not in st.session_state: st.session_state.streak = 0
if 'history' not in st.session_state: st.session_state.history = []
if 'current_data' not in st.session_state: st.session_state.current_data = None
if 'student_name' not in st.session_state: st.session_state.student_name = ""
if 'answered' not in st.session_state: st.session_state.answered = set()

# --- 3. CSS GIAO DIỆN CHUẨN ---
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

# --- 4. HÀM XỬ LÝ CHÍNH ---
def run_analysis(text, title="Bài học"):
    if not text: return
    # Cắt ngắn 3000 ký tự để tránh lỗi 504 Deadline Exceeded
    clean_text = text[:3000]
    with st.spinner("SmartLens AI đang thẩm định tri thức..."):
        try:
            prompt = f"""
            Hãy đóng vai chuyên gia thẩm định thông tin. Phân tích nội dung sau bằng tiếng Việt:
            1. Xác thực (Sự thật). 2. Phản biện (Góc nhìn khác). 3. Mở rộng (Ứng dụng).
            Sau đó tạo 3 câu hỏi trắc nghiệm. 
            TRẢ VỀ ĐỊNH DẠNG JSON THUẦN TÚY:
            {{
                "verification": "nội dung phân tích (dùng HTML <b> <br> để xuống dòng)",
                "questions": [
                    {{"q": "Câu hỏi", "options": ["A. x", "B. y", "C. z", "D. t"], "correct": "A"}}
                ]
            }}
            Nội dung: {clean_text}
            """
            response = model.generate_content(prompt)
            # Lọc lấy phần JSON
            json_match = re.search(r"\{.*\}", response.text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                st.session_state.current_data = data
                st.session_state.history.append({"title": title[:25], "data": data})
                st.session_state.answered = set()
                st.rerun()
        except Exception as e:
            st.error(f"Lỗi AI hoặc Quota: {e}")

# --- 5. SIDEBAR (PROFILE & LỊCH SỬ) ---
with st.sidebar:
    st.markdown("## 🛡️ SMARTLENS AI")
    if not st.session_state.student_name:
        st.session_state.student_name = st.text_input("👤 Nhập tên bạn:")
    else:
        st.markdown(f"Học sinh: **{st.session_state.student_name}**")

    st.markdown(f"""
        <div style="text-align: center; background: #161b22; padding: 20px; border-radius: 15px; border: 2px solid #58a6ff;">
            <p style="font-size: 14px; color: #8b949e;">ĐIỂM SỐ</p>
            <h1 style="color: #f2cc60; font-size: 60px !important; margin: 0;">{st.session_state.score}</h1>
            <p style="font-size: 14px; color: #8b949e;">STREAK</p>
            <p class="streak-val">{st.session_state.streak} 🔥</p>
        </div>
    """, unsafe_allow_html=True)

    if st.button("➕ BÀI HỌC MỚI", use_container_width=True, type="primary"):
        st.session_state.current_data = None
        st.rerun()
    
    st.markdown("---")
    st.write("📚 LỊCH SỬ BÀI HỌC")
    for i, h in enumerate(st.session_state.history):
        if st.button(f"📖 {h['title']}", key=f"hist_{i}", use_container_width=True):
            st.session_state.current_data = h['data']
            st.rerun()

# --- 6. GIAO DIỆN CHÍNH ---
st.markdown("<h1>🛡️ THẨM ĐỊNH CHUYÊN SÂU</h1>", unsafe_allow_html=True)
m_col, n_col = st.columns([3.8, 1.2])

with n_col:
    st.markdown("### 📝 GHI CHÚ (750px)")
    st.text_area("", height=750, key="main_notes", placeholder="Ghi chép tại đây...")

with m_col:
    tab1, tab2 = st.tabs(["📺 KIỂM CHỨNG VIDEO", "📝 KIỂM CHỨNG VĂN BẢN"])
    
    with tab1:
        url = st.text_input("Dán link YouTube:")
        if st.button("🚀 PHÂN TÍCH VIDEO", type="primary"):
            v_id = re.search(r"(?:v=|\/)([a-zA-Z0-9_-]{11})", url)
            if v_id:
                try:
                    ts = YouTubeTranscriptApi.get_transcript(v_id.group(1), languages=['vi', 'en'])
                    run_analysis(" ".join([i['text'] for i in ts]), title=f"Video {v_id.group(1)}")
                except:
                    st.warning("⚠️ YouTube không cho lấy phụ đề. Hãy dùng Tab Văn Bản!")
            else:
                st.error("Link YouTube không hợp lệ.")

    with tab2:
        txt_in = st.text_area("Dán văn bản cần thẩm định:", height=300)
        if st.button("🔍 KIỂM CHỨNG NGAY", type="primary"):
            run_analysis(txt_in, title=txt_in[:20])

    if st.session_state.current_data:
        data = st.session_state.current_data
        st.markdown("---")
        st.markdown(f'<div class="check-box">{data.get("verification", "")}</div>', unsafe_allow_html=True)
        
        st.markdown("### ✍️ THỬ THÁCH TƯ DUY")
        for idx, q in enumerate(data.get('questions', [])):
            st.write(f"**Câu {idx+1}: {q['q']}**")
            choice = st.radio(f"Chọn đáp án câu {idx+1}:", q['options'], key=f"q_{idx}", index=None)
            if choice:
                if choice.startswith(q['correct']):
                    if f"q_{idx}" not in st.session_state.answered:
                        st.session_state.score += 10
                        st.session_state.streak += 1
                        st.session_state.answered.add(f"q_{idx}")
                        st.success("Chính xác! +10 điểm")
                        st.rerun()
                    else:
                        st.info("Câu này bạn đã trả lời đúng rồi.")
                else:
                    st.error("Chưa đúng, hãy thử lại!")
