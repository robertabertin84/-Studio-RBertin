import streamlit as st
import pandas as pd
from datetime import datetime, date
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# ==========================================
# 1. CONFIGURAZIONE ESTETICA (FORZA TOTALE)
# ==========================================
st.set_page_config(page_title="Studio R Bertin", layout="wide")

st.markdown("""
    <style>
    /* 1. Fundo Global e Lateral Creme */
    .stApp, [data-testid="stSidebar"], [data-testid="stSidebarContent"] { 
        background-color: #f4e7e1 !important; 
    }

    /* 2. Texto Preto em Tudo */
    label, p, h1, h2, h3, h4, span, li, div, .stMarkdown { 
        color: black !important; 
        font-weight: 500;
    }

    /* 3. Centralização e Caixa de Login */
    [data-testid="stForm"] {
        max-width: 400px;
        margin-left: auto;
        margin-right: auto;
        padding: 40px;
        background-color: #f4e7e1 !important; 
        border-radius: 15px;
        border: 2px solid #bc9e92 !important;
    }

    /* 4. FORÇAR COR DO BOTÃO (QUALQUER BOTÃO) */
    /* Isso cobre botões normais e botões de formulário */
    button, [data-testid="baseButton-primary"], [data-testid="baseButton-secondary"], .stButton>button {
        background-color: #bc9e92 !important;
        color: black !important;
        border: 1px solid #a88a7e !important;
        font-weight: bold !important;
        opacity: 1 !important;
    }
    
    /* Garantir que o texto continue preto no hover (passar o mouse) */
    button:hover {
        border: 1px solid black !important;
        color: black !important;
    }

    /* 5. FORÇAR COR DO OLHINHO (👁️) */
    button[aria-label="Show password"] {
        background-color: #bc9e92 !important;
        color: black !important;
    }
    button[aria-label="Show password"] svg {
        fill: black !important;
    }

    /* 6. Barra Lateral e Itens de Menu */
    [data-testid="stSidebarNavItems"] li {
        background-color: #bc9e92 !important;
        margin-bottom: 8px;
        border-radius: 8px;
    }

    /* 7. Inputs Brancos */
    input, .stSelectbox div {
        background-color: white !important;
        color: black !important;
    }

    header { visibility: hidden; }
    footer { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI GOOGLE SERVICES (FULL) ---
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
# 2. LOGIN CENTRALIZADO (Studio R Bertin)
# ==========================================
if 'autenticato' not in st.session_state: st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.write("<br><br><br><br>", unsafe_allow_html=True)
    with st.form("login_form"):
        st.markdown("<h2 style='text-align: center;'>⚖️ Studio R Bertin</h2>", unsafe_allow_html=True)
        pwd = st.text_input("Password:", type="password")
        # Botão de Login
        if st.form_submit_button("Entra"):
            if pwd == "RB2026": 
                st.session_state.autenticato = True
                st.rerun()
            else:
                st.error("Password Errata")
    st.stop()

# ==========================================
# 3. GESTIONALE (PÓS-LOGIN)
# ==========================================
if 'clienti' not in st.session_state: st.session_state.clienti = []
if 'pratiche' not in st.session_state: st.session_state.pratiche = []

LISTA_REGIONI = ["Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna", "Friuli Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche", "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana", "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto"]
DOC_TYPES = ["C.I. Italiana", "Passaporto", "Permesso di Soggiorno", "Patente", "Codice Fiscale", "Tessera Sanitaria", "Altro"]

st.sidebar.markdown("<h2 style='text-align: center;'>⚖️ Studio R Bertin</h2>", unsafe_allow_html=True)
menu = st.sidebar.radio("NAVIGAZIONE", ["Dashboard", "Anagrafica Clienti", "Nuova Pratica", "Archivio"])

# --- DASHBOARD ---
if menu == "Dashboard":
    st.header("📊 Riepilogo Statistiche")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👥 Clienti", len(st.session_state.clienti))
    c2.metric("📂 Pratiche", len(st.session_state.pratiche))
    c3.metric("🔓 Aperte", sum(1 for p in st.session_state.pratiche if p.get("Stato") == "Aperta"))
    c4.metric("🔒 Chiuse", sum(1 for p in st.session_state.pratiche if p.get("Stato") == "Chiusa"))
    
    st.write("---")
    st.subheader("📍 Distribuição Geográfica")
    if st.session_state.clienti:
        df = pd.DataFrame(st.session_state.clienti)
        st.bar_chart(df['Regione'].value_counts(), color="#bc9e92")
    else:
        st.info("In attesa de novos dados.")

# --- ANAGRAFICA ---
elif menu == "Anagrafica Clienti":
    st.header("👥 Gestione Anagrafica")
    t1, t2 = st.tabs(["➕ Registra Cliente", "📑 Lista Clienti"])
    
    with t1:
        with st.expander("📍 DATI PERSONALI", expanded=True):
            col1, col2 = st.columns(2)
            nome = col1.text_input("Nome e Cognome")
            cf = col1.text_input("Codice Fiscale")
            tel = col2.text_input("Telefono")
            reg = col2.selectbox("Regione", LISTA_REGIONI)
            email = col1.text_input("Email")
        
        st.subheader("🗂️ DOCUMENTI")
        f_doc = st.file_uploader("Carica Documento para o Drive")

        if st.button("🚀 SALVA CLIENTE"):
            if nome and cf:
                srb_id = f"SRB{len(st.session_state.clienti)+1:04d}"
                folder = cria_cartella_cliente_drive(nome, srb_id)
                if folder and f_doc:
                    upload_to_drive(f_doc, folder['id'])
                
                st.session_state.clienti.append({
                    "ID": srb_id, "Nome": nome, "CF": cf, "Regione": reg, 
                    "Tel": tel, "Drive_URL": folder['webViewLink'] if folder else "#"
                })
                st.success(f"✅ Cliente {srb_id} salvo!")
            else:
                st.error("Campos obrigatórios faltando.")

    with t2:
        if st.session_state.clienti:
            st.dataframe(pd.DataFrame(st.session_state.clienti)[["ID", "Nome", "Regione"]], use_container_width=True)
        else:
            st.info("Nessun cliente in lista.")

# --- PRATICHE ---
elif menu == "Nuova Pratica":
    st.header("📂 Apertura Pratica")
    if st.session_state.clienti:
        cli = st.selectbox("Cliente", [c["Nome"] for c in st.session_state.clienti])
        if st.button("Crea Nuova Pratica"):
            st.session_state.pratiche.append({"Cliente": cli, "Stato": "Aperta"})
            st.success("Pratica Aperta!")
    else:
        st.warning("Crea prima um cliente.")

# --- ARCHIVIO ---
elif menu == "Archivio":
    st.header("🗄️ Archivio")
    if st.session_state.pratiche:
        st.write(pd.DataFrame(st.session_state.pratiche))
