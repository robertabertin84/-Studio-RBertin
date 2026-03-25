import streamlit as st
import pandas as pd
from datetime import datetime, date
import io
import time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ==============================================================================
# 1. CONFIGURAZIONE E CSS AVANZATO (CONTRO IL NERO E PER IL RESTAURO BEGE)
# ==============================================================================
st.set_page_config(page_title="Studio R Bertin - Gestionale", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    /* 1.1 Fundo Global SRB */
    .stApp, [data-testid="stSidebar"], [data-testid="stSidebarContent"] { 
        background-color: #f4e7e1 !important; 
    }

    /* 1.2 Restauro das Barras de Título (Expanders) - FIM DAS BARRAS PRETAS */
    .st-emotion-cache-p6495m, .st-emotion-cache-1h9bt9w, [data-testid="stExpander"] details summary {
        background-color: #bc9e92 !important;
        color: black !important;
        border-radius: 8px !important;
        border: 1px solid #a88a7e !important;
        padding: 12px !important;
    }
    
    /* 1.3 Forçar Texto Preto em Todo o Sistema */
    label, p, h1, h2, h3, h4, span, li, div, .stMarkdown, [data-testid="stMetricValue"], [data-testid="stMetricLabel"] { 
        color: black !important; 
        font-weight: 700 !important;
    }

    /* 1.4 Inputs, Selectbox e Áreas de Texto: Branco com Borda Bege */
    input, textarea, [data-baseweb="select"] > div, .stSelectbox div, [data-baseweb="popover"], [data-baseweb="input"], .stDateInput div {
        background-color: white !important;
        color: black !important;
        border: 2px solid #bc9e92 !important;
    }

    /* 1.5 Correção de Menus Suspensos (Não ficam pretos ao abrir) */
    div[role="listbox"] ul, div[role="listbox"] li, div[data-baseweb="menu"] {
        background-color: white !important;
        color: black !important;
    }

    /* 1.6 Botões SRB, Uploaders e Olhinho da Senha */
    button, [data-testid="baseButton-primary"], .stButton>button, button[aria-label="Show password"], .stFileUploader button {
        background-color: #bc9e92 !important;
        color: black !important;
        border: 2px solid #a88a7e !important;
        font-weight: bold !important;
        transition: 0.3s;
    }
    button:hover { background-color: #a88a7e !important; }
    button[aria-label="Show password"] svg { fill: black !important; }

    /* 1.7 Estilização das Métricas da Dashboard */
    [data-testid="stMetric"] {
        background-color: #eaddd7 !important;
        padding: 20px !important;
        border-radius: 12px !important;
        border: 2px solid #bc9e92 !important;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }

    /* 1.8 Limpeza de Interface */
    header { visibility: hidden; }
    footer { visibility: hidden; }
    [data-testid="stFileUploader"] { background-color: white; border-radius: 8px; padding: 5px; }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 2. INTEGRAZIONE GOOGLE DRIVE (LÓGICA COMPLETA DE BACK-END)
# ==============================================================================
SCOPES = ["https://www.googleapis.com/auth/drive"]

def get_google_service(name, version):
    """Inicializa conexão com Google Cloud"""
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("Credenziali Google non trovate in Secrets!")
            return None
        info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        return build(name, version, credentials=creds)
    except Exception as e:
        st.error(f"Errore critico Google: {e}")
        return None

def find_or_create_main_folder():
    """Garante que a pasta GESTIONALE RBERTIN existe"""
    service = get_google_service('drive', 'v3')
    if not service: return None
    
    query = "name = 'GESTIONALE RBERTIN' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(q=query, fields="files(id)").execute()
    items = results.get('files', [])
    
    if not items:
        file_meta = {'name': 'GESTIONALE RBERTIN', 'mimeType': 'application/vnd.google-apps.folder'}
        folder = service.files().create(body=file_meta, fields='id').execute()
        return folder['id']
    return items[0]['id']

def create_client_folder(nome_cliente, srb_code):
    """Cria pasta individual para o cliente"""
    service = get_google_service('drive', 'v3')
    parent_id = find_or_create_main_folder()
    if not service or not parent_id: return None
    
    meta = {
        'name': f"{srb_code} - {nome_cliente}",
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    return service.files().create(body=meta, fields='id, webViewLink').execute()

def upload_to_drive(file, folder_id):
    """Faz o upload dos documentos para a pasta do cliente"""
    service = get_google_service('drive', 'v3')
    if not service or not folder_id: return False
    
    try:
        meta = {'name': file.name, 'parents': [folder_id]}
        media = MediaIoBaseUpload(io.BytesIO(file.read()), mimetype=file.type, resumable=True)
        service.files().create(body=meta, media_body=media, fields='id').execute()
        return True
    except: return False

# ==============================================================================
# 3. SISTEMA DI AUTENTICAZIONE (ACCESSO STUDIO RBERTIN)
# ==============================================================================
if 'autenticato' not in st.session_state: st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.write("<br><br><br>", unsafe_allow_html=True)
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        with st.form("login_srb"):
            st.markdown("<h1 style='text-align: center;'>⚖️ Accesso Studio RBertin</h1>", unsafe_allow_html=True)
            pwd = st.text_input("Password Amministratore:", type="password")
            if st.form_submit_button("ENTRA NEL GESTIONALE"):
                if pwd == "RB2026": 
                    st.session_state.autenticato = True
                    st.success("Accesso Autorizzato...")
                    time.sleep(1)
                    st.rerun()
                else: st.error("Password Errata. Riprova.")
    st.stop()

# ==============================================================================
# 4. GESTIONALE PRINCIPALE (RESTAURADO E EXPANDIDO)
# ==============================================================================
if 'clienti' not in st.session_state: st.session_state.clienti = []
if 'pratiche' not in st.session_state: st.session_state.pratiche = []

LISTA_REGIONI = ["", "Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna", "Friuli Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche", "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana", "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto"]
TIPOS_DOC = ["", "C.I. Italiana", "Passaporto", "Permesso di Soggiorno", "Patente", "Codice Fiscale", "Tessera Sanitaria"]

st.sidebar.markdown("<h2 style='text-align: center;'>⚖️ Studio R Bertin</h2>", unsafe_allow_html=True)
menu = st.sidebar.radio("MENÙ PRINCIPALE", ["Dashboard", "Anagrafica Clienti", "Nuova Pratica", "Archivio Documenti"])

# --- 4.1 DASHBOARD (RESTITUITA) ---
if menu == "Dashboard":
    st.header("📊 Riepilogo Statistiche Studio")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👥 Total Clienti", len(st.session_state.clienti))
    c2.metric("📂 Total Pratiche", len(st.session_state.pratiche))
    c3.metric("🔓 Pratiche Aperte", sum(1 for p in st.session_state.pratiche if p.get("Stato") == "Aperta"))
    c4.metric("🔒 Pratiche Chiuse", sum(1 for p in st.session_state.pratiche if p.get("Stato") == "Chiusa"))
    
    st.write("---")
    if st.session_state.clienti:
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.subheader("📍 Clienti per Regione")
            df_geo = pd.DataFrame(st.session_state.clienti)
            st.bar_chart(df_geo['Regione'].value_counts())

# --- 4.2 ANAGRAFICA (RESTAURO TOTAL DOS CAMPOS E UPLOADS) ---
elif menu == "Anagrafica Clienti":
    st.header("👥 Gestione Anagrafica e Documenti Cliente")
    t1, t2 = st.tabs(["➕ Registra Nuovo Cliente", "📑 Lista Anagrafica (SRB Order)"])
    
    with t1:
        # SEÇÃO 1: DATI PERSONALI
        with st.expander("📍 DATI PERSONALI", expanded=True):
            col_p1, col_p2 = st.columns(2)
            nome = col_p1.text_input("Nome e Cognome Completo")
            cf = col_p1.text_input("Codice Fiscale")
            tel = col_p2.text_input("Telefono / Cellulare")
            email = col_p2.text_input("Indirizzo Email")
            
        # SEÇÃO 2: INDIRIZZO (RESTAURADO)
        with st.expander("🏠 INDIRIZZO DI RESIDENZA", expanded=True):
            c_ind1, c_ind2, c_ind3 = st.columns([2, 1, 1])
            rua = c_ind1.text_input("Via / Piazza e Numero Civico")
            cidade = c_ind2.text_input("Città")
            cap = c_ind3.text_input("CAP")
            regiao = st.selectbox("Regione d'Appartenenza", LISTA_REGIONI)

        # SEÇÃO 3: DOCUMENTI (4 LINHAS COM UPLOAD LATERAL CONFORME FOTOS)
        with st.expander("📄 CARICAMENTO DOCUMENTI (Max 4)", expanded=True):
            st.info("Seleziona il tipo, inserisci il numero e carica il file corrispondente.")
            docs_to_upload = []
            for i in range(1, 5):
                ca, cb, cc, cd = st.columns([1.2, 1.2, 0.8, 1.3])
                t_doc = ca.selectbox(f"Tipo Doc {i}", TIPOS_DOC, key=f"t_type_{i}")
                n_doc = cb.text_input(f"Numero Doc {i}", key=f"n_num_{i}")
                v_doc = cc.date_input(f"Scadenza {i}", value=date.today(), key=f"v_val_{i}")
                f_doc = cd.file_uploader(f"Caricare file {i}", key=f"f_file_{i}", label_visibility="collapsed")
                
                if t_doc and n_doc and f_doc:
                    docs_to_upload.append({"tipo": t_doc, "num": n_doc, "val": v_doc, "file": f_doc})

        # SEÇÃO 4: ANNOTAZIONI (RESTAURADO)
        st.subheader("📝 ANNOTAZIONI E NOTE")
        notas = st.text_area("Inserisci qui eventuali note legali o informazioni sulla pratica...", height=150)

        # BOTÃO DE SALVAMENTO COM LÓGICA DE DRIVE
        if st.button("🚀 SALVA ANAGRAFICA E CREA CARTELLA DRIVE"):
            if nome and cf:
                srb_id = f"SRB{len(st.session_state.clienti)+1:04d}"
                with st.spinner(f"Creazione cartella per {nome}..."):
                    # 1. Cria pasta no Drive
                    folder = create_client_folder(nome, srb_id)
                    # 2. Upload de arquivos
                    if folder:
                        for d in docs_to_upload:
                            upload_to_drive(d['file'], folder['id'])
                    
                    # 3. Salva no banco local
                    st.session_state.clienti.append({
                        "ID": srb_id, "Nome": nome, "CF": cf, "Regione": regiao,
                        "Tel": tel, "Email": email, "Città": cidade,
                        "Drive": folder['webViewLink'] if folder else "N/A"
                    })
                st.success(f"✅ Cliente {srb_id} registrato! Cartella Drive creata.")
            else: st.error("I campi Nome e Codice Fiscale sono obbligatori!")

    with t2:
        if st.session_state.clienti:
            st.write("### Archivio Anagrafico")
            df_final = pd.DataFrame(st.session_state.clienti)
            st.dataframe(df_final, use_container_width=True)
        else: st.info("Nessun cliente registrato.")

# --- 4.3 NUOVA PRATICA (RESTAURADO) ---
elif menu == "Nuova Pratica":
    st.header("📂 Apertura Nuova Pratica Legale")
    if not st.session_state.clienti:
        st.warning("È necessario registrare un cliente prima di aprire una pratica.")
    else:
        with st.form("form_pratica"):
            cli_n = st.selectbox("Seleziona Cliente", [c["Nome"] for c in st.session_state.clienti])
            tipo_p = st.selectbox("Tipologia di Pratica", ["Cittadinanza", "Fiscale", "Permesso di Soggiorno", "Visto", "Altro"])
            desc_p = st.text_area("Descrizione Pratica")
            if st.form_submit_button("APRI PRATICA"):
                st.session_state.pratiche.append({"Cliente": cli_n, "Tipo": tipo_p, "Stato": "Aperta", "Data": date.today()})
                st.success(f"Pratica per {cli_n} aperta correttamente!")

elif menu == "Archivio Documenti":
    st.header("🗄️ Archivio Digitale Drive")
    st.info("Qui puoi visualizzare i link diretti alle cartelle Google Drive dei clienti.")
    if st.session_state.clienti:
        for c in st.session_state.clienti:
            st.markdown(f"- **{c['ID']} - {c['Nome']}**: [Link Cartella Drive]({c['Drive']})")
