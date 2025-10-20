import streamlit as st
from lxml import etree
import pandas as pd
from datetime import datetime, timedelta
import re
import isodate
from io import BytesIO

# --- CONFIGURAZIONE DELLA PAGINA ---
st.set_page_config(page_title="InfraTrack v1.5", page_icon="🚆", layout="wide") # Version updated

# --- CSS ---
st.markdown("""
<style>
    /* ... (CSS omesso per brevità, è lo stesso di prima) ... */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, .stApp p, .stApp .stDataFrame, .stApp .stButton>button {
        font-size: 0.85rem !important;
    }
     .stApp h2 {
        font-size: 1.5rem !important;
     }
     .stApp .stMarkdown h4 {
         font-size: 0.95rem !important;
         margin-bottom: 0.5rem;
     }
     .stApp .stMarkdown h5 {
         font-size: 0.90rem !important;
          margin-bottom: 0.5rem;
     }
    .stApp .stButton>button {
         padding: 0.2rem 0.5rem;
    }
    .stApp {
        padding-top: 2rem;
    }
    .stDataFrame td {
        text-align: center !important;
    }
</style>
""", unsafe_allow_html=True)

# --- TITOLO E HEADER ---
st.markdown("## 🚆 InfraTrack v1.5") # Version updated
st.caption("La tua centrale di controllo per progetti infrastrutturali")

# --- GESTIONE RESET CON SESSION STATE ---
# Inizializza il contatore per la chiave del file uploader se non esiste
if 'widget_key_counter' not in st.session_state:
    st.session_state.widget_key_counter = 0

# Bottone Reset
if st.button("🔄 Reset Completo"):
    # Incrementa il contatore per cambiare la chiave del widget
    st.session_state.widget_key_counter += 1
    # Pulisce esplicitamente lo stato del file caricato (se presente in sessione)
    if 'uploaded_file_state' in st.session_state:
        del st.session_state['uploaded_file_state']
    # Ricarica l'app
    st.rerun()

# --- CARICAMENTO FILE ---
st.markdown("---")
st.markdown("#### 1. Carica la Baseline di Riferimento")

# Usa una chiave dinamica basata sul contatore
uploader_key = f"file_uploader_{st.session_state.widget_key_counter}"
uploaded_file = st.file_uploader(
    "Seleziona il file .XML esportato da MS Project",
    type=["xml"],
    label_visibility="collapsed",
    key=uploader_key
)

# Salva lo stato del file caricato in session state per persistenza tra rerun parziali
if uploaded_file is not None:
    st.session_state['uploaded_file_state'] = uploaded_file
elif 'uploaded_file_state' in st.session_state:
     # Se non c'è un nuovo file caricato ma uno stato salvato, usalo
     # Utile se altre parti dell'app causano un rerun senza un reset completo
     uploaded_file = st.session_state['uploaded_file_state']


