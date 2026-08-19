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
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Konfigurasi Halaman Streamlit
st.set_page_config(page_title="HR Policy Q&A Assistant", page_icon="🏢", layout="wide")

# Sembunyikan Sidebar
st.markdown("""<style>[data-testid="stSidebar"] {display: none;}</style>""", unsafe_allow_html=True)

# Ambil Konfigurasi
groq_api_key = st.secrets.get("GROQ_API_KEY")
admin_pass_secret = st.secrets.get("ADMIN_PASSWORD", "2273")

# Fungsi untuk menemukan model yang PASTI aktif di akun Anda
@st.cache_data(show_spinner=False)
def get_active_model(api_key):
    try:
        client = Groq(api_key=api_key)
        # Ambil model pertama yang tersedia yang bukan model audio/vision
        models = client.models.list().data
        for m in models:
            if "whisper" not in m.id and "vision" not in m.id:
                return m.id
        return "llama3-8b-8192"
    except:
        return "llama3-8b-8192"

st.title("🏢 HR Policy & Employee Handbook Q&A Assistant")

if "vector_store" not in st.session_state:
    st.session_state.vector_store = None

TARGET_PDF = "CJ LOGISTICS SERVICE INDONESIA_PP.pdf"
tab1, tab2, tab3 = st.tabs(["💬 Chat Karyawan", "📥 Download Dokumen", "🔐 Mode Admin"])

# --- TAB 1 ---
with tab1:
    if st.session_state.vector_store is None and os.path.exists(TARGET_PDF) and groq_api_key:
        with st.spinner("Memuat dokumen..."):
            loader = PyPDFLoader(TARGET_PDF)
            docs = loader.load()
            splits = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200).split_documents(docs)
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            st.session_state.vector_store = Chroma.from_documents(documents=splits, embedding=embeddings)

    if st.session_state.vector_store and groq_api_key:
        model_name = get_active_model(groq_api_key)
        llm = ChatGroq(groq_api_key=groq_api_key, model_name=model_name, temperature=0.1, max_tokens=1024)
        retriever = st.session_state.vector_store.as_retriever(search_kwargs={"k": 3})
        
        user_query = st.chat_input("Tanyakan tentang aturan perusahaan...")
        if user_query:
            with st.chat_message("user"): st.markdown(user_query)
            with st.chat_message("assistant"):
                try:
                    docs = retriever.invoke(user_query)
                    context = "\n\n".join([d.page_content for d in docs])
                    prompt = PromptTemplate.from_template("Gunakan konteks ini: {context}\n\nJawab: {question}").format(context=context, question=user_query)
                    answer = llm.invoke(prompt).content
                    st.markdown(answer)
                except Exception as e:
                    st.error(f"Error AI: {e}")
    else:
        st.info("Pastikan API Key sudah benar dan dokumen sudah di-commit.")

# --- TAB 2 & 3 ---
with tab2:
    if os.path.exists(TARGET_PDF):
        with open(TARGET_PDF, "rb") as f:
            st.download_button("📥 Download PDF", data=f, file_name=TARGET_PDF)
with tab3:
    pwd = st.text_input("Password:", type="password")
    if pwd == admin_pass_secret:
        file = st.file_uploader("Upload PDF Baru", type=["pdf"])
        if st.button("Simpan"):
            with open(TARGET_PDF, "wb") as f: f.write(file.getbuffer())
            st.success("Berhasil! Silakan refresh aplikasi.")
