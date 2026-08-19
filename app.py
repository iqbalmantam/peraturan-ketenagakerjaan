import os
import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader

# Konfigurasi Halaman Streamlit
st.set_page_config(page_title="HR Policy Assistant (Gemini)", page_icon="🏢", layout="wide")

# Sembunyikan Sidebar
st.markdown("<style>[data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)

# Ambil API Key Gemini dari Streamlit Secrets
gemini_api_key = st.secrets.get("GEMINI_API_KEY") or (st.secrets.get("general") or {}).get("GEMINI_API_KEY")
admin_pass_secret = st.secrets.get("ADMIN_PASSWORD") or (st.secrets.get("general") or {}).get("ADMIN_PASSWORD") or "2273"

if gemini_api_key:
    genai.configure(api_key=gemini_api_key)

TARGET_PDF = "CJ LOGISTICS SERVICE INDONESIA_PP.pdf"

st.title("🏢 HR Policy & Employee Handbook Q&A Assistant")
st.markdown("Asisten cerdas berbasis Google Gemini untuk menjawab aturan perusahaan secara akurat.")

tab1, tab2, tab3 = st.tabs(["💬 Chat Karyawan", "📥 Download Dokumen", "🔐 Mode Admin"])

# Fungsi membaca teks PDF secara efisien (Hemat RAM)
@st.cache_resource
def load_pdf_text(pdf_path):
    if not os.path.exists(pdf_path):
        return ""
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text

pdf_content = load_pdf_text(TARGET_PDF)

# --- FUNGSI PENCARI MODEL GEMINI OTOMATIS (Mencegah Error 404) ---
def get_working_gemini_model():
    try:
        for m in genai.list_models():
            if "generateContent" in m.supported_generation_methods and "flash" in m.name.lower():
                return m.name
        return "gemini-1.5-flash"
    except Exception:
        return "gemini-1.5-flash"

# --- TAB 1: CHAT KARYAWAN ---
with tab1:
    st.subheader("💬 Tanya Jawab Kebijakan Perusahaan")
    
    user_query = st.chat_input("Tanyakan tentang aturan cuti, PHK, klaim, dll...")
    
    if user_query:
        st.chat_message("user").markdown(user_query)
        
        with st.chat_message("assistant"):
            with st.spinner("Gemini sedang menganalisis dokumen perusahaan..."):
                try:
                    if not gemini_api_key:
                        st.error("⚠️ `GEMINI_API_KEY` belum dikonfigurasi di Streamlit Secrets.")
                    elif not pdf_content:
                        st.error(f"⚠️ File PDF `{TARGET_PDF}` tidak ditemukan di repositori.")
                    else:
                        # Memilih model yang aktif secara otomatis
                        model_name = get_working_gemini_model()
                        model = genai.GenerativeModel(model_name)
                        
                        prompt = f"""
                        Anda adalah Asisten HR PT CJ Logistics Service Indonesia yang profesional, teliti, dan ramah.
                        Jawablah pertanyaan karyawan HANYA berdasarkan dokumen Peraturan Perusahaan di bawah ini.
                        Jika informasi tidak ditemukan di dalam teks, katakan dengan jujur bahwa informasi tersebut tidak tersedia.
                        Sajikan jawaban secara terstruktur dalam bentuk poin-poin yang rapi.

                        --- DOKUMEN PERATURAN PERUSAHAAN ---
                        {pdf_content}
                        ------------------------------------

                        Pertanyaan Karyawan: {user_query}
                        """
                        
                        response = model.generate_content(prompt)
                        st.markdown(response.text)
                except Exception as e:
                    st.error(f"Terjadi kesalahan: {e}")

# --- TAB 2: DOWNLOAD DOKUMEN ---
with tab2:
    st.subheader("📥 Unduh Peraturan Perusahaan")
    if os.path.exists(TARGET_PDF):
        with open(TARGET_PDF, "rb") as f:
            st.download_button(
                label="📥 Download Peraturan Perusahaan (PDF)",
                data=f.read(),
                file_name=TARGET_PDF,
                mime="application/pdf",
            )
    else:
        st.warning(f"⚠️ File `{TARGET_PDF}` tidak ditemukan.")

# --- TAB 3: MODE ADMIN ---
with tab3:
    st.subheader("🔐 Panel Admin")
    pwd = st.text_input("Masukkan Password Admin:", type="password")
    if pwd == admin_pass_secret:
        uploaded_file = st.file_uploader("Upload PDF Peraturan Baru", type=["pdf"])
        if uploaded_file:
            with open(TARGET_PDF, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success("File berhasil diunggah! Silakan refresh halaman.")

st.markdown("---")
st.markdown("<p style='text-align: center; color: gray; font-size: 13px;'>Developed by <b>iqbalmantam</b></p>", unsafe_allow_html=True)
