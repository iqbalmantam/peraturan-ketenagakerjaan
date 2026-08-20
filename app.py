import os
import streamlit as st
from cerebras.cloud.sdk import Cerebras
from pypdf import PdfReader

# Konfigurasi Halaman
st.set_page_config(page_title="HR Assistant (Cerebras)", layout="wide")
st.markdown("<style>[data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)

# Ambil API Key Cerebras dari Secrets
cerebras_api_key = st.secrets.get("CEREBRAS_API_KEY") or (st.secrets.get("general") or {}).get("CEREBRAS_API_KEY")
admin_pass_secret = st.secrets.get("ADMIN_PASSWORD") or (st.secrets.get("general") or {}).get("ADMIN_PASSWORD") or "2273"

TARGET_PDF = "CJ LOGISTICS SERVICE INDONESIA_PP.pdf"

# Fungsi Membaca PDF secara efisien (Hemat RAM)
@st.cache_resource
def load_pdf_text(path):
    if not os.path.exists(path):
        return ""
    reader = PdfReader(path)
    return "\n".join([page.extract_text() for page in reader.pages])

pdf_content = load_pdf_text(TARGET_PDF)

st.title("🏢 HR Policy Assistant (Cerebras Powered)")
st.markdown("Asisten cerdas berkecepatan tinggi dengan infrastruktur resmi Cerebras.")

# --- CHAT KARYAWAN ---
user_query = st.chat_input("Tanyakan aturan cuti, PHK, klaim, dll...")

if user_query:
    st.chat_message("user").markdown(user_query)
    with st.chat_message("assistant"):
        with st.spinner("Mencari jawaban kilat..."):
            if not cerebras_api_key:
                st.error("⚠️ `CEREBRAS_API_KEY` belum diset di Streamlit Secrets.")
            elif not pdf_content:
                st.error(f"⚠️ File PDF `{TARGET_PDF}` tidak ditemukan di repositori.")
            else:
                try:
                    # Menggunakan SDK resmi Cerebras (Tanpa perantara LangChain)
                    client = Cerebras(api_key=cerebras_api_key)
                    
                    prompt = f"""
                    Anda adalah Asisten HR PT CJ Logistics Service Indonesia yang profesional dan teliti.
                    Jawablah pertanyaan karyawan HANYA berdasarkan dokumen Peraturan Perusahaan di bawah ini.
                    Jika tidak ada di teks, katakan informasi tidak tersedia.
                    Sajikan dalam bentuk poin-poin rapi.

                    Dokumen Perusahaan:
                    {pdf_content[:15000]}

                    Pertanyaan Karyawan: {user_query}
                    """

                    response = client.chat.completions.create(
                        model="llama3.1-8b",  # Model standar resmi Cerebras
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=500,
                        temperature=0.0
                    )
                    
                    st.markdown(response.choices[0].message.content)
                    
                except Exception as e:
                    st.error(f"Terjadi kesalahan pada Cerebras: {e}")

# --- MODE ADMIN ---
with st.expander("🔐 Mode Admin"):
    pwd = st.text_input("Password Admin:", type="password")
    if pwd == admin_pass_secret:
        uploaded = st.file_uploader("Upload PDF Peraturan Baru", type=["pdf"])
        if uploaded:
            with open(TARGET_PDF, "wb") as f:
                f.write(uploaded.getbuffer())
            st.success("File berhasil diunggah! Silakan Refresh halaman.")

st.markdown("---")
st.markdown("<p style='text-align: center; color: gray; font-size: 13px;'>Developed by <b>iqbalmantam</b></p>", unsafe_allow_html=True)
