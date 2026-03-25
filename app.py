import streamlit as st
import pandas as pd
from datetime import datetime, date
import io
import time
import os
import base64
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ==============================================================================
# 1. CONFIGURAZIONE E CSS AVANZATO (DESIGN ORIGINAL RBERTIN)
# ==============================================================================
st.set_page_config(
    page_title="Studio R Bertin - Gestionale Professionale",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    /* Fundo Global */
    .stApp, [data-testid="stSidebar"], [data-testid="stSidebarContent"] { 
        background-color: #f4e7e1 !important; 
    }

    /* Expanders */
    [data-testid="stExpander"] details summary {
        background-color: #bc9e92 !important;
        color: black !important;
        border-radius: 8px !important;
        border: 1px solid #a88a7e !important;
        padding: 12px !important;
        font-size: 16px !important;
    }
    
    /* Texto em Preto Negrito */
    label, p, h1, h2, h3, h4, span, li, div, .stMarkdown, [data-testid="stMetricValue"] { 
        color: black !important; 
        font-weight: 700 !important;
    }

    /* Inputs */
    input, textarea, [data-baseweb="input"], .stDateInput div {
        background-color: white !important;
        color: black !important;
        border: 1px solid #bc9e92 !important;
    }

    /* Menus Suspensos e Calendário */
    div[data-baseweb="select"] > div, .stSelectbox > div > div {
        background-color: #f3f2f1 !important;
        color: black !important;
        border: 1px solid #bc9e92 !important;
    }

    /* Botões */
    button, [data-testid="baseButton-primary"] {
        background-color: #bc9e92 !important;
        color: black !important;
        border: 2px solid #a88a7e !important;
        width: 100% !important;
    }

    header { visibility: hidden; }
    footer { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 2. SISTEMA DE BACK-END: GOOGLE DRIVE (COM PROTEÇÃO DE CHAVE)
# ==============================================================================
SCOPES = ["https://www.googleapis.com/auth/drive"]

def init_google_drive():
    try:
        if "gcp_service_account" not in st.secrets:
            return None, "Secret gcp_service_account não encontrada."
        
        # --- PROTEÇÃO REFORÇADA ---
        # Converte os segredos em um dicionário mutável
        info = dict(st.secrets["gcp_service_account"])
        
        # Remove eventuais caracteres de escape \n que quebram o arquivo PEM
        if "private_key" in info:
            info["private_key"] = info["private_key"].replace("\\n", "\n")
        
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        return build('drive', 'v3', credentials=creds), None
    except Exception as e:
        return None, f"Erro de Autenticação: {str(e)}"

def manage_drive_structure(nome_cliente, srb_code):
    service, err = init_google_drive()
    if err: return None, err
    try:
        q = "name = 'GESTIONALE RBERTIN' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        res = service.files().list(q=q).execute()
        folders = res.get('files', [])
        
        if folders:
            root_id = folders[0]['id']
        else:
            root_meta = {'name': 'GESTIONALE RBERTIN', 'mimeType': 'application/vnd.google-apps.folder'}
            root_id = service.files().create(body=root_meta, fields='id').execute()['id']
            
        folder_meta = {
            'name': f"{srb_code} - {nome_cliente}",
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [root_id]
        }
        return service.files().create(body=folder_meta, fields='id, webViewLink').execute(), None
    except Exception as e:
        return None, str(e)

def upload_to_client_folder(file_obj, folder_id, new_filename):
    service, _ = init_google_drive()
    if not service: return False
    try:
        meta = {'name': new_filename, 'parents': [folder_id]}
        media = MediaIoBaseUpload(io.BytesIO(file_obj.read()), mimetype=file_obj.type, resumable=True)
        service.files().create(body=meta, media_body=media).execute()
        return True
    except:
        return False

# ==============================================================================
# 3. CONTROLE DE ESTADO E LOGIN
# ==============================================================================
if 'autenticato' not in st.session_state: st.session_state.autenticato = False
if 'clienti' not in st.session_state: st.session_state.clienti = []
if 'pratiche' not in st.session_state: st.session_state.pratiche = []

if not st.session_state.autenticato:
    st.write("<br><br><br>", unsafe_allow_html=True)
    c_log1, c_log2, c_log3 = st.columns([1, 1.5, 1])
    with c_log2:
        with st.form("login_form"):
            st.markdown("<h1 style='text-align: center;'>⚖️ Studio R Bertin</h1>", unsafe_allow_html=True)
            pwd = st.text_input("Inserire Password:", type="password")
            if st.form_submit_button("ACCEDI"):
                if pwd == "RB2026": 
                    st.session_state.autenticato = True
                    st.rerun()
                else:
                    st.error("Accesso Negato.")
    st.stop()

# ==============================================================================
# 4. INTERFACE DO GESTIONALE
# ==============================================================================
LISTA_REGIONI = ["", "Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna", "Friuli Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche", "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana", "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto"]

st.sidebar.markdown("<h2 style='text-align: center;'>Menu Studio</h2>", unsafe_allow_html=True)
menu = st.sidebar.radio("NAVIGAZIONE", ["📊 Dashboard", "👥 Anagrafica Clienti", "📂 Nuova Pratica", "🗄️ Archivio"])

# --- DASHBOARD ---
if menu == "📊 Dashboard":
    st.header("📊 Stato Generale dello Studio")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("👥 Clienti Totali", len(st.session_state.clienti))
    m2.metric("📂 Pratiche Totali", len(st.session_state.pratiche))
    m3.metric("🔓 Pratiche Aperte", sum(1 for p in st.session_state.pratiche if p.get("Stato") == "Aperta"))
    m4.metric("🔒 Pratiche Chiuse", sum(1 for p in st.session_state.pratiche if p.get("Stato") == "Chiusa"))
    
    st.write("---")
    if st.session_state.clienti:
        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            st.subheader("📍 Geografia Clienti")
            df_cli = pd.DataFrame(st.session_state.clienti)
            st.bar_chart(df_cli['Regione'].value_counts())

# --- ANAGRAFICA CLIENTI ---
elif menu == "👥 Anagrafica Clienti":
    st.header("👥 Gestione Anagrafica e Documentale")
    t_aba1, t_aba2 = st.tabs(["➕ Registra Cliente", "📑 Lista Clienti (SRB Order)"])
    
    with t_aba1:
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
            st.markdown("<p style='font-size: 13px;'>Inserisci numeri e scadenze. Carica i file nel campo em baixo.</p>", unsafe_allow_html=True)
            
            DOCS_FIXOS = ["Carta d'Identità", "Permesso di Soggiorno", "Patente Italiana", "Tessera Sanitaria", "Passaporto Brasiliano"]
            doc_entries = []
            
            h1, h2, h3 = st.columns([0.8, 1.2, 1.0])
            h1.markdown("**Documento**")
            h2.markdown("**Numero**")
            h3.markdown("**Scadenza**")

            for d_name in DOCS_FIXOS:
                c1, c2, c3 = st.columns([0.8, 1.2, 1.0])
                c1.write(f"**{d_name}**")
                n_val = c2.text_input("Numero", key=f"n_{d_name}", label_visibility="collapsed", placeholder="Numero")
                s_val = c3.date_input("Scadenza", value=date.today(), key=f"s_{d_name}", label_visibility="collapsed", format="DD/MM/YYYY")
                if n_val:
                    doc_entries.append({"tipo": d_name, "num": n_val, "scad": s_val})

        st.subheader("📤 Upload Documenti (Lotto)")
        uploaded_files = st.file_uploader("Seleziona tutti i file dei documentos acima", accept_multiple_files=True)

        st.subheader("📝 ANNOTAZIONI")
        notas = st.text_area("Note e dettagli...", height=100)

        if st.button("🚀 REGISTRA CLIENTE E SINCRONIZZA DRIVE"):
            if nome and cf:
                srb_code = f"SRB{len(st.session_state.clienti)+1:04d}"
                with st.spinner("Sincronizzazione Drive..."):
                    folder_obj, error = manage_drive_structure(nome, srb_code)
                    if folder_obj:
                        # Upload dos arquivos renomeados
                        for idx, f in enumerate(uploaded_files):
                            if idx < len(doc_entries):
                                d = doc_entries[idx]
                                ext = os.path.splitext(f.name)[1]
                                new_name = f"{d['tipo']}_{d['num']}{ext}"
                                upload_to_client_folder(f, folder_obj['id'], new_name)
                        
                        st.session_state.clienti.append({
                            "ID": srb_code, 
                            "Nome": nome, 
                            "CF": cf, 
                            "Regione": regiao, 
                            "Link": folder_obj['webViewLink']
                        })
                        st.success(f"✅ Cliente {srb_code} salvato con successo!")
                    else:
                        st.error(f"Errore critico Drive: {error}")
            else:
                st.error("Per favore, inserisci almeno Nome e Codice Fiscale!")

    with t_aba2:
        if st.session_state.clienti:
            st.dataframe(pd.DataFrame(st.session_state.clienti), use_container_width=True)

# --- OUTRAS PÁGINAS ---
elif menu == "📂 Nuova Pratica":
    st.header("📂 Apertura Nuova Pratica")
elif menu == "🗄️ Archivio":
    st.header("🗄️ Archivio Digitale")
    if not st.session_state.clienti:
        st.info("Nessun cliente registrato.")
    else:
        for c in st.session_state.clienti:
            st.markdown(f"📁 **{c['ID']}** - {c['Nome']} - [Apri Cartella Google Drive]({c['Link']})")
