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

@st.cache_resource
def load_pdf_text(path):
    if not os.path.exists(path):
        return ""
    reader = PdfReader(path)
    return "\n".join([page.extract_text() for page in reader.pages])

pdf_content = load_pdf_text(TARGET_PDF)

st.title("🏢 HR Policy Assistant")

user_query = st.chat_input("Tanyakan aturan perusahaan...")

if user_query:
    st.chat_message("user").markdown(user_query)
    with st.chat_message("assistant"):
        with st.spinner("Mencari jawaban..."):
            if not cerebras_api_key:
                st.error("API Key belum diset.")
            elif not pdf_content:
                st.error("File PDF tidak ditemukan.")
            else:
                try:
                    # Langsung panggil model yang pasti ada
                    client = Cerebras(api_key=cerebras_api_key)
                    
                    prompt = f"""
                    Anda adalah Asisten HR PT CJ Logistics Service Indonesia yang profesional.
                    Jawablah pertanyaan karyawan HANYA berdasarkan dokumen di bawah.
                    Jika tidak ada, katakan 'Informasi tidak ditemukan'.

                    Dokumen: {pdf_content[:15000]}
                    Pertanyaan: {user_query}
                    """

                    # Menggunakan llama3.1-8b secara eksplisit
                    response = client.chat.completions.create(
                        model="llama3.1-8b", 
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=500,
                        temperature=0.0
                    )
                    
                    st.markdown(response.choices[0].message.content)
                except Exception as e:
                    st.error(f"Error: {e}")

# Admin
with st.expander("🔐 Mode Admin"):
    if st.text_input("Password:", type="password") == "2273":
        uploaded = st.file_uploader("Upload PDF baru", type=["pdf"])
        if uploaded:
            with open(TARGET_PDF, "wb") as f: f.write(uploaded.getbuffer())
            st.success("Berhasil! Refresh halaman.")
