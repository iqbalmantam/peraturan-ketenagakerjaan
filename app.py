import os

try:
  import pysqlite3
  import sys
  sys.modules["sqlite3"] = pysqlite3
except ImportError:
  pass

import streamlit as st
from groq import Groq
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Konfigurasi Dasar
st.set_page_config(page_title="HR Q&A", layout="wide")

# Styling
st.markdown("<style>[data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)

# Secrets
groq_api_key = st.secrets.get("GROQ_API_KEY") or (st.secrets.get("general") or {}).get("GROQ_API_KEY")
admin_pass_secret = st.secrets.get("ADMIN_PASSWORD") or (st.secrets.get("general") or {}).get("ADMIN_PASSWORD") or "2273"

if "vector_store" not in st.session_state: st.session_state.vector_store = None

TARGET_PDF = "CJ LOGISTICS SERVICE INDONESIA_PP.pdf"

# Fungsi Pemilih Model Dinamis (Aman dari Error 404)
@st.cache_data(show_spinner=False)
def get_safe_model(api_key):
    try:
        client = Groq(api_key=api_key)
        models = client.models.list().data
        # Cari model Llama yang aktif
        for m in models:
            if "llama" in m.id.lower() and "vision" not in m.id.lower():
                return m.id
        # Jika tidak ada Llama, ambil model teks pertama yang tersedia
        for m in models:
            if "whisper" not in m.id and "tts" not in m.id and "embedding" not in m.id:
                return m.id
        return models[0].id if models else "llama3-8b-8192"
    except Exception:
        return "llama3-8b-8192"

st.title("🏢 HR Policy Q&A Assistant")

tab1, tab2, tab3 = st.tabs(["💬 Chat", "📥 Download", "🔐 Admin"])

with tab1:
    # Load PDF
    if st.session_state.vector_store is None and os.path.exists(TARGET_PDF) and groq_api_key:
        with st.spinner("Indexing dokumen..."):
            loader = PyPDFLoader(TARGET_PDF)
            docs = loader.load()
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
            splits = text_splitter.split_documents(docs)
            embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
            st.session_state.vector_store = Chroma.from_documents(documents=splits, embedding=embeddings)

    if st.session_state.vector_store and groq_api_key:
        selected_model = get_safe_model(groq_api_key)
        llm = ChatGroq(groq_api_key=groq_api_key, model_name=selected_model, temperature=0, max_tokens=512)
        
        user_query = st.chat_input("Tanyakan aturan perusahaan...")
        if user_query:
            st.chat_message("user").markdown(user_query)
            with st.chat_message("assistant"):
                with st.spinner("Mencari..."):
                    try:
                        retriever = st.session_state.vector_store.as_retriever(search_kwargs={"k": 3})
                        docs = retriever.invoke(user_query)
                        
                        context_text = "\n\n".join([d.page_content for d in docs])
                        if len(context_text) > 2500:
                            context_text = context_text[:2500] + "..."

                        prompt = ChatPromptTemplate.from_template(
                            "Jawab pertanyaan berikut hanya berdasarkan konteks.\n\nKonteks: {context}\n\nPertanyaan: {question}"
                        )
                        response = llm.invoke(prompt.format(context=context_text, question=user_query))
                        st.markdown(response.content)
                    except Exception as e:
                        st.error(f"Error: {e}")

with tab2:
    if os.path.exists(TARGET_PDF):
        with open(TARGET_PDF, "rb") as f:
            st.download_button("Download PDF", f, file_name=TARGET_PDF)

with tab3:
    pwd = st.text_input("Password:", type="password")
    if pwd == admin_pass_secret:
        uploaded_file = st.file_uploader("Upload PDF baru", type=["pdf"])
        if uploaded_file:
            with open(TARGET_PDF, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success("Berhasil! Silakan refresh halaman.")
