import streamlit as st
import pandas as pd
from datetime import datetime, date
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# ==========================================
# 1. CONFIGURAZIONE ESTETICA TOTALE (NO NERO)
# ==========================================
st.set_page_config(page_title="Studio RBertin - Gestionale", layout="wide")

st.markdown(f"""
    <style>
    /* 1. Fundo Global e da Barra Lateral claro #f4e7e1 */
    .stApp, [data-testid="stSidebar"], [data-testid="stSidebarContent"], [data-testid="stSidebarNav"] {{ 
        background-color: #f4e7e1 !important; 
    }}

    /* 2. Forçar texto preto em tudo */
    label, p, h1, h2, h3, h4, span, li, div, .stMarkdown {{ 
        color: black !important; 
        font-weight: 500; 
    }}

    /* 3. Botões, Expanders e Cabeçalhos (Bege #bc9e92) */
    .streamlit-expanderHeader, div[data-testid="stExpander"], 
    div[data-baseweb="select"] > div,
    header[data-testid="stHeader"],
    button[kind="primary"], button[kind="secondary"] {{
        background-color: #bc9e92 !important;
        color: black !important;
        border: none !important;
    }}

    /* 4. Menu Lateral (Nav Items) - Fundo Creme e Itens Bege */
    [data-testid="stSidebarNavItems"] li {{
        background-color: #bc9e92 !important;
        margin-bottom: 8px;
        border-radius: 5px;
    }}
    [data-testid="stSidebarNavItems"] li a {{
        background-color: transparent !important;
        color: black !important;
    }}
    /* Item selecionado no menu */
    [data-testid="stSidebarNavItems"] li [aria-current="page"] {{
        background-color: #a88a7e !important;
        color: white !important;
    }}

    /* 5. Campos de Entrada e Password (Branco para leitura) */
    input, textarea, [data-baseweb="input"] {{
        background-color: white !important;
        color: black !important;
    }}
    
    /* 6. Remover a linha preta do topo */
    header {{ visibility: hidden; }}
    
    /* 7. Estilo específico para o campo de senha e botão 'Entra' */
    div[data-testid="stForm"] {{
        background-color: #f4e7e1 !important;
        border: 1px solid #bc9e92;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI GOOGLE SERVICES ---
def get_google_service(name, version, scopes):
    try:
        info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        return build(name, version, credentials=creds)
    except Exception as e:
        st.error(f"Errore Google {name}: {e}"); return None

def cria_cartella_cliente_drive(nome, srb_code):
    service = get_google_service('drive', 'v3', ["https://www.googleapis.com/auth/drive"])
    if not service: return None
    query = "name = 'GESTIONALE RBERTIN' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(q=query, fields="files(id)").execute()
    items = results.get('files', [])
    if items:
        parent_id = items[0]['id']
        file_metadata = {'name': f"{srb_code} - {nome}", 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_id]}
        folder = service.files().create(body=file_metadata, fields='id, webViewLink').execute()
        return folder
    return None

def upload_to_drive(file, folder_id):
    service = get_google_service('drive', 'v3', ["https://www.googleapis.com/auth/drive"])
    if not service or not folder_id: return None
    file_metadata = {'name': file.name, 'parents': [folder_id]}
    media = service.files().create(body=file_metadata, media_body=file, fields='id').execute()
    return media.get('id')

# ==========================================
# 2. LOGIN E BANCO DE DADOS
# ==========================================
if 'autenticato' not in st.session_state: st.session_state.autenticato = False
if not st.session_state.autenticato:
    st.title("🏛️ Studio RBertin")
    with st.container():
        pwd = st.text_input("Password Studio RBertin:", type="password")
        if st.button("Entra"):
            if pwd == "RB2026": 
                st.session_state.autenticato = True
                st.rerun()
            else:
                st.error("Password Errata")
    st.stop()

if 'clienti' not in st.session_state: st.session_state.clienti = []
if 'pratiche' not in st.session_state: st.session_state.pratiche = []

LISTA_REGIONI = ["Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna", "Friuli Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche", "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana", "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto"]

# ==========================================
# 3. INTERFACE E NAVEGAÇÃO
# ==========================================
st.sidebar.title("🏛️ Studio RBertin")
menu = st.sidebar.radio("NAVIGAZIONE", ["Dashboard", "Anagrafica Clienti", "Nuova Pratica", "Archivio"])

# --- DASHBOARD SEM MAPA ---
if menu == "Dashboard":
    st.header("📊 Dashboard Riepilogativa")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👥 Clienti", len(st.session_state.clienti))
    c2.metric("📂 Pratiche", len(st.session_state.pratiche))
    c3.metric("🔓 Aperte", sum(1 for p in st.session_state.pratiche if p.get("Stato") == "Aperta"))
    c4.metric("🔒 Chiuse", sum(1 for p in st.session_state.pratiche if p.get("Stato") == "Chiusa"))

    st.write("---")
    st.subheader("📋 Ultime Attività")
    if st.session_state.clienti:
        st.write(f"Ultimo cliente aggiunto: **{st.session_state.clienti[-1]['Nome']}**")
    else:
        st.info("Nessun dado ancora registrato.")

# --- ANAGRAFICA ---
elif menu == "Anagrafica Clienti":
    st.header("👥 Gestione Clienti")
    t_reg, t_list = st.tabs(["➕ Nuovo Cliente", "📑 Elenco Clienti"])
    
    with t_reg:
        with st.expander("📍 DATI PERSONALI", expanded=True):
            col1, col2 = st.columns(2)
            nome = col1.text_input("Nome e Cognome")
            cf = col1.text_input("Codice Fiscale")
            regione = col2.selectbox("Regione", LISTA_REGIONI)
            tel = col2.text_input("Telefono")

        if st.button("🚀 SALVA CLIENTE"):
            if nome and cf:
                srb_code = f"SRB{len(st.session_state.clienti) + 1:04d}"
                st.session_state.clienti.append({
                    "ID": srb_code, "Nome": nome, "CF": cf, "Regione": região, "Tel": tel
                })
                st.success(f"✅ Cliente {srb_code} salvato!")
            else: st.error("Nome e CF obbligatori!")

    with t_list:
        if st.session_state.clienti:
            st.dataframe(pd.DataFrame(st.session_state.clienti), use_container_width=True)
        else: st.info("Elenco vuoto.")

# --- PRATICHE E ARCHIVIO ---
elif menu == "Nuova Pratica":
    st.header("📂 Nuova Pratica")
    if st.session_state.clienti:
        st.selectbox("Seleziona Cliente", [c["Nome"] for c in st.session_state.clienti])
        st.selectbox("Tipo Pratica", ["FISCO", "CONSOLARI", "PA", "ALTRO"])
        if st.button("Apri Pratica"):
            st.success("Pratica registrata!")
    else: st.warning("Crea prima um cliente!")

elif menu == "Archivio":
    st.header("🗄️ Archivio")
    st.info("Qui verranno visualizzate le pratiche chiuse.")
