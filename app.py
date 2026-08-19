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
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from groq import Groq

st.set_page_config(page_title="HR Assistant", layout="wide")

# Konfigurasi API
groq_api_key = st.secrets.get("GROQ_API_KEY") or (st.secrets.get("general") or {}).get("GROQ_API_KEY")
TARGET_PDF = "CJ LOGISTICS SERVICE INDONESIA_PP.pdf"

# --- FUNGSI DETEKSI MODEL OTOMATIS (Mencegah Error 404) ---
@st.cache_data(show_spinner=False)
def get_best_model(api_key):
    try:
        client = Groq(api_key=api_key)
        models = client.models.list().data
        # Mencari model yang paling umum digunakan
        for m in models:
            if "llama3-8b" in m.id: return m.id
        # Jika tidak ada, ambil model pertama yang tersedia
        return models[0].id
    except:
        return "llama3-8b-8192" # Fallback standar

# --- FUNGSI UTAMA ---
if "vector_store" not in st.session_state: st.session_state.vector_store = None

st.title("🏢 HR Policy Assistant")

if not groq_api_key:
    st.error("API Key belum diset.")
else:
    # Indexing Dokumen (hanya sekali)
    if st.session_state.vector_store is None and os.path.exists(TARGET_PDF):
        with st.spinner("Indexing dokumen..."):
            loader = PyPDFLoader(TARGET_PDF)
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
            splits = text_splitter.split_documents(loader.load())
            embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
            st.session_state.vector_store = Chroma.from_documents(documents=splits, embedding=embeddings)

    # Chat
    user_query = st.chat_input("Tanya aturan perusahaan...")
    if user_query and st.session_state.vector_store:
        st.chat_message("user").markdown(user_query)
        with st.chat_message("assistant"):
            try:
                # Ambil 2 chunk saja agar sangat ringan (mencegah Error 400)
                docs = st.session_state.vector_store.as_retriever(search_kwargs={"k": 2}).invoke(user_query)
                context = " ".join([d.page_content for d in docs])[:1000] # Maksimal 1000 karakter
                
                llm = ChatGroq(groq_api_key=groq_api_key, model_name=get_best_model(groq_api_key), temperature=0, max_tokens=300)
                
                response = llm.invoke(f"Jawab pertanyaan berikut berdasarkan konteks: {context}\n\nPertanyaan: {user_query}")
                st.markdown(response.content)
            except Exception as e:
                st.error(f"Error: {e}")
