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
from groq import Groq  # Import tambahan untuk auto-discovery model
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Konfigurasi Halaman Streamlit
st.set_page_config(
    page_title="HR Policy Q&A Assistant", page_icon="🏢", layout="wide"
)

# Sembunyikan Sidebar, Header, dan Footer bawaan Streamlit
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
    admin_pass_secret = st.secrets["general"]["ADMIN_PASSWORD"]
except Exception:
  pass

# Fungsi Auto-Discovery Model (Mencari model terbaik yang aktif di API Key Anda)
@st.cache_data(show_spinner=False)
def get_best_active_model(api_key):
    try:
        client = Groq(api_key=api_key)
        models_data = client.models.list().data
        available_models = [m.id for m in models_data]
        
        # Urutan prioritas model dari yang tercerdas hingga standar
        priorities = [
            "llama-3.3-70b-versatile",
            "llama-3.1-70b-versatile",
            "llama-3.1-8b-instant",
            "llama-3.2-3b-preview",
            "llama-3.2-1b-preview",
            "mixtral-8x7b-32768",
            "gemma2-9b-it"
        ]
        
        # Cek dan pilih model terbaik yang tersedia di akun Anda
        for p in priorities:
            if p in available_models:
                return p
                
        # Jika prioritas tidak ada, ambil model teks apa saja yang tersedia
        for model in available_models:
            if "whisper" not in model.lower() and "vision" not in model.lower():
                return model
                
        return "llama-3.1-8b-instant" # Fallback mutlak
    except Exception:
        return "llama-3.1-8b-instant"

# Judul Aplikasi
st.title("🏢 HR Policy & Employee Handbook Q&A Assistant")
st.markdown(
    "Asisten cerdas untuk menjawab pertanyaan seputar aturan, SOP, dan"
    " kebijakan perusahaan."
)

# Inisialisasi Sesi State untuk Penyimpanan Vektor
if "vector_store" not in st.session_state:
  st.session_state.vector_store = None

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
    with st.spinner("Memuat dokumen peraturan perusahaan secara otomatis..."):
      try:
        loader = PyPDFLoader(TARGET_PDF)
        docs = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )
        splits = text_splitter.split_documents(docs)
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        st.session_state.vector_store = Chroma.from_documents(
            documents=splits, embedding=embeddings
        )
      except Exception as e:
        st.error(f"Gagal memuat dokumen otomatis: {e}")

  if st.session_state.vector_store is not None and groq_api_key:
    # --- MENDAPATKAN MODEL TERBAIK SECARA OTOMATIS ---
    best_model_id = get_best_active_model(groq_api_key)
    
    llm = ChatGroq(
        groq_api_key=groq_api_key,
        model_name=best_model_id,
        temperature=0.1,
    )
    retriever = st.session_state.vector_store.as_retriever(
        search_kwargs={"k": 3}
    )

    def format_docs(docs):
      return "\n\n".join(doc.page_content for doc in docs)

    # Prompt text murni (Sangat aman dari BadRequest)
    template = """Anda adalah asisten HR yang ramah dan profesional.
Gunakan konteks dokumen kebijakan perusahaan berikut untuk menjawab pertanyaan.
Jika Anda tidak tahu jawabannya, katakan dengan jujur bahwa informasi tersebut tidak ditemukan dalam dokumen.

Konteks:
{context}

Pertanyaan: {question}

Jawaban:"""
    
    prompt = PromptTemplate.from_template(template)
    
    # Rantai pemrosesan yang simpel dan stabil
    rag_chain = prompt | llm | StrOutputParser()

    user_query = st.chat_input(
        "Tanyakan tentang aturan cuti, klaim, atau SOP perusahaan..."
    )

    if user_query:
      with st.chat_message("user"):
        st.markdown(user_query)

      with st.chat_message("assistant"):
        with st.spinner(f"Mencari jawaban menggunakan AI ({best_model_id})..."):
          try:
            source_docs = retriever.invoke(user_query)
            context_text = format_docs(source_docs)

            # Menghasilkan jawaban
            answer = rag_chain.invoke({
                "context": context_text,
                "question": user_query
            })

            st.markdown(answer)

            with st.expander("📚 Lihat Sumber Dokumen (Citation)"):
              for i, doc in enumerate(source_docs):
                page_num = doc.metadata.get("page", 0)
                st.markdown(f"**Sumber {i+1} (Halaman {page_num + 1}):**")
                st.markdown(f"> {doc.page_content[:300]}...")
                st.markdown("---")
          except Exception as e:
            st.error(
                f"Terjadi kesalahan saat memproses jawaban dari AI. Detail: {e}"
            )
  else:
    if not groq_api_key:
      st.warning("⚠️ `GROQ_API_KEY` belum dikonfigurasi di Streamlit Secrets.")
    else:
      st.info(
          "ℹ️ File dokumen belum terdeteksi. Pastikan file"
          f" `{TARGET_PDF}` sudah di-commit dengan benar di GitHub."
      )

# --- TAB 2: DOWNLOAD DOKUMEN ---
with tab2:
  st.subheader("📥 Unduh Peraturan Perusahaan")
  st.markdown(
      "Anda dapat mengunduh dokumen resmi peraturan perusahaan melalui tombol di"
      " bawah ini."
  )

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
    st.warning(
        f"⚠️ File `{TARGET_PDF}` belum ditemukan di repositori GitHub."
    )

# --- TAB 3: MODE ADMIN ---
with tab3:
  st.subheader("🔐 Panel Admin")
  input_password = st.text_input(
      "Masukkan Password Admin:", type="password", key="admin_pass_input"
  )

  if input_password == admin_pass_secret:
    st.success("✅ Autentikasi Admin Berhasil!")
    st.markdown("---")
    st.subheader("📁 Perbarui Dokumen Peraturan")
    st.markdown(
        "Jika Anda ingin mengganti dokumen, silakan unggah file PDF baru di"
        " bawah ini:"
    )

    with st.form("admin_upload_form"):
      uploaded_file = st.file_uploader(
          "Pilih file PDF Peraturan/Handbook baru", type=["pdf"]
      )
      submit_btn = st.form_submit_button("Proses & Perbarui Dokumen")

    if submit_btn:
      if not groq_api_key:
        st.error("❌ Groq API Key belum diatur di Streamlit Secrets.")
      elif not uploaded_file:
        st.error("❌ Mohon pilih file PDF terlebih dahulu.")
      else:
        with st.spinner(
            "Sedang memproses dokumen baru dan memperbarui indeks vektor..."
        ):
          try:
            with open(TARGET_PDF, "wb") as f:
              f.write(uploaded_file.getbuffer())

            loader = PyPDFLoader(TARGET_PDF)
            docs = loader.load()

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000, chunk_overlap=200
            )
            splits = text_splitter.split_documents(docs)

            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            vector_store = Chroma.from_documents(
                documents=splits, embedding=embeddings
            )
            st.session_state.vector_store = vector_store

            st.success(
                "✅ Dokumen berhasil diperbarui! Silakan kembali ke tab 'Chat"
                " Karyawan'."
            )
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
    "<p style='text-align: center; color: gray; font-size: 13px;'>Developed by"
    " <b>iqbalmantam</b></p>",
    unsafe_allow_html=True,
)
