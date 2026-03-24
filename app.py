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
        query = "name = 'GESTIONALE RBERTIN' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = service.files().list(q=query, fields="files(id)").execute()
        items = results.get('files', [])
        if not items:
            st.error("⚠️ Cartella 'GESTIONALE RBERTIN' non trovata su Drive!")
            return None
        parent_id = items[0]['id']
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
                st.error("Password errata.")
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
            scadenze = {"C.I.": "Scad_CI", "Passaporto": "Scad_Pass", "Permesso": "Scad_Perm", "Patente": "Scad_Pat"}
            for label, key in scadenze.items():
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
menu = st.sidebar.radio("NAVIGAZIONE:", ["Dashboard", "Anagrafica Clienti", "Nuova Pratica", "Archivio"])

# ------------------------------------------
# SEZIONE 1: DASHBOARD (AGGIORNATA)
# ------------------------------------------
if menu == "Dashboard":
    st.header("📊 Riepilogo Statistiche Studio")
    
    # Calcolo dei numeri richiesti
    tot_clienti = len(st.session_state.clienti)
    tot_pratiche = len(st.session_state.pratiche)
    pratiche_aperte = sum(1 for p in st.session_state.pratiche if p.get("Stato") == "Aperta")
    pratiche_chiuse = sum(1 for p in st.session_state.pratiche if p.get("Stato") == "Chiusa")

    # Visualizzazione Metriche
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("👥 Totale Clienti", tot_clienti)
    m2.metric("📂 Totale Pratiche", tot_pratiche)
    m3.metric("🔓 Pratiche Aperte", pratiche_aperte, delta_color="normal")
    m4.metric("🔒 Pratiche Chiuse", pratiche_chiuse)

    st.write("---")
    st.subheader("🔔 Avvisi Scadenze Documenti")
    notifiche = monitor_scadenze()
    if notifiche:
        for n in notifiche: st.warning(n)
    else:
        st.success("✅ Nessun documento in scadenza nei prossimi 30 giorni.")

# ------------------------------------------
# SEZIONE 2: ANAGRAFICA CLIENTI
# ------------------------------------------
elif menu == "Anagrafica Clienti":
    st.header("👥 Gestione Anagrafica e Drive")
    with st.expander("➕ AGGIUNGI NUOVO CLIENTE"):
        col1, col2, col3 = st.columns(3)
        with col1:
            nome = st.text_input("Nome e Cognome")
            cf = st.text_input("Codice Fiscale")
            nascita_d = st.date_input("Data Nascita", value=date(1985,1,1), format="DD/MM/YYYY")
            nascita_l = st.text_input("Luogo di Nascita")
            residenza = st.text_input("Indirizzo Residenza")
            attivo = st.toggle("Cliente Attivo", value=True)
        with col2:
            tel = st.text_input("Telefono")
            mail = st.text_input("Email")
            pec = st.text_input("PEC")
            note = st.text_area("Note e Appunti")
        with col3:
            s_ci = st.date_input("Scadenza C.I.", format="DD/MM/YYYY")
            s_pass = st.date_input("Scadenza Passaporto", format="DD/MM/YYYY")
            s_perm = st.date_input("Scadenza Permesso", format="DD/MM/YYYY")
            s_pat = st.date_input("Scadenza Patente", format="DD/MM/YYYY")
            st.file_uploader("Carica file su Drive", accept_multiple_files=True)

        if st.button("🚀 SALVA CLIENTE E CREA CARTELLA"):
            if nome and cf:
                id_drive = crea_cartella_cliente_drive(nome)
                st.session_state.clienti.append({
                    "Nome": nome, "CF": cf, "Nascita": nascita_d, "Luogo": nascita_l,
                    "Residenza": residenza, "Attivo": attivo, "Telefono": tel,
                    "Email": mail, "PEC": pec, "Note": note,
                    "Scad_CI": s_ci, "Scad_Pass": s_pass, "Scad_Perm": s_perm, "Scad_Pat": s_pat,
                    "Drive_ID": id_drive
                })
                st.success(f"✅ Cliente {nome} creato con successo!")
            else: st.error("Nome e CF sono obbligatori.")

    if st.session_state.clienti:
        st.dataframe(pd.DataFrame(st.session_state.clienti), use_container_width=True)

# ------------------------------------------
# SEZIONE 3: NUOVA PRATICA
# ------------------------------------------
elif menu == "Nuova Pratica":
    st.header("📂 Apertura Nuovo Fascicolo")
    if not st.session_state.clienti:
        st.warning("Aggiungi prima un cliente in anagrafica.")
    else:
        lista_nomi = [cl["Nome"] for cl in st.session_state.clienti if cl["Attivo"]]
        cliente_scelto = st.selectbox("Seleziona il Cliente", lista_nomi)
        
        c_p1, c_p2 = st.columns(2)
        with c_p1:
            cat = st.selectbox("Categoria", ["FISCO", "CONSOLARI", "PA", "VARIE"])
            desc = st.text_area("Oggetto/Note Pratica")
        with c_p2:
            stato = st.selectbox("Stato Iniziale", ["Aperta", "Chiusa"])
            st.write("Checklist:")
            st.checkbox("Documento Identità")
            st.checkbox("Mandato firmato")
            
        if st.button("Registra Pratica"):
            st.session_state.pratiche.append({
                "Data": f_data(date.today()), 
                "Cliente": cliente_scelto, 
                "Tipo": cat, 
                "Stato": stato,
                "Note": desc
            })
            st.success(f"Pratica registrata come '{stato}'!")

# ------------------------------------------
# SEZIONE 4: ARCHIVIO
# ------------------------------------------
elif menu == "Archivio":
    st.header("🗄️ Storico Pratiche")
    if st.session_state.pratiche:
        st.dataframe(pd.DataFrame(st.session_state.pratiche), use_container_width=True)
    else: st.info("L'archivio è vuoto.")
