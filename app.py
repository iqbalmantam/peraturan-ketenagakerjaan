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
    " kebijakan perusahaan dari seluruh isi dokumen."
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
    with st.spinner("Memproses seluruh dokumen peraturan perusahaan (52 Halaman)..."):
      try:
        loader = PyPDFLoader(TARGET_PDF)
        docs = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )
        splits = text_splitter.split_documents(docs)
        
        # Simpan seluruh pecahan teks untuk filtering langsung
        st.session_state.raw_splits = splits
        
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
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
        temperature=0.0,  # 0.0 agar AI fokus total pada teks dan tidak berimajinasi
        max_tokens=1500,
    )
    
    retriever = st.session_state.vector_store.as_retriever(
        search_kwargs={"k": 5}
    )

    chat_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            (
                "Anda adalah HR Assistant profesional untuk PT CJ Logistics Service Indonesia. "
                "Jawablah pertanyaan karyawan HANYA berdasarkan teks konteks dokumen resmi perusahaan yang diberikan di bawah ini. "
                "DILARANG KERAS menggunakan Pasal 6 atau informasi penggolongan karyawan untuk menjawab pertanyaan tentang PHK. "
                "Sajikan jawaban dengan terstruktur rapi ke dalam bagian-bagian berikut jika relevan:\n"
                "1. Prinsip Umum (Pasal 52)\n"
                "2. Ketentuan Khusus Berdasarkan Kategori (Pasal 53–61)\n"
                "3. Hutang Pekerja Terkait PHK (Pasal 62)\n"
                "Gunakan format poin-poin yang jelas dan profesional."
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
        with st.spinner("Mencari pasal resmi PHK di dalam dokumen..."):
          try:
            ql = user_query.lower()
            
            # --- STRICT NEGATIVE FILTERING: Blokir Pasal 6, Paksa ambil Bab X (Pasal 52-62) ---
            if any(k in ql for k in ["phk", "pemutusan", "pesangon", "pengakhiran", "pisah", "pemberhentian"]):
                source_docs = [
                    doc for doc in st.session_state.raw_splits 
                    if ("pasal 6" not in doc.page_content.lower() and "penggolongan pekerja" not in doc.page_content.lower()) 
                    and any(term in doc.page_content.lower() for term in ["bab x", "pasal 52", "pasal 53", "pasal 54", "pasal 55", "pasal 56", "pasal 57", "pasal 58", "pasal 59", "pasal 60", "pasal 61", "pasal 62", "termination of employment"])
                ]
                if not source_docs:
                    source_docs = retriever.invoke(user_query)
                else:
                    source_docs = source_docs[:8]
            elif "cuti" in ql:
                source_docs = [
                    doc for doc in st.session_state.raw_splits 
                    if "cuti" in doc.page_content.lower()
                ][:5]
                if not source_docs:
                    source_docs = retriever.invoke(user_query)
            else:
                source_docs = retriever.invoke(user_query)

            context_text = "\n\n".join([doc.page_content for doc in source_docs])

            messages = chat_prompt.format_messages(
                context=context_text, question=user_query
            )
            response = llm.invoke(messages)
            answer = response.content

            st.markdown(answer)

            if source_docs:
              with st.expander("📚 Lihat Sumber Dokumen (Citation)"):
                for i, doc in enumerate(source_docs):
                  page_num = doc.metadata.get("page", 0)
                  st.markdown(f"**Sumber {i+1} (Halaman {page_num + 1}):**")
                  st.markdown(f"> {doc.page_content[:300]}...")
                  st.markdown("---")
          except Exception as e:
            st.error(
                f"Terjadi kesalahan saat memproses jawaban di program. Detail: {e}"
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

    with st.form("admin_form"):
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
            with open(TARGET_PDF, "wb`") as f:
              f.write(uploaded_file.getbuffer())

            loader = PyPDFLoader(TARGET_PDF)
            docs = loader.load()

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000, chunk_overlap=200
            )
            splits = text_splitter.split_documents(docs)
            st.session_state.raw_splits = splits

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
