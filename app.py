import os
import streamlit as st
import google.generativeai as genai
from pathlib import Path

# Konfigurasi Halaman
st.set_page_config(page_title="HR Policy Assistant", layout="wide")

# Ambil API Key Gemini
gemini_key = st.secrets.get("GEMINI_API_KEY") or (st.secrets.get("general") or {}).get("GEMINI_API_KEY")
TARGET_PDF = "CJ LOGISTICS SERVICE INDONESIA_PP.pdf"
file_path = Path(__file__).parent / TARGET_PDF

if gemini_key:
    genai.configure(api_key=gemini_key)

st.title("🏢 HR Policy Assistant")
st.markdown("Asisten cerdas yang kini dioptimasi dengan **Native Document Processing** untuk respons instan.")

# --- OPTIMASI: UPLOAD FILE KE SERVER GOOGLE (SEKALI SAJA) ---
@st.cache_resource(show_spinner=False)
def get_gemini_file(path):
    if not path.exists():
        return None
    try:
        # Mengunggah file ke server Google agar diproses cepat (Native PDF)
        return genai.upload_file(path)
    except Exception as e:
        st.error(f"Gagal mengunggah file ke Gemini: {e}")
        return None

# Panggil fungsi upload di awal
gemini_file = get_gemini_file(file_path)

if "messages" not in st.session_state:
    st.session_state.messages = []

tab1, tab2 = st.tabs(["💬 Tanya Jawab AI", "📖 Baca Peraturan Perusahaan"])

with tab1:
    st.markdown("### Kolom Pertanyaan")
    
    # Grid Tombol Cepat
    quick_questions = [
        {"label": "📅 Cuti Tahunan", "prompt": "Berapa jatah cuti tahunan dan bagaimana ketentuannya?"},
        {"label": "🏥 Klaim Pengobatan", "prompt": "Bagaimana aturan dan prosedur klaim pengobatan?"},
        {"label": "📝 Ketentuan PHK", "prompt": "Apa saja ketentuan dan prosedur PHK?"},
        {"label": "⏰ Jam Kerja", "prompt": "Bagaimana aturan mengenai jam kerja dan lembur?"},
        {"label": "⚠️ Sanksi Disiplin", "prompt": "Apa saja jenis sanksi disiplin bagi karyawan?"},
        {"label": "✈️ Perjalanan Dinas", "prompt": "Bagaimana kebijakan terkait perjalanan dinas?"}
    ]
    
    cols = st.columns(3)
    clicked_query = None
    for i, q in enumerate(quick_questions):
        if cols[i % 3].button(q["label"], use_container_width=True):
            clicked_query = q["prompt"]

    st.markdown("---")
    
    with st.form(key="query_form", clear_on_submit=True):
        user_query = st.text_input("Atau ketik pertanyaan sendiri:")
        submit_btn = st.form_submit_button("Kirim Pertanyaan")

    target_query = clicked_query if clicked_query else (user_query if submit_btn else None)

    if target_query:
        st.session_state.messages.append({"role": "user", "content": target_query})
        with st.spinner("Mencari jawaban (Optimized)..."):
            try:
                if not gemini_file:
                    answer = "File PDF tidak terdeteksi di server. Mohon hubungi admin."
                else:
                    model = genai.GenerativeModel('gemini-3.6-flash')
                    
                    # Cukup kirim file yang sudah di-upload + prompt
                    response = model.generate_content([
                        gemini_file, 
                        f"Anda adalah Asisten HR PT CJ Logistics Service Indonesia. Jawablah berdasarkan dokumen yang dilampirkan. Wajib sebutkan Pasal/Bab rujukan. Pertanyaan: {target_query}"
                    ])
                    answer = response.text
            except Exception as e:
                answer = f"Terjadi kesalahan saat menghubungi server: {e}"
            
            st.session_state.messages.append({"role": "assistant", "content": answer})
            st.rerun()

    for msg in reversed(st.session_state.messages):
        if msg["role"] == "user":
            st.markdown(f"**👤 Anda:** {msg['content']}")
        else:
            st.markdown(f"**🤖 Asisten HR:**\n{msg['content']}")
        st.markdown("---")

with tab2:
    st.markdown("Anda dapat mengunduh dokumen lengkap Peraturan Perusahaan:")
    if file_path.exists():
        with open(file_path, "rb") as f:
            st.download_button("📥 Download PDF", f, file_name=TARGET_PDF, mime="application/pdf")

# Admin
with st.expander("🔐 Mode Admin"):
    if st.text_input("Password:", type="password", key="admin_pwd") == "2273":
        uploaded = st.file_uploader("Upload PDF baru", type=["pdf"])
        if uploaded:
            with open(file_path, "wb") as f: f.write(uploaded.getbuffer())
            st.cache_resource.clear()
            st.success("File diperbarui! Refresh halaman.")
