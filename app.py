import streamlit as st
import pandas as pd
from datetime import datetime, date
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import plotly.express as px

# ==========================================
# 1. CONFIGURAZIONE E ESTILO (COR #bc9e92)
# ==========================================
st.set_page_config(page_title="Studio RBertin - Gestionale", layout="wide")

st.markdown(f"""
    <style>
    .stApp {{
        background-color: #bc9e92;
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
# 2. FUNÇÕES CORE (DRIVE, CONTATOS, REGISTRO)
# ==========================================

def criar_contato_google(nome, tel, email):
    # Nota: Richiede abilitazione Google People API nel Cloud Console
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

# ==========================================
# 4. DASHBOARD COM MAPA
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
        fig = px.bar(counts, x='Regione', y='Clienti', color_discrete_sequence=['#4a3b35'])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Inizia a registrare clienti per vedere la mappa.")

# ==========================================
# 5. ANAGRAFICA (SRB CODE, ENDEREÇO, DOCS)
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
                tipo_doc = st.selectbox("Tipo Doc", ["C.I.", "Passaporto", "Permesso", "Patente"])
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
                        "Tel": tel, "Email": email, "Doc": tipo_doc, "Doc_Num": num_doc, 
                        "Scadenza": scad_doc, "Drive_URL": folder['webViewLink'] if folder else "#"
                    })
                    st.success(f"Registrato con successo! Codice: {srb_code}")
                else: st.error("Inserisci Nome e Codice Fiscale!")

    with tab_lista:
        if st.session_state.clienti:
            df = pd.DataFrame(st.session_state.clienti).sort_values("ID")
            st.dataframe(df[["ID", "Nome", "Regione", "Email", "Tel"]], use_container_width=True)
            
            sel_srb = st.selectbox("Seleziona Cliente per dettagli/Drive", df["ID"])
            curr = next(item for item in st.session_state.clienti if item["ID"] == sel_srb)
            
            st.info(f"📁 [CLICCA QUI PER APRIRE LA CARTELLA DRIVE DI {curr['Nome']}]({curr['Drive_URL']})")

# ==========================================
# 6. NUOVA PRATICA E ARCHIVIO
# ==========================================
elif menu == "Nuova Pratica":
    st.header("📂 Nuova Pratica")
    if not st.session_state.clienti: st.warning("Aggiungi un cliente prima.")
    else:
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
            st.success("Pratica registrata!")

elif menu == "Archivio":
    st.header("🗄️ Archivio Storico")
    if st.session_state.pratiche: 
        st.dataframe(pd.DataFrame(st.session_state.pratiche), use_container_width=True)
    else: st.info("L'archivio è vuoto.")
