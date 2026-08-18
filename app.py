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
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Konfigurasi Halaman Streamlit
st.set_page_config(
    page_title="HR Policy Q&A Assistant", page_icon="🏢", layout="wide"
)

# Sembunyikan Header dan Footer bawaan Streamlit
hide_streamlit_style = """
    <style>
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

# Judul Aplikasi
st.title("🏢 HR Policy & Employee Handbook Q&A Assistant")
st.markdown(
    "Asisten cerdas untuk menjawab pertanyaan seputar aturan, SOP, dan kebijakan"
    " perusahaan."
)

# Sidebar untuk Navigasi & Mode Admin
with st.sidebar:
  st.header("⚙️ Menu Navigasi")

  # Pilihan Mode (Karyawan vs Admin)
  app_mode = st.radio("Pilih Mode:", ["💬 Chat Karyawan", "🔐 Mode Admin"])

  st.markdown("---")

  if app_mode == "🔐 Mode Admin":
    st.subheader("Autentikasi Admin")
    input_password = st.text_input("Masukkan Password Admin:", type="password")

    if input_password == admin_pass_secret:
      st.success("✅ Login Admin Berhasil!")
      st.markdown("---")
      st.subheader("📁 Upload Dokumen Peraturan")
      uploaded_file = st.file_uploader(
          "Pilih file PDF Peraturan/Handbook baru", type=["pdf"]
      )
      process_btn = st.button("Proses & Simpan Dokumen")
    else:
      if input_password:
        st.error("❌ Password salah!")
      else:
      # Simpan state kosong jika belum login
        uploaded_file = None
        process_btn = False
      st.info("ℹ️ Masukkan password admin (2273) untuk mengunggah dokumen.")
  else:
    st.subheader("📁 Unduh Dokumen Perusahaan")
    st.markdown(
        "Anda dapat mengunduh dokumen peraturan perusahaan resmi di sini."
    )

    # Cek apakah file dokumen perusahaan tersedia secara lokal di repo
    default_doc_path = "peraturan_perusahaan.pdf"  # Letakkan file PDF ini di GitHub jika ingin langsung bisa didownload
    if os.path.exists(default_doc_path):
      with open(default_doc_path, "rb") as pdf_file:
        PDFbyte = pdf_file.read()
      st.download_button(
          label="📥 Download Peraturan Perusahaan (PDF)",
          data=PDFbyte,
          file_name="Peraturan_Perusahaan.pdf",
          mime="application/pdf",
      )
    else:
      st.info(
          "ℹ️ File dokumen belum diunggah oleh Admin ke server. Hubungi HR"
          " untuk mendapatkan file."
      )

  # Watermark di Sidebar
  st.markdown("---")
  st.markdown(
      "<p style='text-align: center; color: gray; font-size: 12px;'>Developed"
      " by iqbalmantam</p>",
      unsafe_allow_html=True,
  )

# Inisialisasi Sesi State untuk Penyimpanan Vektor & File Aktif
if "vector_store" not in st.session_state:
  st.session_state.vector_store = None

# Logika Pemrosesan Dokumen oleh Admin
if app_mode == "🔐 Mode Admin" and input_password == admin_pass_secret:
  if process_btn:
    if not groq_api_key:
      st.error("❌ Groq API Key belum diatur di Streamlit Secrets.")
    elif not uploaded_file:
      st.error("❌ Mohon unggah file PDF terlebih dahulu.")
    else:
      with st.spinner("Sedang memproses dokumen dan membuat indeks vektor..."):
        # Simpan file sementara & file permanen untuk didownload user
        temp_file_path = f"./temp_{uploaded_file.name}"
        with open(temp_file_path, "wb") as f:
          f.write(uploaded_file.getbuffer())

        # Simpan juga sebagai default_doc_path agar bisa di-download di mode karyawan
        with open("peraturan_perusahaan.pdf", "wb") as f:
          f.write(uploaded_file.getbuffer())

        # 1. Load Dokumen PDF
        loader = PyPDFLoader(temp_file_path)
        docs = loader.load()

        # 2. Split Dokumen menjadi chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )
        splits = text_splitter.split_documents(docs)

        # 3. Buat Embeddings
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

        # 4. Simpan ke Vector Store
        vector_store = Chroma.from_documents(
            documents=splits, embedding=embeddings
        )
        st.session_state.vector_store = vector_store

        os.remove(temp_file_path)
        st.success(
            "✅ Dokumen berhasil diproses dan disimpan! Silakan beralih ke"
            " 'Chat Karyawan'."
        )

# Antarmuka Chat Utama (Mode Karyawan)
if app_mode == "💬 Chat Karyawan":
  if st.session_state.vector_store is not None and groq_api_key:
    # Inisialisasi LLM Groq
    llm = ChatGroq(
        groq_api_key=groq_api_key,
        model_name="llama-3.3-70b-versatile",
        temperature=0.1,
    )

    retriever = st.session_state.vector_store.as_retriever(
        search_kwargs={"k": 3}
    )


    def format_docs(docs):
      return "\n\n".join(doc.page_content for doc in docs)


    template = (
        "Anda adalah asisten HR yang ramah dan profesional.\n"
        "Gunakan konteks potongan dokumen kebijakan perusahaan berikut untuk menjawab pertanyaan.\n"
        "Jika Anda tidak tahu jawabannya, katakan dengan jujur bahwa informasi tersebut tidak ditemukan dalam dokumen.\n"
        "Sertakan kutipan atau referensi halaman dokumen jika tersedia pada konteks.\n\n"
        "Konteks:\n{context}\n\n"
        "Pertanyaan: {question}"
    )
    prompt = ChatPromptTemplate.from_template(template)

    user_query = st.chat_input(
        "Tanyakan tentang aturan cuti, klaim, atau SOP perusahaan..."
    )

    if user_query:
      with st.chat_message("user"):
        st.markdown(user_query)

      with st.chat_message("assistant"):
        with st.spinner("Mencari jawaban dalam dokumen..."):
          source_docs = retriever.invoke(user_query)
          context_text = format_docs(source_docs)

          rag_chain = (
              {
                  "context": lambda x: context_text,
                  "question": RunnablePassthrough(),
              }
              | prompt
              | llm
              | StrOutputParser()
          )

          answer = rag_chain.invoke(user_query)

          st.markdown(answer)

          with st.expander("📚 Lihat Sumber Dokumen (Citation)"):
            for i, doc in enumerate(source_docs):
              page_num = doc.metadata.get("page", 0)
              st.markdown(f"**Sumber {i+1} (Halaman {page_num + 1}):**")
              st.markdown(f"> {doc.page_content[:300]}...")
              st.markdown("---")
  else:
    st.info(
        "ℹ️ Belum ada dokumen kebijakan yang diunggah. Silakan minta Admin"
        " mengunggah dokumen melalui **Mode Admin** (Password: 2273) di sidebar"
        " kiri."
    )

# Watermark di bawah halaman utama
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: gray; font-size: 13px;'>Developed by"
    " <b>iqbalmantam</b></p>",
    unsafe_allow_html=True,
)
