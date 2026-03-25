import streamlit as st
import pandas as pd
from datetime import datetime, date
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import plotly.express as px

# ==========================================
# 1. CONFIGURAÇÃO E ESTILO (CORES CLARAS)
# ==========================================
st.set_page_config(page_title="Studio RBertin - Gestionale", layout="wide")

# Aplicação do fundo #f4e7e1 e campos brancos com letras pretas
st.markdown(f"""
    <style>
    .stApp {{
        background-color: #f4e7e1;
    }}
    /* Estilo dos campos de entrada: Fundo Branco e Letras Pretas */
    .stTextInput>div>div>input, 
    .stSelectbox>div>div>select, 
    .stTextArea>div>div>textarea, 
    .stDateInput>div>div>input {{
        background-color: white !important;
        color: black !important;
    }}
    /* Ajuste para que os textos das etiquetas fiquem bem visíveis */
    label, p, .stMarkdown, h1, h2, h3 {{
        color: #2c2c2c !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO SERVIÇOS GOOGLE ---
def get_google_service(name, version, scopes):
    try:
        info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        return build(name, version, credentials=creds)
    except Exception as e:
        st.error(f"Errore Google {name}: {e}")
        return None

# ==========================================
# 2. FUNÇÕES CORE (DRIVE, CONTATOS)
# ==========================================

def criar_contato_google(nome, tel, email):
    service = get_google_service('people', 'v1', ["https://www.googleapis.com/auth/contacts"])
    if service:
        try:
            service.people().createContact(body={
                "names": [{"givenName": nome}],
                "phoneNumbers": [{"value": tel}],
                "emailAddresses": [{"value": email}]
            }).execute()
        except: pass

def cria_cartella_cliente_drive(nome_completo, srb_code):
    service = get_google_service('drive', 'v3', ["https://www.googleapis.com/auth/drive"])
    if not service: return None
    
    query = "name = 'GESTIONALE RBERTIN' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(q=query, fields="files(id)").execute()
    items = results.get('files', [])
    
    if items:
        parent_id = items[0]['id']
        nome_pasta = f"{srb_code} - {nome_completo}"
        file_metadata = {'name': nome_pasta, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_id]}
        folder = service.files().create(body=file_metadata, fields='id, webViewLink').execute()
        return folder
    return None

# ==========================================
# 3. LOGIN E DATABASE
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
# 4. DASHBOARD
# ==========================================
st.sidebar.title("🏛️ Studio RBertin")
menu = st.sidebar.radio("MENU", ["Dashboard", "Anagrafica Clienti", "Nuova Pratica", "Archivio"])

if menu == "Dashboard":
    st.header("📊 Dashboard Studio RBertin")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Clienti", len(st.session_state.clienti))
    c2.metric("Pratiche Totali", len(st.session_state.pratiche))
    c3.metric("Aperte", sum(1 for p in st.session_state.pratiche if p.get('Stato') == "Aperta"))
    c4.metric("Chiuse", sum(1 for p in st.session_state.pratiche if p.get('Stato') == "Chiusa"))

    st.subheader("📍 Distribuzione Geografica")
    if st.session_state.clienti:
        df_clienti = pd.DataFrame(st.session_state.clienti)
        counts = df_clienti['Regione'].value_counts().reset_index()
        counts.columns = ['Regione', 'Clienti']
        fig = px.bar(counts, x='Regione', y='Clienti', color_discrete_sequence=['#8d6e63'])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nessun dato geografico. Registra i clienti na Anagrafica.")

# ==========================================
# 5. ANAGRAFICA (SRB + DOCUMENTOS FLEXÍVEIS)
# ==========================================
elif menu == "Anagrafica Clienti":
    st.header("👥 Gestione Clienti")
    tab_reg, tab_lista = st.tabs(["➕ Registra", "📑 Lista Clienti (SRB Order)"])
    
    with tab_reg:
        with st.expander("Dati Nuovo Cliente", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                nome = st.text_input("Nome e Cognome")
                cf = st.text_input("Codice Fiscale")
                st.markdown("**Indirizzo**")
                via = st.text_input("Via/Piazza")
                citta = st.text_input("Città")
                cap = st.text_input("CAP")
                regione = st.selectbox("Regione", LISTA_REGIONI)
            
            with col2:
                tel = st.text_input("Telefono")
                email = st.text_input("Email")
                st.markdown("**Documento**")
                tipo_doc_sel = st.selectbox("Tipo Documento", DOC_TYPES)
                if tipo_doc_sel == "Altro":
                    tipo_doc_final = st.text_input("Specifica tipo documento")
                else:
                    tipo_doc_final = tipo_doc_sel
                num_doc = st.text_input("Numero Documento")
                scad_doc = st.date_input("Scadenza Documento")

            if st.button("🚀 SALVA E GENERA SRB"):
                if nome and cf:
                    srb_num = len(st.session_state.clienti) + 1
                    srb_code = f"SRB{srb_num:04d}"
                    folder = cria_cartella_cliente_drive(nome, srb_code)
                    criar_contato_google(nome, tel, email)
                    
                    st.session_state.clienti.append({
                        "ID": srb_code, "Nome": nome, "CF": cf, "Citta": citta, "Regione": regione,
                        "Tel": tel, "Email": email, "Doc": tipo_doc_final, "Doc_Num": num_doc, 
                        "Scadenza": scad_doc, "Drive_URL": folder['webViewLink'] if folder else "#"
                    })
                    st.success(f"Registrato! Codice: {srb_code}")
                else: st.error("Inserisci Nome e Codice Fiscale!")

    with tab_lista:
        if st.session_state.clienti:
            df = pd.DataFrame(st.session_state.clienti).sort_values("ID")
            st.dataframe(df[["ID", "Nome", "Regione", "Doc", "Scadenza"]], use_container_width=True)
            sel_srb = st.selectbox("Seleziona Cliente para detalhes", df["ID"])
            curr = next(item for item in st.session_state.clienti if item["ID"] == sel_srb)
            
            st.markdown(f"### 📄 Dettagli {curr['ID']}")
            st.write(f"**Drive:** [Apri Cartella Cliente]({curr['Drive_URL']})")
            
            # Mostrar Práticas associadas a este cliente específico
            p_cli = [p for p in st.session_state.pratiche if p['Cliente'] == curr['Nome']]
            if p_cli:
                st.table(pd.DataFrame(p_cli))
            else:
                st.write("Nessuna pratica associata.")

# ==========================================
# 6. NUOVA PRATICA E ARCHIVIO
# ==========================================
elif menu == "Nuova Pratica":
    st.header("📂 Nuova Pratica")
    if st.session_state.clienti:
        nome_sel = st.selectbox("Cliente", [c["Nome"] for c in st.session_state.clienti])
        cat = st.selectbox("Tipo", ["FISCO", "CONSOLARI", "PA", "ALTRO"])
        stato = st.radio("Stato", ["Aperta", "Chiusa"], horizontal=True)
        if st.button("Salva Pratica"):
            st.session_state.pratiche.append({
                "Data": date.today().strftime("%d/%m/%Y"), 
                "Cliente": nome_sel, 
                "Tipo": cat, 
                "Stato": stato
            })
            st.success("Pratica salvata!")
    else:
        st.warning("Aggiungi prima un cliente.")

elif menu == "Archivio":
    st.header("🗄️ Archivio Storico")
    if st.session_state.pratiche:
        st.dataframe(pd.DataFrame(st.session_state.pratiche), use_container_width=True)
    else:
        st.info("L'archivio è vuoto.")
