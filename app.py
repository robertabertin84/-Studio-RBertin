import streamlit as st
import pandas as pd
from datetime import datetime, date
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# 1. Configurazione Pagina
st.set_page_config(page_title="Studio RBertin - Gestionale", layout="wide")

# --- CONNESSIONE GOOGLE DRIVE ---
def get_drive_service():
    try:
        # Utilizza le credenziali salvate nei Secrets di Streamlit
        info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/drive"])
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"Errore di connessione a Google Drive: {e}")
        return None

def crea_cartella_cliente_drive(nome_cliente):
    service = get_drive_service()
    if not service:
        return None
    
    try:
        # 1. Cerca la cartella principale 'GESTIONALE RBERTIN'
        query = "name = 'GESTIONALE RBERTIN' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = service.files().list(q=query, fields="files(id)").execute()
        items = results.get('files', [])
        
        if not items:
            st.error("Cartella 'GESTIONALE RBERTIN' non trovata su Drive. Creala e condividila con l'email del Service Account.")
            return None
            
        parent_id = items[0]['id']

        # 2. Crea la sottocartella con il nome del cliente
        file_metadata = {
            'name': nome_cliente,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        cartella = service.files().create(body=file_metadata, fields='id').execute()
        return cartella.get('id')
    except Exception as e:
        st.error(f"Errore durante la creazione della cartella: {e}")
        return None

# --- LOGIN ---
if 'autenticato' not in st.session_state:
    st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.title("🔐 Accesso Studio RBertin")
    password = st.text_input("Inserisci Password:", type="password")
    if st.button("Entra"):
        if password == "RB2026":
            st.session_state.autenticato = True
            st.rerun()
        else:
            st.error("Password errata")
    st.stop()

# --- DATABASE IN MEMORIA ---
if 'clienti' not in st.session_state:
    st.session_state.clienti = []
if 'pratiche' not in st.session_state:
    st.session_state.pratiche = []

# --- FUNZIONI DI SUPPORTO ---
def f_data(dt):
    return dt.strftime("%d/%m/%Y") if dt else ""

def monitor_scadenze():
    oggi = date.today()
    avvisi = []
    for c in st.session_state.clienti:
        if c.get("Attivo", True):
            docs = {"C.I.": "Scad_CI", "Passaporto": "Scad_Pass", "Permesso": "Scad_Perm", "Patente": "Scad_Pat"}
            for label, key in docs.items():
                scad = c.get(key)
                if scad:
                    giorni = (scad - oggi).days
                    if 0 <= giorni <= 30:
                        avvisi.append(f"⚠️ {c['Nome']}: {label} in scadenza il {f_data(scad)}")
                    elif giorni < 0:
                        avvisi.append(f"🚨 {c['Nome']}: {label} SCADUTO il {f_data(scad)}!")
    return avvisi

# --- SIDEBAR MENU ---
st.sidebar.title("🏛️ Studio RBertin")
menu = st.sidebar.radio("VAI A:", ["Dashboard", "Anagrafica Clienti", "Nuova Pratica", "Archivio"])

# 1. DASHBOARD
if menu == "Dashboard":
    st.header("📊 Riepilogo Scadenze")
    notifiche = monitor_scadenze()
    for n in notifiche:
        st.warning(n)
    if not notifiche:
        st.success("✅ Tutti i documenti sono in regola.")
    
    c1, c2 = st.columns(2)
    c1.metric("Clienti in Anagrafica", len(st.session_state.clienti))
    c2.metric("Data di Oggi", f_data(date.today()))

# 2. ANAGRAFICA CLIENTI
elif menu == "Anagrafica Clienti":
    st.header("👥 Gestione Anagrafica")
    
    with st.expander("➕ Inserisci Nuovo Cliente"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("📍 Dati Personali")
            nome = st.text_input("Nome e Cognome")
            cf = st.text_input("Codice Fiscale")
            nascita_d = st.date_input("Data Nascita", value=date(1985,1,1), format="DD/MM/YYYY")
            nascita_l = st.text_input("Luogo di Nascita")
            residenza = st.text_input("Indirizzo Residenza")
            attivo = st.toggle("Cliente Attivo", value=True)
            
        with col2:
            st.subheader("📞 Contatti & Note")
            tel = st.text_input("Telefono")
            email_c = st.text_input("Email")
            pec = st.text_input("PEC")
            note_c = st.text_area("Note e Appunti")
            
        with col3:
            st.subheader("🪪 Documenti e Scadenze")
            s_ci = st.date_input("Scadenza C.I.", format="DD/MM/YYYY")
            s_pass = st.date_input("Scadenza Passaporto", format="DD/MM/YYYY")
            s_perm = st.date_input("Scadenza Permesso Soggiorno", format="DD/MM/YYYY")
            s_pat = st.date_input("Scadenza Patente", format="DD/MM/YYYY")
            
            st.write("---")
            caricamento = st.file_uploader("Scegli file da caricare su Drive", accept_multiple_files=True)

        if st.button("🚀 SALVA E CREA CARTELLA DRIVE"):
            if nome and cf:
                # Creazione cartella reale su Drive
                id_drive = crea_cartella_cliente_drive(nome)
                
                # Salvataggio dati nel database locale
                nuovo_cliente = {
                    "Nome": nome, "CF": cf, "Nascita": nascita_d, "Luogo": nascita_l,
                    "Residenza": residenza, "Attivo": attivo, "Telefono": tel,
                    "Email": email_c, "PEC": pec, "Note": note_c,
                    "Scad_CI": s_ci, "Scad_Pass": s_pass, "Scad_Perm": s_perm, "Scad_Pat": s_pat,
                    "Drive_ID": id_drive
                }
                st.session_state.clienti.append(nuovo_cliente)
                st.success(f"✅ Cliente {nome} registrato con successo!")
            else:
                st.error("Nome e Codice Fiscale sono obbligatori.")

    if st.session_state.clienti:
        st.subheader("Elenco Clienti")
        df_clienti = pd.DataFrame(st.session_state.clienti)
        st.dataframe(df_clienti, use_container_width=True)

# 3. NUOVA PRATICA
elif menu == "Nuova Pratica":
    st.header("📂 Apertura Nuova Pratica")
    if not st.session_state.clienti:
        st.warning("Devi prima inserire almeno un cliente in Anagrafica.")
    else:
        nomi_clienti = [c["Nome"] for c in st.session_state.clienti if c["Attivo"]]
        cliente_scelto = st.selectbox("Seleziona Cliente", nomi_clienti)
        
        macro_cat = st.selectbox("Categoria Pratica", ["FISCO", "CONSOLARI", "PUBBLICA AMMINISTRAZIONE", "VARIE"])
        
        st.subheader("✅ Checklist Documenti")
        check_list = {
            "FISCO": ["Fatture", "Delega firmata", "Documento Identità"],
            "CONSOLARI": ["Passaporto", "Foto tessere", "Modulo richiesta"],
            "PUBBLICA AMMINISTRAZIONE": ["Tessera Sanitaria", "Modulo PA", "Marca da bollo"],
            "VARIE": ["Documentazione generica"]
        }
        
        for item in check_list.get(macro_cat):
            st.checkbox(item, key=f"check_{item}")
            
        dettagli = st.text_area("Oggetto della pratica / Note aggiuntive")
        
        if st.button("Registra Pratica"):
            st.session_state.pratiche.append({
                "Data": f_data(date.today()),
                "Cliente": cliente_scelto,
                "Tipo": macro_cat,
                "Dettagli": dettagli
            })
            st.success("Pratica registrata correttamente nell'archivio.")

# 4. ARCHIVIO
elif menu == "Archivio":
    st.header("🗄️ Archivio Storico Pratiche")
    if st.session_state.pratiche:
        df_pratiche = pd.DataFrame(st.session_state.pratiche)
        st.dataframe(df_pratiche, use_container_width=True)
    else:
        st.info("L'archivio è vuoto. Registra una nuova pratica per vederla qui.")
