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

# --- FUNGSI AUTO-DETECT MODEL DARI SERVER GOOGLE ---
def generate_gemini_dynamic(prompt_text):
    try:
        # Mengambil daftar model yang aktif dan mendukung generateContent di akun Anda
        available_models = [
            m.name for m in genai.list_models() 
            if 'generateContent' in m.supported_generation_methods
        ]
        
        if not available_models:
            raise Exception("Tidak ada model Gemini yang tersedia untuk akun ini.")
        
        # Menggunakan model pertama yang aktif dari server Google
        selected_model = available_models[0]
        model = genai.GenerativeModel(selected_model)
        response = model.generate_content(prompt_text)
        
        if response and response.text:
            return response.text
        else:
            raise Exception("Respons dari model kosong.")
            
    except Exception as e:
        raise Exception(f"Gagal terhubung ke Gemini: {e}")

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
                    
                    answer = generate_gemini_dynamic(prompt)
                    st.markdown(answer)
                except Exception as e:
                    st.error(f"Terjadi kesalahan: {e}")

# Admin
with st.expander("🔐 Mode Admin"):
    if st.text_input("Password:", type="password", key="admin_pwd") == "2273":
        uploaded = st.file_uploader("Upload PDF baru", type=["pdf"])
        if uploaded:
            with open(TARGET_PDF, "wb") as f: f.write(uploaded.getbuffer())
            st.cache_resource.clear()
            st.success("File berhasil diunggah dan cache dibersihkan! Silakan refresh halaman.")

st.markdown("---")
st.markdown("<p style='text-align: center; color: gray; font-size: 13px;'>Developed by <b>iqbalmantam</b></p>", unsafe_allow_html=True)
