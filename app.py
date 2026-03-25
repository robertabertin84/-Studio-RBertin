import streamlit as st
import pandas as pd
from datetime import datetime, date
import io
import time
import os
import base64
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ==============================================================================
# 1. CONFIGURAZIONE E CSS AVANZATO
# ==============================================================================
st.set_page_config(
    page_title="Studio R Bertin - Gestionale Professionale",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS (mantenuto quello che funzionava)
st.markdown("""
    <style>
    .stApp, [data-testid="stSidebar"], [data-testid="stSidebarContent"] { 
        background-color: #f4e7e1 !important; 
    }
    .st-emotion-cache-p6495m, .st-emotion-cache-1h9bt9w, [data-testid="stExpander"] details summary {
        background-color: #bc9e92 !important;
        color: black !important;
        border-radius: 8px !important;
        border: 1px solid #a88a7e !important;
        padding: 12px !important;
    }
    label, p, h1, h2, h3, h4, span, li, div, .stMarkdown, [data-testid="stMetricValue"] { 
        color: black !important; 
        font-weight: 700 !important;
    }
    input, textarea, [data-baseweb="input"], .stDateInput div {
        background-color: white !important;
        color: black !important;
        border: 1px solid #bc9e92 !important;
    }
    [data-baseweb="select"] > div, div[role="listbox"], div[role="listbox"] ul, div[role="listbox"] li,
    div[data-baseweb="menu"], [data-baseweb="popover"] {
        background-color: #f3f2f1 !important;
        color: black !important;
    }
    div[role="listbox"] li:hover {
        background-color: #e8e6e4 !important;
    }
    .stDateInput input, .stDateInput > div > div {
        background-color: #f3f2f1 !important;
        color: black !important;
    }
    [data-testid="stFileUploader"] {
        background-color: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin-top: 10px !important;
    }
    [data-testid="stFileUploaderSection"] {
        display: none !important;
    }
    [data-testid="stFileUploader"] button {
        background-color: #bc9e92 !important;
        color: black !important;
        width: 100% !important;
        border-radius: 4px !important;
        border: 1px solid #a88a7e !important;
        height: 42px !important;
    }
    button, [data-testid="baseButton-primary"] {
        background-color: #bc9e92 !important;
        color: black !important;
        border: 2px solid #a88a7e !important;
    }
    button:hover { background-color: #a88a7e !important; }
    header { visibility: hidden; }
    footer { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 2. SISTEMA DI BACK-END: GOOGLE DRIVE
# ==============================================================================
SCOPES = ["https://www.googleapis.com/auth/drive"]

def init_google_drive():
    try:
        if "gcp_service_account" not in st.secrets:
            return None, "Secret gcp_service_account non trovata."
        info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        return build('drive', 'v3', credentials=creds), None
    except Exception as e:
        return None, str(e)

def manage_drive_structure(nome_cliente, srb_code):
    service, err = init_google_drive()
    if err: return None, err
    
    try:
        q = "name = 'GESTIONALE RBERTIN' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        res = service.files().list(q=q).execute()
        folders = res.get('files', [])
        
        if not folders:
            meta = {'name': 'GESTIONALE RBERTIN', 'mimeType': 'application/vnd.google-apps.folder'}
            root = service.files().create(body=meta, fields='id').execute()
            root_id = root['id']
        else:
            root_id = folders[0]['id']
            
        folder_meta = {
            'name': f"{srb_code} - {nome_cliente}",
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [root_id]
        }
        new_folder = service.files().create(body=folder_meta, fields='id, webViewLink').execute()
        return new_folder, None
    except Exception as e:
        return None, f"Errore Drive: {e}"

def upload_to_client_folder(file_obj, folder_id):
    service, _ = init_google_drive()
    if not service: return False
    try:
        meta = {'name': file_obj.name, 'parents': [folder_id]}
        media = MediaIoBaseUpload(io.BytesIO(file_obj.read()), mimetype=file_obj.type, resumable=True)
        service.files().create(body=meta, media_body=media).execute()
        return True
    except: return False

# ==============================================================================
# 3. CONTROLE DI STATO E LOGIN
# ==============================================================================
if 'autenticato' not in st.session_state: st.session_state.autenticato = False
if 'clienti' not in st.session_state: st.session_state.clienti = []
if 'pratiche' not in st.session_state: st.session_state.pratiche = []

if not st.session_state.autenticato:
    st.write("<br><br><br>", unsafe_allow_html=True)
    c_log1, c_log2, c_log3 = st.columns([1, 1.5, 1])
    with c_log2:
        with st.form("login_form"):
            st.markdown("<h1 style='text-align: center;'>⚖️ Studio R Bertin</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center;'>Accesso Riservato</p>", unsafe_allow_html=True)
            pwd = st.text_input("Inserire Password:", type="password")
            if st.form_submit_button("ACCEDI"):
                if pwd == "RB2026": 
                    st.session_state.autenticato = True
                    st.rerun()
                else: st.error("Accesso Negato.")
    st.stop()

# ==============================================================================
# 4. INTERFACE DO GESTIONALE
# ==============================================================================
LISTA_REGIONI = ["", "Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna", "Friuli Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche", "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana", "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto"]

st.sidebar.markdown("<h2 style='text-align: center;'>Menu Studio</h2>", unsafe_allow_html=True)
menu = st.sidebar.radio("NAVIGAZIONE", ["📊 Dashboard", "👥 Anagrafica Clienti", "📂 Nuova Pratica", "🗄️ Archivio"])

# --- DASHBOARD ---
if menu == "📊 Dashboard":
    st.header("📊 Stato Generale dello Studio")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("👥 Clienti Totali", len(st.session_state.clienti))
    m2.metric("📂 Pratiche Totali", len(st.session_state.pratiche))
    m3.metric("🔓 Pratiche Aperte", sum(1 for p in st.session_state.pratiche if p.get("Stato") == "Aperta"))
    m4.metric("🔒 Pratiche Chiuse", sum(1 for p in st.session_state.pratiche if p.get("Stato") == "Chiusa"))
    
    st.write("---")
    if st.session_state.clienti:
        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            st.subheader("📍 Geografia Clienti")
            df_cli = pd.DataFrame(st.session_state.clienti)
            st.bar_chart(df_cli['Regione'].value_counts())

# --- ANAGRAFICA CLIENTI (CON LE MODIFICHE RICHIESTE) ---
elif menu == "👥 Anagrafica Clienti":
    st.header("👥 Gestione Anagrafica e Documentale")
    t_aba1, t_aba2 = st.tabs(["➕ Registra Cliente", "📑 Lista Clienti (SRB Order)"])
    
    with t_aba1:
        with st.expander("📍 DATI PERSONALI", expanded=True):
            cp1, cp2 = st.columns(2)
            nome = cp1.text_input("Nome e Cognome")
            cf = cp1.text_input("Codice Fiscale")
            tel = cp2.text_input("Telefono (WhatsApp)")
            email = cp2.text_input("Indirizzo Email")
            
        with st.expander("🏠 INDIRIZZO", expanded=True):
            ci1, ci2, ci3 = st.columns([2, 1, 1])
            rua = ci1.text_input("Via / Piazza e Civico")
            cidade = ci2.text_input("Città")
            cap = ci3.text_input("CAP")
            regiao = st.selectbox("Regione", LISTA_REGIONI)

        # SEZIONE DOCUMENTI - Formato originale + nomi modificati
        with st.expander("📄 DOCUMENTI (Caricamento Singolo)", expanded=True):
            st.markdown("<p style='font-size: 13px;'>Seleziona il tipo e carica il file. Il sistema creerà automaticamente la cartella nel Drive.</p>", unsafe_allow_html=True)
            
            doc_list = []
            # Documento 1
            d1, d2, d3, d4 = st.columns([1.3, 1.1, 0.9, 1.1])
            st.markdown("**Carta d'Identità**", unsafe_allow_html=True)
            num1 = d2.text_input("Numero", key="n_doc_1")
            scad1 = d3.date_input("Scadenza", value=date.today(), key="s_doc_1", format="DD/MM/YYYY")
            file1 = d4.file_uploader("Upload", key="f_doc_1")
            if num1: doc_list.append({"tipo": "CartaIdentita", "num": num1, "scad": scad1, "file": file1})

            # Documento 2
            d1, d2, d3, d4 = st.columns([1.3, 1.1, 0.9, 1.1])
            st.markdown("**Permesso di Soggiorno**", unsafe_allow_html=True)
            num2 = d2.text_input("Numero", key="n_doc_2")
            scad2 = d3.date_input("Scadenza", value=date.today(), key="s_doc_2", format="DD/MM/YYYY")
            file2 = d4.file_uploader("Upload", key="f_doc_2")
            if num2: doc_list.append({"tipo": "PermessoSoggiorno", "num": num2, "scad": scad2, "file": file2})

            # Documento 3
            d1, d2, d3, d4 = st.columns([1.3, 1.1, 0.9, 1.1])
            st.markdown("**Patente Italiana**", unsafe_allow_html=True)
            num3 = d2.text_input("Numero", key="n_doc_3")
            scad3 = d3.date_input("Scadenza", value=date.today(), key="s_doc_3", format="DD/MM/YYYY")
            file3 = d4.file_uploader("Upload", key="f_doc_3")
            if num3: doc_list.append({"tipo": "PatenteItaliana", "num": num3, "scad": scad3, "file": file3})

            # Documento 4
            d1, d2, d3, d4 = st.columns([1.3, 1.1, 0.9, 1.1])
            st.markdown("**Tessera Sanitaria**", unsafe_allow_html=True)
            num4 = d2.text_input("Numero", key="n_doc_4")
            scad4 = d3.date_input("Scadenza", value=date.today(), key="s_doc_4", format="DD/MM/YYYY")
            file4 = d4.file_uploader("Upload", key="f_doc_4")
            if num4: doc_list.append({"tipo": "TesseraSanitaria", "num": num4, "scad": scad4, "file": file4})

            # Documento 5 - Passaporto Brasiliano
            d1, d2, d3, d4 = st.columns([1.3, 1.1, 0.9, 1.1])
            st.markdown("**Passaporto Brasiliano**", unsafe_allow_html=True)
            num5 = d2.text_input("Numero", key="n_doc_5")
            scad5 = d3.date_input("Scadenza", value=date.today(), key="s_doc_5", format="DD/MM/YYYY")
            file5 = d4.file_uploader("Upload", key="f_doc_5")
            if num5: doc_list.append({"tipo": "PassaportoBrasiliano", "num": num5, "scad": scad5, "file": file5})

        st.subheader("ANNOTAZIONI CLIENTE")
        notas = st.text_area("ANNOTAZIONI CLIENTE", height=120)

        if st.button("🚀 REGISTRA CLIENTE E SINCRONIZZA DRIVE"):
            if nome and cf:
                srb_code = f"SRB{len(st.session_state.clienti)+1:04d}"
                with st.spinner("Creazione cartella Drive in corso..."):
                    folder_obj, error = manage_drive_structure(nome, srb_code)
                    if folder_obj:
                        for d in doc_list:
                            if d.get('file'):
                                upload_to_client_folder(d['file'], folder_obj['id'])
                        
                        st.session_state.clienti.append({
                            "ID": srb_code, "Nome": nome, "CF": cf, "Regione": regiao,
                            "Link": folder_obj['webViewLink']
                        })
                        st.success(f"✅ Cliente {srb_code} salvato con successo!")
                    else: 
                        st.error(f"Errore Drive: {error}")
            else: 
                st.error("Inserire almeno Nome e Codice Fiscale!")

    with t_aba2:
        if st.session_state.clienti:
            st.dataframe(pd.DataFrame(st.session_state.clienti), use_container_width=True)

# --- ALTRE PAGINE (tutto ripristinato) ---
elif menu == "📂 Nuova Pratica":
    st.header("📂 Apertura Nuova Pratica")
    
elif menu == "🗄️ Archivio":
    st.header("🗄️ Archivio Documentale Drive")
    for c in st.session_state.clienti:
        st.write(f"📁 {c['ID']} - {c['Nome']} - [Apri Cartella]({c['Link']})")
