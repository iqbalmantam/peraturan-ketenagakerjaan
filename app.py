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
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Konfigurasi Halaman Streamlit (Menyembunyikan menu/logo GitHub bawaan dengan hide_streamlit_style)
st.set_page_config(
    page_title="HR Policy Q&A Assistant", page_icon="🏢", layout="wide"
)

hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Judul Aplikasi
st.title("🏢 HR Policy & Employee Handbook Q&A Assistant")
st.markdown(
    "Unggah dokumen kebijakan perusahaan (PDF) dan tanyakan apa saja terkait"
    " aturan atau SOP perusahaan."
)

# Sidebar untuk Konfigurasi & Unggah Dokumen
with st.sidebar:
  st.header("⚙️ Konfigurasi & Data")

  # Input API Key Groq secara dinamis
  groq_api_key = st.text_input(
      "Masukkan Groq API Key:", type="password", help="Dapatkan dari console.groq.com"
  )

  st.markdown("---")
  st.subheader("📁 Unggah Dokumen Kebijakan")
  uploaded_file = st.file_uploader(
      "Pilih file PDF Peraturan/Handbook", type=["pdf"]
  )

  process_btn = st.button("Proses Dokumen")

  # Watermark di Sidebar
  st.markdown("---")
  st.markdown(
      "<p style='text-align: center; color: gray; font-size: 12px;'>Developed"
      " by iqbalmantam</p>",
      unsafe_allow_html=True,
  )

# Inisialisasi Sesi State untuk Penyimpanan Vektor
if "vector_store" not in st.session_state:
  st.session_state.vector_store = None

# Proses Dokumen saat tombol ditekan
if process_btn:
  if not groq_api_key:
    st.error("❌ Mohon masukkan Groq API Key terlebih dahulu.")
  elif not uploaded_file:
    st.error("❌ Mohon unggah file PDF terlebih dahulu.")
  else:
    with st.spinner(
        "Sedang memproses dokumen (membuat embeddings & indeks)..."
    ):
      # Simpan file PDF sementara
      temp_file_path = f"./temp_{uploaded_file.name}"
      with open(temp_file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

      # 1. Load Dokumen PDF
      loader = PyPDFLoader(temp_file_path)
      docs = loader.load()

      # 2. Split Dokumen menjadi bagian-bagian kecil (Chunks)
      text_splitter = RecursiveCharacterTextSplitter(
          chunk_size=1000, chunk_overlap=200
      )
      splits = text_splitter.split_documents(docs)

      # 3. Buat Embeddings menggunakan model open-source ringan
      embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

      # 4. Simpan ke Chroma Vector Database secara in-memory
      vector_store = Chroma.from_documents(documents=splits, embedding=embeddings)
      st.session_state.vector_store = vector_store

      # Hapus file sementara
      os.remove(temp_file_path)

      st.success(
          "✅ Dokumen berhasil diproses! Silakan ajukan pertanyaan di bawah."
      )

# Antarmuka Chat Utama
if st.session_state.vector_store is not None:
  # Inisialisasi LLM Groq
  llm = ChatGroq(
      groq_api_key=groq_api_key,
      model_name="llama-3.3-70b-versatile",
      temperature=0.1,
  )

  # Buat Prompt Khusus dengan Instruksi Citation
  system_prompt = (
      "Anda adalah asisten HR yang ramah dan profesional. "
      "Gunakan konteks potongan dokumen kebijakan perusahaan berikut untuk"
      " menjawab pertanyaan. "
      "Jika Anda tidak tahu jawabannya, katakan dengan jujur bahwa informasi"
      " tersebut tidak ditemukan dalam dokumen. "
      "Sertakan kutipan atau referensi halaman dokumen jika tersedia pada"
      " konteks.\n\n"
      "Konteks:\n{context}"
  )

  prompt = ChatPromptTemplate.from_messages([
      ("system", system_prompt),
      ("human", "{input}"),
  ])

  # Bangun RAG Chain
  question_answer_chain = create_stuff_documents_chain(llm, prompt)
  retriever = st.session_state.vector_store.as_retriever(
      search_kwargs={"k": 3}
  )
  rag_chain = create_retrieval_chain(retriever, question_answer_chain)

  # Input Pertanyaan dari Pengguna
  user_query = st.chat_input(
      "Tanyakan tentang aturan cuti, klaim, atau SOP perusahaan..."
  )

  if user_query:
    with st.chat_message("user"):
      st.markdown(user_query)

    with st.chat_message("assistant"):
      with st.spinner("Mencari jawaban dalam dokumen..."):
        # Eksekusi RAG Query
        response = rag_chain.invoke({"input": user_query})
        answer = response["answer"]
        source_docs = response["context"]

        # Tampilkan Jawaban Utama
        st.markdown(answer)

        # Tampilkan Fitur Citation (Sumber Dokumen & Halaman)
        with st.expander("📚 Lihat Sumber Dokumen (Citation)"):
          for i, doc in enumerate(source_docs):
            page_num = doc.metadata.get("page", 0)
            st.markdown(f"**Sumber {i+1} (Halaman {page_num + 1}):**")
            st.markdown(f"> {doc.page_content[:300]}...")
            st.markdown("---")
else:
  st.info(
      "ℹ️ Silakan masukkan Groq API Key dan unggah file PDF kebijakan perusahaan"
      " di sidebar kiri untuk mulai."
  )

# Watermark di bawah halaman utama
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: gray; font-size: 13px;'>Developed by"
    " <b>iqbalmantam</b></p>",
    unsafe_allow_html=True,
)
