import os
import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader

# Konfigurasi Halaman
st.set_page_config(page_title="HR Policy Assistant", layout="wide")

# Ambil API Key Gemini dari Streamlit Secrets
gemini_key = st.secrets.get("GEMINI_API_KEY") or (st.secrets.get("general") or {}).get("GEMINI_API_KEY")
TARGET_PDF = "CJ LOGISTICS SERVICE INDONESIA_PP.pdf"
file_path = os.path.join(os.path.dirname(__file__), TARGET_PDF)

if gemini_key:
    genai.configure(api_key=gemini_key)

# Fungsi Membaca PDF secara lokal (Stabil & Cepat)
@st.cache_resource
def get_pdf_text(path):
    if not os.path.exists(path): return ""
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
    
    # --- FITUR: GRID TOMBOL PERTANYAAN CEPAT ---
    st.markdown("💡 **Pilih topik pertanyaan populer:**")
    
    quick_questions = [
        {"label": "📅 Cuti Tahunan", "prompt": "Berapa jatah cuti tahunan dan bagaimana ketentuannya?"},
        {"label": "🏥 Klaim Pengobatan", "prompt": "Bagaimana aturan dan prosedur klaim pengobatan?"},
        {"label": "📝 Ketentuan PHK", "prompt": "Apa saja ketentuan dan prosedur PHK?"},
        {"label": "⏰ Jam Kerja & Lembur", "prompt": "Bagaimana aturan mengenai jam kerja dan lembur?"},
        {"label": "⚠️ Sanksi Disiplin", "prompt": "Apa saja jenis sanksi disiplin bagi karyawan?"},
        {"label": "✈️ Perjalanan Dinas", "prompt": "Bagaimana kebijakan terkait perjalanan dinas?"}
    ]
    
    # Membuat 2 baris, masing-masing 3 kolom
    cols = st.columns(3)
    clicked_query = None
    
    for i, q in enumerate(quick_questions):
        with cols[i % 3]:
            if st.button(q["label"], use_container_width=True):
                clicked_query = q["prompt"]

    st.markdown("---")

    # Form input manual
    with st.form(key="query_form", clear_on_submit=True):
        user_query = st.text_input("Atau ketik pertanyaan Anda sendiri di sini:")
        submit_btn = st.form_submit_button("Kirim Pertanyaan")

    # Logika eksekusi: pilih dari tombol cepat ATAU input manual
    target_query = clicked_query if clicked_query else (user_query if submit_btn else None)

    if target_query:
        st.session_state.messages.append({"role": "user", "content": target_query})
        with st.spinner("Gemini sedang menganalisis dokumen..."):
            try:
                if not pdf_text:
                    answer = "File PDF kosong atau gagal dibaca oleh sistem."
                else:
                    model = genai.GenerativeModel('gemini-3.6-flash')
                    
                    prompt = f"""
                    Anda adalah Asisten HR PT CJ Logistics Service Indonesia yang profesional dan teliti.
                    Jawablah pertanyaan karyawan HANYA berdasarkan dokumen Peraturan Perusahaan di bawah ini.
                    **PENTING:** Wajib sebutkan nomor pasal, bab, atau bagian dokumen secara spesifik yang menjadi rujukan jawaban Anda (contoh: Pasal X ayat Y).
                    Jika informasi tidak ditemukan di dalam teks, katakan dengan jujur bahwa informasi tersebut tidak tersedia.
                    Sajikan jawaban secara terstruktur dalam bentuk poin-poin yang rapi.

                    --- DOKUMEN PERATURAN PERUSAHAAN ---
                    {pdf_text}
                    ------------------------------------

                    Pertanyaan Karyawan: {target_query}
                    """
                    
                    response = model.generate_content(prompt)
                    answer = response.text
            except Exception as e:
                answer = f"Terjadi kesalahan: {e}"
            
            st.session_state.messages.append({"role": "assistant", "content": answer})
            st.rerun() # Refresh untuk memunculkan jawaban baru

    # Tampilkan Riwayat Percakapan
    st.markdown("### Riwayat Percakapan")
    if not st.session_state.messages:
        st.info("Belum ada pertanyaan yang diajukan.")
    else:
        for msg in reversed(st.session_state.messages):
            if msg["role"] == "user":
                st.markdown(f"**👤 Anda:** {msg['content']}")
            else:
                st.markdown(f"**🤖 Asisten HR:**\n{msg['content']}")
            st.markdown("---")

with tab2:
    st.subheader("📖 Dokumen Peraturan Perusahaan")
    st.markdown("Anda dapat mengunduh dokumen lengkap Peraturan Perusahaan melalui tombol di bawah ini:")
    
    if os.path.exists(file_path):
        with open(file_path, "rb") as pdf_file:
            pdf_bytes = pdf_file.read()
            
        st.download_button(
            label="📥 Download Dokumen Peraturan Perusahaan (PDF)",
            data=pdf_bytes,
            file_name=TARGET_PDF,
            mime="application/pdf"
        )
    else:
        st.error(f"File PDF `{TARGET_PDF}` tidak ditemukan.")

# --- MODE ADMIN ---
with st.expander("🔐 Mode Admin"):
    if st.text_input("Password:", type="password", key="admin_pwd") == "2273":
        uploaded = st.file_uploader("Upload PDF baru", type=["pdf"])
        if uploaded:
            with open(file_path, "wb") as f: 
                f.write(uploaded.getbuffer())
            st.cache_resource.clear()
            st.success("File berhasil diunggah!")

st.markdown("---")
st.markdown("<p style='text-align: center; color: gray; font-size: 13px;'>Developed by <b>iqbalmantam</b></p>", unsafe_allow_html=True)
