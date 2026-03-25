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
# 1. CONFIGURAZIONE E CSS AVANZATO (CORREÇÃO DA CAIXA PRETA E DISTÂNCIA)
# ==============================================================================
st.set_page_config(
    page_title="Studio R Bertin - Gestionale Professionale",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    /* Fundo Global */
    .stApp, [data-testid="stSidebar"], [data-testid="stSidebarContent"] { 
        background-color: #f4e7e1 !important; 
    }

    /* Barras de Título (Expanders) */
    .st-emotion-cache-p6495m, .st-emotion-cache-1h9bt9w, [data-testid="stExpander"] details summary {
        background-color: #bc9e92 !important;
        color: black !important;
        border-radius: 8px !important;
        border: 1px solid #a88a7e !important;
        padding: 12px !important;
        font-size: 16px !important;
    }
    
    /* Texto em Preto Negrito */
    label, p, h1, h2, h3, h4, span, li, div, .stMarkdown, [data-testid="stMetricValue"] { 
        color: black !important; 
        font-weight: 700 !important;
    }

    /* Inputs e DateInput */
    input, textarea, [data-baseweb="input"], .stDateInput div {
        background-color: white !important;
        color: black !important;
        border: 1px solid #bc9e92 !important;
    }

    /* Menus Suspensos (Fundo Branco Real) */
    div[data-baseweb="select"] > div, .stSelectbox > div > div {
        background-color: white !important;
        color: black !important;
        border: 1px solid #bc9e92 !important;
    }

    div[role="listbox"], div[data-baseweb="menu"], [data-baseweb="popover"], ul[data-testid="stSelectboxVirtualDropdown"] {
        background-color: white !important;
        color: black !important;
    }

    /* ==================== ELIMINAÇÃO DA CAIXA PRETA DO UPLOAD ==================== */
    [data-testid="stFileUploader"] {
        background-color: transparent !important;
        border: none !important;
        padding: 0 !important;
    }
    
    /* Mata o fundo preto e a área de drop */
    [data-testid="stFileUploaderSection"] {
        display: none !important;
    }

    /* Estiliza o botão Browse Files */
    [data-testid="stFileUploader"] button {
        background-color: #bc9e92 !important;
        color: black !important;
        width: 100% !important;
        border: 1px solid #a88a7e !important;
        height: 42px !important;
        margin-top: 0px !important;
    }

    /* ==================== REDUÇÃO DE VÁCUO (ESPAÇOS) ==================== */
    [data-testid="stHorizontalBlock"] {
        gap: 0.5rem !important; /* Aproxima as colunas lateralmente */
    }
    
    [data-testid="column"] {
        padding: 0 2px !important; /* Remove o vácuo interno das colunas */
    }

    /* Ajuste para alinhar verticalmente o botão de upload com os inputs */
    [data-testid="stFileUploader"] {
        margin-top: 28px !important;
    }

    /* Métricas e Botões */
    [data-testid="stMetric"] { background-color: #eaddd7 !important; padding: 15px !important; border-radius: 10px !important; border: 2px solid #bc9e92 !important; }
    button, [data-testid="baseButton-primary"] { background-color: #bc9e92 !important; color: black !important; border: 2px solid #a88a7e !important; }
    button:hover { background-color: #a88a7e !important; }

    header { visibility: hidden; }
    footer { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 2. SISTEMA DE BACK-END: GOOGLE DRIVE
# ==============================================================================
SCOPES = ["https://www.googleapis.com/auth/drive"]

def init_google_drive():
    try:
        if "gcp_service_account" not in st.secrets:
            return None, "Secret gcp_service_account não encontrada."
        info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        return build('drive', 'v3', credentials=creds), None
    except Exception as e: return None, str(e)

def manage_drive_structure(nome_cliente, srb_code):
    service, err = init_google_drive()
    if err: return None, err
    try:
        q = "name = 'GESTIONALE RBERTIN' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        res = service.files().list(q=q).execute()
        folders = res.get('files', [])
        root_id = folders[0]['id'] if folders else service.files().create(body={'name': 'GESTIONALE RBERTIN', 'mimeType': 'application/vnd.google-apps.folder'}, fields='id').execute()['id']
        folder_meta = {'name': f"{srb_code} - {nome_cliente}", 'mimeType': 'application/vnd.google-apps.folder', 'parents': [root_id]}
        return service.files().create(body=folder_meta, fields='id, webViewLink').execute(), None
    except Exception as e: return None, str(e)

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
# 3. CONTROLE DE ESTADO E LOGIN
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
TIPOS_DOC = ["", "C.I. Italiana", "Passaporto", "Permesso di Soggiorno", "Patente", "Codice Fiscale", "Tessera Sanitaria"]

st.sidebar.radio("NAVIGAZIONE", ["📊 Dashboard", "👥 Anagrafica Clienti", "📂 Nuova Pratica", "🗄️ Archivio"], key="nav_menu")
menu = st.session_state.nav_menu

if menu == "📊 Dashboard":
    st.header("📊 Dashboard")
    m1, m2 = st.columns(2)
    m1.metric("👥 Clienti", len(st.session_state.clienti))
    m2.metric("📂 Pratiche", len(st.session_state.pratiche))

elif menu == "👥 Anagrafica Clienti":
    st.header("👥 Gestione Anagrafica")
    t1, t2 = st.tabs(["➕ Registra Cliente", "📑 Lista Clienti"])
    
    with t1:
        with st.expander("📍 DATI PERSONALI", expanded=True):
            cp1, cp2 = st.columns(2)
            nome = cp1.text_input("Nome e Cognome")
            cf = cp1.text_input("Codice Fiscale")
            tel = cp2.text_input("Telefono")
            email = cp2.text_input("Email")
            
        with st.expander("🏠 INDIRIZZO", expanded=True):
            ci1, ci2, ci3 = st.columns([2, 1, 1])
            rua = ci1.text_input("Via / Piazza")
            cidade = ci2.text_input("Città")
            cap = ci3.text_input("CAP")
            regiao = st.selectbox("Regione", LISTA_REGIONI)

        with st.expander("📄 DOCUMENTI", expanded=True):
            doc_list = []
            for i in range(1, 5):
                # Colunas ajustadas para reduzir o vácuo
                d1, d2, d3, d4 = st.columns([1.1, 1.1, 0.7, 1.1])
                tipo = d1.selectbox(f"Tipo Doc {i}", TIPOS_DOC, key=f"t_doc_{i}")
                num = d2.text_input(f"Numero Doc {i}", key=f"n_doc_{i}")
                scad = d3.date_input(f"Scadenza {i}", value=date.today(), key=f"s_doc_{i}")
                file = d4.file_uploader(f"Upload {i}", key=f"f_doc_{i}")
                if tipo and num:
                    doc_list.append({"tipo": tipo, "num": num, "scad": scad, "file": file})

        if st.button("🚀 REGISTRA E SINCRONIZZA"):
            if nome and cf:
                srb_code = f"SRB{len(st.session_state.clienti)+1:04d}"
                folder_obj, error = manage_drive_structure(nome, srb_code)
                if folder_obj:
                    for d in doc_list:
                        if d['file']: upload_to_client_folder(d['file'], folder_obj['id'])
                    st.session_state.clienti.append({"ID": srb_code, "Nome": nome, "CF": cf, "Regione": regiao, "Link": folder_obj['webViewLink']})
                    st.success("✅ Salvato!")
            else: st.error("Dati mancanti.")

    with t2:
        if st.session_state.clienti: st.dataframe(pd.DataFrame(st.session_state.clienti))

elif menu == "🗄️ Archivio":
    st.header("🗄️ Archivio Drive")
    for c in st.session_state.clienti:
        st.write(f"📁 {c['ID']} - {c['Nome']} - [Apri]({c['Link']})")
