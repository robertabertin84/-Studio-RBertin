import streamlit as st
import pandas as pd
from datetime import datetime, date
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# ==========================================
# 1. CONFIGURAZIONE ESTETICA (UNIFICATA)
# ==========================================
st.set_page_config(page_title="Studio R Bertin", layout="wide")

st.markdown("""
    <style>
    /* Fundo Total e Lateral Creme #f4e7e1 */
    .stApp, [data-testid="stSidebar"], [data-testid="stSidebarContent"] { 
        background-color: #f4e7e1 !important; 
    }

    /* Texto Preto para leitura */
    label, p, h1, h2, h3, h4, span, li, div, .stMarkdown { 
        color: black !important; 
        font-weight: 500;
    }

    /* Centralização e Estilo do Card de Login */
    [data-testid="stForm"] {
        max-width: 400px;
        margin-left: auto;
        margin-right: auto;
        padding: 40px;
        background-color: #f4e7e1 !important; 
        border-radius: 15px;
        border: 2px solid #bc9e92 !important;
    }

    /* BARRA LATERAL: Cor Bege #bc9e92 */
    [data-testid="stSidebarNavItems"] li {
        background-color: #bc9e92 !important;
        margin-bottom: 8px;
        border-radius: 8px;
    }

    /* FORÇAR COR DO BOTÃO (BEGE #bc9e92) */
    div.stButton > button, button[kind="primaryFormSubmit"], .stButton>button {
        background-color: #bc9e92 !important;
        color: black !important;
        border: 1px solid #a88a7e !important;
        font-weight: bold !important;
    }

    /* FORÇAR COR DO OLHINHO (BEGE #bc9e92) */
    button[aria-label="Show password"] {
        background-color: #bc9e92 !important;
        color: black !important;
    }
    
    /* Inputs Brancos para contraste */
    input, .stSelectbox div {
        background-color: white !important;
        color: black !important;
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
# 2. LOGIN CENTRALIZADO
# ==========================================
if 'autenticato' not in st.session_state: st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.write("<br><br><br><br>", unsafe_allow_html=True)
    with st.form("login_form"):
        st.markdown("<h2 style='text-align: center;'>⚖️ Studio R Bertin</h2>", unsafe_allow_html=True)
        pwd = st.text_input("Password:", type="password")
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
    st.header("📊 Riepilogo Statistiche Studio")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👥 Totale Clienti", len(st.session_state.clienti))
    c2.metric("📂 Totale Pratiche", len(st.session_state.pratiche))
    c3.metric("🔓 Aperte", sum(1 for p in st.session_state.pratiche if p.get("Stato") == "Aperta"))
    c4.metric("🔒 Chiuse", sum(1 for p in st.session_state.pratiche if p.get("Stato") == "Chiusa"))
    
    st.write("---")
    st.subheader("📍 Distribuzione Geografica")
    if st.session_state.clienti:
        df = pd.DataFrame(st.session_state.clienti)
        st.bar_chart(df['Regione'].value_counts(), color="#bc9e92")
    else:
        st.info("Nessun dato registrato.")

# --- ANAGRAFICA ---
elif menu == "Anagrafica Clienti":
    st.header("👥 Gestione Clienti e Documenti")
    t1, t2 = st.tabs(["➕ Registra Cliente", "📑 Lista Clienti (SRB Order)"])
    
    with t1:
        with st.expander("📍 DATI PERSONALI", expanded=True):
            col1, col2 = st.columns(2)
            nome = col1.text_input("Nome e Cognome")
            cf = col1.text_input("Codice Fiscale")
            tel = col2.text_input("Telefono")
            reg = col2.selectbox("Regione", LISTA_REGIONI)
            email = col1.text_input("Email")
        
        st.subheader("🗂️ DOCUMENTI")
        with st.expander("📄 Caricamento File (Drive)", expanded=False):
            tipo_doc = st.selectbox("Tipo Documento", DOC_TYPES)
            f_doc = st.file_uploader("Seleziona File")

        if st.button("🚀 SALVA CLIENTE"):
            if nome and cf:
                srb_id = f"SRB{len(st.session_state.clienti)+1:04d}"
                folder = cria_cartella_cliente_drive(nome, srb_id)
                if folder and f_doc:
                    upload_to_drive(f_doc, folder['id'])
                
                st.session_state.clienti.append({
                    "ID": srb_id, "Nome": nome, "CF": cf, "Regione": reg, 
                    "Tel": tel, "Email": email,
                    "Drive_URL": folder['webViewLink'] if folder else "#"
                })
                st.success(f"✅ Cliente {srb_id} salvato com sucesso!")
            else:
                st.error("Nome e Codice Fiscale são obrigatórios!")

    with t2:
        if st.session_state.clienti:
            df_c = pd.DataFrame(st.session_state.clienti)
            st.dataframe(df_c[["ID", "Nome", "Regione", "Tel"]], use_container_width=True)
            sel_id = st.selectbox("Dettagli Cliente (ID):", df_c["ID"])
            cli = next(c for c in st.session_state.clienti if c["ID"] == sel_id)
            st.markdown(f"🔗 [Apri Cartella Google Drive]({cli['Drive_URL']})")
        else:
            st.info("Nessun cliente registrato.")

# --- PRATICHE ---
elif menu == "Nuova Pratica":
    st.header("📂 Gestione Pratiche")
    if not st.session_state.clienti:
        st.warning("Registra prima um cliente!")
    else:
        with st.form("pratica_form"):
            c_nome = st.selectbox("Seleziona Cliente", [c["Nome"] for c in st.session_state.clienti])
            tipo_p = st.selectbox("Tipo Pratica", ["FISCO", "CONSOLARI", "PA", "ALTRO"])
            desc = st.text_area("Descrizione")
            status = st.radio("Stato Iniciale", ["Aperta", "In Corso"], horizontal=True)
            if st.form_submit_button("Crea Pratica"):
                st.session_state.pratiche.append({
                    "Data": date.today().strftime("%d/%m/%Y"),
                    "Cliente": c_nome, "Tipo": tipo_p, "Stato": status
                })
                st.success("Pratica creata!")

# --- ARCHIVIO ---
elif menu == "Archivio":
    st.header("🗄️ Archivio Storico")
    if st.session_state.pratiche:
        st.table(pd.DataFrame(st.session_state.pratiche))
    else:
        st.info("L'archivio è vuoto.")
