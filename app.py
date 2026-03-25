import streamlit as st
import pandas as pd
from datetime import datetime, date
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import plotly.express as px

# ==========================================
# 1. CONFIGURAZIONE E ESTILO (COLORI E INPUT)
# ==========================================
st.set_page_config(page_title="Studio RBertin - Gestionale", layout="wide")

# Aplicação de cores solicitadas: Fundo #f4e7e1, Barras #bc9e92 e Inputs Brancos
st.markdown(f"""
    <style>
    .stApp {{ background-color: #f4e7e1; }}
    
    /* Cabeçalhos e Dropdowns em Bege #bc9e92 com letras pretas */
    .streamlit-expanderHeader, div[data-testid="stExpander"], div[data-baseweb="select"] > div {{
        background-color: #bc9e92 !important;
        color: black !important;
        border-radius: 5px;
    }}
    
    /* Garantir que textos de labels e títulos sejam pretos */
    label, p, .stMarkdown, h1, h2, h3, span {{ color: black !important; font-weight: 500; }}

    /* Campos de entrada Brancos com letras pretas */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stDateInput>div>div>input {{
        background-color: white !important;
        color: black !important;
        border: 1px solid #bc9e92 !important;
    }}
    
    /* Estilo das Abas */
    .stTabs [data-baseweb="tab"] {{ color: black !important; }}
    .stTabs [aria-selected="true"] {{ border-bottom: 2px solid #bc9e92 !important; }}
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI GOOGLE ---
def get_google_service(name, version, scopes):
    try:
        info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        return build(name, version, credentials=creds)
    except Exception as e:
        st.error(f"Errore Google {name}: {e}"); return None

def upload_to_drive(file, folder_id):
    service = get_google_service('drive', 'v3', ["https://www.googleapis.com/auth/drive"])
    if not service or not folder_id: return None
    file_metadata = {'name': file.name, 'parents': [folder_id]}
    media = service.files().create(body=file_metadata, media_body=file, fields='id').execute()
    return media.get('id')

def cria_cartella_cliente_drive(nome, srb_code):
    service = get_google_service('drive', 'v3', ["https://www.googleapis.com/auth/drive"])
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
# 2. AUTENTICAZIONE E DATABASE
# ==========================================
if 'autenticato' not in st.session_state: st.session_state.autenticato = False
if not st.session_state.autenticato:
    st.title("🔐 Accesso Studio RBertin")
    pwd = st.text_input("Password:", type="password")
    if st.button("Entra"):
        if pwd == "RB2026": st.session_state.autenticato = True; st.rerun()
    st.stop()

if 'clienti' not in st.session_state: st.session_state.clienti = []
if 'pratiche' not in st.session_state: st.session_state.pratiche = []

LISTA_REGIONI = ["Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna", "Friuli Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche", "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana", "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto"]
DOC_TYPES = ["C.I. Italiana", "Passaporto", "Permesso di Soggiorno", "Patente", "Codice Fiscale", "Tessera Sanitaria", "Altro"]

# ==========================================
# 3. MENU LATERALE
# ==========================================
st.sidebar.title("🏛️ Studio RBertin")
menu = st.sidebar.radio("NAVIGAZIONE:", ["Dashboard", "Anagrafica Clienti", "Nuova Pratica", "Archivio"])

# ------------------------------------------
# SEZIONE: DASHBOARD
# ------------------------------------------
if menu == "Dashboard":
    st.header("📊 Riepilogo Statistiche Studio")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👥 Totale Clienti", len(st.session_state.clienti))
    c2.metric("📂 Totale Pratiche", len(st.session_state.pratiche))
    c3.metric("🔓 Aperte", sum(1 for p in st.session_state.pratiche if p.get("Stato") == "Aperta"))
    c4.metric("🔒 Chiuse", sum(1 for p in st.session_state.pratiche if p.get("Stato") == "Chiusa"))

    st.subheader("📍 Distribuzione Geografica")
    if st.session_state.clienti:
        df_geo = pd.DataFrame(st.session_state.clienti)
        counts = df_geo['Regione'].value_counts().reset_index()
        counts.columns = ['Regione', 'Clienti']
        fig = px.bar(counts, x='Regione', y='Clienti', color_discrete_sequence=['#bc9e92'])
        st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------
# SEZIONE: ANAGRAFICA (4 DOCUMENTOS)
# ------------------------------------------
elif menu == "Anagrafica Clienti":
    st.header("👥 Gestione Anagrafica e Documenti")
    tab_reg, tab_lista = st.tabs(["➕ Registra Nuovo", "📑 Lista Completa"])
    
    with tab_reg:
        with st.expander("📍 DATI PERSONALI E CONTATTO", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                nome = st.text_input("Nome e Cognome")
                cf = st.text_input("Codice Fiscale")
                nascita = st.date_input("Data di Nascita", value=date(1990, 1, 1))
                citta = st.text_input("Città di Residenza")
                regione = st.selectbox("Regione", LISTA_REGIONI)
            with col2:
                tel = st.text_input("Telefono")
                email = st.text_input("Email")
                pec = st.text_input("PEC")
                note = st.text_area("Note e Appunti")

        st.subheader("🗂️ DOCUMENTI (Aggiungi fino a 4)")
        docs_to_save = []
        for i in range(1, 5):
            with st.expander(f"📄 DOCUMENTO {i}", expanded=(i==1)):
                c1, c2, c3 = st.columns(3)
                tipo = c1.selectbox(f"Tipo {i}", ["-"] + DOC_TYPES, key=f"t{i}")
                if tipo == "Altro":
                    tipo = c1.text_input(f"Specifica Doc {i}", key=f"alt{i}")
                num = c2.text_input(f"Numero {i}", key=f"n{i}")
                scad = c3.date_input(f"Scadenza {i}", key=f"s{i}")
                foto = st.file_uploader(f"Carica Immagine/PDF {i}", key=f"f{i}")
                if tipo != "-" and tipo != "":
                    docs_to_save.append({"tipo": tipo, "num": num, "scad": scad, "file": foto})

        if st.button("🚀 SALVA ANAGRAFICA E CREA CARTELLA"):
            if nome and cf:
                srb_num = len(st.session_state.clienti) + 1
                srb_code = f"SRB{srb_num:04d}"
                folder = cria_cartella_cliente_drive(nome, srb_code)
                
                # Upload dos arquivos se existirem
                if folder:
                    for d in docs_to_save:
                        if d['file']: upload_to_drive(d['file'], folder['id'])
                
                st.session_state.clienti.append({
                    "ID": srb_code, "Nome": nome, "CF": cf, "Regione": regione,
                    "Tel": tel, "Email": email, "Docs": docs_to_save,
                    "Drive_URL": folder['webViewLink'] if folder else "#"
                })
                st.success(f"✅ Cliente {nome} ({srb_code}) salvato!")
            else: st.error("Errore: Nome e Codice Fiscale são obrigatórios.")

    with tab_lista:
        if st.session_state.clienti:
            df = pd.DataFrame(st.session_state.clienti)
            st.dataframe(df[["ID", "Nome", "Regione", "Tel"]], use_container_width=True)
            sel = st.selectbox("Seleziona per dettagli:", df["ID"])
            curr = next(c for c in st.session_state.clienti if c["ID"] == sel)
            st.info(f"📁 [APRI CARTELLA GOOGLE DRIVE]({curr['Drive_URL']})")

# ------------------------------------------
# SEZIONE: PRATICHE E ARCHIVIO
# ------------------------------------------
elif menu == "Nuova Pratica":
    st.header("📂 Apertura Nuovo Fascicolo")
    if st.session_state.clienti:
        cliente_scelto = st.selectbox("Seleziona Cliente", [c["Nome"] for c in st.session_state.clienti])
        colp1, colp2 = st.columns(2)
        tipo_p = colp1.selectbox("Tipo Pratica", ["FISCO", "CONSOLARI", "PA", "VARIE"])
        stato_p = colp2.radio("Stato", ["Aperta", "Chiusa"], horizontal=True)
        if st.button("Registra Pratica"):
            st.session_state.pratiche.append({"Data": date.today(), "Cliente": cliente_scelto, "Tipo": tipo_p, "Stato": stato_p})
            st.success("Pratica registrata!")
    else: st.warning("Aggiungi prima um cliente.")

elif menu == "Archivio":
    st.header("🗄️ Archivio Storico")
    if st.session_state.pratiche: st.table(pd.DataFrame(st.session_state.pratiche))
    else: st.info("Archivio vuoto.")
