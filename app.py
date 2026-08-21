import os
import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
from pathlib import Path

# Konfigurasi Halaman
st.set_page_config(page_title="UU No. 6 Tahun 2023 Assistant", layout="wide")

# CSS untuk menyembunyikan header/ikon bawaan Streamlit
st.markdown("""
    <style>
    [data-testid="stHeader"] {
        display: none;
    }
    </style>
""", unsafe_allow_html=True)

# Ambil API Key Gemini dari Streamlit Secrets
gemini_key = st.secrets.get("GEMINI_API_KEY") or (st.secrets.get("general") or {}).get("GEMINI_API_KEY")

# --- PENYESUAIAN NAMA FILE PDF (PASTIKAN SAMA DENGAN DI GITHUB) ---
TARGET_PDF = "Undang-undang Nomor 6 Tahun 2023.pdf"
file_path = Path(__file__).parent / TARGET_PDF

if gemini_key:
    genai.configure(api_key=gemini_key)

# Fungsi Membaca PDF secara lokal
@st.cache_resource
def get_pdf_text(path):
    if not path.exists(): return ""
    try:
        reader = PdfReader(path)
        return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
    except Exception:
        return ""

pdf_text = get_pdf_text(file_path)

st.title("⚖️ UU No. 6 Tahun 2023 Assistant")
st.markdown("Asisten cerdas untuk informasi Undang-Undang Nomor 6 Tahun 2023 (Klaster Ketenagakerjaan / Cipta Kerja).")

# Inisialisasi Riwayat Percakapan
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- MENU UTAMA ---
tab1, tab2 = st.tabs(["💬 Tanya Jawab AI", "📖 Download Undang-Undang"])

with tab1:
    st.markdown("### Kolom Pertanyaan")
    
    st.markdown("💡 **Pilih topik pertanyaan populer berdasarkan isi teks dokumen PDF:**")
    
    quick_questions = [
        {"label": "🏫 Ringkasan Isi Dokumen", "prompt": "Apa saja pokok-pokok ketentuan yang dibahas dalam dokumen UU No. 6 Tahun 2023 ini?"},
        {"label": "📜 Ketentuan Pasal 81", "prompt": "Jelaskan mengenai poin-poin perubahan ketentuan yang tercantum dalam Pasal 81 di dokumen ini."},
        {"label": "🛡️ Program Jaminan Sosial", "prompt": "Bagaimana ketentuan mengenai jaminan sosial atau Jaminan Kehilangan Pekerjaan dalam dokumen ini?"},
        {"label": "👥 Ketentuan Umum Kerja", "prompt": "Apa saja aturan mengenai ketenagakerjaan yang dimuat dalam dokumen lampiran ini?"},
        {"label": "🔍 Analisis Dokumen", "prompt": "Tolong ringkas isi keseluruhan dari teks dokumen PDF yang terbaca saat ini."},
        {"label": "📋 Status Peraturan", "prompt": "Bagaimana kedudukan hukum dari dokumen Undang-Undang Nomor 6 Tahun 2023 ini?"}
    ]
    
    cols = st.columns(3)
    clicked_query = None
    for i, q in enumerate(quick_questions):
        if cols[i % 3].button(q["label"], use_container_width=True):
            clicked_query = q["prompt"]

    st.markdown("---")
    
    with st.form(key="query_form", clear_on_submit=True):
        user_query = st.text_input("Atau ketik pertanyaan Anda sendiri di sini:")
        submit_btn = st.form_submit_button("Kirim Pertanyaan")

    target_query = clicked_query if clicked_query else (user_query if submit_btn else None)

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if target_query:
        st.session_state.messages.append({"role": "user", "content": target_query})
        with st.chat_message("user"):
            st.markdown(target_query)
            
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("⏳ *Sedang menganalisis dokumen Undang-Undang...*")
            full_response = ""
            
            try:
                if not pdf_text:
                    message_placeholder.error(f"File `{TARGET_PDF}` tidak ditemukan atau gagal dibaca. Pastikan nama file di GitHub adalah '{TARGET_PDF}'.")
                else:
                    model = genai.GenerativeModel('gemini-3.6-flash')
                    prompt = f"""
                    Anda adalah Asisten hukum yang analitis. Berikan penjelasan sebaik mungkin berdasarkan teks dokumen PDF di bawah ini. Jika ada bagian yang terpotong di dalam teks, jelaskan berdasarkan potongan teks yang tersedia saja secara objektif.

                    --- DOKUMEN UNDANG-UNDANG NO. 6 TAHUN 2023 ---
                    {pdf_text[:30000]}
                    ----------------------------------------------

                    Pertanyaan Pengguna: {target_query}
                    """
                    
                    response = model.generate_content(prompt, stream=True)
                    for chunk in response:
                        if chunk.text:
                            full_response += chunk.text
                            message_placeholder.markdown(full_response + "▌")
                    
                    message_placeholder.markdown(full_response)
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
            except Exception as e:
                message_placeholder.error(f"Terjadi kesalahan: {e}")

with tab2:
    st.subheader("📖 Dokumen Undang-Undang")
    if file_path.exists():
        with open(file_path, "rb") as f:
            st.download_button("📥 Download UU No. 6 Tahun 2023 (PDF)", f, file_name=TARGET_PDF, mime="application/pdf")
    else:
        st.error(f"File `{TARGET_PDF}` tidak ditemukan di direktori.")

# Admin
with st.expander("🔐 Mode Admin"):
    if st.text_input("Password:", type="password", key="admin_pwd") == "2273":
        uploaded = st.file_uploader("Upload PDF baru", type=["pdf"])
        if uploaded:
            with open(file_path, "wb") as f: 
                f.write(uploaded.getbuffer())
            st.cache_resource.clear()
            st.success("File berhasil diunggah! Silakan refresh halaman.")

st.markdown("---")
st.markdown("<p style='text-align: center; color: gray; font-size: 13px;'>Developed by <b>iqbalmantam</b></p>", unsafe_allow_html=True)
