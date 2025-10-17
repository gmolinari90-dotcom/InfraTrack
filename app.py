import streamlit as st
from lxml import etree
import pandas as pd
from datetime import datetime

# --- CONFIGURAZIONE DELLA PAGINA (con versione) ---
st.set_page_config(page_title="InfraTrack v0.4", page_icon="🚆", layout="wide")

# --- TITOLO E HEADER (con versione) ---
# QUESTA E' LA RIGA MODIFICATA
st.title("🚆 InfraTrack v0.4")
st.subheader("La tua centrale di controllo per progetti infrastrutturali")

placeholder = st.empty()
if placeholder.button("🔄 Reset e Ricarica Nuovo File"):
    st.rerun()

# --- CARICAMENTO FILE ---
st.markdown("---")
st.header("1. Carica la Baseline di Riferimento")

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
            st.header("📄 Informazioni Generali del Progetto")

            project_name = "Attività con UID 1 non trovata"
            formatted_cost = "€ 0,00"

            # Trova l'attività specifica con UID = 1
            task_uid_1 = tree.find(".//msp:Task[msp:UID='1']", namespaces=ns)
            
            if task_uid_1 is not None:
                # Estrai Nome e Costo da QUESTA specifica attività
                project_name = task_uid_1.findtext('msp:Name', namespaces=ns) or "Nome non trovato"
                
                total_cost_str = task_uid_1.findtext('msp:Cost', namespaces=ns) or "0"
                total_cost = float(total_cost_str)
                formatted_cost = f"€ {total_cost:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

            col1, col2 = st.columns(2)
            with col1:
                st.metric(label="Nome Appalto", value=project_name)
            with col2:
                st.metric(label="Importo Totale Lavori", value=formatted_cost)

            # Estrazione TUP e TUF
            st.subheader("🗓️ Milestone Principali (TUP e TUF)")
            milestones_data = []
            all_tasks = tree.findall('.//msp:Task', namespaces=ns)
            
            for task in all_tasks:
                is_milestone_text = (task.findtext('msp:Milestone', namespaces=ns) or '0').lower()
                is_milestone = is_milestone_text == '1' or is_milestone_text == 'true'
                
                task_name = task.findtext('msp:Name', namespaces=ns) or ""
                
                if is_milestone and ("TUP" in task_name.upper() or "TUF" in task_name.upper()):
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

            st.markdown("---")
            with st.expander("🔍 Dati Grezzi per Debug (prime 50 righe del file)"):
                raw_text = file_content_bytes.decode('utf-8', errors='ignore')
                st.code('\n'.join(raw_text.splitlines()[:50]), language='xml')

        except Exception as e:
            st.error(f"Errore durante l'analisi del file XML: {e}")
            st.error("Il file potrebbe essere corrotto o in un formato non valido.")
