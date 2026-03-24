import streamlit as st
import pandas as pd
from datetime import datetime, date

# 1. Configurazione della Pagina
st.set_page_config(page_title="Studio RBertin - Gestionale", layout="wide")

# --- SISTEMA DI ACCESSO (Password) ---
if 'autenticato' not in st.session_state:
    st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.title("🔐 Accesso Studio RBertin")
    password = st.text_input("Inserisci la password per entrare:", type="password")
    if st.button("Entra"):
        if password == "RB2026":
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

# --- FUNZIONE NOTIFICHE SCADENZE ---
def ottieni_notifiche():
    oggi = date.today()
    avvisi = []
    for c in st.session_state.clienti:
        if c.get("Attivo", True) and c.get("Scadenza_Doc"):
            giorni = (c["Scadenza_Doc"] - oggi).days
            data_f = c["Scadenza_Doc"].strftime('%d/%m/%Y')
            if 0 <= giorni <= 30:
                avvisi.append(f"⚠️ {c['Nome']}: {c['Tipo_Doc']} in scadenza il {data_f} ({giorni} gg)")
            elif giorni < 0:
                avvisi.append(f"🚨 {c['Nome']}: {c['Tipo_Doc']} SCADUTO il {data_f}!")
    return avvisi

# --- SIDEBAR (Menu) ---
st.sidebar.title("🏛️ Studio RBertin")
menu = st.sidebar.radio("VAI A:", ["Dashboard", "Anagrafica Clienti", "Nuova Pratica", "Archivio Pratiche"])

# --- 1. DASHBOARD ---
if menu == "Dashboard":
    st.header("📊 Riepilogo Studio")
    notifiche = ottieni_notifiche()
    if notifiche:
        st.subheader("🔔 Avvisi Scadenze")
        for n in notifiche:
            st.warning(n)
    else:
        st.success("✅ Nessuna scadenza imminente (prossimi 30 giorni).")

    col1, col2, col3 = st.columns(3)
    clienti_attivi = [c for c in st.session_state.clienti if c.get("Attivo", True)]
    col1.metric("Clienti Attivi", len(clienti_attivi))
    col2.metric("Pratiche Totali", len(st.session_state.pratiche))
    col3.metric("Oggi", date.today().strftime('%d/%m/%Y'))

# --- 2. ANAGRAFICA CLIENTI ---
elif menu == "Anagrafica Clienti":
    st.header("👥 Gestione Anagrafica")
    
    with st.expander("➕ Aggiungi / Modifica Cliente"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("Dati Personali")
            nome = st.text_input("Nome e Cognome")
            cf = st.text_input("Codice Fiscale")
            nascita_data = st.date_input("Data di Nascita", value=date(1985,1,1), format="DD/MM/YYYY")
            nascita_luogo = st.text_input("Luogo di Nascita")
            residenza = st.text_input("Indirizzo Residenza")
            attivo = st.toggle("Cliente Attivo", value=True)
        
        with col2:
            st.subheader("Contatti & Note")
            tel = st.text_input("Telefono")
            mail = st.text_input("Email")
            pec = st.text_input("PEC")
            note = st.text_area("Note Cliente (Promemoria)")
        
        with col3:
            st.subheader("Documento")
            tipo_doc = st.selectbox("Tipo Documento", ["Carta d'Identità", "Passaporto", "Permesso di Soggiorno", "Patente"])
            num_doc = st.text_input("Numero Documento")
            scadenza_doc = st.date_input("Data di Scadenza", format="DD/MM/YYYY")
            file_doc = st.file_uploader("Carica scansione (PDF/JPG)", type=["pdf", "jpg", "png"])

        if st.button("Salva Cliente"):
            if nome and cf:
                st.session_state.clienti.append({
                    "Nome": nome, "CF": cf, "Nascita": nascita_data, "Luogo": nascita_luogo,
                    "Residenza": residenza, "Telefono": tel, "Email": mail, "PEC": pec, 
                    "Attivo": attivo, "Tipo_Doc": tipo_doc, "Num_Doc": num_doc, 
                    "Scadenza_Doc": scadenza_doc, "Note": note
                })
                st.success(f"Cliente {nome} salvato!")
            else:
                st.error("Nome e Codice Fiscale sono obbligatori!")

    if st.session_state.clienti:
        st.subheader("Lista Clienti")
        df = pd.DataFrame(st.session_state.clienti).copy()
        df["Nascita"] = df["Nascita"].apply(lambda x: x.strftime('%d/%m/%Y'))
        df["Scadenza_Doc"] = df["Scadenza_Doc"].apply(lambda x: x.strftime('%d/%m/%Y'))
        st.dataframe(df, use_container_width=True)

# --- 3. NUOVA PRATICA (Con Checklist rimesse) ---
elif menu == "Nuova Pratica":
    st.header("📂 Nuova Pratica")
    if not st.session_state.clienti:
        st.warning("Aggiungi un cliente in anagrafica prima.")
    else:
        nomi_attivi = [c["Nome"] for c in st.session_state.clienti if c["Attivo"]]
        scelto = st.selectbox("Seleziona Cliente", nomi_attivi)
        macro = st.selectbox("Categoria", ["FISCO", "CONSOLARI", "PUBBLICA AMMINISTRAZIONE", "VARIE"])
        
        # Checklist dinamiche come richiesto inizialmente
        checklist = []
        if macro == "FISCO":
            checklist = ["Fatture/Ricevute", "Documento d'identità", "Delega firmata"]
        elif macro == "CONSOLARI":
            checklist = ["Passaporto originale", "Foto tessere", "Modulo Ministero"]
        elif macro == "PUBBLICA AMMINISTRAZIONE":
            checklist = ["Tessera Sanitaria", "Certificato Residenza", "Delega"]
        elif macro == "VARIE":
            checklist = ["Documentazione base", "Pagamento ricevuto"]

        for item in checklist:
            st.checkbox(item, key=f"{scelto}_{item}")
            
        dettaglio = st.text_area("Oggetto della Delega / Note Pratica")
        
        if st.button("Avvia Pratica"):
            st.session_state.pratiche.append({
                "Data": date.today().strftime('%d/%m/%Y'), "Cliente": scelto, 
                "Categoria": macro, "Oggetto": dettaglio, "Stato": "Aperta"
            })
            st.balloons()
            st.success("Pratica registrata correttamente!")

# --- 4. ARCHIVIO ---
elif menu == "Archivio Pratiche":
    st.header("🗄️ Archivio")
    if st.session_state.pratiche:
        st.dataframe(pd.DataFrame(st.session_state.pratiche), use_container_width=True)
    else:
        st.info("Nessuna pratica registrata.")
