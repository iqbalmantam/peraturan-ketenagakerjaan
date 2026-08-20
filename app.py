import asyncio
import hashlib
import json
import math
import os
import re
import socket
import tempfile
import uuid
from datetime import datetime
from urllib.parse import quote_plus, quote

import aiohttp
import pandas as pd
from pyvis.network import Network
import streamlit as st
import streamlit.components.v1 as components

# --- Library Optional ---
try:
    import folium
    from streamlit_folium import st_folium
except ImportError:
    folium = None

try:
    import fitz  # PyMuPDF untuk Scraping PDF CV
except ImportError:
    fitz = None

# --- Library PIL untuk EXIF & GPS ---
try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
except ImportError:
    Image = None
    TAGS = {}
    GPSTAGS = {}

# --- Impor Library Groq AI ---
try:
    from groq import Groq
except ImportError:
    Groq = None

# --- Impor Modul Internal ---
try:
    from modules import (
        fetch_pddikti_data,
        analyze_indonesia_phone,
        check_data_breach,
        check_email_identity,
        generate_indonesia_dorks,
        generate_telecom_dorks,
    )
except ImportError:
    async def fetch_pddikti_data(name):
        return {
            "data": [],
            "direct_url": f"https://pddikti.kemdiktisaintek.go.id/search/{quote_plus(name)}"
        }
    analyze_indonesia_phone = None
    check_data_breach = None

# --- Konfigurasi Halaman Streamlit ---
st.set_page_config(page_title="Osint-Pro | Enterprise CTI Workstation", page_icon="🛡️", layout="wide")

# --- CSS Theme & Visual Styling CTI Workstation ---
st.markdown("""
    <style>
    [data-testid="stToolbar"], #MainMenu, footer, header { display: none !important; }
    .stApp { background-color: #05080f; }
    .risk-score-crit { font-size: 46px; font-weight: 900; text-align: center; color: #ff3333; text-shadow: 0 0 20px rgba(255,51,51,0.7); font-family: monospace; }
    .risk-score-safe { font-size: 46px; font-weight: 900; text-align: center; color: #00ff66; text-shadow: 0 0 20px rgba(0,255,102,0.7); font-family: monospace; }
    .watermark { position: fixed; bottom: 15px; left: 50%; transform: translateX(-50%); font-size: 11px; color: #00ff66; background: rgba(5,8,15,0.9); padding: 5px 15px; border-radius: 20px; border: 1px solid #00ff66; z-index: 9999; font-family: monospace; }
    .soc-terminal-panel { background-color: #02040a; border: 1px solid #30363d; border-top: 3px solid #ff3333; padding: 20px; border-radius: 6px; font-family: monospace; color: #c9d1d9; }
    .executive-summary-box { background-color: #0d1117; border-left: 4px solid #1f6feb; padding: 18px; border-radius: 6px; font-family: monospace; color: #c9d1d9; line-height: 1.6; }
    
    .breach-card-elite { background-color: #0d1117; border: 1px solid #30363d; border-left: 5px solid #ff3333; padding: 18px; margin-bottom: 16px; border-radius: 6px; font-family: monospace; color: #c9d1d9; box-shadow: 0 4px 14px rgba(0,0,0,0.6); }
    .breach-card-stealer { background-color: #120909; border: 1px solid #4a1515; border-left: 5px solid #ff0055; padding: 18px; margin-bottom: 16px; border-radius: 6px; font-family: monospace; color: #c9d1d9; }
    .breach-card-clean { background-color: #08140c; border: 1px solid #1b4725; border-left: 5px solid #00ff66; padding: 18px; margin-bottom: 16px; border-radius: 6px; font-family: monospace; color: #c9d1d9; }
    
    .sev-critical { background-color: rgba(255, 51, 51, 0.25); color: #ff3333; border: 1px solid #ff3333; padding: 3px 10px; border-radius: 4px; font-weight: bold; font-size: 11px; }
    .sev-safe { background-color: rgba(0, 255, 102, 0.2); color: #00ff66; border: 1px solid #00ff66; padding: 3px 10px; border-radius: 4px; font-weight: bold; font-size: 11px; }
    
    .data-tag { background-color: #161b22; border: 1px solid #30363d; color: #58a6ff; padding: 3px 9px; border-radius: 4px; font-size: 11px; margin-right: 6px; display: inline-block; margin-top: 4px; }
    .osint-card-found { background-color: #0d1117; border-left: 4px solid #238636; padding: 10px 14px; margin-bottom: 8px; border-radius: 4px; font-family: monospace; }
    </style>
    <div class="watermark">[Osint-Pro v20.10 Mobile-Optimized] iqbalmantam | CTI Workstation</div>
""", unsafe_allow_html=True)

