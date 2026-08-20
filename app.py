import os
import streamlit as st
import google.generativeai as genai

# Konfigurasi Halaman
st.set_page_config(page_title="HR Policy Assistant", layout="wide")

# Ambil API Key Gemini dari Streamlit Secrets
gemini_key = st.secrets.get("GEMINI_API_KEY") or (st.secrets.get("general") or {}).get("GEMINI_API_KEY")
TARGET_PDF = "CJ LOGISTICS SERVICE INDONESIA_PP.pdf"
file_path = os.path.join(os.path.dirname(__file__), TARGET_PDF)

if gemini_key:
    genai.configure(api_key=gemini_key)

st.title("🏢 HR Policy Assistant")
st.markdown("Asisten cerdas untuk informasi Peraturan Perusahaan PT CJ Logistics Service Indonesia.")

# Inisialisasi Riwayat Percakapan
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- UPLOAD FILE LANGSUNG KE GEMINI API ---
@st.cache_resource
def get_gemini_file(path):
    if not os.path.exists(path):
        return None
    try:
        # Mengunggah file PDF langsung ke server Gemini (mendukung PDF teks maupun scan)
        uploaded_file = genai.upload_file(path)
        return uploaded_file
    except Exception as e:
        return None

gemini_file = get_gemini_file(file_path)

# --- MENU UTAMA (MENGGUNAKAN TABS) ---
tab1, tab2 = st.tabs(["💬 Tanya Jawab AI", "📖 Info Dokumen"])

with tab1:
    st.markdown("### Kolom Pertanyaan")
    
    # Form input chat berada di atas
    with st.form(key="query_form", clear_on_submit=True):
        user_query = st.text_input("Tanyakan aturan cuti, PHK, klaim, dll:")
        submit_btn = st.form_submit_button("Kirim Pertanyaan")

    if submit_btn and user_query:
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.spinner("Gemini sedang membaca dan menganalisis dokumen..."):
            try:
                if not gemini_file:
                    answer = "File PDF tidak ditemukan atau gagal diunggah ke server Gemini."
                else:
                    # Menggunakan model gemini-3.6-flash
                    model = genai.GenerativeModel('gemini-3.6-flash')
                    
                    prompt = f"""
                    Anda adalah Asisten HR PT CJ Logistics Service Indonesia yang profesional dan teliti.
                    Jawablah pertanyaan karyawan HANYA berdasarkan dokumen Peraturan Perusahaan yang dilampirkan.
                    Jika informasi tidak ditemukan di dalam teks, katakan dengan jujur bahwa informasi tersebut tidak tersedia.
                    Sajikan jawaban secara terstruktur dalam bentuk poin-poin yang rapi.
                    
                    Pertanyaan Karyawan: {user_query}
                    """
                    
                    # Kirim file PDF langsung bersama prompt ke Gemini
                    response = model.generate_content([gemini_file, prompt])
                    answer = response.text
            except Exception as e:
                answer = f"Terjadi kesalahan: {e}"
            
            st.session_state.messages.append({"role": "assistant", "content": answer})

    # Tampilkan Riwayat Percakapan
    st.markdown("---")
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
    st.subheader("📖 Informasi Dokumen Perusahaan")
    st.markdown(f"File PDF Aktif di Repositori: **{TARGET_PDF}**")
    st.markdown(
        "Dokumen ini terhubung langsung ke sistem pemrosesan cerdas Gemini. "
        "Gemini membaca langsung file PDF tersebut secara utuh (baik format teks digital maupun hasil *scan*), "
        "sehingga tidak ada informasi yang terlewat."
    )
    if os.path.exists(file_path):
        st.success("✅ Status: File PDF terdeteksi dan aktif.")
    else:
        st.error("❌ Status: File PDF tidak ditemukan di direktori utama.")

# --- MODE ADMIN ---
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
