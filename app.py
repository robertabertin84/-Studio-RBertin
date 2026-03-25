import streamlit as st
import pandas as pd
from datetime import datetime, date
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import plotly.express as px

# ==========================================
# 1. CONFIGURAÇÃO E ESTILO (CORES E CAMPOS)
# ==========================================
st.set_page_config(page_title="Studio RBertin - Gestionale", layout="wide")

st.markdown(f"""
    <style>
    .stApp {{ background-color: #f4e7e1; }}
    label, p, .stMarkdown, h1, h2, h3 {{ color: #2c2c2c !important; }}

    /* Cabeçalhos Bege #bc9e92 com letras pretas */
    .streamlit-expanderHeader, div[data-testid="stExpander"] {{
        background-color: #bc9e92 !important;
        color: black !important;
        border-radius: 5px;
    }}
    .streamlit-expanderHeader p {{ color: black !important; font-weight: bold; }}

    /* Dropdowns Bege #bc9e92 com letras pretas */
    div[data-baseweb="select"] > div {{
        background-color: #bc9e92 !important;
        color: black !important;
    }}
    div[data-baseweb="select"] span {{ color: black !important; }}

    /* Campos de entrada Brancos com letras pretas */
    .stTextInput>div>div>input, .stDateInput>div>div>input {{
        background-color: white !important;
        color: black !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO GOOGLE ---
def get_google_service(name, version, scopes):
    try:
        info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        return build(name, version, credentials=creds)
    except Exception as e:
        st.error(f"Errore Google {name}: {e}"); return None

def upload_to_drive(file, folder_id):
    service = get_google_service('drive', 'v3', ["https://www.googleapis.com/auth/drive"])
    if not service or not folder_id: return None
    file_metadata = {'name': file.name, 'parents': [folder_id]}
    media = service.files().create(body=file_metadata, media_body=file, fields='id').execute()
    return media.get('id')

def cria_cartella_cliente_drive(nome, srb_code):
    service = get_google_service('drive', 'v3', ["https://www.googleapis.com/auth/drive"])
    query = "name = 'GESTIONALE RBERTIN' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(q=query, fields="files(id)").execute()
    items = results.get('files', [])
    if items:
        parent_id = items[0]['id']
        file_metadata = {'name': f"{srb_code} - {nome}", 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_id]}
        folder = service.files().create(body=file_metadata, fields='id, webViewLink').execute()
        return folder
    return None

# ==========================================
# 2. LOGIN E DATABASE
# ==========================================
if 'autenticato' not in st.session_state: st.session_state.autenticato = False
if not st.session_state.autenticato:
    st.title("🔐 Accesso Studio RBertin")
    pwd = st.text_input("Password:", type="password")
    if st.button("Entra"):
        if pwd == "RB2026": st.session_state.autenticato = True; st.rerun()
    st.stop()

if 'clienti' not in st.session_state: st.session_state.clienti = []
if 'pratiche' not in st.session_state: st.session_state.pratiche = []

DOC_TYPES = ["C.I. Italiana", "Passaporto", "Permesso di Soggiorno", "Patente", "Codice Fiscale", "Tessera Sanitaria", "Altro"]

# ==========================================
# 3. MENU E ANAGRAFICA
# ==========================================
st.sidebar.title("🏛️ Studio RBertin")
menu = st.sidebar.radio("MENU", ["Dashboard", "Anagrafica Clienti", "Nuova Pratica", "Archivio"])

if menu == "Anagrafica Clienti":
    st.header("👥 Gestione Clienti")
    tab_reg, tab_lista = st.tabs(["➕ Registra", "📑 Lista Clienti"])
    
    with tab_reg:
        with st.expander("Dati Anagrafici", expanded=True):
            col1, col2 = st.columns(2)
            nome = col1.text_input("Nome e Cognome")
            cf = col1.text_input("Codice Fiscale")
            tel = col2.text_input("Telefono")
            email = col2.text_input("Email")
            regione = col2.selectbox("Regione", ["Veneto", "Lombardia", "Lazio", "Outras..."])

        st.subheader("🗂️ Documenti (Fino a 4)")
        docs_data = []
        for i in range(1, 5):
            with st.expander(f"Documento {i}", expanded=(i==1)):
                c1, c2, c3 = st.columns(3)
                tipo = c1.selectbox(f"Tipo Doc {i}", ["-"] + DOC_TYPES, key=f"t{i}")
                num = c2.text_input(f"Numero Doc {i}", key=f"n{i}")
                scad = c3.date_input(f"Scadenza Doc {i}", key=f"s{i}")
                foto = st.file_uploader(f"Carica Immagine Doc {i}", key=f"f{i}")
                if tipo != "-":
                    docs_data.append({"tipo": tipo, "num": num, "scad": scad, "file": foto})

        if st.button("🚀 SALVA CLIENTE E DOCUMENTI"):
            if nome and cf:
                srb_num = len(st.session_state.clienti) + 1
                srb_code = f"SRB{srb_num:04d}"
                folder = cria_cartella_cliente_drive(nome, srb_code)
                
                if folder:
                    for d in docs_data:
                        if d['file']: upload_to_drive(d['file'], folder['id'])
                
                st.session_state.clienti.append({
                    "ID": srb_code, "Nome": nome, "CF": cf, "Docs": docs_data, 
                    "Drive_URL": folder['webViewLink'] if folder else "#"
                })
                st.success(f"Cliente {srb_code} salvato con successo!")
            else: st.error("Nome e CF obbligatori!")

elif menu == "Dashboard":
    st.header("📊 Dashboard")
    st.metric("Totale Clienti", len(st.session_state.clienti))
