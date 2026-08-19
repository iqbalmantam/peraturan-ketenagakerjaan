import os
import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader

# Konfigurasi Halaman
st.set_page_config(page_title="HR Assistant", layout="wide")
st.markdown("<style>[data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)

# API Konfigurasi
gemini_key = st.secrets.get("GEMINI_API_KEY")
TARGET_PDF = "CJ LOGISTICS SERVICE INDONESIA_PP.pdf"

if gemini_key:
    genai.configure(api_key=gemini_key)

# Fungsi Membaca PDF
@st.cache_resource
def get_pdf_text(path):
    if not os.path.exists(path): return None
    reader = PdfReader(path)
    return "\n".join([page.extract_text() for page in reader.pages])

pdf_text = get_pdf_text(TARGET_PDF)

st.title("🏢 HR Policy Assistant")

# Chat
user_query = st.chat_input("Tanyakan aturan perusahaan...")

if user_query:
    st.chat_message("user").markdown(user_query)
    with st.chat_message("assistant"):
        if not gemini_key:
            st.error("API Key belum diset di Secrets.")
        elif not pdf_text:
            st.error("File PDF tidak ditemukan.")
        else:
            try:
                # Diperbarui menggunakan gemini-2.0-flash yang aktif dan stabil
                model = genai.GenerativeModel('gemini-2.0-flash')
                
                # Mengirim prompt yang ringkas
                prompt = f"Berdasarkan dokumen ini, jawablah: {user_query}. Jika tidak ada, katakan tidak tahu. Dokumen: {pdf_text[:15000]}"
                
                response = model.generate_content(prompt)
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Error: {e}")

# Admin
with st.expander("🔐 Mode Admin"):
    if st.text_input("Password:", type="password") == "2273":
        uploaded = st.file_uploader("Upload PDF baru", type=["pdf"])
        if uploaded:
            with open(TARGET_PDF, "wb") as f: f.write(uploaded.getbuffer())
            st.success("Berhasil! Refresh halaman.")
