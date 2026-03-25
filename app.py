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
# 1. CONFIGURAZIONE E CSS AVANZATO (CORREÇÃO TOTAL DE CORES E ESPAÇOS)
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

    /* Correção de Menus Suspensos (Selectbox) */
    div[data-baseweb="select"] > div, .stSelectbox > div > div {
        background-color: white !important;
        color: black !important;
        border: 1px solid #bc9e92 !important;
    }

    div[role="listbox"], ul[data-testid="stSelectboxVirtualDropdown"], [data-baseweb="popover"] {
        background-color: white !important;
        color: black !important;
    }

    /* ==================== ELIMINAÇÃO DA CAIXA PRETA DO UPLOAD ==================== */
    [data-testid="stFileUploader"] {
        background-color: transparent !important;
        border: none !important;
        padding: 0 !important;
    }
    [data-testid="stFileUploaderSection"] {
        background-color: transparent !important;
        border: none !important;
        display: none !important; /* Esconde a zona de arrastar preta */
    }
    [data-testid="stFileUploader"] button {
        background-color: #bc9e92 !important;
        color: black !important;
        width: 100% !important;
        border-radius: 4px !important;
        border: 1px solid #a88a7e !important;
        height: 40px !important;
        margin-top: 0px !important;
    }

    /* Redução de espaço entre colunas */
    [data-testid="stHorizontalBlock"] {
        gap: 0.5rem !important;
    }
    [data-testid="column"] {
        padding: 0 2px !important;
    }

    /* Métricas */
    [data-testid="stMetric"] {
        background-color: #eaddd7 !important;
        padding: 15px !important;
        border-radius: 10px !important;
        border: 2px solid #bc9e92 !important;
    }

    /* Botões Gerais */
    button, [data-testid="baseButton-primary"] {
        background-color: #bc9e92 !important;
        color: black !important;
        border: 2px solid #a88a7e !important;
    }

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
            return None, "Secret não encontrada."
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
        root_id = folders[0]['id'] if folders else service.files().create(body={'name': 'GESTIONALE RBERTIN', 'mimeType': 'application/vnd.google-apps.folder'}, fields='id').execute()['id']
        
        folder_meta = {'name': f"{srb_code} - {nome_cliente}", 'mimeType': 'application/vnd.google-apps.folder', 'parents': [root_id]}
        return service.files().create(body=folder_meta, fields='id, webViewLink').execute(), None
    except Exception as e:
        return None, str(e)

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
    st.write("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        with st.form("login"):
            st.markdown("<h1 style='text-align: center;'>⚖️ Studio R Bertin</h1>", unsafe_allow_html=True)
            pwd = st.text_input("Password:", type="password")
            if st.form_submit_button("ACCEDI"):
                if pwd == "RB2026": 
                    st.session_state.autenticato = True
                    st.rerun()
                else: st.error("Negato.")
    st.stop()

# ==============================================================================
# 4. INTERFACE DO GESTIONALE
# ==============================================================================
LISTA_REGIONI = ["", "Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna", "Friuli Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche", "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana", "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto"]
TIPOS_DOC = ["", "C.I. Italiana", "Passaporto", "Permesso di Soggiorno", "Patente", "Codice Fiscale", "Tessera Sanitaria"]

menu = st.sidebar.radio("NAVIGAZIONE", ["📊 Dashboard", "👥 Anagrafica Clienti", "📂 Nuova Pratica", "🗄️ Archivio"])

if menu == "📊 Dashboard":
    st.header("📊 Stato Generale")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("👥 Clienti", len(st.session_state.clienti))
    m2.metric("📂 Pratiche", len(st.session_state.pratiche))
    m3.metric("🔓 Aperte", sum(1 for p in st.session_state.pratiche if p.get("Stato") == "Aperta"))
    m4.metric("🔒 Chiuse", sum(1 for p in st.session_state.pratiche if p.get("Stato") == "Chiusa"))

elif menu == "👥 Anagrafica Clienti":
    st.header("👥 Gestione Clienti")
    t1, t2 = st.tabs(["➕ Registra", "📑 Lista"])
    
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
            # Títulos das colunas apenas uma vez no topo para economizar espaço
            h1, h2, h3, h4 = st.columns([1.1, 1.1, 0.7, 1.1])
            h1.markdown("<p style='font-size:12px'>Tipo</p>", unsafe_allow_html=True)
            h2.markdown("<p style='font-size:12px'>Numero</p>", unsafe_allow_html=True)
            h3.markdown("<p style='font-size:12px'>Scadenza</p>", unsafe_allow_html=True)
            h4.markdown("<p style='font-size:12px'>File</p>", unsafe_allow_html=True)
            
            doc_list = []
            for i in range(1, 5):
                d1, d2, d3, d4 = st.columns([1.1, 1.1, 0.7, 1.1])
                tipo = d1.selectbox(f"T{i}", TIPOS_DOC, key=f"t{i}", label_visibility="collapsed")
                num = d2.text_input(f"N{i}", key=f"n{i}", label_visibility="collapsed")
                scad = d3.date_input(f"S{i}", value=date.today(), key=f"s{i}", label_visibility="collapsed")
                file = d4.file_uploader(f"F{i}", key=f"f{i}", label_visibility="collapsed")
                if tipo and num:
                    doc_list.append({"tipo": tipo, "num": num, "scad": scad, "file": file})

        if st.button("🚀 SALVA CLIENTE"):
            if nome and cf:
                srb_code = f"SRB{len(st.session_state.clienti)+1:04d}"
                f_obj, err = manage_drive_structure(nome, srb_code)
                if f_obj:
                    for d in doc_list:
                        if d['file']: upload_to_client_folder(d['file'], f_obj['id'])
                    st.session_state.clienti.append({"ID": srb_code, "Nome": nome, "CF": cf, "Regione": regiao, "Link": f_obj['webViewLink']})
                    st.success("Salvato!")
            else: st.error("Nome/CF mancano!")

    with t2:
        if st.session_state.clienti: st.dataframe(pd.DataFrame(st.session_state.clienti))

elif menu == "📂 Nuova Pratica":
    st.header("📂 Nuova Pratica")
elif menu == "🗄️ Archivio":
    st.header("🗄️ Archivio")
    for c in st.session_state.clienti:
        st.write(f"📁 {c['ID']} - {c['Nome']} - [Link Drive]({c['Link']})")
