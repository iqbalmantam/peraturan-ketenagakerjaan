import os
import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
from pathlib import Path

# Konfigurasi Halaman
st.set_page_config(page_title="Asisten Ketenagakerjaan (UU No. 6/2023 & UU No. 13/2003)", layout="wide")

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

# --- DEFINISI FILE PDF ---
FILE_UU_6 = "Undang-undang Nomor 6 Tahun 2023.pdf"
FILE_UU_13 = "UU No 13 Tahun 2003.pdf"

path_uu_6 = Path(__file__).parent / FILE_UU_6
path_uu_13 = Path(__file__).parent / FILE_UU_13

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

# Membaca kedua teks dokumen
text_uu_6 = get_pdf_text(path_uu_6)
text_uu_13 = get_pdf_text(path_uu_13)

st.title("⚖️ Asisten Hukum Ketenagakerjaan")
st.markdown("Asisten cerdas untuk informasi **UU No. 6 Tahun 2023** (Cipta Kerja) dan **UU No. 13 Tahun 2003** (Ketenagakerjaan).")

# Inisialisasi Riwayat Percakapan
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- MENU UTAMA ---
tab1, tab2 = st.tabs(["💬 Tanya Jawab AI", "📖 Download Dokumen Undang-Undang"])

with tab1:
    st.markdown("### Kolom Pertanyaan")
    
    st.markdown("💡 **Pilih topik pertanyaan populer berdasarkan dokumen ketenagakerjaan:**")
    
    quick_questions = [
        {"label": "📝 Ketentuan PHK & Pesangon", "prompt": "Bagaimana aturan pemutusan hubungan kerja (PHK) serta perhitungan uang pesangon dan penghargaan masa kerja berdasarkan dokumen undang-undang ketenagakerjaan?"},
        {"label": "📅 Waktu Istirahat & Cuti", "prompt": "Bagaimana ketentuan waktu istirahat, istirahat mingguan, dan cuti tahunan minimal 12 hari menurut dokumen undang-undang?"},
        {"label": "📜 Kontrak PKWT & Kompensasi", "prompt": "Bagaimana ketentuan Perjanjian Kerja Waktu Tertentu (PKWT) serta aturan masa berlakunya dalam dokumen undang-undang?"},
        {"label": "👥 Alih Daya (Outsourcing)", "prompt": "Bagaimana aturan mengenai perusahaan alih daya (outsourcing) dan batasan pekerjaannya berdasarkan dokumen undang-undang?"},
        {"label": "⏰ Jam Kerja & Lembur", "prompt": "Bagaimana ketentuan waktu kerja (5 atau 6 hari kerja) serta syarat upah kerja lembur menurut dokumen undang-undang?"},
        {"label": "💰 Kebijakan Upah Minimum", "prompt": "Bagaimana prinsip dan kebijakan penetapan upah minimum yang melindungi pekerja berdasarkan dokumen undang-undang?"}
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
                if not text_uu_13 and not text_uu_6:
                    message_placeholder.error("File PDF dokumen undang-undang tidak ditemukan atau gagal dibaca di direktori.")
                else:
                    model = genai.GenerativeModel('gemini-3.6-flash')
                    
                    # Menggabungkan referensi kedua dokumen agar AI dapat membaca keduanya
                    combined_docs = f"""
                    === DOKUMEN 1: UU NO. 13 TAHUN 2003 TENTANG KETENAGAKERJAAN ===
                    {text_uu_13[:25000]}
                    
                    === DOKUMEN 2: UU NO. 6 TAHUN 2023 TENTANG CIPTA KERJA ===
                    {text_uu_6[:25000]}
                    """
                    
                    prompt = f"""
                    Anda adalah Ahli Hukum Ketenagakerjaan dan Asisten profesional yang teliti.
                    Jawablah pertanyaan berdasarkan dokumen Undang-Undang di bawah ini (UU No. 13 Tahun 2003 dan/atau UU No. 6 Tahun 2023).
                    Wajib sebutkan nomor pasal, ayat, atau bagian undang-undang secara spesifik (contoh: Pasal X UU No. ...).
                    Jika informasi tidak ditemukan di kedua dokumen, katakan dengan jujur bahwa informasi tersebut tidak tersedia.
                    Sajikan jawaban secara terstruktur dalam bentuk poin-poin yang rapi.

                    {combined_docs}

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
    st.subheader("📖 Download Dokumen Undang-Undang")
    st.markdown("Pilih dokumen undang-undang yang ingin Anda unduh:")
    
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        if path_uu_13.exists():
            with open(path_uu_13, "rb") as f:
                st.download_button("📥 Download UU No. 13 Tahun 2003 (PDF)", f, file_name=FILE_UU_13, mime="application/pdf")
        else:
            st.warning(f"File `{FILE_UU_13}` tidak ditemukan.")
            
    with col_dl2:
        if path_uu_6.exists():
            with open(path_uu_6, "rb") as f:
                st.download_button("📥 Download UU No. 6 Tahun 2023 (PDF)", f, file_name=FILE_UU_6, mime="application/pdf")
        else:
            st.warning(f"File `{FILE_UU_6}` tidak ditemukan.")

# Admin
with st.expander("🔐 Mode Admin"):
    admin_pw = st.text_input("Password:", type="password", key="admin_pwd")
    if admin_pw == "2273":
        target_upload = st.selectbox("Pilih file yang ingin diperbarui:", [FILE_UU_13, FILE_UU_6])
        uploaded = st.file_uploader("Upload PDF baru", type=["pdf"])
        if uploaded:
            target_path = path_uu_13 if target_upload == FILE_UU_13 else path_uu_6
            with open(target_path, "wb") as f: 
                f.write(uploaded.getbuffer())
            st.cache_resource.clear()
            st.success(f"File `{target_upload}` berhasil diperbarui! Silakan refresh halaman.")

st.markdown("---")
st.markdown("<p style='text-align: center; color: gray; font-size: 13px;'>Developed by <b>iqbalmantam</b></p>", unsafe_allow_html=True)
