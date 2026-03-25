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
# 1. CONFIGURAZIONE E CSS AVANZATO (CORREÇÃO FORTE)
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
    .st-emotion-cache-p6495m, .st-emotion-cache-1h9bt9w, [data-testid="stExpander"] details summary {
        background-color: #bc9e92 !important;
        color: black !important;
        border-radius: 8px !important;
        border: 1px solid #a88a7e !important;
        padding: 12px !important;
    }
    
    /* Texto geral */
    label, p, h1, h2, h3, h4, span, li, div, .stMarkdown, [data-testid="stMetricValue"] { 
        color: black !important; 
        font-weight: 700 !important;
    }

    /* Inputs */
    input, textarea, [data-baseweb="input"] {
        background-color: white !important;
        color: black !important;
        border: 1px solid #bc9e92 !important;
    }

    /* Menus suspensos */
    [data-baseweb="select"] > div,
    div[role="listbox"], div[role="listbox"] ul, div[role="listbox"] li,
    div[data-baseweb="menu"], [data-baseweb="popover"] {
        background-color: #f3f2f1 !important;
        color: black !important;
    }
    div[role="listbox"] li:hover {
        background-color: #e8e6e4 !important;
    }

    /* Calendário Scadenza */
    .stDateInput > div > div,
    .stDateInput input,
    div[data-baseweb="calendar"],
    div[data-baseweb="calendar"] div,
    div[data-baseweb="calendar"] button {
        background-color: #f3f2f1 !important;
        color: black !important;
        border: 1px solid #bc9e92 !important;
    }
    div[data-baseweb="calendar"] button:hover {
        background-color: #e8e6e4 !important;
    }

    /* Upload */
    [data-testid="stFileUploader"] section,
    [data-testid="stFileUploadDropzone"] {
        background-color: transparent !important;
        border: 2px dashed #bc9e92 !important;
        border-radius: 8px !important;
        padding: 20px !important;
    }
    [data-testid="stFileUploader"] button {
        background-color: #bc9e92 !important;
        color: black !important;
        width: 100% !important;
        height: 48px !important;
        border-radius: 6px !important;
        border: 1px solid #a88a7e !important;
    }

    /* Botão grande */
    button[kind="primary"], .stButton > button {
        background-color: #bc9e92 !important;
        color: black !important;
        border: 2px solid #a88a7e !important;
        font-weight: 700 !important;
        height: 52px !important;
    }
    button[kind="primary"]:hover, .stButton > button:hover {
        background-color: #a88a7e !important;
    }

    [data-testid="column"] { padding: 0 5px !important; }
    [data-testid="stHorizontalBlock"] { gap: 0.3rem !important; }

    header, footer { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 2. BACK-END GOOGLE DRIVE
# ==============================================================================
SCOPES = ["https://www.googleapis.com/auth/drive"]

def init_google_drive():
    try:
        if "gcp_service_account" not in st.secrets:
            return None, "Secret gcp_service_account não encontrada."
        info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        return build('drive', 'v3', credentials=creds), None
    except Exception as e:
        return None, str(e)

def manage_drive_structure(nome_cliente, srb_code):
    service, err = init_google_drive()
    if err: return None, err
    
    try:
        q = "name = 'GESTIONALE RBERTIN' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        res = service.files().list(q=q).execute()
        folders = res.get('files', [])
        
        if not folders:
            meta = {'name': 'GESTIONALE RBERTIN', 'mimeType': 'application/vnd.google-apps.folder'}
            root = service.files().create(body=meta, fields='id').execute()
            root_id = root['id']
        else:
            root_id = folders[0]['id']
            
        folder_meta = {
            'name': f"{srb_code} - {nome_cliente}",
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [root_id]
        }
        new_folder = service.files().create(body=folder_meta, fields='id, webViewLink').execute()
        return new_folder, None
    except Exception as e:
        return None, f"Errore Drive: {e}"

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
# 3. LOGIN
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
            st.markdown("<p style='text-align: center;'>Accesso Riservato</p>", unsafe_allow_html=True)
            pwd = st.text_input("Inserire Password:", type="password")
            if st.form_submit_button("ACCEDI"):
                if pwd == "RB2026": 
                    st.session_state.autenticato = True
                    st.rerun()
                else: st.error("Accesso Negato.")
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

        # ==================== SEÇÃO DOCUMENTI MODIFICADA ====================
        with st.expander("📄 DOCUMENTI", expanded=True):
            st.markdown("<p style='font-size: 13px;'>Inserisci il numero di ciascun documento e la scadenza. Carica poi tutti i file nell'ordine corrispondente.</p>", unsafe_allow_html=True)
            
            doc_list = []
            cols = st.columns(3)

            # 1. Carta d'Identità
            with cols[0]:
                num_ci = st.text_input("Numero", key="num_ci", placeholder="Carta d'Identità")
                scad_ci = st.date_input("Scadenza", value=date.today(), key="scad_ci", format="DD/MM/YYYY")
            doc_list.append({"tipo": "CartaIdentita", "num": num_ci, "scad": scad_ci})

            # 2. Permesso di Soggiorno
            with cols[1]:
                num_ps = st.text_input("Numero", key="num_ps", placeholder="Permesso di Soggiorno")
                scad_ps = st.date_input("Scadenza", value=date.today(), key="scad_ps", format="DD/MM/YYYY")
            doc_list.append({"tipo": "PermessoSoggiorno", "num": num_ps, "scad": scad_ps})

            # 3. Patente Italiana
            with cols[2]:
                num_pat = st.text_input("Numero", key="num_pat", placeholder="Patente Italiana")
                scad_pat = st.date_input("Scadenza", value=date.today(), key="scad_pat", format="DD/MM/YYYY")
            doc_list.append({"tipo": "PatenteItaliana", "num": num_pat, "scad": scad_pat})

            # Nova linha
            cols2 = st.columns(3)

            # 4. Tessera Sanitaria
            with cols2[0]:
                num_ts = st.text_input("Numero", key="num_ts", placeholder="Tessera Sanitaria")
                scad_ts = st.date_input("Scadenza", value=date.today(), key="scad_ts", format="DD/MM/YYYY")
            doc_list.append({"tipo": "TesseraSanitaria", "num": num_ts, "scad": scad_ts})

            # 5. Passaporto Brasiliano
            with cols2[1]:
                num_pb = st.text_input("Numero", key="num_pb", placeholder="Passaporto Brasiliano")
                scad_pb = st.date_input("Scadenza", value=date.today(), key="scad_pb", format="DD/MM/YYYY")
            doc_list.append({"tipo": "PassaportoBrasiliano", "num": num_pb, "scad": scad_pb})

        st.subheader("📤 Upload Único de Documentos")
        st.info("Carica i file nell'ordine: Carta d'Identità → Permesso di Soggiorno → Patente Italiana → Tessera Sanitaria → Passaporto Brasiliano")
        uploaded_files = st.file_uploader("Carica tutti i documenti", accept_multiple_files=True, key="multi_upload")

        st.subheader("ANNOTAZIONI CLIENTE")
        notas = st.text_area("ANNOTAZIONI CLIENTE", height=120)

        if st.button("🚀 REGISTRA CLIENTE E SINCRONIZZA DRIVE"):
            if nome and cf:
                srb_code = f"SRB{len(st.session_state.clienti)+1:04d}"
                
                with st.spinner("Creazione cartella Drive e upload documenti..."):
                    folder_obj, error = manage_drive_structure(nome, srb_code)
                    
                    if folder_obj:
                        success_count = 0
                        for idx, file in enumerate(uploaded_files):
                            if idx < len(doc_list) and doc_list[idx]["num"]:
                                doc = doc_list[idx]
                                new_filename = f"{doc['tipo']}_{doc['num']}.pdf"
                                if upload_to_client_folder(file, folder_obj['id'], new_filename):
                                    success_count += 1
                        
                        st.session_state.clienti.append({
                            "ID": srb_code, 
                            "Nome": nome, 
                            "CF": cf, 
                            "Regione": regiao,
                            "Link": folder_obj['webViewLink']
                        })
                        st.success(f"✅ Cliente {srb_code} registrato con successo! {success_count} documento(s) caricati.")
                    else:
                        st.error(f"Errore Drive: {error}")
            else:
                st.error("Inserire almeno Nome e Codice Fiscale!")

    with t_aba2:
        if st.session_state.clienti:
            st.dataframe(pd.DataFrame(st.session_state.clienti), use_container_width=True)

# --- OUTRAS PÁGINAS ---
elif menu == "📂 Nuova Pratica":
    st.header("📂 Apertura Nuova Pratica")
    
elif menu == "🗄️ Archivio":
    st.header("🗄️ Archivio Documentale Drive")
    for c in st.session_state.clienti:
        st.write(f"📁 {c['ID']} - {c['Nome']} - [Apri Cartella]({c['Link']})")
