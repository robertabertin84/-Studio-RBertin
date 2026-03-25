import streamlit as st
import pandas as pd
from datetime import datetime, date
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# ==========================================
# 1. CSS DE FORÇA TOTAL (BANIMENTO DO PRETO)
# ==========================================
st.set_page_config(page_title="Studio R Bertin", layout="wide")

st.markdown("""
    <style>
    /* FUNDO GLOBAL */
    .stApp, [data-testid="stSidebar"], [data-testid="stSidebarContent"] { 
        background-color: #f4e7e1 !important; 
    }

    /* TEXTOS SEMPRE PRETOS */
    label, p, h1, h2, h3, h4, span, li, div, .stMarkdown, [data-testid="stMetricValue"] { 
        color: black !important; 
        font-weight: 600 !important;
    }

    /* ELIMINAR FUNDOS PRETOS EM INPUTS E SELECTBOX */
    input, textarea, [data-baseweb="select"] > div, .stSelectbox div, [data-baseweb="input"] {
        background-color: white !important;
        color: black !important;
        border: 1px solid #bc9e92 !important;
    }

    /* CORRIGIR TEXTO DENTRO DOS SELECTS E DATAS */
    div[data-testid="stMarkdownContainer"] p, .stSelectbox p, div[role="listbox"] div {
        color: black !important;
    }
    
    /* BOTÕES E OLHINHO (BEGE #bc9e92) */
    button, [data-testid="baseButton-primary"], .stButton>button, button[aria-label="Show password"] {
        background-color: #bc9e92 !important;
        color: black !important;
        border: 2px solid #a88a7e !important;
        font-weight: bold !important;
    }
    
    /* ÍCONE DO OLHINHO */
    button[aria-label="Show password"] svg { fill: black !important; }

    /* CARD DE LOGIN CENTRALIZADO */
    [data-testid="stForm"] {
        max-width: 450px;
        margin: auto;
        padding: 40px;
        background-color: #f4e7e1 !important; 
        border: 2px solid #bc9e92 !important;
        border-radius: 15px;
    }

    /* SIDEBAR */
    [data-testid="stSidebarNavItems"] li {
        background-color: #bc9e92 !important;
        margin-bottom: 8px;
        border-radius: 8px;
    }

    header { visibility: hidden; }
    footer { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. FUNÇÕES GOOGLE (RESTALROU)
# ==========================================
def get_google_service(name, version, scopes):
    try:
        info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        return build(name, version, credentials=creds)
    except Exception: return None

def cria_cartella_cliente_drive(nome, srb_code):
    service = get_google_service('drive', 'v3', ["https://www.googleapis.com/auth/drive"])
    if not service: return None
    query = "name = 'GESTIONALE RBERTIN' and mimeType = 'application/vnd.google-apps.folder'"
    results = service.files().list(q=query).execute()
    items = results.get('files', [])
    if items:
        parent_id = items[0]['id']
        meta = {'name': f"{srb_code} - {nome}", 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_id]}
        return service.files().create(body=meta, fields='id, webViewLink').execute()
    return None

def upload_to_drive(file, folder_id):
    service = get_google_service('drive', 'v3', ["https://www.googleapis.com/auth/drive"])
    if not service or not folder_id: return None
    file_metadata = {'name': file.name, 'parents': [folder_id]}
    media = service.files().create(body=file_metadata, media_body=file, fields='id').execute()
    return media.get('id')

# ==========================================
# 3. LOGIN
# ==========================================
if 'autenticato' not in st.session_state: st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.write("<br><br><br>", unsafe_allow_html=True)
    with st.form("login_form"):
        st.markdown("<h2 style='text-align: center;'>⚖️ Studio R Bertin</h2>", unsafe_allow_html=True)
        pwd = st.text_input("Password:", type="password")
        if st.form_submit_button("Entra"):
            if pwd == "RB2026": 
                st.session_state.autenticato = True
                st.rerun()
            else: st.error("Password Errata")
    st.stop()

# ==========================================
# 4. GESTIONALE COMPLETO
# ==========================================
if 'clienti' not in st.session_state: st.session_state.clienti = []
if 'pratiche' not in st.session_state: st.session_state.pratiche = []

LISTA_REGIONI = ["Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna", "Friuli Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche", "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana", "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto"]
TIPOS_DOC = ["C.I. Italiana", "Passaporto", "Permesso di Soggiorno", "Patente", "Codice Fiscale", "Tessera Sanitaria"]

st.sidebar.markdown("<h2 style='text-align: center;'>⚖️ Studio R Bertin</h2>", unsafe_allow_html=True)
menu = st.sidebar.radio("NAVIGAZIONE", ["Dashboard", "Anagrafica Clienti", "Nuova Pratica", "Archivio"])

if menu == "Anagrafica Clienti":
    st.header("👥 Gestione Anagrafica")
    t1, t2 = st.tabs(["➕ Registra Cliente", "📑 Lista Clienti (SRB Order)"])
    
    with t1:
        # --- DATI PERSONALI ---
        with st.expander("📍 DATI PERSONALI", expanded=True):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Nome e Cognome")
            cf = c1.text_input("Codice Fiscale")
            tel = c2.text_input("Telefono")
            email = c2.text_input("Email")
            
        # --- INDIRIZZO (RESTAURADO) ---
        with st.expander("🏠 INDIRIZZO", expanded=True):
            c3, c4, c5 = st.columns([2, 1, 1])
            rua = c3.text_input("Via/Piazza")
            cidade = c4.text_input("Città")
            cap = c5.text_input("CAP")
            regiao = st.selectbox("Regione", LISTA_REGIONI)

        # --- DOCUMENTI (4 LINHAS CONFORME FOTO) ---
        with st.expander("📄 DOCUMENTO", expanded=True):
            for i in range(1, 5):
                col_a, col_b, col_c = st.columns([1.5, 1.5, 1])
                col_a.selectbox(f"Tipo Documento {i}", TIPOS_DOC, key=f"t{i}")
                col_b.text_input(f"Numero Documento {i}", key=f"n{i}")
                col_c.date_input(f"Scadenza Documento {i}", value=date.today(), key=f"v{i}")

        # --- ANNOTAZIONI ---
        st.subheader("📝 ANNOTAZIONI")
        notas = st.text_area("Altre Informações", height=150)

        # --- CARICAMENTO DRIVE ---
        st.subheader("🗂️ CARICAMENTO DRIVE")
        f_doc = st.file_uploader("Trascina qui i file do cliente")

        if st.button("🚀 SALVA CLIENTE COMPLETO"):
            if nome and cf:
                srb_id = f"SRB{len(st.session_state.clienti)+1:04d}"
                # Lógica de salvar e Drive...
                st.session_state.clienti.append({"ID": srb_id, "Nome": nome, "Regione": regiao})
                st.success(f"Cliente {srb_id} salvato!")
            else: st.error("Dati obbligatori mancanti!")

    with t2:
        if st.session_state.clienti:
            st.dataframe(pd.DataFrame(st.session_state.clienti), use_container_width=True)

elif menu == "Dashboard":
    st.header("📊 Dashboard")
    st.metric("Total Clienti", len(st.session_state.clienti))
