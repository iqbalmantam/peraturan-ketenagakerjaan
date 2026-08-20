import os
import base64
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

# --- UPLOAD FILE KE GEMINI API DI BALIK LAYAR ---
@st.cache_resource
def get_gemini_file(path):
    if not os.path.exists(path):
        return None
    try:
        return genai.upload_file(path)
    except Exception:
        return None

gemini_file = get_gemini_file(file_path)

# --- MENU UTAMA (MENGGUNAKAN TABS) ---
tab1, tab2 = st.tabs(["💬 Tanya Jawab AI", "📖 Baca Peraturan Perusahaan"])

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
    st.subheader("📖 Dokumen Peraturan Perusahaan")
    st.markdown("Anda dapat membaca langsung isi dokumen PDF perusahaan melalui tampilan di bawah ini:")
    
    if os.path.exists(file_path):
        # Membaca file PDF dan mengubahnya ke base64 untuk ditampilkan di browser
        with open(file_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        
        # Menampilkan PDF menggunakan tag iframe HTML
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800px" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    else:
        st.error(f"File PDF `{TARGET_PDF}` tidak ditemukan di direktori utama.")

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
