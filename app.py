import streamlit as st
import pandas as pd
from datetime import datetime, date
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import plotly.express as px

# ==========================================
# 1. CONFIGURAZIONE ESTETICA (STUDIO RBERTIN)
# ==========================================
st.set_page_config(page_title="Studio RBertin - Gestionale", layout="wide")

st.markdown(f"""
    <style>
    /* Fundo principal claro */
    .stApp {{ background-color: #f4e7e1; }}
    
    /* Títulos e textos em preto para contraste */
    label, p, .stMarkdown, h1, h2, h3, span {{ color: black !important; font-weight: 500; }}

    /* Barras de Expander e Dropdowns em Bege #bc9e92 */
    .streamlit-expanderHeader, div[data-testid="stExpander"], div[data-baseweb="select"] > div {{
        background-color: #bc9e92 !important;
        color: black !important;
        border-radius: 5px;
    }}
    
    /* Campos de input Brancos com letras pretas */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stDateInput>div>div>input {{
        background-color: white !important;
        color: black !important;
        border: 1px solid #bc9e92 !important;
    }}

    /* Estilo das Abas (Tabs) */
    .stTabs [data-baseweb="tab"] {{ color: black !important; }}
    .stTabs [aria-selected="true"] {{ border-bottom: 2px solid #bc9e92 !important; font-weight: bold; }}
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI GOOGLE SERVICES ---
def get_google_service(name, version, scopes):
    try:
        info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        return build(name, version, credentials=creds)
    except Exception as e:
        st.error(f"Errore Google {name}: {e}")
        return None

def upload_to_drive(file, folder_id):
    service = get_google_service('drive', 'v3', ["https://www.googleapis.com/auth/drive"])
    if not service or not folder_id: return None
    file_metadata = {'name': file.name, 'parents': [folder_id]}
    media = service.files().create(body=file_metadata, media_body=file, fields='id').execute()
    return media.get('id')

def cria_cartella_cliente_drive(nome, srb_code):
    service = get_google_service('drive', 'v3', ["https://www.googleapis.com/auth/drive"])
    if not service: return None
    query = "name = 'GESTIONALE RBERTIN' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(q=query, fields="files(id)").execute()
    items = results.get('files', [])
    if items:
        parent_id = items[0]['id']
        nome_pasta = f"{srb_code} - {nome}"
        file_metadata = {'name': nome_pasta, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_id]}
        folder = service.files().create(body=file_metadata, fields='id, webViewLink').execute()
        return folder
    return None

# ==========================================
# 2. SISTEMA DE LOGIN E SESSÃO
# ==========================================
if 'autenticato' not in st.session_state: st.session_state.autenticato = False
if not st.session_state.autenticato:
    st.title("🔐 Accesso Studio RBertin")
    pwd = st.text_input("Password:", type="password")
    if st.button("Entra"):
        if pwd == "RB2026": 
            st.session_state.autenticato = True
            st.rerun()
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

# --- DASHBOARD ---
if menu == "Dashboard":
    st.header("📊 Dashboard Riepilogativa")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👥 Clienti", len(st.session_state.clienti))
    c2.metric("📂 Pratiche", len(st.session_state.pratiche))
    c3.metric("🔓 Aperte", sum(1 for p in st.session_state.pratiche if p.get("Stato") == "Aperta"))
    c4.metric("🔒 Chiuse", sum(1 for p in st.session_state.pratiche if p.get("Stato") == "Chiusa"))

    st.subheader("📍 Presenza nelle Regioni")
    if st.session_state.clienti:
        df_geo = pd.DataFrame(st.session_state.clienti)
        counts = df_geo['Regione'].value_counts().reset_index()
        counts.columns = ['Regione', 'Clienti']
        fig = px.bar(counts, x='Regione', y='Clienti', color_discrete_sequence=['#bc9e92'])
        st.plotly_chart(fig, use_container_width=True)

# --- ANAGRAFICA ---
elif menu == "Anagrafica Clienti":
    st.header("👥 Gestione Clienti e Documenti")
    t_reg, t_list = st.tabs(["➕ Nuovo Cliente", "📑 Elenco Clienti"])
    
    with t_reg:
        with st.expander("📍 DATI ANAGRAFICI", expanded=True):
            col1, col2 = st.columns(2)
            nome = col1.text_input("Nome e Cognome")
            cf = col1.text_input("Codice Fiscale")
            nascita = col1.date_input("Data di Nascita", value=date(1990, 1, 1))
            tel = col2.text_input("Telefono")
            email = col2.text_input("Email")
            regione = col2.selectbox("Regione", LISTA_REGIONI)
            note = st.text_area("Note aggiuntive")

        st.subheader("🗂️ DOCUMENTI (Fino a 4 slot)")
        docs_temp = []
        for i in range(1, 5):
            with st.expander(f"📄 DOCUMENTO {i}", expanded=(i==1)):
                d1, d2, d3 = st.columns(3)
                t_doc = d1.selectbox(f"Tipo {i}", ["-"] + DOC_TYPES, key=f"t{i}")
                if t_doc == "Altro": t_doc = d1.text_input(f"Quale? {i}", key=f"alt{i}")
                n_doc = d2.text_input(f"Numero {i}", key=f"n{i}")
                s_doc = d3.date_input(f"Scadenza {i}", key=f"s{i}")
                f_doc = st.file_uploader(f"Carica File {i}", key=f"f{i}")
                if t_doc != "-" and t_doc != "":
                    docs_temp.append({"tipo": t_doc, "num": n_doc, "scad": s_doc, "file": f_doc})

        if st.button("🚀 SALVA CLIENTE"):
            if nome and cf:
                srb_code = f"SRB{len(st.session_state.clienti) + 1:04d}"
                folder = cria_cartella_cliente_drive(nome, srb_code)
                if folder:
                    for d in docs_temp:
                        if d['file']: upload_to_drive(d['file'], folder['id'])
                
                st.session_state.clienti.append({
                    "ID": srb_code, "Nome": nome, "CF": cf, "Regione": regione,
                    "Tel": tel, "Docs": docs_temp, "Drive_URL": folder['webViewLink'] if folder else "#"
                })
                st.success(f"Cliente {srb_code} registrato!")
            else: st.error("Inserire Nome e Codice Fiscale!")

    with t_list:
        if st.session_state.clienti:
            df = pd.DataFrame(st.session_state.clienti)
            st.dataframe(df[["ID", "Nome", "Regione", "Tel"]], use_container_width=True)
            sel = st.selectbox("Seleziona ID per dettagli", df["ID"])
            c_sel = next(c for c in st.session_state.clienti if c["ID"] == sel)
            st.write(f"📁 [Apri Cartella Drive]({c_sel['Drive_URL']})")

# --- PRATICHE ---
elif menu == "Nuova Pratica":
    st.header("📂 Nuova Pratica")
    if st.session_state.clienti:
        cli = st.selectbox("Cliente", [c["Nome"] for c in st.session_state.clienti])
        tp = st.selectbox("Tipo", ["FISCO", "CONSOLARI", "PA", "ALTRO"])
        stt = st.radio("Stato", ["Aperta", "Chiusa"], horizontal=True)
        if st.button("Salva"):
            st.session_state.pratiche.append({"Data": date.today(), "Cliente": cli, "Tipo": tp, "Stato": stt})
            st.success("Pratica aggiunta!")
    else: st.warning("Crea prima um cliente!")

elif menu == "Archivio":
    st.header("🗄️ Archivio")
    if st.session_state.pratiche: st.table(pd.DataFrame(st.session_state.pratiche))
    else: st.info("Vuoto.")
