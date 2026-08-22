import streamlit as st
import pypdf
import os
import re

# Konfigurasi Halaman
st.set_page_config(page_title="Local Legal Agent (UU No. 13/2003)", page_icon="⚖️", layout="wide")

# CSS untuk merapikan tampilan
st.markdown("""
    <style>
    [data-testid="stHeader"] {
        display: none;
    }
    </style>
""", unsafe_allow_html=True)

# Nama file PDF lokal di GitHub
PDF_FILENAME = "UU No 13 Tahun 2003.pdf"

# Fungsi Membaca PDF secara lokal
@st.cache_resource
def load_pdf_text():
    if not os.path.exists(PDF_FILENAME):
        return None
    reader = pypdf.PdfReader(PDF_FILENAME)
    teks_gabungan = ""
    for halaman in reader.pages:
        teks = halaman.extract_text()
        if teks:
            teks_gabungan += teks + "\n"
    return teks_gabungan

teks_dokumen = load_pdf_text()

st.title("⚖️ Local Legal Agent: Spesialis UU No. 13 Tahun 2003")
st.markdown("AI Agent mandiri yang memindai dan mencarikan pasal secara presisi langsung dari dokumen **UU No. 13 Tahun 2003 tentang Ketenagakerjaan**[cite: 1] tanpa ketergantungan pada layanan AI eksternal.")

# --- PENCARIAN BERBASIS PASAL ---
st.subheader("🔍 Mesin Pencari & Analisis Pasal")

# Tombol Cepat untuk Topik Populer
st.markdown("💡 **Pilih topik instan untuk melihat pasal terkait:**")
col1, col2, col3, col4 = st.columns(4)

selected_keyword = None
if col1.button("💰 Pesangon (Pasal 156)", use_container_width=True):
    selected_keyword = "pesangon"
if col2.button("📜 PKWT (Pasal 59)", use_container_width=True):
    selected_keyword = "perjanjian kerja untuk waktu tertentu"
if col3.button("⏳ Masa Percobaan", use_container_width=True):
    selected_keyword = "masa percobaan"
if col4.button("🏖️ Cuti & Istirahat", use_container_width=True):
    selected_keyword = "waktu istirahat"

st.markdown("---")

# Input Pencarian Manual
keyword_input = st.text_input(
    "Atau masukkan kata kunci pencarian hukum:", 
    value=selected_keyword if selected_keyword else "",
    placeholder="contoh: pemutusan hubungan kerja, skorsing, lembur..."
)

def cari_pasal_lokal(teks, keyword):
    if not teks:
        return []
    # Memecah dokumen berdasarkan pola "Pasal [angka]"
    pasal_list = re.split(r'(Pasal\s+\d+)', teks)
    results = []
    
    for i in range(1, len(pasal_list), 2):
        header = pasal_list[i]
        body = pasal_list[i+1] if i+1 < len(pasal_list) else ""
        full_block = header + body
        
        # Abaikan Pasal 1 (Ketentuan Umum) agar hasil lebih spesifik ke substansi
        if "pasal 1" in header.lower():
            continue
            
        if keyword in full_block.lower():
            matching_lines = [line.strip() for line in full_block.split('\n') if keyword in line.lower() or "pasal" in line.lower()]
            results.append({
                "title": header,
                "matching_lines": matching_lines,
                "full_text": full_block.strip()
            })
    return results

if st.button("🚀 Jalankan Pencarian Dokumen", type="primary"):
    if teks_dokumen is None:
        st.error(f"⚠️ File '{PDF_FILENAME}' tidak ditemukan di repository GitHub Anda. Pastikan file PDF tersebut sudah di-upload sejajar dengan file app.py.")
    elif not keyword_input.strip():
        st.warning("⚠️ Harap masukkan kata kunci pencarian terlebih dahulu.")
    else:
        with st.spinner("Sistem sedang memindai pasal-pasal relevan dari dokumen..."):
            kw = keyword_input.lower()
            hasil_pencarian = cari_pasal_lokal(teks_dokumen, kw)
            
        st.success("Pencarian Selesai!")
        st.markdown(f"### 📋 Hasil Pencarian untuk: *'{keyword_input}'*")
        
        if hasil_pencarian:
            st.info(f"Ditemukan **{len(hasil_pencarian)} Pasal** yang relevan dalam dokumen[cite: 1]:")
            
            for idx, item in enumerate(hasil_pencarian[:10], 1):
                with st.expander(f"Hasil {idx}: {item['title']} (Relevan dengan topik)"):
                    st.markdown("**Poin Penting:**")
                    for line in item['matching_lines'][:5]:
                        st.write(f"- {line}")
                        
                    with st.expander("📖 Lihat Teks Lengkap Pasal Ini"):
                        st.text(item['full_text'])
        else:
            st.warning("Kata kunci tidak ditemukan. Coba gunakan istilah lain seperti 'pesangon', 'phk', atau 'upah'.")

# Footer
st.markdown("---")
st.markdown("<p style='text-align: center; color: gray; font-size: 13px;'>Local Compliance Agent • Berbasis UU No. 13 Tahun 2003[cite: 1] • Dikelola via GitHub & Streamlit</p>", unsafe_allow_html=True)
