import streamlit as st
from lxml import etree
import pandas as pd
from datetime import datetime, timedelta
import re # Importiamo il modulo per le espressioni regolari
import isodate # Libreria per interpretare le durate ISO 8601 (es. P1DT8H)

# --- CONFIGURAZIONE DELLA PAGINA ---
st.set_page_config(page_title="InfraTrack v0.8", page_icon="🚆", layout="wide")

# --- CSS PER RIDURRE LA DIMENSIONE DEI CARATTERI ---
st.markdown("""
<style>
    /* Stili CSS per ridurre dimensioni */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, .stApp p, .stApp .stDataFrame, .stApp .stButton>button {
        font-size: 0.85rem !important;
    }
     .stApp .stMarkdown h4 { /* Target specifici per header informazioni */
         font-size: 0.95rem !important;
         margin-bottom: 0.5rem; /* Aggiusta spaziatura */
     }
     .stApp .stMarkdown h5 { /* Target specifici per header milestone */
         font-size: 0.90rem !important;
          margin-bottom: 0.5rem; /* Aggiusta spaziatura */
     }
    /* Riduci dimensione testo bottone Reset */
    .stApp .stButton>button {
         padding: 0.2rem 0.5rem;
    }
     /* Riduciamo un po' il padding generale per compattare */
    .stApp {
        padding-top: 2rem; /* Riduci padding superiore */
    }
</style>
""", unsafe_allow_html=True)

# --- TITOLO E HEADER ---
st.markdown("### 🚆 InfraTrack v0.8")
st.caption("La tua centrale di controllo per progetti infrastrutturali")

# --- BOTTONE RESET SEMPRE VISIBILE ---
# Lo mettiamo qui, fuori dal placeholder, così rimane sempre
if st.button("🔄 Reset e Ricarica Nuovo File"):
    # Cancella lo stato del file caricato (se presente) e riesegue lo script
    st.session_state.uploaded_file = None # Assumiamo che st.file_uploader usi questo per lo stato
    st.rerun()

# --- CARICAMENTO FILE ---
st.markdown("---")
st.markdown("#### 1. Carica la Baseline di Riferimento")

# Usiamo una chiave per poter resettare lo stato del file_uploader
uploaded_file = st.file_uploader("Seleziona il file .XML esportato da MS Project", type=["xml"], label_visibility="collapsed", key="uploaded_file")

if uploaded_file is not None:
    # Non nascondiamo più il bottone reset

    with st.spinner('Caricamento e analisi del file in corso...'):
        try:
            file_content_bytes = uploaded_file.getvalue()
            # Usiamo 'recover=True' per gestire XML potenzialmente malformati
            parser = etree.XMLParser(recover=True)
            tree = etree.fromstring(file_content_bytes, parser=parser)
            ns = {'msp': 'http://schemas.microsoft.com/project'}

            st.success('File XML analizzato con successo!')
            st.markdown("---")
            st.markdown("#### 📄 Informazioni Generali del Progetto")

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
                st.markdown(f"**Nome Appalto:** {project_name}")
            with col2:
                st.markdown(f"**Importo Totale Lavori:** {formatted_cost}")

            # --- Estrazione TUP e TUF con NUOVA REGOLA (Durata Massima) ---
            st.markdown("##### 🗓️ Milestone Principali (TUP/TUF)")
            
            potential_milestones = {} # Usiamo un dizionario per gestire i duplicati
            all_tasks = tree.findall('.//msp:Task', namespaces=ns)

            tup_tuf_pattern = re.compile(r'(?i)(TUP|TUF)\s*\d*')

            # Helper function per convertire durata ISO 8601 in minuti (o altra unità comparabile)
            def parse_duration_to_minutes(duration_str):
                if not duration_str:
                    return 0
                try:
                    # isodate.parse_duration si aspetta 'P...'
                    if not duration_str.startswith('P'):
                         duration_str = 'P'+ duration_str # Aggiungiamo 'P' se manca
                    duration = isodate.parse_duration(duration_str)
                    # Convertiamo tutto in minuti per confronto
                    total_minutes = duration.total_seconds() / 60
                    return total_minutes
                except Exception:
                    # Se il parsing fallisce, consideriamo durata 0
                    return 0

            for task in all_tasks:
                task_name = task.findtext('msp:Name', namespaces=ns) or ""

                # Cerchiamo TUP/TUF nel nome
                match = tup_tuf_pattern.search(task_name)
                if match:
                    # Abbiamo trovato un candidato TUP/TUF
                    tup_tuf_key = match.group(0).upper() # Es: "TUP1", "TUF 2" -> "TUF 2" (Manteniamo spazi e numeri per unicità)
                                                        # Usiamo .upper() per raggruppare "Tup1" e "tup1"
                    
                    duration_str = task.findtext('msp:Duration', namespaces=ns)
                    duration_minutes = parse_duration_to_minutes(duration_str)

                    # Estraiamo le date
                    start_date_str = task.findtext('msp:Start', namespaces=ns)
                    finish_date_str = task.findtext('msp:Finish', namespaces=ns)
                    start_date = datetime.fromisoformat(start_date_str).date() if start_date_str else "N/D"
                    finish_date = datetime.fromisoformat(finish_date_str).date() if finish_date_str else "N/D"

                    current_task_data = {
                        "Nome Completo": task_name,
                        "Data Inizio": start_date,
                        "Data Fine": finish_date,
                        "DurataMinuti": duration_minutes # Teniamo traccia della durata per il confronto
                    }

                    # Controlliamo se abbiamo già visto questo TUP/TUF
                    if tup_tuf_key not in potential_milestones or duration_minutes > potential_milestones[tup_tuf_key]["DurataMinuti"]:
                        # Se è la prima volta che lo vediamo O se questa attività ha durata maggiore, la salviamo
                         potential_milestones[tup_tuf_key] = current_task_data

            # Ora estraiamo solo i dati finali dal dizionario, scartando la durata in minuti
            final_milestones_data = []
            for key in potential_milestones:
                data = potential_milestones[key]
                final_milestones_data.append({
                    "Nome Completo": data["Nome Completo"],
                    "Data Inizio": data["Data Inizio"],
                    "Data Fine": data["Data Fine"]
                })


            if final_milestones_data:
                df_milestones = pd.DataFrame(final_milestones_data)
                # Ordiniamo per data di inizio per una migliore leggibilità
                df_milestones = df_milestones.sort_values(by="Data Inizio").reset_index(drop=True)
                st.dataframe(df_milestones, use_container_width=True)
            else:
                st.warning("Nessuna milestone TUP o TUF trovata nel file.")

            # Manteniamo la sezione di debug
            st.markdown("---")
            with st.expander("🔍 Dati Grezzi per Debug (prime 50 righe del file)"):
                raw_text = file_content_bytes.decode('utf-8', errors='ignore')
                st.code('\n'.join(raw_text.splitlines()[:50]), language='xml')

        except etree.XMLSyntaxError as e:
             st.error(f"Errore di sintassi XML: {e}")
             st.error("Il file XML sembra essere malformato o incompleto. Prova a riesportarlo da MS Project.")
             # Mostra l'inizio del file per aiutare a diagnosticare
             try:
                 raw_text = file_content_bytes.decode('utf-8', errors='ignore')
                 st.code('\n'.join(raw_text.splitlines()[:20]), language='xml')
             except Exception:
                 st.error("Impossibile leggere l'inizio del file.")
        except Exception as e:
            st.error(f"Errore imprevisto durante l'analisi del file XML: {e}")
            st.error("Verifica che il file sia un XML valido esportato da MS Project.")
