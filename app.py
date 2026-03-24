import streamlit as st
import pandas as pd
from datetime import datetime, date

# 1. Configurazione Pagina
st.set_page_config(page_title="Studio RBertin - Gestionale", layout="wide")

# --- LOGIN ---
if 'autenticato' not in st.session_state:
    st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.title("🔐 Accesso Studio RBertin")
    password = st.text_input("Password:", type="password")
    if st.button("Entra"):
        if password == "RB2026":
            st.session_state.autenticato = True
            st.rerun()
        else:
            st.error("Password errata")
    st.stop()

# --- DATABASE ---
if 'clienti' not in st.session_state:
    st.session_state.clienti = []
if 'pratiche' not in st.session_state:
    st.session_state.pratiche = []

# --- FUNZIONE NOTIFICHE ---
def check_scadenze():
    oggi = date.today()
    avvisi = []
    for c in st.session_state.clienti:
        if c.get("Attivo", True) and c.get("Scadenza_Doc"):
            giorni = (c["Scadenza_Doc"] - oggi).days
            if 0 <= giorni <= 30:
                avvisi.append(f"⚠️ {c['Nome']}: {c['Tipo_Doc']} in scadenza tra {giorni} giorni!")
            elif giorni < 0:
                avvisi.append(f"🚨 {c['Nome']}: {c['Tipo_Doc']} SCADUTO!")
    return avvisi

# --- MENU ---
st.sidebar.title("🏛️ Studio RBertin")
menu = st.sidebar.radio("VAI A:", ["Dashboard", "Anagrafica Clienti", "Nuova Pratica", "Archivio"])

# 1. DASHBOARD
if menu == "Dashboard":
    st.header("📊 Dashboard Riepilogo")
    notifiche = check_scadenze()
    if notifiche:
        for n in notifiche: st.warning(n)
    else: st.success("✅ Nessuna scadenza imminente.")
    
    col1, col2 = st.columns(2)
    col1.metric("Clienti Totali", len(st.session_state.clienti))
    col2.metric("Pratiche Aperte", len(st.session_state.pratiche))

# 2. ANAGRAFICA (Qui ho rimesso tutto nel dettaglio)
elif menu == "Anagrafica Clienti":
    st.header("👥 Gestione Anagrafica")
    
    with st.expander("➕ Inserisci Nuovo Cliente"):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.subheader("Dati Personali")
            nome = st.text_input("Nome e Cognome")
            nascita_data = st.date_input("Data di Nascita", value=date(1980,1,1))
            nascita_luogo = st.text_input("Luogo di Nascita")
            cf = st.text_input("Codice Fiscale")
            indirizzo = st.text_input("Indirizzo Residenza")
            attivo = st.toggle("Cliente Attivo", value=True)
        
        with c2:
            st.subheader("Contatti & Note")
            tel = st.text_input("Telefono")
            email = st.text_input("Email")
            pec = st.text_input("PEC")
            note = st.text_area("Note sul cliente (es. preferenze, orari)")
        
        with c3:
            st.subheader("Documentazione")
            tipo_doc = st.selectbox("Documento", ["Carta Identità", "Passaporto", "Permesso di Soggiorno", "Patente"])
            num_doc = st.text_input("Numero Documento")
            scadenza_doc = st.date_input("Scadenza Documento")
            carica_doc = st.file_uploader("Carica File (Scansione)", type=['pdf', 'jpg', 'png'])

        if st.button("Salva nel Database"):
            st.session_state.clienti.append({
                "Nome": nome, "Nascita": nascita_data, "Luogo": nascita_luogo,
                "CF": cf, "Indirizzo": indirizzo, "Attivo": attivo,
                "Telefono": tel, "Email": email, "PEC": pec, "Note": note,
                "Tipo_Doc": tipo_doc, "Num_Doc": num_doc, "Scadenza_Doc": scadenza_doc
            })
            st.success("Cliente salvato correttamente!")

    if st.session_state.clienti:
        st.write("---")
        st.subheader("Lista Clienti")
        df = pd.DataFrame(st.session_state.clienti)
        st.dataframe(df, use_container_width=True)

# 3. NUOVA PRATICA
elif menu == "Nuova Pratica":
    st.header("📂 Apertura Pratica / Delega")
    if not st.session_state.clienti:
        st.warning("Inserisci prima un cliente in Anagrafica.")
    else:
        nomi_attivi = [c["Nome"] for c in st.session_state.clienti if c.get("Attivo", True)]
        scelto = st.selectbox("Seleziona Cliente", nomi_attivi)
        macro = st.selectbox("Tipo Pratica", ["FISCO", "CONSOLARI", "PUBBLICA AMMINISTRAZIONE", "VARIE"])
        dettaglio = st.text_area("Dettaglio Pratica / Oggetto Delega")
        
        if st.button("Avvia Pratica"):
            st.session_state.pratiche.append({
                "Data": date.today(), "Cliente": scelto, 
                "Tipo": macro, "Dettaglio": dettaglio, "Stato": "Aperta"
            })
            st.success("Pratica registrata nell'Archivio!")

# 4. ARCHIVIO
elif menu == "Archivio":
    st.header("🗄️ Archivio Storico")
    if st.session_state.pratiche:
        st.dataframe(pd.DataFrame(st.session_state.pratiche), use_container_width=True)
    else:
        st.info("L'archivio è vuoto.")
