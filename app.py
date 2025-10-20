import streamlit as st
from lxml import etree
import pandas as pd
from datetime import datetime
import re # Importiamo il modulo per le espressioni regolari

# --- CONFIGURAZIONE DELLA PAGINA ---
st.set_page_config(page_title="InfraTrack v0.7", page_icon="🚆", layout="wide")

# --- CSS PER RIDURRE LA DIMENSIONE DEI CARATTERI ---
# Applichiamo CSS per rendere il testo più piccolo
st.markdown("""
<style>
    /* Riduci dimensione font per header, subheader, testo normale, metriche, tabelle */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, .stApp .stMetric, .stApp p, .stApp .stDataFrame, .stApp .stButton>button {
        font-size: 0.85rem !important; /* Puoi provare valori come 0.8rem o 0.9rem se questo è troppo piccolo/grande */
    }
    /* Riduci dimensione etichette metriche */
     .stApp .stMetric > label {
        font-size: 0.75rem !important;
    }
     /* Riduci dimensione valore metriche */
     .stApp .stMetric > div {
        font-size: 1.2rem !important; /* Riduciamo anche questo ma meno drasticamente */
    }
    /* Riduci dimensione testo bottone Reset */
    .stApp .stButton>button {
         padding: 0.2rem 0.5rem; /* Riduciamo anche il padding del bottone */
    }
</style>
""", unsafe_allow_html=True)


# --- TITOLO E HEADER (con versione) ---
# Usiamo st.markdown per avere più controllo sulla dimensione rispetto a st.header
st.markdown("### 🚆 InfraTrack v0.7") # Era st.header
st.caption("La tua centrale di controllo per progetti infrastrutturali")

placeholder = st.empty()
if placeholder.button("🔄 Reset e Ricarica Nuovo File"):
    st.rerun()

# --- CARICAMENTO FILE ---
st.markdown("---")
st.markdown("#### 1. Carica la Baseline di Riferimento") # Era st.subheader

uploaded_file = st.file_uploader("Seleziona il file .XML esportato da MS Project", type=["xml"], label_visibility="collapsed")

if uploaded_file is not None:
    placeholder.empty()

    with st.spinner('Caricamento e analisi del file in corso...'):
        try:
            file_content_bytes = uploaded_file.getvalue()
            tree = etree.fromstring(file_content_bytes)
            ns = {'msp': 'http://schemas.microsoft.com/project'}

            st.success('File XML analizzato con successo!')
            st.markdown("---")
            st.markdown("#### 📄 Informazioni Generali del Progetto") # Era st.subheader

            project_name = "Attività con UID 1 non trovata"
            formatted_cost = "€ 0,00"

            task_uid_1 = tree.find(".//msp:Task[msp:UID='1']", namespaces=ns)

            if task_uid_1 is not None:
                project_name = task_uid_1.findtext('msp:Name', namespaces=ns) or "Nome non trovato"
                total_cost_str = task_uid_1.findtext('msp:Cost', namespaces=ns) or "0"
                total_cost_cents = float(total_cost_str)
                total_cost_euros = total_cost_cents / 100.0
                formatted_cost = f"€ {total_cost_euros:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

            col1, col2 = st.columns(2)
            with col1:
                # Usiamo st.text o st.markdown per l'etichetta per controllarne la dimensione
                st.markdown(f"**Nome Appalto:** {project_name}")
            with col2:
                st.markdown(f"**Importo Totale Lavori:** {formatted_cost}")
            # Rimuoviamo st.metric che ha dimensioni meno controllabili

            # --- Estrazione TUP e TUF con NUOVA REGOLA ---
            st.markdown("##### 🗓️ Milestone Principali (TUP/TUF)") # Era st.markdown("#### ...")
            milestones_data = []
            all_tasks = tree.findall('.//msp:Task', namespaces=ns)

            # Definiamo il pattern regex: cerca TUP o TUF, seguiti da zero o più spazi (\s*), seguiti da zero o più numeri (\d*)
            # Il (?i) all'inizio rende la ricerca case-insensitive (ignora maiuscole/minuscole)
            tup_tuf_pattern = re.compile(r'(?i)(TUP|TUF)\s*\d*')

            for task in all_tasks:
                is_milestone_text = (task.findtext('msp:Milestone', namespaces=ns) or '0').lower()
                is_milestone = is_milestone_text == '1' or is_milestone_text == 'true'
                task_name = task.findtext('msp:Name', namespaces=ns) or ""

                # Usiamo il pattern regex per cercare nel nome dell'attività
                if is_milestone and tup_tuf_pattern.search(task_name):
                    start_date_str = task.findtext('msp:Start', namespaces=ns)
                    finish_date_str = task.findtext('msp:Finish', namespaces=ns)
                    start_date = datetime.fromisoformat(start_date_str).date() if start_date_str else "N/D"
                    finish_date = datetime.fromisoformat(finish_date_str).date() if finish_date_str else "N/D"

                    milestones_data.append({
                        "Nome Completo": task_name,
                        "Data Inizio": start_date,
                        "Data Fine": finish_date
                    })

            if milestones_data:
                df_milestones = pd.DataFrame(milestones_data).drop_duplicates()
                st.dataframe(df_milestones, use_container_width=True)
            else:
                st.warning("Nessuna milestone TUP o TUF trovata nel file.")

            # Manteniamo la sezione di debug
            st.markdown("---")
            with st.expander("🔍 Dati Grezzi per Debug (prime 50 righe del file)"):
                raw_text = file_content_bytes.decode('utf-8', errors='ignore')
                st.code('\n'.join(raw_text.splitlines()[:50]), language='xml')

        except Exception as e:
            st.error(f"Errore durante l'analisi del file XML: {e}")
            st.error("Il file potrebbe essere corrotto o in un formato non valido.")
