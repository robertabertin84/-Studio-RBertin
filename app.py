import streamlit as st
import pandas as pd
from datetime import datetime, date
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# ==========================================
# 1. CONFIGURAZIONE APPLICAZIONE
# ==========================================
st.set_page_config(page_title="Studio RBertin - Gestionale", layout="wide")

# --- CONNESSIONE GOOGLE DRIVE ---
def get_drive_service():
    try:
        # Recupera le credenziali dai Secrets di Streamlit
        info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(
            info, 
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"Errore di configurazione Drive: {e}")
        return None

def crea_cartella_cliente_drive(nome_cliente):
    service = get_drive_service()
    if not service:
        return None
    
    try:
        # Cerca la cartella madre 'GESTIONALE RBERTIN'
        query = "name = 'GESTIONALE RBERTIN' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = service.files().list(q=query, fields="files(id)").execute()
        items = results.get('files', [])
        
        if not items:
            st.error("⚠️ Cartella 'GESTIONALE RBERTIN' non trovata su Drive!")
            return None
            
        parent_id = items[0]['id']

        # Crea la sottocartella del cliente
        file_metadata = {
            'name': nome_cliente,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        cartella = service.files().create(body=file_metadata, fields='id').execute()
        return cartella.get('id')
    except Exception as e:
        st.error(f"Errore creazione cartella: {e}")
        return None

# ==========================================
# 2. SISTEMA DI AUTENTICAZIONE
# ==========================================
if 'autenticato' not in st.session_state:
    st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.title("🔐 Accesso Studio RBertin")
    col_login, _ = st.columns([1, 2])
    with col_login:
        password = st.text_input("Inserisci Password Studio:", type="password")
        if st.button("Accedi al Sistema"):
            if password == "RB2026":
                st.session_state.autenticato = True
                st.rerun()
            else:
                st.error("Password errata. Riprova.")
    st.stop()

# ==========================================
# 3. DATABASE E UTILS
# ==========================================
if 'clienti' not in st.session_state:
    st.session_state.clienti = []
if 'pratiche' not in st.session_state:
    st.session_state.pratiche = []

def f_data(dt):
    return dt.strftime("%d/%m/%Y") if dt else ""

def monitor_scadenze():
    oggi = date.today()
    avvisi = []
    for c in st.session_state.clienti:
        if c.get("Attivo", True):
            scadenze_da_controllare = {
                "Carta d'Identità": "Scad_CI",
                "Passaporto": "Scad_Pass",
                "Permesso Soggiorno": "Scad_Perm",
                "Patente": "Scad_Pat"
            }
            for label, key in scadenze_da_controllare.items():
                scad = c.get(key)
                if scad:
                    giorni = (scad - oggi).days
                    if 0 <= giorni <= 30:
                        avvisi.append(f"⚠️ {c['Nome']}: {label} in scadenza il {f_data(scad)}")
                    elif giorni < 0:
                        avvisi.append(f"🚨 {c['Nome']}: {label} SCADUTO il {f_data(scad)}!")
    return avvisi

# ==========================================
# 4. MENU LATERALE
# ==========================================
st.sidebar.title("🏛️ Studio RBertin")
st.sidebar.write("---")
menu = st.sidebar.radio(
    "NAVIGAZIONE:", 
    ["Dashboard", "Anagrafica Clienti", "Nuova Pratica", "Archivio"]
)

# ------------------------------------------
# SEZIONE 1: DASHBOARD
# ------------------------------------------
if menu == "Dashboard":
    st.header("📊 Riepilogo Attività")
    
    notifiche = monitor_scadenze()
    if notifiche:
        for n in notifiche:
            st.warning(n)
    else:
        st.success("✅ Nessuna scadenza imminente (prossimi 30 gg).")
    
    st.write("---")
    c1, c2, c3 = st.columns(3)
    c1.metric("Clienti Totali", len(st.session_state.clienti))
    c2.metric("Pratiche Aperte", len(st.session_state.pratiche))
    c3.metric("Oggi è il", f_data(date.today()))

# ------------------------------------------
# SEZIONE 2: ANAGRAFICA CLIENTI
# ------------------------------------------
elif menu == "Anagrafica Clienti":
    st.header("👥 Gestione Anagrafica e Drive")
    
    with st.expander("➕ AGGIUNGI NUOVO CLIENTE"):
        st.write("Compila tutti i campi per registrare il cliente e creare la sua cartella Drive.")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("📍 Dati Anagrafici")
            nome = st.text_input("Nome e Cognome")
            cf = st.text_input("Codice Fiscale")
            nascita_d = st.date_input("Data di Nascita", value=date(1985,1,1), format="DD/MM/YYYY")
            nascita_l = st.text_input("Luogo di Nascita")
            residenza = st.text_input("Indirizzo Residenza")
            attivo = st.toggle("Cliente Attivo", value=True)
            
        with col2:
            st.subheader("📞 Contatti & Note")
            tel = st.text_input("Recapito Telefonico")
            mail = st.text_input("Indirizzo Email")
            pec = st.text_input("Indirizzo PEC")
            note = st.text_area("Note e Appunti particolari")
            
        with col3:
            st.subheader("🪪 Scadenze Documenti")
            s_ci = st.date_input("Scadenza C.I.", format="DD/MM/YYYY")
            s_pass = st.date_input("Scadenza Passaporto", format="DD/MM/YYYY")
            s_perm = st.date_input("Scadenza Permesso Soggiorno", format="DD/MM/YYYY")
            s_pat = st.date_input("Scadenza Patente", format="DD/MM/YYYY")
            
            st.write("---")
            st.file_uploader("Trascina qui i documenti per Drive", accept_multiple_files=True)

        if st.button("🚀 SALVA CLIENTE E CREA CARTELLA"):
            if nome and cf:
                # Azione Drive
                id_drive = crea_cartella_cliente_drive(nome)
                
                # Salvataggio Database
                nuovo_c = {
                    "Nome": nome, "CF": cf, "Nascita": nascita_d, "Luogo": nascita_l,
                    "Residenza": residenza, "Attivo": attivo, "Telefono": tel,
                    "Email": mail, "PEC": pec, "Note": note,
                    "Scad_CI": s_ci, "Scad_Pass": s_pass, "Scad_Perm": s_perm, "Scad_Pat": s_pat,
                    "Drive_ID": id_drive
                }
                st.session_state.clienti.append(nuovo_c)
                st.success(f"✅ Cliente {nome} creato con successo su Drive e in locale!")
            else:
                st.error("Attenzione: Nome e Codice Fiscale sono campi obbligatori.")

    st.write("---")
    if st.session_state.clienti:
        st.subheader("Elenco Completo")
        st.dataframe(pd.DataFrame(st.session_state.clienti), use_container_width=True)

# ------------------------------------------
# SEZIONE 3: NUOVA PRATICA
# ------------------------------------------
elif menu == "Nuova Pratica":
    st.header("📂 Apertura Nuovo Fascicolo")
    if not st.session_state.clienti:
        st.warning("Nessun cliente in anagrafica. Aggiungine uno prima.")
    else:
        lista_nomi = [cl["Nome"] for cl in st.session_state.clienti if cl["Attivo"]]
        cliente_scelto = st.selectbox("Seleziona il Cliente", lista_nomi)
        
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            cat = st.selectbox("Categoria", ["FISCO", "CONSOLARI", "PUBBLICA AMMINISTRAZIONE", "VARIE"])
            desc = st.text_area("Descrizione Pratica")
        with col_p2:
            st.write("Checklist Documenti Ricevuti:")
            st.checkbox("Documento Identità")
            st.checkbox("Mandato di Assistenza")
            st.checkbox("Ricevuta Pagamento")
            
        if st.button("Apri Pratica"):
            st.session_state.pratiche.append({
                "Data": f_data(date.today()), 
                "Cliente": cliente_scelto, 
                "Tipo": cat, 
                "Note": desc
            })
            st.success("Pratica registrata!")

# ------------------------------------------
# SEZIONE 4: ARCHIVIO
# ------------------------------------------
elif menu == "Archivio":
    st.header("🗄️ Storico Pratiche")
    if st.session_state.pratiche:
        st.dataframe(pd.DataFrame(st.session_state.pratiche), use_container_width=True)
    else:
        st.info("L'archivio pratiche è attualmente vuoto.")
