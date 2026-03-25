import streamlit as st
import pandas as pd
from datetime import datetime, date
import io
import time
import os
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

st.markdown("""
    <style>
    .stApp, [data-testid="stSidebar"], [data-testid="stSidebarContent"] { background-color: #f4e7e1 !important; }
    [data-testid="stExpander"] details summary {
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
    [data-testid="stFileUploader"] section {
        background-color: transparent !important;
        border: 2px dashed #bc9e92 !important;
        border-radius: 8px !important;
    }
    button, .stButton > button {
        background-color: #bc9e92 !important;
        color: black !important;
        border: 2px solid #a88a7e !important;
        font-weight: 700 !important;
        height: 52px !important;
    }
    header, footer { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 2. SISTEMA DE BACK-END: GOOGLE DRIVE
# ==============================================================================
SCOPES = ["https://www.googleapis.com/auth/drive"]

def init_google_drive():
    try:
        if "gcp_service_account" not in st.secrets: return None, "Secret missing"
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

def upload_to_client_folder(file_obj, folder_id, new_filename):
    service, _ = init_google_drive()
    if not service: return False
    try:
        meta = {'name': new_filename, 'parents': [folder_id]}
        media = MediaIoBaseUpload(io.BytesIO(file_obj.read()), mimetype=file_obj.type, resumable=True)
        service.files().create(body=meta, media_body=media).execute()
        return True
    except: return False

# ==============================================================================
# 3. LOGIN
# ==============================================================================
if 'autenticato' not in st.session_state: st.session_state.autenticato = False
if 'clienti' not in st.session_state: st.session_state.clienti = []

if not st.session_state.autenticato:
    c_log1, c_log2, c_log3 = st.columns([1, 1.5, 1])
    with c_log2:
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
# 4. INTERFACE
# ==============================================================================
LISTA_REGIONI = ["", "Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna", "Friuli Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche", "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana", "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto"]

st.sidebar.title("Menu Studio")
menu = st.sidebar.radio("NAVIGAZIONE", ["📊 Dashboard", "👥 Anagrafica Clienti", "🗄️ Archivio"])

if menu == "👥 Anagrafica Clienti":
    st.header("👥 Gestione Anagrafica")
    t1, t2 = st.tabs(["➕ Registra Cliente", "📑 Lista"])
    
    with t1:
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

        with st.expander("📄 DOCUMENTI", expanded=True):
            st.markdown("<p style='font-size: 13px;'>Inserisci i numeri e le scadenze. Carica i file in fondo.</p>", unsafe_allow_html=True)
            
            # Lista fixa de documentos solicitada
            DOCS_FIXOS = [
                "Carta d'Identità", 
                "Permesso di Soggiorno", 
                "Patente Italiana", 
                "Tessera Sanitaria", 
                "Passaporto Brasiliano"
            ]
            
            doc_entries = []
            # Cabeçalho da tabela
            h1, h2, h3 = st.columns([1.5, 1, 1])
            h1.markdown("**Documento**")
            h2.markdown("**Numero**")
            h3.markdown("**Scadenza**")

            for doc_name in DOCS_FIXOS:
                col1, col2, col3 = st.columns([1.5, 1, 1])
                col1.write(f"**{doc_name}**")
                n_val = col2.text_input("Numero", key=f"num_{doc_name}", label_visibility="collapsed", placeholder="Numero")
                # Formato de data ajustado visualmente pelo format="DD/MM/YYYY"
                s_val = col3.date_input("Scadenza", value=date.today(), key=f"scad_{doc_name}", label_visibility="collapsed", format="DD/MM/YYYY")
                
                if n_val:
                    doc_entries.append({"tipo": doc_name, "num": n_val, "scad": s_val})

        st.subheader("📤 Upload Documenti")
        uploaded_files = st.file_uploader("Trascina qui i file (Seleziona più file)", accept_multiple_files=True)

        if st.button("🚀 REGISTRA CLIENTE E SINCRONIZZA DRIVE"):
            if nome and cf:
                srb_code = f"SRB{len(st.session_state.clienti)+1:04d}"
                with st.spinner("Sincronizzazione Drive..."):
                    folder_obj, error = manage_drive_structure(nome, srb_code)
                    if folder_obj:
                        # Upload associando os arquivos às entradas da tabela
                        for idx, file in enumerate(uploaded_files):
                            if idx < len(doc_entries):
                                d = doc_entries[idx]
                                # Nome do arquivo no Drive: Tipo_Numero.extensao
                                ext = os.path.splitext(file.name)[1]
                                new_name = f"{d['tipo']}_{d['num']}{ext}"
                                upload_to_client_folder(file, folder_obj['id'], new_name)
                        
                        st.session_state.clienti.append({"ID": srb_code, "Nome": nome, "CF": cf, "Regione": regiao, "Link": folder_obj['webViewLink']})
                        st.success(f"✅ Cliente {nome} salvato!")
                    else: st.error(f"Errore: {error}")
            else: st.error("Nome e Codice Fiscale obbligatori!")

    with t2:
        if st.session_state.clienti:
            st.dataframe(pd.DataFrame(st.session_state.clienti), use_container_width=True)

elif menu == "📊 Dashboard":
    st.header("📊 Dashboard")
    st.metric("Clienti Totali", len(st.session_state.clienti))
    if st.session_state.clienti:
        df = pd.DataFrame(st.session_state.clienti)
        st.bar_chart(df['Regione'].value_counts())

elif menu == "🗄️ Archivio":
    st.header("🗄️ Archivio")
    for c in st.session_state.clienti:
        st.write(f"📁 {c['ID']} - {c['Nome']} - [Apri Drive]({c['Link']})")
