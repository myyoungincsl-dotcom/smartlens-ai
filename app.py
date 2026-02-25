import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import re
import json

# --- 1. CẤU HÌNH AI CHI TIẾT ---
API_KEY = st.secrets.get("GEMINI_API_KEY", "")

# Thiết lập Model với cấu hình sáng tạo cao để phân tích dài và sâu
generation_config = {
  "temperature": 0.9,
  "top_p": 0.95,
  "top_k": 40,
  "max_output_tokens": 4096, # Cho phép AI viết cực dài
}

if API_KEY:
    try:
        genai.configure(api_key=API_KEY)
        # Sử dụng bản 1.5-Flash (Nhanh, mạnh, ít lỗi 429 nhất)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=generation_config
        )
    except:
        st.error("⚠️ API Key có vấn đề, nhưng App vẫn sẽ chạy giao diện cho bạn!")
else:
    st.warning("⚠️ Chưa dán API Key vào Secrets.")

# --- 2. QUẢN LÝ DỮ LIỆU ---
if 'score' not in st.session_state: st.session_state.score = 0
if 'streak' not in st.session_state: st.session_state.streak = 0
if 'history' not in st.session_state: st.session_state.history = []
if 'current_data' not in st.session_state: st.session_state.current_data = None

# --- 3. GIAO DIỆN CHUẨN 100% (70px - 80px - 750px) ---
st.set_page_config(page_title="SmartLens AI Pro", layout="wide")
st.markdown(f"""
<style>
    .stApp {{ background-color: #0d1117; color: #c9d1d9; }}
    /* Tiêu đề 70px */
    .main-title {{ font-size: 70px !important; color: #58a6ff !important; text-align: center; font-weight: 900; margin-bottom: 20px; }}
    /* Streak 80px */
    .streak-val {{ color: #ff4b4b !important; font-size: 80px !important; font-weight: 900 !important; text-align: center; margin: 0; }}
    /* Ghi chú 750px */
    .note-box textarea {{ height: 750px !important; background-color: #161b22 !important; color: #e6edf3 !important; border: 1px solid #30363d !important; border-radius: 10px; }}
    .check-box {{ background-color: #161b22; border-left: 10px solid #58a6ff; padding: 25px; border-radius: 15px; border: 1px solid #30363d; line-height: 1.8; font-size: 18px; }}
</style>
""", unsafe_allow_html=True)

# --- 4. HÀM PHÂN TÍCH CHI TIẾT (DÀI DÒNG THEO Ý BẠN) ---
def run_analysis(text, title="Bài học"):
    if not text: return
    with st.spinner("🛡️ SmartLens đang thực hiện thẩm định chuyên sâu..."):
        try:
            # Prompt yêu cầu phân tích cực kỳ chi tiết
            prompt = f"""
            Hãy đóng vai một Chuyên gia Thẩm định Tư duy và Phê phán. 
            Phân tích nội dung sau đây một cách CHI TIẾT, DÀI DÒNG và ĐA CHIỀU:
            1. XÁC THỰC (Fact-check): Kiểm tra tính đúng đắn, các số liệu, nguồn tin.
            2. PHẢN BIỆN (Critical Thinking): Chỉ ra các điểm chưa hợp lý, các thiên kiến có thể có.
            3. MỞ RỘNG (Expansion): Liên hệ thực tế cuộc sống, đưa ra lời khuyên ứng dụng.
            Yêu cầu định dạng: Sử dụng các thẻ HTML <b>, <br>, <li> để nội dung trông chuyên nghiệp.
            
            Cuối cùng, tạo 3 câu hỏi trắc nghiệm cực hay để kiểm tra tư duy người xem.
            TRẢ VỀ JSON THUẦN TÚY:
            {{
                "verification": "nội dung phân tích cực kỳ dài và chi tiết ở đây",
                "questions": [
                    {{"q": "Câu hỏi 1", "options": ["A", "B", "C", "D"], "correct": "A"}}
                ]
            }}
            NỘI DUNG CẦN PHÂN TÍCH: {text[:3500]}
            """
            response = model.generate_content(prompt)
            json_match = re.search(r"\{.*\}", response.text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                st.session_state.current_data = data
                st.session_state.history.append({"title": title[:20], "data": data})
                st.rerun()
        except Exception as e:
            st.error(f"Lỗi AI: {e}. Vui lòng kiểm tra lại API Key hoặc dán văn bản ngắn hơn.")

# --- 5. BỐ CỤC CHÍNH ---
st.markdown("<div class='main-title'>🛡️ THẨM ĐỊNH SMARTLENS</div>", unsafe_allow_html=True)

col_left, col_right = st.columns([3.8, 1.2])

with col_right:
    st.markdown("### 📝 GHI CHÚ BÀI HỌC")
    st.text_area("", height=750, placeholder="Ghi chép kiến thức tại đây...", key="notes_area")

with col_left:
    st.markdown(f"""<div style="background:#161b22; padding:15px; border-radius:15px; border:1px solid #30363d; margin-bottom:20px;">
        <p style="text-align:center; margin:0; color:#8b949e;">CHUỖI HỌC TẬP (STREAK)</p>
        <p class="streak-val">{st.session_state.streak} 🔥</p>
    </div>""", unsafe_allow_html=True)

    t1, t2 = st.tabs(["📺 PHÂN TÍCH VIDEO", "📝 PHÂN TÍCH VĂN BẢN"])
    
    with t1:
        url = st.text_input("Nhập Link YouTube:")
        if st.button("🚀 PHÂN TÍCH NGAY", type="primary"):
            v_id = re.search(r"(?:v=|\/)([a-zA-Z0-9_-]{11})", url)
            if v_id:
                try:
                    ts = YouTubeTranscriptApi.get_transcript(v_id.group(1), languages=['vi', 'en'])
                    run_analysis(" ".join([i['text'] for i in ts]), title=f"Video {v_id.group(1)}")
                except:
                    st.warning("YouTube chặn lấy phụ đề. Hãy dùng văn bản thay thế!")
    
    with t2:
        txt = st.text_area("Dán nội dung cần thẩm định:", height=250)
        if st.button("🔍 THẨM ĐỊNH KIẾN THỨC", type="primary"):
            run_analysis(txt, title="Văn bản")

    if st.session_state.current_data:
        d = st.session_state.current_data
        st.markdown("---")
        st.markdown("### 🕵️ KẾT QUẢ PHÂN TÍCH CHI TIẾT")
        st.markdown(f'<div class="check-box">{d.get("verification", "")}</div>', unsafe_allow_html=True)
        
        st.markdown("### ✍️ KIỂM TRA TƯ DUY")
        for i, q in enumerate(d.get('questions', [])):
            st.write(f"**{i+1}. {q['q']}**")
            ans = st.radio(f"Chọn đáp án câu {i+1}:", q['options'], key=f"q_{i}", index=None)
            if ans and ans.startswith(q['correct']):
                st.success("Tuyệt vời! +10 điểm")
                if f"done_{i}" not in st.session_state:
                    st.session_state.score += 10
                    st.session_state.streak += 1
                    st.session_state.update({f"done_{i}": True})
