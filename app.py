import streamlit as st
from lxml import etree
import pandas as pd
from datetime import datetime

# --- CONFIGURAZIONE DELLA PAGINA ---
st.set_page_config(page_title="InfraTrack", page_icon="🚆", layout="wide")

# --- TITOLO E HEADER ---
st.title("🚆 InfraTrack")
st.subheader("La tua centrale di controllo per progetti infrastrutturali")

# --- CARICAMENTO FILE ---
st.markdown("---")
st.header("1. Carica la Baseline di Riferimento")

# Accettiamo file .xml
uploaded_file = st.file_uploader("Seleziona il file .XML esportato da MS Project", type=["xml"])

if uploaded_file is not None:
    with st.spinner('Caricamento e analisi del file in corso...'):
        try:
            # Leggiamo e analizziamo l'albero XML
            tree = etree.parse(uploaded_file)
            root = tree.getroot()

            # Definiamo il namespace di MS Project, essenziale per trovare gli elementi
            ns = {'msp': 'http://schemas.microsoft.com/project'}

            st.success('File XML analizzato con successo!')
            st.markdown("---")
            st.header("📄 Informazioni Generali del Progetto")

            # --- ESTRAZIONE DATI SECONDO LE NUOVE ISTRUZIONI ---

            project_name = "Nome non trovato"
            formatted_cost = "€ 0,00"

            # Troviamo il contenitore di tutte le attività <Tasks>
            tasks_container = root.find('msp:Tasks', namespaces=ns)
            if tasks_container is not None:
                # Troviamo la PRIMA attività nel file
                first_task = tasks_container.find('msp:Task', namespaces=ns)
                
                if first_task is not None:
                    # 1. Nome Appalto (preso dal campo "Nome" della PRIMA attività)
                    project_name = first_task.findtext('msp:Name', namespaces=ns) or "Nome non trovato"

                    # 2. Importo Totale Lavori (preso dal campo "Costo" della STESSA attività)
                    total_cost_str = first_task.findtext('msp:Cost', namespaces=ns) or "0"
                    total_cost = float(total_cost_str)
                    formatted_cost = f"€ {total_cost:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

            # Mostriamo le info in due colonne
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label="Nome Appalto", value=project_name)
            with col2:
                st.metric(label="Importo Totale Lavori", value=formatted_cost)

            # 3. Estrazione TUP e TUF (Milestone)
            st.subheader("🗓️ Milestone Principali (TUP e TUF)")

            milestones_data = []
            # Troviamo TUTTE le attività nel progetto per cercare le milestone
            all_tasks = root.findall('.//msp:Task', namespaces=ns)
            
            for task in all_tasks:
                is_milestone_text = (task.findtext('msp:Milestone', namespaces=ns) or '0').lower()
                is_milestone = is_milestone_text == '1' or is_milestone_text == 'true'
                
                task_name_element = task.find('msp:Name', namespaces=ns)
                task_name = task_name_element.text if task_name_element is not None else ""
                
                # Cerchiamo TUP o TUF nel campo "Nome"
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
                df_milestones = pd.DataFrame(milestones_data)
                st.dataframe(df_milestones, use_container_width=True)
            else:
                st.warning("Nessuna milestone TUP o TUF trovata nel file.")

        except Exception as e:
            st.error(f"Errore durante l'analisi del file XML: {e}")
            st.error("Il file potrebbe essere corrotto o in un formato non valido. Assicurati che sia stato esportato correttamente da MS Project.")
