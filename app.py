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
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Konfigurasi Halaman Streamlit
st.set_page_config(page_title="HR Policy Assistant", page_icon="🏢", layout="wide")

# Styling UI
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
groq_api_key = st.secrets.get("GROQ_API_KEY") or (st.secrets.get("general") or {}).get("GROQ_API_KEY")
admin_pass_secret = st.secrets.get("ADMIN_PASSWORD") or (st.secrets.get("general") or {}).get("ADMIN_PASSWORD") or "2273"

# Inisialisasi Session State
if "vector_store" not in st.session_state:
    st.session_state.vector_store = None

TARGET_PDF = "CJ LOGISTICS SERVICE INDONESIA_PP.pdf"

# Judul Aplikasi
st.title("🏢 HR Policy & Employee Handbook Q&A Assistant")
st.markdown("Asisten cerdas untuk menjawab pertanyaan seputar aturan dan kebijakan perusahaan.")

tab1, tab2, tab3 = st.tabs(["💬 Chat Karyawan", "📥 Download Dokumen", "🔐 Mode Admin"])

# --- TAB 1: CHAT KARYAWAN ---
with tab1:
    st.subheader("💬 Tanya Jawab Kebijakan Perusahaan")

    # Load PDF otomatis jika vector store belum ada
    if st.session_state.vector_store is None and os.path.exists(TARGET_PDF) and groq_api_key:
        with st.spinner("Memproses dokumen peraturan..."):
            try:
                loader = PyPDFLoader(TARGET_PDF)
                docs = loader.load()
                
                # Chunking super hemat token
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=400, 
                    chunk_overlap=40
                )
                splits = text_splitter.split_documents(docs)
                
                embeddings = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
                )
                st.session_state.vector_store = Chroma.from_documents(
                    documents=splits, embedding=embeddings
                )
            except Exception as e:
                st.error(f"Gagal memuat dokumen: {e}")

    if st.session_state.vector_store and groq_api_key:
        # Menggunakan model llama-3.1-8b-instant dengan max_tokens aman
        llm = ChatGroq(
            groq_api_key=groq_api_key,
            model_name="llama-3.1-8b-instant",
            temperature=0.0,
            max_tokens=350,  # Membatasi jawaban agar tidak terkena limit output
        )

        user_query = st.chat_input("Tanyakan tentang aturan cuti, PHK, klaim, dll...")

        if user_query:
            st.chat_message("user").markdown(user_query)

            with st.chat_message("assistant"):
                with st.spinner("Mencari jawaban..."):
                    try:
                        # Ambil hanya 2 potongan paling relevan untuk menghemat token secara drastis
                        retriever = st.session_state.vector_store.as_retriever(search_kwargs={"k": 2})
                        source_docs = retriever.invoke(user_query)
                        
                        # Gabungkan teks & bersihkan spasi ganda
                        raw_context = " ".join([d.page_content.replace("\n", " ") for d in source_docs])
                        
                        # Pemotongan Keras (Hard Limit): Maksimal 1200 karakter
                        clean_context = raw_context[:1200]

                        # Prompt ultra-ringkas
                        prompt = ChatPromptTemplate.from_template(
                            "Jawab pertanyaan berikut HANYA berdasarkan konteks di bawah.\n"
                            "Jika tidak ada di teks, katakan 'Informasi tidak ditemukan di dokumen.'\n\n"
                            "Konteks: {context}\n\n"
                            "Pertanyaan: {question}"
                        )

                        formatted_prompt = prompt.format(context=clean_context, question=user_query)
                        response = llm.invoke(formatted_prompt)
                        st.markdown(response.content)

                    except Exception as e:
                        st.error(f"Terjadi kesalahan: {e}")
    else:
        if not groq_api_key:
            st.warning("⚠️ `GROQ_API_KEY` belum dikonfigurasi di Streamlit Secrets.")
        else:
            st.info("ℹ️ File PDF belum ditemukan di repositori.")

# --- TAB 2: DOWNLOAD DOKUMEN ---
with tab2:
    st.subheader("📥 Unduh Peraturan Perusahaan")
    if os.path.exists(TARGET_PDF):
        with open(TARGET_PDF, "rb") as f:
            st.download_button(
                label="📥 Download Peraturan Perusahaan (PDF)",
                data=f.read(),
                file_name=TARGET_PDF,
                mime="application/pdf",
            )
    else:
        st.warning(f"⚠️ File `{TARGET_PDF}` tidak ditemukan.")

# --- TAB 3: MODE ADMIN ---
with tab3:
    st.subheader("🔐 Panel Admin")
    pwd = st.text_input("Masukkan Password Admin:", type="password")
    if pwd == admin_pass_secret:
        uploaded_file = st.file_uploader("Upload PDF Peraturan Baru", type=["pdf"])
        if uploaded_file:
            with open(TARGET_PDF, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success("File berhasil diunggah! Silakan refresh halaman aplikasi.")

st.markdown("---")
st.markdown("<p style='text-align: center; color: gray; font-size: 13px;'>Developed by <b>iqbalmantam</b></p>", unsafe_allow_html=True)
