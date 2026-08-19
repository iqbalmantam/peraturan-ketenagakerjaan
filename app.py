import os

# --- FIX UNTUK CHROMADB DI STREAMLIT CLOUD ---
try:
  import pysqlite3
  import sys
  sys.modules["sqlite3"] = pysqlite3
except ImportError:
  pass
# ---------------------------------------------

import streamlit as st
from groq import Groq
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Konfigurasi Halaman Streamlit
st.set_page_config(
    page_title="HR Policy Q&A Assistant", page_icon="🏢", layout="wide"
)

# Sembunyikan Sidebar bawaan Streamlit
hide_streamlit_style = """
    <style>
    [data-testid="stSidebar"] {display: none;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Ambil Konfigurasi dari Streamlit Secrets
groq_api_key = None
admin_pass_secret = "2273"  # Fallback default

try:
  if "GROQ_API_KEY" in st.secrets:
    groq_api_key = st.secrets["GROQ_API_KEY"]
  elif "general" in st.secrets and "GROQ_API_KEY" in st.secrets["general"]:
    groq_api_key = st.secrets["general"]["GROQ_API_KEY"]

  if "ADMIN_PASSWORD" in st.secrets:
    admin_pass_secret = st.secrets["ADMIN_PASSWORD"]
  elif "general" in st.secrets and "ADMIN_PASSWORD" in st.secrets["general"]:
    admin_pass_secret = st.secrets["ADMIN_PASSWORD"]
except Exception:
  pass

# Fungsi Pemilih Model Pintar
@st.cache_data(show_spinner=False)
def get_safe_model(api_key):
    try:
        client = Groq(api_key=api_key)
        models = client.models.list().data
        for m in models:
            if "llama-3.1-8b-instant" in m.id or "llama3-8b" in m.id:
                return m.id
        for m in models:
            if "whisper" not in m.id and "tts" not in m.id and "orpheus" not in m.id and "vision" not in m.id:
                return m.id
        return "llama-3.1-8b-instant"
    except:
        return "llama-3.1-8b-instant"

# Judul Aplikasi
st.title("🏢 HR Policy & Employee Handbook Q&A Assistant")
st.markdown(
    "Asisten cerdas untuk menjawab pertanyaan seputar aturan, SOP, dan"
    " kebijakan perusahaan berdasarkan dokumen resmi."
)

# Inisialisasi Sesi State
if "vector_store" not in st.session_state:
  st.session_state.vector_store = None
if "raw_splits" not in st.session_state:
  st.session_state.raw_splits = []

TARGET_PDF = "CJ LOGISTICS SERVICE INDONESIA_PP.pdf"

# Gunakan Tab di Header Atas sebagai Menu Navigasi Utama
tab1, tab2, tab3 = st.tabs(
    ["💬 Chat Karyawan", "📥 Download Dokumen", "🔐 Mode Admin"]
)

# --- TAB 1: CHAT KARYAWAN ---
with tab1:
  st.subheader("💬 Tanya Jawab Kebijakan Perusahaan")

  # Muat otomatis dokumen dari GitHub jika vector_store masih kosong
  if st.session_state.vector_store is None and os.path.exists(TARGET_PDF) and groq_api_key:
    with st.spinner("Memproses seluruh dokumen peraturan perusahaan..."):
      try:
        loader = PyPDFLoader(TARGET_PDF)
        docs = loader.load()
        
        # Chunking dioptimalkan agar lebih ringkas (mencegah error kepanjangan token)
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800, 
            chunk_overlap=150,
            add_start_index=True
        )
        splits = text_splitter.split_documents(docs)
        st.session_state.raw_splits = splits
        
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        st.session_state.vector_store = Chroma.from_documents(
            documents=splits, embedding=embeddings
        )
      except Exception as e:
        st.error(f"Gagal memuat dokumen otomatis: {e}")

  if st.session_state.vector_store is not None and groq_api_key:
    selected_model = get_safe_model(groq_api_key)
    
    llm = ChatGroq(
        groq_api_key=groq_api_key,
        model_name=selected_model,
        temperature=0.0,
        max_tokens=512,
    )

    chat_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            (
                "Anda adalah Asisten HR PT CJ Logistics Service Indonesia yang teliti dan profesional. "
                "Jawablah pertanyaan karyawan HANYA berdasarkan konteks dokumen resmi perusahaan yang diberikan. "
                "Jika informasi tidak ditemukan di dalam teks, katakan dengan jujur bahwa informasi tersebut tidak tersedia. "
                "Sajikan jawaban secara terstruktur dalam bentuk poin-poin yang rapi."
            ),
        ),
        ("human", "Konteks Dokumen Resmi:\n{context}\n\nPertanyaan Karyawan: {question}"),
    ])

    user_query = st.chat_input(
        "Tanyakan tentang aturan cuti, PHK, klaim, atau SOP perusahaan..."
    )

    if user_query:
      with st.chat_message("user"):
        st.markdown(user_query)

      with st.chat_message("assistant"):
        with st.spinner("Mencari jawaban akurat di dokumen..."):
          try:
            # Retriever disesuaikan ukurannya agar jumlah token aman
            retriever = st.session_state.vector_store.as_retriever(
                search_type="mmr",
                search_kwargs={
                    "k": 4,          # Dikurangi dari 6 ke 4 agar teks konteks tidak berlebihan
                    "fetch_k": 12    # Dikurangi dari 20 ke 12
                }
            )
            source_docs = retriever.invoke(user_query)
            
            seen_texts = set()
            unique_docs = []
            for d in source_docs:
                if d.page_content not in seen_texts:
                    seen_texts.add(d.page_content)
                    unique_docs.append(d)
            
            context_text = "\n\n".join([d.page_content for d in unique_docs])

            messages = chat_prompt.format_messages(
                context=context_text, question=user_query
            )
            response = llm.invoke(messages)
            st.markdown(response.content)

          except Exception as e:
            st.error(f"Terjadi kesalahan saat memproses jawaban: {e}")
  else:
    if not groq_api_key:
      st.warning("⚠️ `GROQ_API_KEY` belum dikonfigurasi di Streamlit Secrets.")
    else:
      st.info("ℹ️ File dokumen belum terdeteksi. Pastikan file sudah di-commit di GitHub.")

# --- TAB 2: DOWNLOAD DOKUMEN ---
with tab2:
  st.subheader("📥 Unduh Peraturan Perusahaan")
  st.markdown("Anda dapat mendownload dokumen resmi peraturan perusahaan melalui tombol di bawah ini.")

  if os.path.exists(TARGET_PDF):
    with open(TARGET_PDF, "rb") as pdf_file:
      PDFbyte = pdf_file.read()
    st.download_button(
        label="📥 Download Peraturan Perusahaan (PDF)",
        data=PDFbyte,
        file_name=TARGET_PDF,
        mime="application/pdf",
    )
  else:
    st.warning(f"⚠️ File `{TARGET_PDF}` belum ditemukan di repositori GitHub.")

# --- TAB 3: MODE ADMIN ---
with tab3:
  st.subheader("🔐 Panel Admin")
  input_password = st.text_input("Masukkan Password Admin:", type="password", key="admin_pass_input")

  if input_password == admin_pass_secret:
    st.success("✅ Autentikasi Admin Berhasil!")
    st.markdown("---")
    st.subheader("📁 Perbarui Dokumen Peraturan")
    
    with st.form("admin_form"):
      uploaded_file = st.file_uploader("Pilih file PDF Peraturan/Handbook baru", type=["pdf"])
      submit_btn = st.form_submit_button("Proses & Perbarui Dokumen")

    if submit_btn:
      if not groq_api_key:
        st.error("❌ Groq API Key belum diatur di Streamlit Secrets.")
      elif not uploaded_file:
        st.error("❌ Mohon pilih file PDF terlebih dahulu.")
      else:
        with st.spinner("Sedang memproses dokumen baru..."):
          try:
            with open(TARGET_PDF, "wb") as f:
              f.write(uploaded_file.getbuffer())

            loader = PyPDFLoader(TARGET_PDF)
            docs = loader.load()
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=800, 
                chunk_overlap=150,
                add_start_index=True
            )
            splits = text_splitter.split_documents(docs)
            st.session_state.raw_splits = splits

            embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            )
            vector_store = Chroma.from_documents(
                documents=splits, embedding=embeddings
            )
            st.session_state.vector_store = vector_store

            st.success("✅ Dokumen berhasil diperbarui! Silakan kembali ke tab 'Chat Karyawan'.")
          except Exception as e:
            st.error(f"Terjadi kesalahan saat memproses dokumen: {e}")
  else:
    if input_password:
      st.error("❌ Password salah!")
    else:
      st.info("ℹ️ Masukkan password admin untuk mengakses panel manajemen.")

# Watermark di bawah halaman utama
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: gray; font-size: 13px;'>Developed by <b>iqbalmantam</b></p>",
    unsafe_allow_html=True,
)
