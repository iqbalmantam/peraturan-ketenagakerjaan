import os

try:
    import pysqlite3
    import sys
    sys.modules["sqlite3"] = pysqlite3
except ImportError:
    pass

import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# Konfigurasi Halaman
st.set_page_config(page_title="HR Assistant (OpenRouter)", layout="wide")
st.markdown("<style>[data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)

# Ambil API Key OpenRouter
openrouter_api_key = st.secrets.get("OPENROUTER_API_KEY") or (st.secrets.get("general") or {}).get("OPENROUTER_API_KEY")
admin_pass_secret = st.secrets.get("ADMIN_PASSWORD") or (st.secrets.get("general") or {}).get("ADMIN_PASSWORD") or "2273"

TARGET_PDF = "CJ LOGISTICS SERVICE INDONESIA_PP.pdf"

if "vector_store" not in st.session_state:
    st.session_state.vector_store = None

st.title("🏢 HR Policy Assistant (OpenRouter)")
st.markdown("Asisten cerdas dengan fleksibilitas pilihan model AI terbaik.")

# --- INDEXING DOKUMEN ---
if st.session_state.vector_store is None and os.path.exists(TARGET_PDF) and openrouter_api_key:
    with st.spinner("Mempersiapkan dokumen perusahaan..."):
        try:
            loader = PyPDFLoader(TARGET_PDF)
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=50)
            splits = text_splitter.split_documents(loader.load())
            
            embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
            st.session_state.vector_store = Chroma.from_documents(documents=splits, embedding=embeddings)
        except Exception as e:
            st.error(f"Gagal memproses dokumen: {e}")

# --- CHAT KARYAWAN ---
user_query = st.chat_input("Tanyakan aturan cuti, PHK, klaim, dll...")

if user_query:
    st.chat_message("user").markdown(user_query)
    with st.chat_message("assistant"):
        with st.spinner("Mencari jawaban akurat..."):
            if not openrouter_api_key:
                st.error("⚠️ `OPENROUTER_API_KEY` belum diset di Streamlit Secrets.")
            elif not st.session_state.vector_store:
                st.error("⚠️ Dokumen belum terindeks.")
            else:
                try:
                    # Menggunakan ChatOpenAI yang diarahkan ke base_url OpenRouter
                    # Kita pakai model Llama 3 8B gratis/andal di OpenRouter
                    llm = ChatOpenAI(
                        openai_api_key=openrouter_api_key,
                        openai_api_base="https://openrouter.ai/api/v1",
                        model_name="meta-llama/llama-3-8b-instruct:free", 
                        temperature=0.0,
                        max_tokens=500
                    )
                    
                    # Ambil dokumen relevan
                    retriever = st.session_state.vector_store.as_retriever(search_kwargs={"k": 2})
                    docs = retriever.invoke(user_query)
                    context = " ".join([d.page_content.replace("\n", " ") for d in docs])
                    
                    prompt = ChatPromptTemplate.from_template(
                        "Jawab pertanyaan berikut HANYA berdasarkan konteks dokumen di bawah.\n"
                        "Jika tidak ada di teks, katakan 'Informasi tidak ditemukan di dokumen.'\n\n"
                        "Konteks: {context}\n\n"
                        "Pertanyaan: {question}"
                    )
                    
                    chain = prompt | llm
                    response = chain.invoke({"context": context, "question": user_query})
                    st.markdown(response.content)
                    
                except Exception as e:
                    st.error(f"Terjadi kesalahan pada OpenRouter: {e}")

# --- MODE ADMIN ---
with st.expander("🔐 Mode Admin"):
    pwd = st.text_input("Password Admin:", type="password")
    if pwd == admin_pass_secret:
        uploaded = st.file_uploader("Upload PDF Peraturan Baru", type=["pdf"])
        if uploaded:
            with open(TARGET_PDF, "wb") as f:
                f.write(uploaded.getbuffer())
            st.success("File berhasil diunggah! Silakan Refresh halaman.")

st.markdown("---")
st.markdown("<p style='text-align: center; color: gray; font-size: 13px;'>Developed by <b>iqbalmantam</b></p>", unsafe_allow_html=True)
