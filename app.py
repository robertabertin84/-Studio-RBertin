import streamlit as st
import pandas as pd
from datetime import datetime, date
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# ==========================================
# 1. CONFIGURAZIONE ESTETICA UNIFICATA
# ==========================================
st.set_page_config(page_title="Studio RBertin - Gestionale", layout="wide")

# Cores Definidas: Fundo #f4e7e1 | Detalhes #bc9e92
st.markdown("""
    <style>
    /* Fundo Total da Aplicação e Barra Lateral */
    .stApp, [data-testid="stSidebar"], [data-testid="stSidebarContent"] { 
        background-color: #f4e7e1 !important; 
    }

    /* Texto sempre Preto para leitura */
    label, p, h1, h2, h3, h4, span, li, div, .stMarkdown { 
        color: black !important; 
        font-weight: 500;
    }

    /* Centralização e Estilo do Card de Login */
    [data-testid="stForm"] {
        max-width: 450px;
        margin-left: auto;
        margin-right: auto;
        padding: 40px;
        background-color: #f4e7e1 !important; 
        border-radius: 15px;
        border: 2px solid #bc9e92 !important;
    }

    /* BARRA LATERAL: Corrigindo a cor para ser igual ao botão */
    [data-testid="stSidebarNavItems"] li {
        background-color: #bc9e92 !important;
        margin-bottom: 8px;
        border-radius: 8px;
    }
    [data-testid="stSidebarNavItems"] li a {
        color: black !important;
    }

    /* CORREÇÃO DO ÍCONE "OLHINHO" (👁️) */
    button[aria-label="Show password"] {
        color: #bc9e92 !important;
    }
    button[aria-label="Show password"]:hover {
        color: black !important;
    }
    
    /* Botões e Inputs */
    button[kind="primaryFormSubmit"], .stButton>button {
        background-color: #bc9e92 !important;
        color: black !important;
        border: 1px solid #a88a7e !important;
        width: 100%;
    }
    
    input {
        background-color: white !important;
        color: black !important;
        border: 1px solid #bc9e92 !important;
    }

    /* Esconder cabeçalhos padrão */
    header { visibility: hidden; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI GOOGLE (Simplificadas para estabilidade) ---
def get_google_service(name, version, scopes):
    try:
        info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        return build(name, version, credentials=creds)
    except Exception as e:
        return None

# ==========================================
# 2. LOGIN CENTRALIZADO
# ==========================================
if 'autenticato' not in st.session_state: st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.write("<br><br><br><br>", unsafe_allow_html=True)
    with st.form("login_form"):
        st.markdown("<h2 style='text-align: center;'>⚖️ Accesso Studio RBertin</h2>", unsafe_allow_html=True)
        pwd = st.text_input("Password:", type="password")
        if st.form_submit_button("Entra"):
            if pwd == "RB2026": 
                st.session_state.autenticato = True
                st.rerun()
            else:
                st.error("Password Errata")
    st.stop()

# ==========================================
# 3. GESTIONALE (PÓS-LOGIN)
# ==========================================
if 'clienti' not in st.session_state: st.session_state.clienti = []
if 'pratiche' not in st.session_state: st.session_state.pratiche = []

# Título da Barra Lateral
st.sidebar.markdown("<h2 style='text-align: center;'>⚖️ Studio RBertin</h2>", unsafe_allow_html=True)
menu = st.sidebar.radio("NAVIGAZIONE", ["Dashboard", "Anagrafica Clienti", "Nuova Pratica", "Archivio"])

if menu == "Dashboard":
    st.header("📊 Riepilogo Statistiche")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👥 Clienti", len(st.session_state.clienti))
    c2.metric("📂 Pratiche", len(st.session_state.pratiche))
    c3.metric("🔓 Aperte", sum(1 for p in st.session_state.pratiche if p.get("Stato") == "Aperta"))
    c4.metric("🔒 Chiuse", sum(1 for p in st.session_state.pratiche if p.get("Stato") == "Chiusa"))
    
    st.write("---")
    st.subheader("📍 Distribuzione Geografica")
    if st.session_state.clienti:
        df = pd.DataFrame(st.session_state.clienti)
        st.bar_chart(df['Regione'].value_counts(), color="#bc9e92")
    else:
        st.info("In attesa de novos dados.")

elif menu == "Anagrafica Clienti":
    st.header("👥 Gestione Anagrafica")
    with st.expander("➕ REGISTRA NUOVO CLIENTE", expanded=True):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome e Cognome")
        cf = col1.text_input("Codice Fiscale")
        tel = col2.text_input("Telefono")
        reg = col2.selectbox("Regione", ["Lombardia", "Lazio", "Veneto", "Altro..."])
        
        if st.button("🚀 SALVA CLIENTE"):
            if nome and cf:
                srb_id = f"SRB{len(st.session_state.clienti)+1:03d}"
                st.session_state.clienti.append({"ID": srb_id, "Nome": nome, "CF": cf, "Regione": reg, "Tel": tel})
                st.success(f"Cliente {srb_id} registrato!")
            else:
                st.error("Compilare i campi obbligatori.")

    if st.session_state.clienti:
        st.write("### Lista Clienti (SRB Order)")
        st.table(pd.DataFrame(st.session_state.clienti))

elif menu == "Nuova Pratica":
    st.header("📂 Apertura Nuova Pratica")
    if not st.session_state.clienti:
        st.warning("Nessun cliente trovato. Registra prima un cliente.")
    else:
        st.selectbox("Seleziona Cliente", [c["Nome"] for c in st.session_state.clienti])
        st.selectbox("Tipo Pratica", ["Fiscale", "Legale", "Consolare"])
        st.button("Crea Pratica")

elif menu == "Archivio":
    st.header("🗄️ Archivio Storico")
    st.write("Le pratiche completate verranno visualizzate qui.")
