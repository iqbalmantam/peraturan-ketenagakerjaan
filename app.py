import os
import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
from pathlib import Path

# Konfigurasi Halaman
st.set_page_config(page_title="HR Policy Assistant", layout="wide")

# CSS untuk menyembunyikan header/ikon bawaan Streamlit (GitHub, Share, Menu, dll)
st.markdown("""
    <style>
    [data-testid="stHeader"] {
        display: none;
    }
    </style>
""", unsafe_allow_html=True)

# Ambil API Key Gemini dari Streamlit Secrets
gemini_key = st.secrets.get("GEMINI_API_KEY") or (st.secrets.get("general") or {}).get("GEMINI_API_KEY")
TARGET_PDF = "CJ LOGISTICS SERVICE INDONESIA_PP.pdf"
file_path = Path(__file__).parent / TARGET_PDF

if gemini_key:
    genai.configure(api_key=gemini_key)

# Fungsi Membaca PDF secara lokal
@st.cache_resource
def get_pdf_text(path):
    if not path.exists(): return ""
    try:
        reader = PdfReader(path)
        return "\n".join([page.extract_text() for page in reader.pages])
    except Exception:
        return ""

pdf_text = get_pdf_text(file_path)

st.title("🏢 HR Policy Assistant")
st.markdown("Asisten cerdas untuk informasi Peraturan Perusahaan PT CJ Logistics Service Indonesia.")

# Inisialisasi Riwayat Percakapan
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- MENU UTAMA ---
tab1, tab2 = st.tabs(["💬 Tanya Jawab AI", "📖 Baca Peraturan Perusahaan"])

with tab1:
    st.markdown("### Kolom Pertanyaan")
    
    # Grid Tombol Cepat
    st.markdown("💡 **Pilih topik pertanyaan populer:**")
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
    
    # Form input manual
    with st.form(key="query_form", clear_on_submit=True):
        user_query = st.text_input("Atau ketik pertanyaan Anda sendiri di sini:")
        submit_btn = st.form_submit_button("Kirim Pertanyaan")

    target_query = clicked_query if clicked_query else (user_query if submit_btn else None)

    # Menampilkan riwayat chat lama
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Proses Chat Streaming
    if target_query:
        st.session_state.messages.append({"role": "user", "content": target_query})
        with st.chat_message("user"):
            st.markdown(target_query)
            
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            try:
                if not pdf_text:
                    st.error("File PDF kosong atau gagal dibaca.")
                else:
                    model = genai.GenerativeModel('gemini-3.6-flash')
                    prompt = f"""
                    Anda adalah Asisten HR PT CJ Logistics Service Indonesia yang profesional dan teliti.
                    Jawablah pertanyaan karyawan HANYA berdasarkan dokumen Peraturan Perusahaan di bawah ini.
                    Wajib sebutkan nomor pasal, bab, atau bagian dokumen secara spesifik (contoh: Pasal X ayat Y).
                    Jika informasi tidak ditemukan, katakan dengan jujur bahwa informasi tersebut tidak tersedia.
                    Sajikan jawaban secara terstruktur dalam bentuk poin-poin yang rapi.

                    --- DOKUMEN PERATURAN PERUSAHAAN ---
                    {pdf_text}
                    ------------------------------------

                    Pertanyaan Karyawan: {target_query}
                    """
                    
                    # Streaming Response
                    response = model.generate_content(prompt, stream=True)
                    for chunk in response:
                        if chunk.text:
                            full_response += chunk.text
                            message_placeholder.markdown(full_response + "▌")
                    
                    message_placeholder.markdown(full_response)
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
            except Exception as e:
                st.error(f"Terjadi kesalahan: {e}")

with tab2:
    st.subheader("📖 Dokumen Peraturan Perusahaan")
    st.markdown("Anda dapat mengunduh dokumen lengkap Peraturan Perusahaan melalui tombol di bawah ini:")
    if file_path.exists():
        with open(file_path, "rb") as f:
            st.download_button("📥 Download Dokumen Peraturan Perusahaan (PDF)", f, file_name=TARGET_PDF, mime="application/pdf")
    else:
        st.error(f"File PDF `{TARGET_PDF}` tidak ditemukan.")

# Admin
with st.expander("🔐 Mode Admin"):
    if st.text_input("Password:", type="password", key="admin_pwd") == "2273":
        uploaded = st.file_uploader("Upload PDF baru", type=["pdf"])
        if uploaded:
            with open(file_path, "wb") as f: 
                f.write(uploaded.getbuffer())
            st.cache_resource.clear()
            st.success("File berhasil diunggah! Silakan refresh halaman.")

# Watermark kembali dipasang di bagian bawah
st.markdown("---")
st.markdown("<p style='text-align: center; color: gray; font-size: 13px;'>Developed by <b>iqbalmantam</b></p>", unsafe_allow_html=True)
