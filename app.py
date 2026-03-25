import streamlit as st
import pandas as pd
from datetime import datetime, date
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# ==========================================
# 1. CONFIGURAZIONE ESTETICA (ZERO NERO)
# ==========================================
st.set_page_config(page_title="Studio RBertin - Gestionale", layout="wide")

st.markdown("""
    <style>
    /* Fundo Global e Lateral Creme #f4e7e1 */
    .stApp, [data-testid="stSidebar"], [data-testid="stSidebarContent"], [data-testid="stSidebarNav"] { 
        background-color: #f4e7e1 !important; 
    }

    /* Forçar texto preto em todos os elementos */
    label, p, h1, h2, h3, h4, span, li, div, .stMarkdown { 
        color: black !important; 
        font-weight: 500;
    }

    /* Barras de Expander e Cabeçalhos em Bege #bc9e92 */
    .streamlit-expanderHeader, div[data-testid="stExpander"], 
    header[data-testid="stHeader"], .stTabs [data-baseweb="tab-list"] {
        background-color: #bc9e92 !important;
        color: black !important;
        border-radius: 8px;
        border: none !important;
    }

    /* Menu Lateral: Itens em Bege com texto preto */
    [data-testid="stSidebarNavItems"] li {
        background-color: #bc9e92 !important;
        margin-bottom: 8px;
        border-radius: 5px;
    }
    
    /* Remover fundo preto do item de menu selecionado */
    [data-testid="stSidebarNavItems"] li [aria-current="page"] {
        background-color: #a88a7e !important;
        color: white !important;
        border-radius: 5px;
    }

    /* Campos de Input Brancos (Contraste para leitura) */
    input, textarea, [data-baseweb="input"], .stSelectbox div {
        background-color: white !important;
        color: black !important;
    }
    
    /* Botões em Bege com borda sutil */
    button[kind="primary"], button[kind="secondary"], .stButton>button {
        background-color: #bc9e92 !important;
        color: black !important;
        border: 1px solid #a88a7e !important;
    }

    /* Esconder elementos padrão que podem vir pretos */
    header { visibility: hidden; }
    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI GOOGLE SERVICES ---
def get_google_service(name, version, scopes):
    try:
        info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        return build(name, version, credentials=creds)
    except Exception as e:
        st.error(f"Errore Google: {e}"); return None

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
# 2. LOGIN E ESTADO DA SESSÃO
# ==========================================
if 'autenticato' not in st.session_state: st.session_state.autenticato = False
if not st.session_state.autenticato:
    st.title("🏛️ Accesso Studio RBertin")
    pwd = st.text_input("Password:", type="password")
    if st.button("Entra"):
        if pwd == "RB2026": 
            st.session_state.autenticato = True
            st.rerun()
        else: st.error("Password Errata")
    st.stop()

if 'clienti' not in st.session_state: st.session_state.clienti = []
if 'pratiche' not in st.session_state: st.session_state.pratiche = []

LISTA_REGIONI = ["Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna", "Friuli Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche", "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana", "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto"]
DOC_TYPES = ["C.I. Italiana", "Passaporto", "Permesso di Soggiorno", "Patente", "Codice Fiscale", "Tessera Sanitaria", "Altro"]

# ==========================================
# 3. INTERFACE E NAVEGAÇÃO
# ==========================================
st.sidebar.title("🏛️ Studio RBertin")
menu = st.sidebar.radio("NAVIGAZIONE", ["Dashboard", "Anagrafica Clienti", "Nuova Pratica", "Archivio"])

# --- DASHBOARD (MAPA REMOVIDO) ---
if menu == "Dashboard":
    st.header("📊 Riepilogo Statistiche")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👥 Clienti", len(st.session_state.clienti))
    c2.metric("📂 Pratiche", len(st.session_state.pratiche))
    c3.metric("🔓 Aperte", sum(1 for p in st.session_state.pratiche if p.get("Stato") == "Aperta"))
    c4.metric("🔒 Chiuse", sum(1 for p in st.session_state.pratiche if p.get("Stato") == "Chiusa"))

    st.write("---")
    st.subheader("📍 Distribuzione per Regione")
    if st.session_state.clienti:
        df = pd.DataFrame(st.session_state.clienti)
        st.bar_chart(df['Regione'].value_counts(), color="#bc9e92")
    else: st.info("Nessun cliente registrato.")

# --- ANAGRAFICA ---
elif menu == "Anagrafica Clienti":
    st.header("👥 Gestione Clienti e Documenti")
    t_reg, t_list = st.tabs(["➕ Registra Cliente", "📑 Lista Clienti"])
    
    with t_reg:
        with st.expander("📍 DATI PERSONALI", expanded=True):
            col1, col2 = st.columns(2)
            nome = col1.text_input("Nome e Cognome")
            cf = col1.text_input("Codice Fiscale")
            regione = col2.selectbox("Regione", LISTA_REGIONI)
            tel = col2.text_input("Telefono")

        st.subheader("🗂️ DOCUMENTI (Drive)")
        f_doc = st.file_uploader("Carica Documento (PDF/JPG)")

        if st.button("🚀 SALVA CLIENTE"):
            if nome and cf:
                srb_code = f"SRB{len(st.session_state.clienti) + 1:04d}"
                folder = cria_cartella_cliente_drive(nome, srb_code)
                if folder and f_doc:
                    upload_to_drive(f_doc, folder['id'])
                
                st.session_state.clienti.append({
                    "ID": srb_code, "Nome": nome, "CF": cf, "Regione": regione,
                    "Drive_URL": folder['webViewLink'] if folder else "#"
                })
                st.success(f"✅ Cliente {srb_code} salvato!")
            else: st.error("Nome e CF são obrigatórios!")

    with t_list:
        if st.session_state.clienti:
            df_display = pd.DataFrame(st.session_state.clienti)
            st.dataframe(df_display[["ID", "Nome", "Regione"]], use_container_width=True)
        else: st.info("Nessun cliente in lista.")

# --- PRATICHE ---
elif menu == "Nuova Pratica":
    st.header("📂 Apertura Pratica")
    if st.session_state.clienti:
        st.selectbox("Seleziona Cliente", [c["Nome"] for c in st.session_state.clienti])
        st.selectbox("Tipo Pratica", ["FISCO", "CONSOLARI", "PA"])
        if st.button("Crea"): st.success("Pratica creata!")
    else: st.warning("Crea prima um cliente!")

elif menu == "Archivio":
    st.header("🗄️ Archivio Storico")
    st.write("Le pratiche concluse appariranno qui.")
