import os
import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader

# Konfigurasi Halaman
st.set_page_config(page_title="HR Assistant", layout="wide")
st.markdown("<style>[data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)

# Ambil API Key Gemini dari Streamlit Secrets
gemini_key = st.secrets.get("GEMINI_API_KEY") or (st.secrets.get("general") or {}).get("GEMINI_API_KEY")
TARGET_PDF = "CJ LOGISTICS SERVICE INDONESIA_PP.pdf"

if gemini_key:
    genai.configure(api_key=gemini_key)

# Fungsi Membaca PDF (Membaca seluruh halaman)
@st.cache_resource
def get_pdf_text(path):
    if not os.path.exists(path): return None
    reader = PdfReader(path)
    return "\n".join([page.extract_text() for page in reader.pages])

pdf_text = get_pdf_text(TARGET_PDF)

st.title("🏢 HR Policy Assistant")
st.markdown("Asisten HR berbasis Gemini - Membaca seluruh dokumen perusahaan.")

# Chat
user_query = st.chat_input("Tanyakan aturan cuti, PHK, klaim, dll...")

if user_query:
    st.chat_message("user").markdown(user_query)
    with st.chat_message("assistant"):
        with st.spinner("Menganalisis seluruh isi dokumen..."):
            if not gemini_key:
                st.error("⚠️ `GEMINI_API_KEY` belum diset di Streamlit Secrets.")
            elif not pdf_text:
                st.error(f"⚠️ File `{TARGET_PDF}` tidak ditemukan. Pastikan file ada di folder utama.")
            else:
                try:
                    # Menggunakan model yang sudah terbukti jalan di akun Anda
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    # Prompt dengan FULL pdf_text (Tanpa batasan 15000)
                    prompt = f"""
                    Anda adalah Asisten HR PT CJ Logistics Service Indonesia yang profesional dan teliti.
                    Jawablah pertanyaan karyawan HANYA berdasarkan dokumen Peraturan Perusahaan di bawah ini.
                    Jika informasi tidak ditemukan di dalam teks, katakan dengan jujur bahwa informasi tersebut tidak tersedia.
                    Sajikan jawaban secara terstruktur dalam bentuk poin-poin yang rapi.

                    --- DOKUMEN PERATURAN PERUSAHAAN ---
                    {pdf_text}
                    ------------------------------------

                    Pertanyaan Karyawan: {user_query}
                    """
                    
                    response = model.generate_content(prompt)
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"Terjadi kesalahan: {e}")

# Admin
with st.expander("🔐 Mode Admin"):
    if st.text_input("Password:", type="password") == "2273":
        uploaded = st.file_uploader("Upload PDF baru", type=["pdf"])
        if uploaded:
            with open(TARGET_PDF, "wb") as f: f.write(uploaded.getbuffer())
            st.success("Berhasil! Refresh halaman.")

st.markdown("---")
st.markdown("<p style='text-align: center; color: gray; font-size: 13px;'>Developed by <b>iqbalmantam</b></p>", unsafe_allow_html=True)
