import streamlit as st
from mpxj import read

# --- CONFIGURAZIONE DELLA PAGINA ---
# Impostiamo il titolo che appare nella tab del browser e l'icona
st.set_page_config(page_title="InfraTrack", page_icon="🚆", layout="wide")

# --- TITOLO E HEADER ---
st.title("🚆 InfraTrack")
st.subheader("La tua centrale di controllo per progetti infrastrutturali")

# --- CARICAMENTO FILE ---
st.markdown("---")
st.header("1. Carica la Baseline di Riferimento")

# Creiamo l'uploader di file, accettando solo estensione .mpp
uploaded_file = st.file_uploader("Seleziona il file .mpp dal tuo computer", type=["mpp"])

# Questo codice viene eseguito solo DOPO che un file è stato caricato
if uploaded_file is not None:

    # Mostra un messaggio di conferma e una barra di avanzamento
    with st.spinner('Caricamento e analisi del file in corso...'):
        try:
            # Leggiamo il file caricato usando la libreria mpxj
            project = read(uploaded_file)

            # --- ESTRAZIONE INFO INIZIALI ---
            st.success('File analizzato con successo!')
            st.markdown("---")
            st.header("📄 Informazioni Generali del Progetto")

            # 1. Nome Appalto (preso dal nome della prima attività di riepilogo)
            project_name = project.tasks[0].name if project.tasks else "Nome non trovato"

            # 2. Importo Totale Lavori (cerchiamo nel campo 'Costo' del progetto)
            # La formattazione serve per mostrarlo come valuta in Euro
            total_cost = project.cost
            formatted_cost = f"€ {total_cost:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

            # Mostriamo le info in due colonne per un layout più pulito
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label="Nome Appalto", value=project_name)
            with col2:
                st.metric(label="Importo Totale Lavori", value=formatted_cost)

            # 3. Estrazione TUP e TUF (Milestone)
            st.subheader("🗓️ Milestone Principali (TUP e TUF)")

            # Creiamo una lista per contenere i dati delle milestone
            milestones_data = []
            for task in project.tasks:
                # Cerchiamo attività che sono milestone e contengono TUP o TUF nel nome
                if task.milestone and ("TUP" in task.name.upper() or "TUF" in task.name.upper()):
                    milestones_data.append({
                        "Nome Completo": task.name,
                        "Data Inizio": task.start.date() if task.start else "N/D",
                        "Data Fine": task.finish.date() if task.finish else "N/D",
                        "Durata (giorni)": task.duration.duration
                    })
            
            # Se abbiamo trovato delle milestone, le mostriamo in una tabella
            if milestones_data:
                st.dataframe(milestones_data, use_container_width=True)
            else:
                st.warning("Nessuna milestone TUP o TUF trovata nel file.")

        except Exception as e:
            # In caso di errore durante la lettura del file, mostriamo un messaggio chiaro
            st.error(f"Errore durante l'analisi del file: {e}")
            st.error("Il file potrebbe essere corrotto o in un formato non supportato.")
