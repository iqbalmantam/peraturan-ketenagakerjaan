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

# --- FUNGSI MENCARI MODEL OTOMATIS (Mencegah Error 404 Selamanya) ---
@st.cache_resource
def get_latest_model():
    try:
        # Menanyakan ke API, model apa saja yang tersedia saat ini
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods and 'flash' in m.name:
                return m.name
        return "gemini-1.5-flash" # Fallback jika daftar kosong
    except:
        return "gemini-1.5-flash"

# Fungsi Membaca PDF
@st.cache_resource
def get_pdf_text(path):
    if not os.path.exists(path): return None
    reader = PdfReader(path)
    # Membatasi pembacaan halaman agar RAM tidak jebol
    return "\n".join([page.extract_text() for page in reader.pages[:20]]) 

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
                # Menggunakan model yang ditemukan secara dinamis
                model_name = get_latest_model()
                model = genai.GenerativeModel(model_name)
                
                # Prompt yang ringkas
                prompt = f"Berdasarkan dokumen ini, jawablah: {user_query}. Jika tidak ada, katakan tidak tahu. Dokumen: {pdf_text[:10000]}"
                
                response = model.generate_content(prompt)
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Error pada model {model_name}: {e}. Silakan refresh.")

# Admin
with st.expander("🔐 Mode Admin"):
    if st.text_input("Password:", type="password") == "2273":
        uploaded = st.file_uploader("Upload PDF baru", type=["pdf"])
        if uploaded:
            with open(TARGET_PDF, "wb") as f: f.write(uploaded.getbuffer())
            st.success("Berhasil! Refresh halaman.")
