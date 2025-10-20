# --- v9.2 (Reset Rafforzato) ---
import streamlit as st
from lxml import etree
import pandas as pd
from datetime import datetime, date, timedelta
import re
import isodate
from io import BytesIO
import math

# --- CONFIGURAZIONE DELLA PAGINA ---
st.set_page_config(page_title="InfraTrack v9.2", page_icon="🚆", layout="wide") # Version updated

# --- CSS ---
# ... (CSS Identico a v9.1 - omesso per brevità) ...
st.markdown("""
<style>
    /* ... */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, .stApp p, .stApp .stDataFrame, .stApp .stButton>button { font-size: 0.85rem !important; }
    .stApp h2 { font-size: 1.5rem !important; }
    .stApp .stMarkdown h4 { font-size: 1.1rem !important; margin-bottom: 0.5rem; margin-top: 1rem; }
    .stApp .stMarkdown h5 { font-size: 0.90rem !important; margin-bottom: 0.5rem; margin-top: 0.8rem; }
    button[data-testid="stButton"][kind="primary"][key="reset_button"] { padding: 0.2rem 0.5rem !important; line-height: 1.2 !important; font-size: 1.1rem !important; border-radius: 0.25rem !important; }
    button[data-testid="stButton"][kind="primary"][key="reset_button"]:disabled { cursor: not-allowed; opacity: 0.5; }
    .stApp { padding-top: 2rem; }
    .stDataFrame td { text-align: center !important; }
    div[data-testid="stDateInput"] label { font-size: 0.85rem !important; }
    div[data-testid="stDateInput"] input { font-size: 0.85rem !important; padding: 0.3rem 0.5rem !important;}
    .stCaptionContainer { font-size: 0.75rem !important; margin-top: -0.5rem; margin-bottom: 1rem;}
</style>
""", unsafe_allow_html=True)


# --- TITOLO E HEADER ---
st.markdown("## 🚆 InfraTrack v9.2") # Version updated
st.caption("La tua centrale di controllo per progetti infrastrutturali")

# --- GESTIONE RESET ---
if 'widget_key_counter' not in st.session_state: st.session_state.widget_key_counter = 0
if 'file_processed_success' not in st.session_state: st.session_state.file_processed_success = False

# Flag per sapere se il bottone reset è stato premuto
reset_clicked = st.button("🔄", key="reset_button", help="Resetta l'analisi", disabled=not st.session_state.file_processed_success)

if reset_clicked:
    st.session_state.widget_key_counter += 1
    st.session_state.file_processed_success = False
    keys_to_reset = ['uploaded_file_state', 'project_name', 'formatted_cost','df_milestones_display', 'debug_raw_text', 'project_start_date','project_finish_date', 'minutes_per_day', 'all_tasks_data']
    for key in keys_to_reset:
        if key in st.session_state: del st.session_state[key]
    # Forziamo il rerun IMMEDIATAMENTE dopo aver gestito lo stato
    st.rerun()


# --- CARICAMENTO FILE ---
st.markdown("---"); st.markdown("#### 1. Carica la Baseline di Riferimento")
uploader_key = f"file_uploader_{st.session_state.widget_key_counter}"
# Forza il rerender del widget cambiando la chiave dopo il reset
uploaded_file = st.file_uploader("Seleziona il file .XML...", type=["xml"], label_visibility="collapsed", key=uploader_key)

# Mostra messaggio successo solo se processato E non stiamo resettando
if st.session_state.file_processed_success and 'uploaded_file_state' in st.session_state and not reset_clicked:
     st.success('File XML analizzato con successo!')

# Gestione stato file (necessaria perché st.rerun mantiene lo stato dei widget se la key non cambia)
if uploaded_file is not None and uploaded_file != st.session_state.get('uploaded_file_state'):
     st.session_state['uploaded_file_state'] = uploaded_file
     st.session_state.file_processed_success = False # Forza riprocessamento se cambia file
elif 'uploaded_file_state' not in st.session_state:
     uploaded_file = None # Assicura che sia None dopo reset vero

# --- INIZIO ANALISI ---
current_file_to_process = st.session_state.get('uploaded_file_state') # Usa sempre il file in sessione

