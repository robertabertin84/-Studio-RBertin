import streamlit as st
import pandas as pd
from datetime import datetime

# 1. Configurazione della Pagina
st.set_page_config(page_title="Studio RBertin - Gestionale", layout="wide")

# --- SISTEMA DI ACCESSO (Password) ---
if 'autenticato' not in st.session_state:
    st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.title("🔐 Accesso Studio RBertin")
    password = st.text_input("Inserisci la password per entrare:", type="password")
    if st.button("Entra"):
        if password == "RB2026": # Puoi cambiare questa password in futuro
            st.session_state.autenticato = True
            st.success("Accesso eseguito!")
            st.rerun()
        else:
            st.error("Password errata. Riprova.")
    st.stop()

# --- DATABASE IN MEMORIA ---
if 'clienti' not in st.session_state:
    st.session_state.clienti = []
if 'pratiche' not in st.session_state:
    st.session_state.pratiche = []

# --- SIDEBAR (Menu di navigazione) ---
st.sidebar.title("🏛️ Studio RBertin")
menu = st.sidebar.radio("VAI A:", ["Dashboard", "Anagrafica Clienti", "Nuova Pratica", "Archivio Pratiche"])

# --- 1. DASHBOARD ---
if menu == "Dashboard":
    st.header("📊 Benvenuta nello Studio RBertin")
    st.write(f"Oggi è il {datetime.now().strftime('%d/%m/%Y')}")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Clienti Totali", len(st.session_state.clienti))
    col2.metric("Pratiche Attive", len(st.session_state.pratiche))
    col3.metric("Stato Sistema", "Online")

# --- 2. ANAGRAFICA CLIENTI ---
elif menu == "Anagrafica Clienti":
    st.header("👥 Gestione Anagrafica")
    
    with st.expander("➕ Aggiungi Nuovo Cliente (Dati per Delega)"):
        c1, c2 = st.columns(2)
        with c1:
            nome = st.text_input("Nome e Cognome")
            nascita_data = st.date_input("Data di Nascita", min_value=datetime(1930, 1, 1))
            nascita_luogo = st.text_input("Luogo di Nascita")
            cf = st.text_input("Codice Fiscale")
        with c2:
            residenza = st.text_input("Indirizzo (Via/Piazza)")
            citta_cap = st.text_input("Città e CAP")
            doc_tipo = st.selectbox("Documento", ["Carta d'Identità", "Passaporto", "Patente"])
            doc_num = st.text_input("Numero Documento")
            doc_ente = st.text_input("Rilasciato da (es. Comune di...)")

        if st.button("Salva Cliente"):
            if nome and cf:
                nuovo_cliente = {
                    "Nome": nome, "Nascita": nascita_data, "Luogo": nascita_luogo,
                    "CF": cf, "Residenza": residenza, "Città/CAP": citta_cap,
                    "Doc": doc_tipo, "Num_Doc": doc_num, "Rilascio": doc_ente
                }
                st.session_state.clienti.append(nuovo_cliente)
                st.success(f"Cliente {nome} salvato!")
            else:
                st.error("Nome e Codice Fiscale sono obbligatori!")

    if st.session_state.clienti:
        st.subheader("Lista Clienti Registrati")
        st.dataframe(pd.DataFrame(st.session_state.clienti), use_container_width=True)

# --- 3. NUOVA PRATICA ---
elif menu == "Nuova Pratica":
    st.header("📂 Apertura Nuova Pratica")
    
    if not st.session_state.clienti:
        st.warning("⚠️ Non ci sono clienti nel database. Vai in Anagrafica!")
    else:
        lista_nomi = [c["Nome"] for c in st.session_state.clienti]
        cliente_scelto = st.selectbox("Seleziona Cliente", lista_nomi)
        
        macro = st.selectbox("Macro-Categoria", ["VARIE", "CONSOLARI", "PUBBLICA AMMINISTRAZIONE", "FISCO"])
        
        # Checklist Dinamiche
        checklist = []
        if macro == "VARIE":
            tipo = st.text_input("Specifica Pratica (es. Traduzione)")
            checklist = ["Documento originale", "Pagamento", "Delega firmata"]
        elif macro == "CONSOLARI":
            tipo = st.selectbox("Tipo", ["Rinnovo Passaporto", "Visti", "Cittadinanza"])
            checklist = ["Passaporto vecchio", "Foto tessere", "Contributo"]
        elif macro == "PUBBLICA AMMINISTRAZIONE":
            tipo = st.selectbox("Tipo", ["SPID", "ISEE", "Residenza"])
            checklist = ["Tessera Sanitaria", "Documento", "Delega"]
        elif macro == "FISCO":
            tipo = st.selectbox("Tipo", ["Partita IVA", "730 / Redditi", "Rottamazione"])
            checklist = ["Certificazioni", "Documenti spese", "Fatture"]

        st.write("---")
        st.subheader(f"📋 Checklist per {macro}")
        for item in checklist:
            st.checkbox(item, key=f"{cliente_scelto}_{item}")
        
        oggetto_delega = st.text_area("Oggetto della Delega (verrà inserito nel PDF)")

        if st.button("Avvia Pratica e Genera Delega"):
            st.session_state.pratiche.append({
                "Cliente": cliente_scelto,
                "Macro": macro,
                "Tipo": tipo,
                "Data": datetime.now().strftime("%d/%m/%Y"),
                "Stato": "In Lavorazione"
            })
            st.balloons()
            st.success(f"Pratica avviata! Il segretario Python sta preparando la delega per {cliente_scelto}...")

# --- 4. ARCHIVIO ---
elif menu == "Archivio Pratiche":
    st.header("🗄️ Archivio Pratiche")
    if st.session_state.pratiche:
        st.dataframe(pd.DataFrame(st.session_state.pratiche), use_container_width=True)
    else:
        st.info("L'archivio è vuoto.")
