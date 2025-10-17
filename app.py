import streamlit as st
# Rimuoviamo 'from mpxj import read' e importiamo la libreria per XML
from lxml import etree
import pandas as pd # Importiamo pandas che ci servirà a breve

# --- CONFIGURAZIONE DELLA PAGINA ---
st.set_page_config(page_title="InfraTrack", page_icon="🚆", layout="wide")

# --- TITOLO E HEADER ---
st.title("🚆 InfraTrack")
st.subheader("La tua centrale di controllo per progetti infrastrutturali")

# --- CARICAMENTO FILE ---
st.markdown("---")
st.header("1. Carica la Baseline di Riferimento")

# Modifichiamo l'uploader per accettare file .xml
uploaded_file = st.file_uploader("Seleziona il file .XML esportato da MS Project", type=["xml"])

if uploaded_file is not None:
    with st.spinner('Caricamento e analisi del file in corso...'):
        try:
            # Leggiamo il file XML
            # Questa parte è solo un esempio e andrà sviluppata,
            # ma dimostra che la lettura avviene con successo.
            tree = etree.parse(uploaded_file)
            root = tree.getroot()

            # Estraiamo il nome del progetto (esempio)
            # Dobbiamo navigare la struttura XML, che è standard
            # I namespace ({http://schemas.microsoft.com/project...}) sono importanti
            ns = {'msp': 'http://schemas.microsoft.com/project'}
            project_name = root.findtext('msp:Title', namespaces=ns)
            
            if not project_name:
                project_name = "Nome non trovato nel file XML"

            st.success('File XML analizzato con successo!')
            st.markdown("---")
            st.header("📄 Informazioni Generali del Progetto")

            st.metric(label="Nome Appalto (dal file XML)", value=project_name)
            
            # --- QUI INIZIERA' IL VERO SVILUPPO ---
            # Nelle prossime fasi, scriveremo il codice per estrarre
            # tutte le altre informazioni (costi, milestone, task)
            # navigando l'albero XML. Ma il punto chiave è che
            # l'applicazione è ONLINE E FUNZIONANTE.

        except Exception as e:
            st.error(f"Errore durante l'analisi del file XML: {e}")
