import streamlit as st
import pandas as pd
from datetime import datetime

# Configurazione Pagina
st.set_page_config(page_title="Studio Robertin - Gestionale", layout="wide")

# --- TITOLO E LOGO ---
st.title("🏛️ Studio Robertin")
st.subheader("Sistema Gestionale Integrato")

# --- DATABASE TEMPORANEO (In un'app reale useremo un file o un database) ---
if 'clienti' not in st.session_state:
    st.session_state.clienti = []
if 'pratiche' not in st.session_state:
    st.session_state.pratiche = []

# --- SIDEBAR (MENU DI NAVIGAZIONE) ---
menu = st.sidebar.radio("VAI A:", ["Dashboard", "Anagrafica Clienti", "Nuova Pratica", "Archivio Pratiche"])

# --- 1. ANAGRAFICA CLIENTI ---
if menu == "Anagrafica Clienti":
    st.header("👥 Gestione Clienti")
    
    with st.expander("➕ Aggiungi Nuovo Cliente"):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome Completo")
            tel = st.text_input("Numero di Telefono")
        with col2:
            mail = st.text_input("Email")
            nascita = st.date_input("Data di Nascita", min_value=datetime(1930, 1, 1))
        
        if st.button("Salva Cliente"):
            st.session_state.clienti.append({"Nome": nome, "Tel": tel, "Email": mail, "Nascita": nascita})
            st.success(f"Cliente {nome} registrato!")

    if st.session_state.clienti:
        st.write("### Lista Clienti")
        st.table(pd.DataFrame(st.session_state.clienti))

# --- 2. NUOVA PRATICA (I TUOI MACRO-GRUPPI) ---
elif menu == "Nuova Pratica":
    st.header("📂 Apertura Nuova Pratica")
    
    if not st.session_state.clienti:
        st.warning("⚠️ Devi prima aggiungere un cliente nell'Anagrafica!")
    else:
        # Selezione Cliente
        lista_nomi = [c["Nome"] for c in st.session_state.clienti]
        cliente_scelto = st.selectbox("Seleziona Cliente", lista_nomi)
        
        # Selezione Macro-Categoria
        macro = st.selectbox("Macro-Categoria", ["VARIE", "CONSOLARI", "PUBBLICA AMMINISTRAZIONE", "FISCO"])
        
        # Sotto-categorie e Checklist dinamiche
        if macro == "VARIE":
            tipo = st.selectbox("Tipo Pratica", ["Traduzioni", "Pratiche Auto", "Altro"])
            checklist = ["Documento d'identità", "Testo da tradurre", "Pagamento ricevuto"]
            
        elif macro == "CONSOLARI":
            tipo = st.selectbox("Tipo Pratica", ["Rinnovo Passaporto", "Visti", "Trascrizioni Atti"])
            checklist = ["Passaporto scaduto", "Foto tessera", "Contributo amministrativo"]
            
        elif macro == "PUBBLICA AMMINISTRAZIONE":
            tipo = st.selectbox("Tipo Pratica", ["SPID", "ISEE", "Bonus", "Residenza"])
            checklist = ["Tessera Sanitaria", "Redditi", "Delega firmata"]
            
        elif macro == "FISCO":
            tipo = st.selectbox("Tipo Pratica", ["Partita IVA", "Dichiarazione Redditi", "Rottamazione"])
            checklist = ["Attribuzione P.IVA", "Fatture/Ricevute", "Visura Camerale"]

        st.info(f"📋 **Checklist per {tipo}:**")
        for item in checklist:
            st.checkbox(item, key=f"{cliente_scelto}_{item}")

        if st.button("Avvia Pratica"):
            st.session_state.pratiche.append({
                "Cliente": cliente_scelto,
                "Macro": macro,
                "Tipo": tipo,
                "Data": datetime.now().strftime("%d/%m/%Y"),
                "Stato": "In Lavorazione"
            })
            st.success("Pratica registrata e checklist salvata!")

# --- 3. DASHBOARD / ARCHIVIO ---
elif menu == "Dashboard" or menu == "Archivio Pratiche":
    st.header("📊 Stato Avanzamento Lavori")
    if st.session_state.pratiche:
        df_pratiche = pd.DataFrame(st.session_state.pratiche)
        st.dataframe(df_pratiche, use_container_width=True)
    else:
        st.info("Nessuna pratica attiva al momento.")
