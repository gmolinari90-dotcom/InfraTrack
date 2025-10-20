import streamlit as st
from lxml import etree
import pandas as pd
from datetime import datetime, timedelta
import re
import isodate # Keep this for parsing the duration string

# --- CONFIGURAZIONE DELLA PAGINA ---
st.set_page_config(page_title="InfraTrack v1.0", page_icon="🚆", layout="wide")

# --- CSS PER RIDURRE LA DIMENSIONE DEI CARATTERI ---
st.markdown("""
<style>
    /* Stili CSS per ridurre dimensioni */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, .stApp p, .stApp .stDataFrame, .stApp .stButton>button {
        font-size: 0.85rem !important;
    }
     .stApp h2 { /* Target per il titolo principale H2 */
        font-size: 1.5rem !important; /* Aumentiamo la dimensione del titolo principale */
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
    /* Formattazione date nelle tabelle */
    .stDataFrame td {
        text-align: center !important; /* Centra testo nelle celle */
    }
</style>
""", unsafe_allow_html=True)

# --- TITOLO E HEADER ---
st.markdown("## 🚆 InfraTrack v1.0")
st.caption("La tua centrale di controllo per progetti infrastrutturali")

# --- BOTTONE RESET SEMPRE VISIBILE ---
if st.button("🔄 Reset e Ricarica Nuovo File"):
    # Clear the file uploader state by modifying the key or using session state
    if 'uploaded_file' in st.session_state:
        st.session_state.uploaded_file = None
    st.rerun()

# --- CARICAMENTO FILE ---
st.markdown("---")
st.markdown("#### 1. Carica la Baseline di Riferimento")

uploaded_file = st.file_uploader("Seleziona il file .XML esportato da MS Project", type=["xml"], label_visibility="collapsed", key="uploaded_file")

if uploaded_file is not None:
    with st.spinner('Caricamento e analisi del file in corso...'):
        try:
            file_content_bytes = uploaded_file.getvalue()
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

            # --- Estrazione TUP e TUF con Durata Corretta ---
            st.markdown("##### 🗓️ Milestone Principali (TUP/TUF)")

            potential_milestones = {}
            all_tasks = tree.findall('.//msp:Task', namespaces=ns)
            tup_tuf_pattern = re.compile(r'(?i)(TUP|TUF)\s*\d*')

            # --- NUOVA FUNZIONE FORMAT_DURATION ---
            def format_duration_from_xml(duration_str, work_hours_per_day=8.0):
                """
                Converte la durata ISO 8601 (es. PT1432H0M0S) in giorni lavorativi.
                Assume 8 ore lavorative per giorno se non specificato.
                Restituisce una stringa formattata "Xg".
                """
                if not duration_str or work_hours_per_day <= 0:
                    return "0g"
                try:
                    # Assicura che la stringa inizi con 'P'
                    if duration_str.startswith('T'): # Formato solo tempo
                         duration_str = 'P' + duration_str
                    elif not duration_str.startswith('P'):
                         return "N/D" # Formato non riconosciuto

                    duration = isodate.parse_duration(duration_str)
                    total_hours = duration.total_seconds() / 3600

                    if total_hours == 0:
                        return "0g" # Milestone pura

                    # Calcola i giorni lavorativi
                    work_days = total_hours / work_hours_per_day
                    return f"{round(work_days)}g" # Arrotonda ai giorni interi

                except Exception:
                    return "N/D" # In caso di errore nel parsing


            for task in all_tasks:
                task_name = task.findtext('msp:Name', namespaces=ns) or ""
                match = tup_tuf_pattern.search(task_name)

                if match:
                    tup_tuf_key = match.group(0).upper().strip() # Rimuoviamo spazi extra
                    duration_str = task.findtext('msp:Duration', namespaces=ns)

                    # Usiamo i secondi totali per confronto preciso
                    try:
                        if duration_str and duration_str.startswith('T'): duration_str = 'P' + duration_str
                        duration_obj = isodate.parse_duration(duration_str) if duration_str and duration_str.startswith('P') else timedelta()
                        duration_seconds = duration_obj.total_seconds()
                    except Exception:
                        duration_seconds = 0

                    # Estrai e formatta le date
                    start_date_str = task.findtext('msp:Start', namespaces=ns)
                    finish_date_str = task.findtext('msp:Finish', namespaces=ns)
                    start_date_obj = datetime.fromisoformat(start_date_str) if start_date_str else None
                    finish_date_obj = datetime.fromisoformat(finish_date_str) if finish_date_str else None

                    # --- FORMATTAZIONE DATA DD/MM/YYYY ---
                    start_date_formatted = start_date_obj.strftime("%d/%m/%Y") if start_date_obj else "N/D"
                    finish_date_formatted = finish_date_obj.strftime("%d/%m/%Y") if finish_date_obj else "N/D"

                    current_task_data = {
                        "Nome Completo": task_name,
                        "Data Inizio": start_date_formatted,
                        "Data Fine": finish_date_formatted,
                        "Durata": format_duration_from_xml(duration_str), # Nuova funzione per la durata
                        "DurataSecondi": duration_seconds, # Per confronto
                        "DataInizioObj": start_date_obj # Per ordinamento
                    }

                    if tup_tuf_key not in potential_milestones or duration_seconds > potential_milestones[tup_tuf_key]["DurataSecondi"]:
                         if duration_seconds > 0 or (tup_tuf_key not in potential_milestones):
                              potential_milestones[tup_tuf_key] = current_task_data
                         elif duration_seconds == 0 and tup_tuf_key in potential_milestones and potential_milestones[tup_tuf_key]["DurataSecondi"] == 0:
                              pass # Manteniamo la prima milestone pura trovata

            # Estraiamo i dati finali
            final_milestones_data = []
            for key in potential_milestones:
                data = potential_milestones[key]
                final_milestones_data.append({
                    "Nome Completo": data["Nome Completo"],
                    "Data Inizio": data["Data Inizio"], # Già formattata
                    "Data Fine": data["Data Fine"],     # Già formattata
                    "Durata": data["Durata"],
                    "DataInizioObj": data["DataInizioObj"] # Per ordinamento
                })

            if final_milestones_data:
                df_milestones = pd.DataFrame(final_milestones_data)
                # Ordina per data di inizio effettiva
                df_milestones = df_milestones.sort_values(by="DataInizioObj").reset_index(drop=True)
                # Rimuovi la colonna oggetto data prima di visualizzare e definisci l'ordine
                st.dataframe(df_milestones[["Nome Completo", "Durata", "Data Inizio", "Data Fine"]], use_container_width=True)
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
             try:
                 raw_text = file_content_bytes.decode('utf-8', errors='ignore')
                 st.code('\n'.join(raw_text.splitlines()[:20]), language='xml')
             except Exception:
                 st.error("Impossibile leggere l'inizio del file.")
        except Exception as e:
            st.error(f"Errore imprevisto durante l'analisi del file XML: {e}")
            st.error("Verifica che il file sia un XML valido esportato da MS Project.")