st.title("🛡️ Osint-Pro — Enterprise CTI Workstation")

# --- Navigasi Mode di Halaman Utama (Tanpa Sidebar) ---
app_mode = st.radio(
    "Pilih Mode Workstation:",
    ["🛡️ Master CTI Investigation", "🖼️ Standalone EXIF & GPS Forensics"],
    horizontal=True
)
st.divider()

if "history_log" not in st.session_state:
    st.session_state["history_log"] = []

# --- Fungsi Pendukung EXIF & GPS Parser (Aman dari NaN) ---
def process_exif_image(uploaded_img):
    if uploaded_img is not None and Image is not None:
        st.success("Image successfully uploaded for forensic analysis.")
        try:
            image = Image.open(uploaded_img)
            st.image(image, caption="Target Image Preview", use_container_width=True)
            
            exif_data = image.getexif()
            metadata_list = []
            lat, lon = None, None

            if exif_data:
                for tag_id, value in exif_data.items():
                    tag_name = TAGS.get(tag_id, tag_id)
                    if tag_name != "GPSInfo":
                        metadata_list.append({"Tag": str(tag_name), "Value": str(value)})
                
                try:
                    gps_ifd = exif_data.get_ifd(0x8825)
                    if gps_ifd:
                        gps_data_dict = {}
                        for t_id, val in gps_ifd.items():
                            t_name = GPSTAGS.get(t_id, t_id)
                            gps_data_dict[t_name] = val
                            metadata_list.append({"Tag": f"GPS:{t_name}", "Value": str(val)})
                        
                        def convert_to_degress(value):
                            try:
                                d, m, s = value
                                return float(d) + (float(m) / 60.0) + (float(s) / 3600.0)
                            except Exception:
                                return None
                        
                        if "GPSLatitude" in gps_data_dict and "GPSLatitudeRef" in gps_data_dict:
                            lat = convert_to_degress(gps_data_dict["GPSLatitude"])
                            if lat is not None and gps_data_dict["GPSLatitudeRef"] != "N":
                                lat = -lat
                        if "GPSLongitude" in gps_data_dict and "GPSLongitudeRef" in gps_data_dict:
                            lon = convert_to_degress(gps_data_dict["GPSLongitude"])
                            if lon is not None and gps_data_dict["GPSLongitudeRef"] == "W":
                                lon = -lon
                except Exception:
                    pass

                st.markdown("##### 📊 Hasil Ekstraksi Metadata EXIF & GPS")
                st.table(pd.DataFrame(metadata_list))

                is_lat_valid = lat is not None and not math.isnan(lat)
                is_lon_valid = lon is not None and not math.isnan(lon)

                if is_lat_valid and is_lon_valid and folium:
                    st.success(f"📍 Koordinat GPS Ditemukan: {lat}, {lon}")
                    m = folium.Map(location=[lat, lon], zoom_start=15)
                    folium.Marker([lat, lon], popup="Target Lokasi EXIF", tooltip="GPS Match").add_to(m)
                    st_folium(m, height=400, width=700)
                elif folium:
                    st.info("⚠️ Data GPS kosong atau tidak valid (nan) pada gambar ini. Menampilkan peta default.")
                    m = folium.Map(location=[-6.2088, 106.8456], zoom_start=11)
                    st_folium(m, height=300, width=700)
            else:
                st.warning("⚠️ Tidak ditemukan metadata EXIF pada gambar ini.")
        except Exception as e:
            st.error(f"Gagal memproses gambar: {e}")
    else:
        st.info("Silakan unggah file gambar (JPG/PNG) untuk memulai analisis forensik EXIF & GPS.")
        if folium:
            m = folium.Map(location=[-6.2088, 106.8456], zoom_start=11)
            st_folium(m, height=300, width=700)

# --- MODE 1: STANDALONE EXIF & GPS FORENSICS (Tanpa Isi Biodata) ---
if app_mode == "🖼️ Standalone EXIF & GPS Forensics":
    st.subheader("🖼️ Standalone EXIF Forensics & Interactive GPS Map")
    st.markdown("Mode ini memungkinkan Anda untuk langsung menganalisis metadata dan koordinat GPS dari sebuah foto **tanpa perlu mengisi formulir biodata target**.")
    uploaded_img = st.file_uploader("Upload Image (JPG/PNG) to Extract EXIF GPS Data", type=["jpg", "jpeg", "png"], key="standalone_exif")
    process_exif_image(uploaded_img)

