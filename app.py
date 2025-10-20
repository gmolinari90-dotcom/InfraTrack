import streamlit as st
from lxml import etree
import pandas as pd
from datetime import datetime, timedelta
import re # Importiamo il modulo per le espressioni regolari
import isodate # Libreria per interpretare le durate ISO 8601 (es. P1DT8H)

# --- CONFIGURAZIONE DELLA PAGINA ---
st.set_page_config(page_title="InfraTrack v0.9", page_icon="🚆", layout="wide")

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
</style>
""", unsafe_allow_html=True)

# --- TITOLO E HEADER (Titolo più grande) ---
# Usiamo H2 per il titolo principale
st.markdown("## 🚆 InfraTrack v0.9")
st.caption("La tua centrale di controllo per progetti infrastrutturali")

# --- BOTTONE RESET SEMPRE VISIBILE ---
if st.button("🔄 Reset e Ricarica Nuovo File"):
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

            # --- Estrazione TUP e TUF con Durata ---
            st.markdown("##### 🗓️ Milestone Principali (TUP/TUF)")
            
            potential_milestones = {}
            all_tasks = tree.findall('.//msp:Task', namespaces=ns)
            tup_tuf_pattern = re.compile(r'(?i)(TUP|TUF)\s*\d*')

            # Funzione per convertire durata ISO 8601 in giorni o ore
            def format_duration(duration_str):
                if not duration_str:
                    return "0g" # 0 giorni se la durata non è specificata
                try:
                    if not duration_str.startswith('P'):
                        duration_str = 'P' + duration_str
                    duration = isodate.parse_duration(duration_str)
                    
                    # Convertiamo in giorni totali
                    total_days = duration.total_seconds() / (24 * 3600)

                    # Se la durata è meno di un giorno, mostriamo le ore
                    if total_days < 1 and total_days > 0:
                        total_hours = duration.total_seconds() / 3600
                        return f"{total_hours:.1f}h" # Ore con un decimale
                    elif total_days == 0:
                         return "0g" # Milestone pura
                    else:
                        # Arrotondiamo i giorni al numero intero più vicino
                        return f"{round(total_days)}g"
                except Exception:
                    return "N/D" # In caso di errore nel parsing

            for task in all_tasks:
                task_name = task.findtext('msp:Name', namespaces=ns) or ""
                match = tup_tuf_pattern.search(task_name)
                
                if match:
                    tup_tuf_key = match.group(0).upper()
                    duration_str = task.findtext('msp:Duration', namespaces=ns)
                    
                    # Usiamo i secondi totali per un confronto preciso della durata
                    try:
                        if duration_str and not duration_str.startswith('P'): duration_str = 'P' + duration_str
                        duration_obj = isodate.parse_duration(duration_str) if duration_str else timedelta()
                        duration_seconds = duration_obj.total_seconds()
                    except Exception:
                        duration_seconds = 0 # Durata 0 se errore o non specificata

                    start_date_str = task.findtext('msp:Start', namespaces=ns)
                    finish_date_str = task.findtext('msp:Finish', namespaces=ns)
                    start_date = datetime.fromisoformat(start_date_str).date() if start_date_str else "N/D"
                    finish_date = datetime.fromisoformat(finish_date_str).date() if finish_date_str else "N/D"

                    current_task_data = {
                        "Nome Completo": task_name,
                        "Data Inizio": start_date,
                        "Data Fine": finish_date,
                        "Durata": format_duration(duration_str), # Salviamo la durata formattata
                        "DurataSecondi": duration_seconds # Usiamo i secondi per il confronto
                    }

                    # Scegliamo quello con durata maggiore (NON zero)
                    if tup_tuf_key not in potential_milestones or duration_seconds > potential_milestones[tup_tuf_key]["DurataSecondi"]:
                         # Ignoriamo le milestone pure (durata 0) se abbiamo già trovato un candidato con durata > 0
                         if duration_seconds > 0 or (tup_tuf_key not in potential_milestones):
                              potential_milestones[tup_tuf_key] = current_task_data
                         # Se la durata attuale è 0 ma abbiamo già una milestone con durata 0, manteniamo la prima trovata (o puoi aggiungere altra logica qui se serve)
                         elif duration_seconds == 0 and tup_tuf_key in potential_milestones and potential_milestones[tup_tuf_key]["DurataSecondi"] == 0:
                              pass # Manteniamo quella esistente

            # Estraiamo i dati finali, escludendo la durata in secondi usata solo per confronto
            final_milestones_data = []
            for key in potential_milestones:
                data = potential_milestones[key]
                final_milestones_data.append({
                    "Nome Completo": data["Nome Completo"],
                    "Data Inizio": data["Data Inizio"],
                    "Data Fine": data["Data Fine"],
                    "Durata": data["Durata"] # Aggiungiamo la durata formattata
                })

            if final_milestones_data:
                df_milestones = pd.DataFrame(final_milestones_data)
                df_milestones = df_milestones.sort_values(by="Data Inizio").reset_index(drop=True)
                # Definiamo l'ordine delle colonne
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