# --- INIZIO ANALISI (Solo se un file è stato caricato) ---
if uploaded_file is not None:
    st.markdown("---")
    # --- NUOVO TITOLO ---
    st.markdown("#### 2. Analisi Preliminare")

    with st.spinner('Caricamento e analisi del file in corso...'):
        try:
            # Leggi il contenuto solo una volta all'inizio dell'analisi
            # Assicurati che il puntatore del file sia all'inizio
            uploaded_file.seek(0)
            file_content_bytes = uploaded_file.read()

            parser = etree.XMLParser(recover=True)
            tree = etree.fromstring(file_content_bytes, parser=parser)
            ns = {'msp': 'http://schemas.microsoft.com/project'}

            st.success('File XML analizzato con successo!')
            st.markdown("---")
            st.markdown("##### 📄 Informazioni Generali del Progetto") # Leggermente più piccolo

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
            with col1: st.markdown(f"**Nome Appalto:** {project_name}")
            with col2: st.markdown(f"**Importo Totale Lavori:** {formatted_cost}")


            st.markdown("###### 🗓️ Milestone Principali (TUP/TUF)") # Ancora più piccolo

            potential_milestones = {}
            all_tasks = tree.findall('.//msp:Task', namespaces=ns)
            tup_tuf_pattern = re.compile(r'(?i)(TUP|TUF)\s*\d*')

            def format_duration_from_xml(duration_str, work_hours_per_day=8.0):
                # ... (funzione durata omessa per brevità) ...
                if not duration_str or work_hours_per_day <= 0: return "0g"
                try:
                    if duration_str.startswith('T'): duration_str = 'P' + duration_str
                    elif not duration_str.startswith('P'): return "N/D"
                    duration = isodate.parse_duration(duration_str)
                    total_hours = duration.total_seconds() / 3600
                    if total_hours == 0: return "0g"
                    work_days = total_hours / work_hours_per_day
                    return f"{round(work_days)}g"
                except Exception: return "N/D"


            for task in all_tasks:
                # ... (Logica estrazione TUP/TUF omessa per brevità) ...
                task_name = task.findtext('msp:Name', namespaces=ns) or ""
                match = tup_tuf_pattern.search(task_name)
                if match:
                    tup_tuf_key = match.group(0).upper().strip()
                    duration_str = task.findtext('msp:Duration', namespaces=ns)
                    try:
                        if duration_str and duration_str.startswith('T'): duration_str = 'P' + duration_str
                        duration_obj = isodate.parse_duration(duration_str) if duration_str and duration_str.startswith('P') else timedelta()
                        duration_seconds = duration_obj.total_seconds()
                    except Exception: duration_seconds = 0
                    start_date_str = task.findtext('msp:Start', namespaces=ns)
                    finish_date_str = task.findtext('msp:Finish', namespaces=ns)
                    start_date_obj = datetime.fromisoformat(start_date_str) if start_date_str else None
                    finish_date_obj = datetime.fromisoformat(finish_date_str) if finish_date_str else None
                    start_date_formatted = start_date_obj.strftime("%d/%m/%Y") if start_date_obj else "N/D"
                    finish_date_formatted = finish_date_obj.strftime("%d/%m/%Y") if finish_date_obj else "N/D"
                    current_task_data = {
                        "Nome Completo": task_name, "Data Inizio": start_date_formatted, "Data Fine": finish_date_formatted,
                        "Durata": format_duration_from_xml(duration_str), "DurataSecondi": duration_seconds, "DataInizioObj": start_date_obj
                    }
                    if tup_tuf_key not in potential_milestones or duration_seconds > potential_milestones[tup_tuf_key]["DurataSecondi"]:
                         if duration_seconds > 0 or (tup_tuf_key not in potential_milestones): potential_milestones[tup_tuf_key] = current_task_data
                         elif duration_seconds == 0 and tup_tuf_key in potential_milestones and potential_milestones[tup_tuf_key]["DurataSecondi"] == 0: pass


            final_milestones_data = []
            for key in potential_milestones:
                 data = potential_milestones[key]
                 final_milestones_data.append({"Nome Completo": data["Nome Completo"], "Data Inizio": data["Data Inizio"], "Data Fine": data["Data Fine"],
                                               "Durata": data["Durata"], "DataInizioObj": data["DataInizioObj"]})

            if final_milestones_data:
                df_milestones = pd.DataFrame(final_milestones_data)
                df_milestones = df_milestones.sort_values(by="DataInizioObj").reset_index(drop=True)
                df_display = df_milestones[["Nome Completo", "Durata", "Data Inizio", "Data Fine"]]
                st.dataframe(df_display, use_container_width=True, hide_index=True)

                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_display.to_excel(writer, index=False, sheet_name='Milestones')
                excel_data = output.getvalue()
                st.download_button(
                    label="Scarica (Excel)",
                    data=excel_data,
                    file_name="milestones_TUP_TUF.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            else:
                st.warning("Nessuna milestone TUP o TUF trovata nel file.")

            # Manteniamo la sezione di debug
            st.markdown("---")
            with st.expander("🔍 Dati Grezzi per Debug (prime 50 righe del file)"):
                # Assicurati che il puntatore sia all'inizio prima di leggere di nuovo per il debug
                uploaded_file.seek(0)
                debug_content_bytes = uploaded_file.read(2000) # Leggi solo i primi 2KB per il debug
                try:
                    raw_text = debug_content_bytes.decode('utf-8', errors='ignore')
                    st.code('\n'.join(raw_text.splitlines()[:50]), language='xml')
                except Exception as decode_err:
                    st.error(f"Errore nella decodifica per il debug: {decode_err}")


        except etree.XMLSyntaxError as e:
             st.error(f"Errore di sintassi XML: {e}")
             st.error("Il file XML sembra essere malformato o incompleto. Prova a riesportarlo da MS Project.")
             try:
                 # Assicurati che il puntatore sia all'inizio
                 uploaded_file.seek(0)
                 error_content_bytes = uploaded_file.read(1000) # Leggi solo l'inizio
                 raw_text = error_content_bytes.decode('utf-8', errors='ignore')
                 st.code('\n'.join(raw_text.splitlines()[:20]), language='xml')
             except Exception:
                 st.error("Impossibile leggere l'inizio del file per il debug.")
        except Exception as e:
            st.error(f"Errore imprevisto durante l'analisi del file XML: {e}")
            st.error("Verifica che il file sia un XML valido esportato da MS Project.")

#else:
    # Questa parte viene eseguita se nessun file è caricato (ad esempio dopo il reset)
    # st.info("Carica un file XML per iniziare l'analisi.") # Puoi aggiungere un messaggio se vuoi
    # pass # Non fare nulla se non c'è un file