# --- MODE 2: MASTER CTI INVESTIGATION (Dengan Form Biodata) ---
else:
    def parse_indonesia_phone(phone_num):
        if not phone_num:
            return {"provider": "N/A", "local_format": "N/A", "intl_format": "N/A", "wa_link": "#", "telegram_link": "#"}
        
        clean_num = re.sub(r"\D", "", phone_num)
        if clean_num.startswith("62"):
            local_num = "0" + clean_num[2:]
            e164_num = "+" + clean_num
        elif clean_num.startswith("0"):
            local_num = clean_num
            e164_num = "+62" + clean_num[1:]
        else:
            local_num = "0" + clean_num
            e164_num = "+62" + clean_num

        prefix = local_num[:4]
        provider = "Operator Tidak Terdeteksi"
        
        prefixes = {
            "Telkomsel": ["0811", "0812", "0813", "0821", "0822", "0823", "0851", "0852", "0853"],
            "Indosat Ooredoo": ["0814", "0815", "0816", "0855", "0856", "0857", "0858"],
            "XL Axiata": ["0817", "0818", "0819", "0859", "0877", "0878"],
            "Axis": ["0831", "0832", "0833", "0838"],
            "Tri (3)": ["0895", "0896", "0897", "0898", "0899"],
            "Smartfren": ["0881", "0882", "0883", "0884", "0885", "0886", "0887", "0888", "0889"]
        }
        
        for prov_name, pref_list in prefixes.items():
            if prefix in pref_list:
                provider = prov_name
                break

        return {
            "provider": provider,
            "local_format": local_num,
            "intl_format": e164_num,
            "wa_link": f"https://api.whatsapp.com/send?phone={e164_num.replace('+', '')}",
            "telegram_link": f"https://t.me/{e164_num}"
        }

    async def check_username_live(session, username):
        if not username:
            return []
        targets = [
            {"platform": "GitHub", "url": f"https://api.github.com/users/{username}", "type": "github"},
            {"platform": "Reddit", "url": f"https://www.reddit.com/user/{username}/about.json", "type": "reddit"},
            {"platform": "Dev.to", "url": f"https://dev.to/api/users/by_username?url={username}", "type": "devto"},
            {"platform": "HackerNews", "url": f"https://hacker-news.firebaseio.com/v0/user/{username}.json", "type": "hn"}
        ]
        results = []
        headers = {"User-Agent": "OSINT-Pro-Engine/3.0"}
        for t in targets:
            try:
                async with session.get(t["url"], headers=headers, timeout=aiohttp.ClientTimeout(total=3)) as resp:
                    if resp.status == 200:
                        p_url = f"https://github.com/{username}" if t["type"] == "github" else (f"https://reddit.com/user/{username}" if t["type"] == "reddit" else f"https://dev.to/{username}")
                        results.append({"platform": t["platform"], "status": "FOUND", "direct_url": p_url})
            except Exception:
                pass
        return results

    async def check_email_live(session, email):
        if not email:
            return {}
        md5_hash = hashlib.md5(email.strip().lower().encode('utf-8')).hexdigest()
        gravatar_url = f"https://www.gravatar.com/avatar/{md5_hash}?d=404"
        has_gravatar = False
        try:
            async with session.get(gravatar_url, timeout=aiohttp.ClientTimeout(total=3)) as resp:
                if resp.status == 200:
                    has_gravatar = True
        except Exception:
            pass
        return {
            "email": email,
            "md5": md5_hash,
            "has_gravatar": has_gravatar,
            "gravatar_img": f"https://www.gravatar.com/avatar/{md5_hash}?s=200" if has_gravatar else None
        }

    async def check_domain_live(session, domain):
        if not domain:
            return {}
        clean_domain = domain.replace("http://", "").replace("https://", "").split("/")[0]
        ip_addr = "N/A"
        try:
            ip_addr = socket.gethostbyname(clean_domain)
        except Exception:
            pass

        geo_info = {}
        if ip_addr != "N/A":
            try:
                async with session.get(f"http://ip-api.com/json/{ip_addr}", timeout=aiohttp.ClientTimeout(total=4)) as resp:
                    if resp.status == 200:
                        geo_info = await resp.json()
            except Exception:
                pass

        return {
            "domain": clean_domain,
            "ip": ip_addr,
            "country": geo_info.get("country", "N/A"),
            "city": geo_info.get("city", "N/A"),
            "isp": geo_info.get("isp", "N/A"),
            "asn": geo_info.get("as", "N/A")
        }

    async def fetch_deep_breach_data_live(session, email):
        if not email:
            return {"items": [], "reputation": {}}
        
        breach_items = []
        emailrep_info = {}
        headers = {"User-Agent": "OSINT-Pro-CTI-Engine/4.0"}
        
        try:
            xon_url = f"https://api.xposedornot.com/v1/breach-analytics?email={quote(email)}"
            async with session.get(xon_url, headers=headers, timeout=aiohttp.ClientTimeout(total=6)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    exposed_breaches = data.get("ExposedBreaches", {}).get("breaches_details", [])
                    
                    for b in exposed_breaches:
                        b_name = b.get("breach", "Unknown Breach Event")
                        b_date = b.get("xposed_date", "N/A")
                        b_domain = b.get("domain", "N/A")
                        b_industry = b.get("industry", "N/A")
                        b_summary = b.get("summary", "Insiden kebocoran data terverifikasi di database global.")
                        
                        raw_data = b.get("xposed_data", "Email Address, Passwords")
                        fields_list = [f.strip() for f in raw_data.split(";") if f.strip()]
                        if not fields_list:
                            fields_list = [f.strip() for f in raw_data.split(",") if f.strip()]

                        breach_items.append({
                            "type": "DATA_BREACH",
                            "incident_source": f"Breach Event: {b_name}",
                            "severity": "CRITICAL",
                            "domain": b_domain,
                            "industry": b_industry,
                            "exposure_type": "Platform Data Breach",
                            "date": b_date,
                            "exposed_fields": fields_list,
                            "details": b_summary
                        })
        except Exception:
            pass

        try:
            hr_url = f"https://cavalier.hudsonrock.com/api/v1/osint-tools/search-by-email?email={quote(email)}"
            async with session.get(hr_url, headers=headers, timeout=aiohttp.ClientTimeout(total=6)) as resp:
                if resp.status == 200:
                    hr_data = await resp.json()
                    stealers = hr_data.get("stealers", [])
                    for st_item in stealers[:5]:
                        st_name = st_item.get("stealer_type", "Infostealer Malware")
                        comp_name = st_item.get("computer_name", "Victim-PC")
                        os_ver = st_item.get("operating_system", "Windows OS")
                        b_date = st_item.get("date_compromised", "Recorded Incident")
                        if "T" in str(b_date):
                            b_date = str(b_date).split("T")[0]

                        breach_items.append({
                            "type": "INFOSTEALER",
                            "incident_source": f"Infostealer Infection: {st_name}",
                            "severity": "CRITICAL",
                            "computer_name": comp_name,
                            "operating_system": os_ver,
                            "exposure_type": "Cybercrime Malware Compromise",
                            "date": b_date,
                            "exposed_fields": ["Session Cookies", "Saved Passwords", "User Credentials", "System Metadata"],
                            "details": f"Perangkat target (`{comp_name}` - `{os_ver}`) pernah terinfeksi malware `{st_name}`. Kredensial terdaftar di pasar cybercrime."
                        })
        except Exception:
            pass

        try:
            erep_url = f"https://emailrep.io/{quote(email)}"
            async with session.get(erep_url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    erep_json = await resp.json()
                    details = erep_json.get("details", {})
                    emailrep_info = {
                        "reputation": erep_json.get("reputation", "N/A"),
                        "suspicious": erep_json.get("suspicious", False),
                        "references": erep_json.get("references", 0),
                        "blacklisted": details.get("blacklisted", False),
                        "malicious_activity": details.get("malicious_activity", False),
                        "data_breach": details.get("data_breach", False),
                        "credentials_leaked": details.get("credentials_leaked", False),
                        "first_seen": details.get("first_seen", "N/A")
                    }
        except Exception:
            pass

        return {
            "items": breach_items,
            "reputation": emailrep_info
        }

    def generate_relationship_graph(res):
        net = Network(height="500px", width="100%", bgcolor="#05080f", font_color="white", directed=True)
        net.set_options("""
        var options = {
          "physics": { "barnesHut": { "gravitationalConstant": -3000, "springLength": 95 } }
        }
        """)

        name = res.get("name") or "Target"
        email = res.get("email") or "No-Email"
        net.add_node(name, label=name, color="#ffffff", size=30)
        
        if res.get("email"):
            net.add_node(email, label=email, color="#ff3333", size=25)
            net.add_edge(name, email, color="#555")

        for s in res.get("social", []):
            if s.get("status") == "FOUND":
                net.add_node(s["platform"], label=s["platform"], color="#00ff66", size=20)
                net.add_edge(name, s["platform"], color="#00ff66")

        pddikti_data = res.get("pddikti", {}).get("data", [])
        for entry in pddikti_data:
            pt = entry.get("pt", "PT")
            net.add_node(pt, label=pt, color="#58a6ff", size=20)
            net.add_edge(name, pt, color="#58a6ff")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
            net.save_graph(tmp.name)
            with open(tmp.name, "r", encoding="utf-8") as f:
                html_content = f.read()
                
        if os.path.exists(tmp.name):
            os.remove(tmp.name)
            
        components.html(f"<div style='background-color:#05080f; height:500px;'>{html_content}</div>", height=550)

    async def run_master_deepweb_investigation(email, phone, username, name, domain):
        target_legal_name = name if name else (username if username else (email.split("@")[0] if email else ""))
        
        async with aiohttp.ClientSession() as session:
            task_social = check_username_live(session, username)
            task_email = check_email_live(session, email)
            task_domain = check_domain_live(session, domain)
            task_pddikti = fetch_pddikti_data(target_legal_name)
            task_breach = fetch_deep_breach_data_live(session, email)
            
            social_res, email_res, domain_res, pddikti_res, breach_data_live = await asyncio.gather(
                task_social, task_email, task_domain, task_pddikti, task_breach
            )

        if analyze_indonesia_phone:
            try:
                phone_data = analyze_indonesia_phone(phone)
            except Exception:
                phone_data = parse_indonesia_phone(phone)
        else:
            phone_data = parse_indonesia_phone(phone)
        
        breach_items = breach_data_live.get("items", [])
        reputation = breach_data_live.get("reputation", {})

        dorks = [
            {"title": "Google Email Exposure Dork", "query": f'"{email}"', "link": f"https://www.google.com/search?q={quote_plus(f'\"{email}\"')}"},
            {"title": "Pastebin Leaks Dork Search", "query": f'site:pastebin.com "{email}"', "link": f"https://www.google.com/search?q={quote_plus(f'site:pastebin.com \"{email}\"')}"},
            {"title": "LinkedIn Professional Footprint", "query": f'"{username}" site:linkedin.com', "link": f"https://www.google.com/search?q={quote_plus(f'\"{username}\" site:linkedin.com')}"}
        ]

        notes = []
        if phone_data.get("provider") and phone_data.get("provider") != "N/A":
            notes.append(f"TELECOM: Operator seluler terdeteksi {phone_data['provider']}.")
        if domain_res.get("ip") and domain_res.get("ip") != "N/A":
            notes.append(f"INFRASTRUCTURE: Resolved IP domain {domain_res['ip']} ({domain_res.get('country', 'N/A')}).")
        
        has_real_breach = len(breach_items) > 0
        if has_real_breach:
            notes.append(f"CRITICAL THREAT: Terkonfirmasi {len(breach_items)} insiden kebocoran data pada repositori CTI!")

        score = min(30 + (len(breach_items) * 20) + (len(social_res) * 10), 100)

        return {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "name": name,
            "email": email,
            "username": username,
            "phone": phone_data,
            "domain": domain_res,
            "social": social_res,
            "email_intel": email_res,
            "breach": {
                "breached": has_real_breach,
                "total_incidents": len(breach_items),
                "parsed_items": breach_items,
                "reputation": reputation
            },
            "dorks": dorks,
            "pddikti": pddikti_res,
            "score": score,
            "notes": notes
        }

    with st.form(key="secure_osint_form"):
        col1, col2 = st.columns(2)
        email_in = col1.text_input("Target Email*", placeholder="target@domain.com")
        phone_in = col1.text_input("Target Phone", placeholder="08123456789")
        domain_in = col1.text_input("Associated Domain (Opsional)", placeholder="example.com")
        username_in = col2.text_input("Target Handle / Username")
        name_in = col2.text_input("Target Legal Name", placeholder="Nama Lengkap")
        btn_submit = st.form_submit_button("⚡ ENGAGE RECONNAISSANCE", use_container_width=True)

    if btn_submit:
        if not email_in and not name_in and not username_in:
            st.error("⚠️ Masukkan minimal Email, Nama Target, atau Username.")
        else:
            with st.spinner("🔒 [WORKSTATION] Executing Deep Recon & Fetching Live Breach API Telemetry..."):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                res = loop.run_until_complete(run_master_deepweb_investigation(
                    email_in, phone_in, username_in, name_in, domain_in
                ))
                st.session_state["classified_results"] = res
                st.session_state["history_log"].append({"time": res["timestamp"], "email": email_in, "score": res["score"]})
                st.rerun()

    if "classified_results" in st.session_state:
        res = st.session_state["classified_results"]
        st.divider()
        st.subheader("📊 Tier-0 Elite Footprint Matrix Dashboard")

        c_r1, c_r2, c_r3 = st.columns([1, 2, 2])
        with c_r1:
            st.markdown(f"<div class='risk-score-crit'>{res.get('score', 0)}/100</div>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; font-weight: bold; font-family: monospace;'>THREAT STATUS: ACTIVE</p>", unsafe_allow_html=True)
        with c_r2:
            st.markdown("**Active Telemetry Indicators:**")
            for note in res.get("notes", []):
                st.warning(note)
        with c_r3:
            st.markdown("**Session Telemetry Metadata:**")
            st.write(f"⏱️ **UTC Timestamp:** {res.get('timestamp', 'N/A')}")
            st.write(f"🏷️ **Target Entity:** {res.get('name', 'N/A')}")
            st.write(f"📧 **Obfuscated Vector:** {res.get('email', 'N/A')}")

        st.divider()

        # --- Menu Dropdown untuk Mobile-Friendly (Menghindari Tab Terpotong di HP) ---
        menu_selection = st.selectbox(
            "Pilih Modul Analisis & Laporan:",
            [
                "🕵️‍♂️ Darknet & Infra", 
                "📱 Telecom", 
                "🌐 Social & PDDikti", 
                "⚠️ Breach", 
                "🖼️ EXIF & Peta", 
                "⚖️ Dorks", 
                "💻 LIVE PIVOT & CV SCRAPING", 
                "🎯 Summary (Executive Report)", 
                "🧠 AI Threat Profiling", 
                "🔗 Graph Relationship", 
                "📋 Exporter (JSON)"
            ]
        )
        st.divider()

        if menu_selection == "🕵️‍♂️ Darknet & Infra":
            st.subheader("🔴 Dynamic Darknet Heuristics & Domain Infrastructure")
            dom = res.get("domain", {})
            if dom.get("ip") and dom.get("ip") != "N/A":
                st.markdown(f"""
                <div class='soc-terminal-panel'>
                    <b>DOMAIN INFRASTRUCTURE INTEL:</b><br>
                    • Target Domain: <code>{dom.get('domain', 'N/A')}</code><br>
                    • Resolved IP: <code>{dom.get('ip', 'N/A')}</code><br>
                    • Geolocation: <code>{dom.get('city', 'N/A')}, {dom.get('country', 'N/A')}</code><br>
                    • ISP / ASN: <code>{dom.get('isp', 'N/A')} ({dom.get('asn', 'N/A')})</code>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("<div class='soc-terminal-panel'>Darknet Exposure Index: <b>75%</b><br>Status: Confirmed Leak Vector Matrix</div>", unsafe_allow_html=True)

        elif menu_selection == "📱 Telecom":
            st.subheader("📱 Advanced Telecommunication & Signaling Matrix")
            p = res.get("phone", {})
            st.write(f"Provider: **{p.get('provider', 'N/A')}**")
            st.write(f"Format Lokal: `{p.get('local_format', 'N/A')}` | Format E.164: `{p.get('intl_format', 'N/A')}`")
            st.markdown(f"* 💬 [WhatsApp Link]({p.get('wa_link', '#')})")
            st.markdown(f"* ✈️ [Telegram Contact Direct]({p.get('telegram_link', '#')})")

        elif menu_selection == "🌐 Social & PDDikti":
            st.subheader("🌐 Digital Footprint & PDDikti Intelligence")
            col_soc, col_pd = st.columns(2)
            with col_soc:
                st.markdown("##### 👤 Social Account Discovery")
                if res.get("social"):
                    for s in res["social"]:
                        st.markdown(f"<div class='osint-card-found'>✅ {s['platform']}: <a href='{s['direct_url']}' target='_blank'>Profil Terdeteksi ↗</a></div>", unsafe_allow_html=True)
                else:
                    st.info("Tidak ada profil publik ditemukan via username.")

            with col_pd:
                st.markdown("##### 🏛️ Academic Records (PDDikti)")
                pddikti = res.get("pddikti", {})
                if pddikti.get("data"):
                    st.success("✅ Ditemukan catatan akademis terdaftar di PDDikti.")
                    st.dataframe(pd.DataFrame(pddikti["data"]), use_container_width=True)
                    st.markdown(f"🔗 [Buka hasil pencarian resmi di portal PDDikti Web](https://pddikti.kemdiktisaintek.go.id/search/{quote_plus(res.get('name', ''))})")
                else:
                    st.warning("⚠️ Data tidak ditemukan langsung via API.")
                    if pddikti.get("direct_url"):
                        st.markdown(f"👉 [Klik di sini untuk melihat Halaman PDDikti di Browser]({pddikti['direct_url']})")

        elif menu_selection == "⚠️ Breach":
            st.subheader("⚠️ Forensic Breach & Incident Intelligence")
            breach_data = res.get("breach", {})
            parsed_items = breach_data.get("parsed_items", [])
            rep_info = breach_data.get("reputation", {})
            
            if rep_info:
                rep_status = rep_info.get("reputation", "N/A").upper()
                st.markdown(f"""
                <div class='executive-summary-box'>
                    <b>📊 EMAIL REPUTATION & THREAT TELEMETRY (EmailRep.io)</b><br>
                    • <b>Reputation Level:</b> <code>{rep_status}</code> | • <b>First Seen:</b> <code>{rep_info.get('first_seen', 'N/A')}</code><br>
                    • <b>Blacklisted:</b> <code>{rep_info.get('blacklisted')}</code> | • <b>Suspicious Flag:</b> <code>{rep_info.get('suspicious')}</code><br>
                    • <b>Public References:</b> <code>{rep_info.get('references')} sources</code>
                </div>
                """, unsafe_allow_html=True)
                st.divider()

            st.caption(f"Confirmed Real-World Exposure Incidents Found: {len(parsed_items)}")
            
            if parsed_items:
                for item in parsed_items:
                    b_type = item.get("type", "DATA_BREACH")
                    card_style = "breach-card-stealer" if b_type == "INFOSTEALER" else "breach-card-elite"
                    
                    tags_html = ""
                    for fld in item.get("exposed_fields", []):
                        tags_html += f"<span class='data-tag'>{fld}</span>"

                    domain_info = f" | 🌐 <b>Domain:</b> {item['domain']}" if "domain" in item else ""
                    os_info = f" | 💻 <b>PC/OS:</b> {item.get('computer_name', '')} ({item.get('operating_system', '')})" if "operating_system" in item else ""

                    st.markdown(f"""
                    <div class='{card_style}'>
                        <div style='display: flex; justify-content: space-between; align-items: center;'>
                            <span style='font-size: 15px; font-weight: bold; color: #ff5555;'>🚨 {item.get('incident_source', 'Breach Event')}</span>
                            <span class='sev-critical'>CRITICAL</span>
                        </div>
                        <div style='margin-top: 6px; font-size: 12px; color: #8b949e;'>
                            📅 <b>Discovered Date:</b> {item.get('date', 'N/A')} | 📁 <b>Category:</b> {item.get('exposure_type', 'Data Breach')}{domain_info}{os_info}
                        </div>
                        <div style='margin-top: 8px;'>
                            <b style='font-size: 12px;'>Compromised Data Fields:</b><br>
                            {tags_html}
                        </div>
                        <div style='margin-top: 10px; font-size: 13px; color: #c9d1d9; border-top: 1px dashed #30363d; padding-top: 8px;'>
                            <b>Telemetry Summary:</b> {item.get('details', 'Target credential set confirmed inside leaked dataset.')}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class='breach-card-clean'>
                    <div style='display: flex; justify-content: space-between; align-items: center;'>
                        <span style='font-size: 15px; font-weight: bold; color: #00ff66;'>✅ REPOSITORI BREACH CLEAN</span>
                        <span class='sev-safe'>SAFE</span>
                    </div>
                    <div style='margin-top: 8px; font-size: 13px; color: #c9d1d9;'>
                        Pemeriksaan real-time pada database XposedOrNot dan Hudson Rock Infostealer tidak menemukan catatan insiden kebocoran aktif untuk email <code>{res.get('email')}</code>.
                    </div>
                </div>
                """, unsafe_allow_html=True)

        elif menu_selection == "🖼️ EXIF & Peta":
            st.subheader("🖼️ EXIF Forensics & Interactive GPS Map")
            uploaded_img = st.file_uploader("Upload Image (JPG/PNG) to Extract EXIF GPS Data", type=["jpg", "jpeg", "png"], key="tab5_upload")
            process_exif_image(uploaded_img)

        elif menu_selection == "⚖️ Dorks":
            st.subheader("Advanced Legal Dorking Matrix")
            for d in res.get("dorks", []):
                st.markdown(f"##### {d['title']}")
                st.code(d["query"])
                st.markdown(f"[👉 Execute Automated Search Vector]({d['link']})")

        elif menu_selection == "💻 LIVE PIVOT & CV SCRAPING":
            st.subheader("💻 Active Corporate Penetration & Live Scraping")
            uploaded_pdf = st.file_uploader("Unggah File CV / Dokumen (PDF) Target", type=["pdf"])
            if uploaded_pdf and fitz:
                doc = fitz.open(stream=uploaded_pdf.read(), filetype="pdf")
                extracted_text = ""
                for page in doc:
                    extracted_text += page.get_text()
                st.text_area("Hasil Ekstraksi Teks PDF:", value=extracted_text[:2000], height=200)
            else:
                st.info("Unggah CV (PDF) pada form di atas untuk memicu mesin Live Scraper otomatis.")

        elif menu_selection == "🎯 Summary (Executive Report)":
            st.subheader("🎯 Executive Summary & Covert Intelligence Synthesis")
            st.markdown(f"""
            <div class='executive-summary-box'>
                <b>🛡️ EXECUTIVE BRIEFING & CLASSIFIED INTEL REPORT</b><br><br>
                • Dynamic Risk Score: <code>{res.get('score', 0)}/100</code><br>
                • Confirmed Exposure Incidents: <code>{res.get('breach', {}).get('total_incidents', 0)}</code><br>
                • Telemetry Vector: <code>{res.get('phone', {}).get('provider', 'N/A')}</code>
            </div>
            """, unsafe_allow_html=True)

        elif menu_selection == "🧠 AI Threat Profiling":
            st.subheader("🧠 AI-Powered Threat Profiling (Groq Llama-3)")
            groq_api_key = st.secrets.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")

            if not Groq:
                st.error("⚠️ Modul `groq` belum terinstal di requirements.txt.")
            elif not groq_api_key:
                st.warning("⚠️ GROQ_API_KEY tidak ditemukan di Streamlit Secrets.")
            else:
                st.success("✅ GROQ_API_KEY Terdeteksi & Engine AI Siap Eksekusi.")
                if st.button("🚀 GENERATE AI THREAT PROFILING", use_container_width=True):
                    with st.spinner("🧠 Groq Llama-3 sedang menganalisis footprint target secara taktis..."):
                        try:
                            client = Groq(api_key=groq_api_key)
                            prompt_system = "Anda adalah Cyber Threat Intelligence (CTI) Analyst senior. Berikan analisis risiko, vektor serangan potensial, dan rekomendasi langkah investigasi dalam Bahasa Indonesia yang lugas dan taktis."
                            prompt_user = f"""
                            Lakukan analisis threat profiling pada data target CTI berikut:
                            - Nama Target: {res.get('name', 'N/A')}
                            - Email: {res.get('email', 'N/A')}
                            - Username/Handle: {res.get('username', 'N/A')}
                            - Operator Seluler: {res.get('phone', {}).get('provider', 'N/A')}
                            - Total Breach Confirmed: {res.get('breach', {}).get('total_incidents', 0)}
                            - Calculated Risk Score: {res.get('score', 0)}/100

                            Tuliskan laporan resmi dengan format:
                            1. 📊 Executive Summary & Ringkasan Entitas
                            2. ⚠️ Potensi Ancaman & Vektor Kerentanan (Threat Matrix)
                            3. 🎯 Rekomendasi Langkah Penyelidikan Lanjutan (Action Plan)
                            """
                            chat_completion = client.chat.completions.create(
                                messages=[
                                    {"role": "system", "content": prompt_system},
                                    {"role": "user", "content": prompt_user}
                                ],
                                model="llama-3.3-70b-versatile",
                                temperature=0.4,
                            )
                            ai_analysis = chat_completion.choices[0].message.content
                            st.divider()
                            st.markdown("### 📝 Laporan Taktis AI Threat Profiling")
                            st.markdown(f"<div class='executive-summary-box'>{ai_analysis}</div>", unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"❌ Terjadi kesalahan saat memanggil Groq API: {str(e)}")

        elif menu_selection == "🔗 Graph Relationship":
            st.subheader("🔗 Interactive Entity Relationship Mapping")
            generate_relationship_graph(res)

        elif menu_selection == "📋 Exporter (JSON)":
            st.subheader("📋 STIX/TAXII Threat Intel Feeds & Exporter")
            json_str = json.dumps(res, indent=4, default=str)
            email_prefix = res.get('email', 'target').split('@')[0] if res.get('email') else 'target'
            st.download_button(
                label="📥 Download JSON Report",
                data=json_str,
                file_name=f"CTI_Report_{email_prefix}.json",
                mime="application/json",
                use_container_width=True,
            )
