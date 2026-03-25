import streamlit as st
import pandas as pd
from datetime import datetime, date
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# ==========================================
# 1. CONFIGURAZIONE ESTETICA (RESTAURO TOTAL)
# ==========================================
st.set_page_config(page_title="Studio R Bertin", layout="wide")

st.markdown("""
    <style>
    /* Fundo Creme Global */
    .stApp, [data-testid="stSidebar"], [data-testid="stSidebarContent"] { 
        background-color: #f4e7e1 !important; 
    }

    /* Texto Preto em tudo */
    label, p, h1, h2, h3, h4, span, li, div, .stMarkdown { 
        color: black !important; 
        font-weight: 600 !important;
    }

    /* Centralização do Login */
    [data-testid="stForm"] {
        max-width: 450px;
        margin-left: auto;
        margin-right: auto;
        padding: 40px;
        background-color: #f4e7e1 !important; 
        border-radius: 15px;
        border: 2px solid #bc9e92 !important;
    }

    /* BOTÕES: Forçar Bege #bc9e92 e remover qualquer PRETO */
    button, [data-testid="baseButton-primary"], [data-testid="baseButton-secondary"], .stButton>button {
        background-color: #bc9e92 !important;
        color: black !important;
        border: 1px solid #a88a7e !important;
        font-weight: bold !important;
    }
    
    /* OLHINHO DA SENHA: Forçar Bege */
    button[aria-label="Show password"] {
        background-color: #bc9e92 !important;
        color: black !important;
    }
    button[aria-label="Show password"] svg {
        fill: black !important;
    }

    /* Input e Selectbox: Fundo Branco para visibilidade */
    input, .stSelectbox div[data-baseweb="select"] {
        background-color: white !important;
        color: black !important;
        border: 1px solid #bc9e92 !important;
    }

    /* Sidebar Menu */
    [data-testid="stSidebarNavItems"] li {
        background-color: #bc9e92 !important;
        margin-bottom: 8px;
        border-radius: 8px;
    }

    header { visibility: hidden; }
    footer { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI GOOGLE SERVICES ---
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

# ==========================================
# 2. LOGIN CENTRALIZADO
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
# 3. GESTIONALE (RESTAURADO)
# ==========================================
if 'clienti' not in st.session_state: st.session_state.clienti = []
if 'pratiche' not in st.session_state: st.session_state.pratiche = []

st.sidebar.markdown("<h2 style='text-align: center;'>⚖️ Studio R Bertin</h2>", unsafe_allow_html=True)
menu = st.sidebar.radio("NAVIGAZIONE", ["Dashboard", "Anagrafica Clienti", "Nuova Pratica", "Archivio"])

if menu == "Dashboard":
    st.header("📊 Estatísticas do Studio")
    c1, c2, c3 = st.columns(3)
    c1.metric("👥 Clienti", len(st.session_state.clienti))
    c2.metric("📂 Pratiche", len(st.session_state.pratiche))
    c3.metric("🔓 Aperte", sum(1 for p in st.session_state.pratiche if p.get("Stato") == "Aperta"))

elif menu == "Anagrafica Clienti":
    st.header("👥 Gestione Anagrafica")
    t1, t2 = st.tabs(["➕ Registra Cliente", "📑 Lista Clienti (SRB Order)"])
    
    with t1:
        with st.expander("📍 DATI PERSONALI", expanded=True):
            col1, col2 = st.columns(2)
            nome = col1.text_input("Nome e Cognome")
            cf = col1.text_input("Codice Fiscale")
            tel = col2.text_input("Telefono")
            email = col2.text_input("Email")
            
        with st.expander("🏠 INDIRIZZO", expanded=True):
            col3, col4, col5 = st.columns([2, 1, 1])
            rua = col3.text_input("Via/Piazza")
            cidade = col4.text_input("Città")
            cap = col5.text_input("CAP")
            regiao = st.selectbox("Regione", ["Lombardia", "Lazio", "Veneto", "Piemonte", "Outra"])

        with st.expander("📄 DOCUMENTO", expanded=True):
            col6, col7, col8 = st.columns(3)
            tipo_doc = col6.selectbox("Tipo Documento", ["C.I. Italiana", "Passaporto", "Permesso di Soggiorno", "Patente"])
            num_doc = col7.text_input("Numero Documento")
            val_doc = col8.date_input("Scadenza Documento", value=date.today())

        st.subheader("📝 ANNOTAZIONI")
        notas = st.text_area("Altre Informazioni")

        st.subheader("🗂️ CARICAMENTO DRIVE")
        f_doc = st.file_uploader("Trascina qui i file del cliente")

        if st.button("🚀 SALVA CLIENTE COMPLETO"):
            if nome and cf:
                srb_id = f"SRB{len(st.session_state.clienti)+1:04d}"
                # Lógica de salvar...
                st.session_state.clienti.append({
                    "ID": srb_id, "Nome": nome, "CF": cf, "Tel": tel, 
                    "Regione": regiao, "Doc": num_doc, "Scadenza": val_doc
                })
                st.success(f"Cliente {srb_id} - {nome} salvo com sucesso!")
            else: st.error("Nome e Codice Fiscale são obrigatórios!")

    with t2:
        if st.session_state.clienti:
            st.table(pd.DataFrame(st.session_state.clienti))
        else: st.info("Nessun cliente registrato.")

# Manutenção das Práticas
elif menu == "Nuova Pratica":
    st.header("📂 Nuova Pratica")
    # Código das práticas aqui...
