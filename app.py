import streamlit as st
import pandas as pd
from datetime import datetime, date

# Configurazione Pagina
st.set_page_config(page_title="Studio RBertin - Gestionale", layout="wide")

# --- LOGIN ---
if 'autenticato' not in st.session_state:
    st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.title("🔐 Accesso Studio RBertin")
    password = st.text_input("Inserisci password:", type="password")
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
                avvisi.append(f"🚨 {c['Nome']}: {c['Tipo_Doc']} SCADUTO il {c['Scadenza_Doc'].strftime('%d/%m/%Y')}!")
    return avvisi

# --- MENU ---
st.sidebar.title("🏛️ Studio RBertin")
menu = st.sidebar.radio("VAI A:", ["Dashboard", "Anagrafica Clienti", "Nuova Pratica", "Archivio"])

if menu == "Dashboard":
    st.header("📊 Riepilogo Studio")
    notifiche = check_scadenze()
    if notifiche:
        for n in notifiche: st.warning(n)
    else: st.success("✅ Nessun documento in scadenza.")

elif menu == "Anagrafica Clienti":
    st.header("👥 Anagrafica e Documenti")
    with st.expander("➕ Aggiungi / Modifica Cliente"):
        c1, c2, c3 = st.columns(3)
        with c1:
            nome = st.text_input("Nome e Cognome")
            cf = st.text_input("Codice Fiscale")
            attivo = st.toggle("Cliente Attivo", value=True)
        with c2:
            tel = st.text_input("Telefono")
            pec = st.text_input("PEC / Email")
            note = st.text_area("Note")
        with c3:
            tipo_doc = st.selectbox("Documento", ["Carta Identità", "Passaporto", "Permesso Soggiorno", "Patente"])
            num_doc = st.text_input("Numero Doc")
            scadenza = st.date_input("Scadenza Doc")
            carica = st.file_uploader("Carica File", type=['pdf', 'jpg', 'png'])
        
        if st.button("Salva Cliente"):
            st.session_state.clienti.append({
                "Nome": nome, "CF": cf, "Attivo": attivo, "Telefono": tel,
                "PEC": pec, "Note": note, "Tipo_Doc": tipo_doc,
                "Num_Doc": num_doc, "Scadenza_Doc": scadenza
            })
            st.success("Salvato!")

    if st.session_state.clienti:
        st.dataframe(pd.DataFrame(st.session_state.clienti), use_container_width=True)

elif menu == "Nuova Pratica":
    st.header("📂 Nuova Pratica")
    # Qui inseriremo la funzione PDF Delega appena carichi il file su GitHub
    st.info("Seleziona un cliente dall'anagrafica per generare la delega.")
