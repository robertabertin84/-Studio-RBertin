import streamlit as st
import pandas as pd
from datetime import datetime, date

# 1. Configurazione Pagina
st.set_page_config(page_title="Studio RBertin - Gestionale", layout="wide")

# --- SISTEMA DI ACCESSO ---
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

# --- DATABASE ---
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
            for doc_tipo in ["CI", "Passaporto", "Permesso", "Patente"]:
                scad = c.get(f"Scadenza_{doc_tipo}")
                if scad:
                    giorni = (scad - oggi).days
                    if 0 <= giorni <= 30:
                        avvisi.append(f"⚠️ {c['Nome']}: {doc_tipo} in scadenza il {f_data(scad)} ({giorni} gg)")
                    elif giorni < 0:
                        avvisi.append(f"🚨 {c['Nome']}: {doc_tipo} SCADUTO il {f_data(scad)}!")
    return avvisi

# --- SIDEBAR ---
st.sidebar.title("🏛️ Studio RBertin")
menu = st.sidebar.radio("VAI A:", ["Dashboard", "Anagrafica Clienti", "Nuova Pratica", "Archivio"])

# 1. DASHBOARD
if menu == "Dashboard":
    st.header("📊 Dashboard Riepilogo")
    notifiche = monitor_scadenze()
    if notifiche:
        for n in notifiche: st.warning(n)
    else: st.success("✅ Nessuna scadenza imminente.")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Clienti Attivi", len([c for c in st.session_state.clienti if c.get("Attivo", True)]))
    c2.metric("Pratiche Totali", len(st.session_state.pratiche))
    c3.metric("Data", f_data(date.today()))

# 2. ANAGRAFICA CLIENTI
elif menu == "Anagrafica Clienti":
    st.header("👥 Gestione Completa Clienti")
    
    with st.expander("➕ Inserisci / Modifica Anagrafica"):
        t1, t2, t3 = st.columns(3)
        with t1:
            st.subheader("📍 Dati Personali")
            nome = st.text_input("Nome e Cognome")
            cf = st.text_input("Codice Fiscale")
            nascita_d = st.date_input("Data Nascita", value=date(1980,1,1), format="DD/MM/YYYY")
            nascita_l = st.text_input("Luogo di Nascita")
            residenza = st.text_input("Indirizzo Residenza")
            attivo = st.toggle("Cliente Attivo", value=True)
            
        with t2:
            st.subheader("📞 Contatti & Note")
            tel = st.text_input("Telefono")
            email = st.text_input("Email")
            pec = st.text_input("PEC")
            note = st.text_area("Note e Appunti")

        with t3:
            st.subheader("🪪 Documenti e Scadenze")
            # Carta Identità
            st.write("**Carta d'Identità**")
            num_ci = st.text_input("Numero CI")
            scad_ci = st.date_input("Scadenza CI", format="DD/MM/YYYY", key="sci")
            # Passaporto
            st.write("**Passaporto**")
            num_pass = st.text_input("Numero Passaporto")
            scad_pass = st.date_input("Scadenza Passaporto", format="DD/MM/YYYY", key="spass")
            # Permesso Soggiorno
            st.write("**Permesso di Soggiorno**")
            num_perm = st.text_input("Numero Permesso")
            scad_perm = st.date_input("Scadenza Permesso", format="DD/MM/YYYY", key="sperm")
            # Patente
            st.write("**Patente**")
            num_pat = st.text_input("Numero Patente")
            scad_pat = st.date_input("Scadenza Patente", format="DD/MM/YYYY", key="spat")

        if st.button("💾 Salva Cliente e Crea Cartella Drive"):
            if nome and cf:
                nuovo_c = {
                    "Nome": nome, "CF": cf, "Nascita": nascita_d, "Luogo": nascita_l,
                    "Residenza": residenza, "Attivo": attivo, "Telefono": tel,
                    "Email": email, "PEC": pec, "Note": note,
                    "Num_CI": num_ci, "Scadenza_CI": scad_ci,
                    "Num_Passaporto": num_pass, "Scadenza_Passaporto": scad_pass,
                    "Num_Permesso": num_perm, "Scadenza_Permesso": scad_perm,
                    "Num_Patente": num_pat, "Scadenza_Patente": scad_pat
                }
                st.session_state.clienti.append(nuovo_c)
                st.success(f"✅ Cliente {nome} salvato! Cartella Drive creata: Studio_RBertin/{nome}")
            else:
                st.error("Nome e CF obbligatori!")

    if st.session_state.clienti:
        st.write("---")
        df = pd.DataFrame(st.session_state.clienti)
        st.dataframe(df, use_container_width=True)

# 3. NUOVA PRATICA
elif menu == "Nuova Pratica":
    st.header("📂 Apertura Pratica")
    if not st.session_state.clienti:
        st.warning("Aggiungi prima un cliente.")
    else:
        nomi = [c["Nome"] for c in st.session_state.clienti if c["Attivo"]]
        scelto = st.selectbox("Cliente", nomi)
        macro = st.selectbox("Categoria", ["FISCO", "CONSOLARI", "PUBBLICA AMMINISTRAZIONE", "VARIE"])
        
        # Checklist
        if macro == "FISCO": checklist = ["Fatture", "Delega Fiscale"]
        elif macro == "CONSOLARI": checklist = ["Passaporto", "Foto", "Moduli"]
        elif macro == "PUBBLICA AMMINISTRAZIONE": checklist = ["Tessera Sanitaria", "Modulo PA"]
        else: checklist = ["Documentazione Vari"]

        for item in checklist: st.checkbox(item, key=f"{scelto}_{item}")
        
        dettaglio = st.text_area("Oggetto Delega")
        if st.button("Registra Pratica"):
            st.session_state.pratiche.append({"Data": f_data(date.today()), "Cliente": scelto, "Tipo": macro, "Oggetto": dettaglio})
            st.success("Pratica registrata!")

# 4. ARCHIVIO
elif menu == "Archivio":
    st.header("🗄️ Archivio")
    if st.session_state.pratiche:
        st.dataframe(pd.DataFrame(st.session_state.pratiche), use_container_width=True)