if current_file_to_process is not None:
    if not st.session_state.get('file_processed_success', False): # Usa .get() per sicurezza
        with st.spinner('Caricamento e analisi completa del file in corso...'):
            try:
                # --- Logica parsing e estrazione dati come v9.1 ---
                # ... (omessa per brevità, identica a v9.1) ...
                current_file_to_process.seek(0); file_content_bytes = current_file_to_process.read()
                parser = etree.XMLParser(recover=True); tree = etree.fromstring(file_content_bytes, parser=parser)
                ns = {'msp': 'http://schemas.microsoft.com/project'}
                # ... Estrazione dati generali, TUP/TUF, all_tasks ...
                # ... Salvataggio in session_state ...
                st.session_state['minutes_per_day'] = minutes_per_day
                st.session_state['project_name'] = project_name; st.session_state['formatted_cost'] = formatted_cost
                st.session_state['project_start_date'] = project_start_date; st.session_state['project_finish_date'] = project_finish_date
                if final_milestones_data:
                    df_milestones = pd.DataFrame(final_milestones_data) #...
                    st.session_state['df_milestones_display'] = df_milestones.drop(columns=['DataInizioObj'])
                else: st.session_state['df_milestones_display'] = None
                st.session_state['all_tasks_data'] = pd.DataFrame(all_tasks_data_list)
                # ... Debug text ...
                st.session_state.file_processed_success = True
                st.rerun() # Forza rerun per mostrare i dati correttamente

            # --- Gestione Errori ---
            # ... (Identica a v9.1) ...
            except etree.XMLSyntaxError as e: st.error(f"Errore Sintassi XML: {e}"); st.error("File malformato?"); st.session_state.file_processed_success = False;
            except KeyError as ke: st.error(f"Errore interno: Chiave mancante {ke}"); st.error("Problema estrazione dati."); st.session_state.file_processed_success = False;
            except Exception as e: st.error(f"Errore Analisi durante elaborazione iniziale: {e}"); st.error("Verifica file XML."); st.session_state.file_processed_success = False;

    # --- VISUALIZZAZIONE DATI E SELEZIONE PERIODO ---
    if st.session_state.get('file_processed_success', False): # Usa .get() per sicurezza
        # --- Sezione 2: Analisi Preliminare ---
        st.markdown("---")
        st.markdown("#### 2. Analisi Preliminare")
        st.markdown("##### 📄 Informazioni Generali dell'Appalto")
        project_name = st.session_state.get('project_name', "N/D")
        formatted_cost = st.session_state.get('formatted_cost', "N/D")
        col1_disp, col2_disp = st.columns(2)
        with col1_disp: st.markdown(f"**Nome:** {project_name}")
        with col2_disp: st.markdown(f"**Importo Totale Lavori:** {formatted_cost}")
        st.markdown("##### 🗓️ Termini Utili Contrattuali (TUP/TUF)")
        df_display = st.session_state.get('df_milestones_display')
        if df_display is not None and not df_display.empty:
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            output = BytesIO();
            with pd.ExcelWriter(output, engine='openpyxl') as writer: df_display.to_excel(writer, index=False, sheet_name='TerminiUtili')
            excel_data = output.getvalue(); st.download_button(label="Scarica (Excel)", data=excel_data, file_name="...", mime="...")
        else: st.warning("Nessun Termine Utile (TUP o TUF) trovato nel file.")

        # --- Sezione 3: Selezione Periodo ---
        st.markdown("---"); st.markdown("#### 3. Analisi Avanzata")
        default_start = st.session_state.get('project_start_date', date.today()); default_finish = st.session_state.get('project_finish_date', date.today() + timedelta(days=365))
        if not default_start: default_start = date.today()
        if not default_finish: default_finish = default_start + timedelta(days=365)
        if default_start > default_finish: default_finish = default_start + timedelta(days=1)
        st.markdown("##### 📅 Seleziona Periodo di Riferimento"); st.caption(f"Default: {default_start.strftime('%d/%m/%Y')} - {default_finish.strftime('%d/%m/%Y')}.")
        col_date1, col_date2 = st.columns(2)
        with col_date1: selected_start_date = st.date_input("Data Inizio", value=default_start, min_value=default_start, max_value=default_finish + timedelta(days=5*365), format="DD/MM/YYYY", key="start_date_selector")
        with col_date2:
            min_end_date = selected_start_date; actual_default_finish = max(default_finish, min_end_date)
            reasonable_max_date = actual_default_finish + timedelta(days=10*365)
            selected_finish_date = st.date_input("Data Fine", value=actual_default_finish, min_value=min_end_date, max_value=reasonable_max_date, format="DD/MM/YYYY", key="finish_date_selector")

        # --- Placeholder per analisi future ---
        st.markdown("---"); st.markdown("##### 📊 Analisi Dettagliate")
        st.info("Seleziona il periodo desiderato. Le prossime analisi (Curva S, Istogrammi) useranno questo intervallo.")

        # --- Debug Section ---
        debug_text = st.session_state.get('debug_raw_text')
        if debug_text:
            st.markdown("---")
            with st.expander("🔍 Dati Grezzi per Debug (prime 50 righe del file)"):
                st.code(debug_text, language='xml')

#else:
#    # Questo blocco viene eseguito solo se current_file_to_process è None
#    st.info("Carica un file XML per iniziare.")
