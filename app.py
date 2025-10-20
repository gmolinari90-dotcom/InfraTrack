import streamlit as st
from lxml import etree
import pandas as pd
from datetime import datetime, timedelta
import re
import isodate
from io import BytesIO

# --- CONFIGURAZIONE DELLA PAGINA ---
st.set_page_config(page_title="InfraTrack v1.7", page_icon="🚆", layout="wide") # Version updated

# --- CSS ---
st.markdown("""
<style>
    /* ... (CSS omesso per brevità, è lo stesso di prima) ... */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, .stApp p, .stApp .stDataFrame, .stApp .stButton>button {
        font-size: 0.85rem !important;
    }
     .stApp h2 { /* Titolo Principale */
        font-size: 1.5rem !important;
     }
     .stApp .stMarkdown h4 { /* Titoli Sezione */
         font-size: 0.95rem !important;
         margin-bottom: 0.5rem;
         margin-top: 1rem;
     }
     .stApp .stMarkdown h5 { /* Sottotitoli */
         font-size: 0.90rem !important;
         margin-bottom: 0.5rem;
         margin-top: 0.8rem;
     }
    .stApp .stButton>button {
         padding: 0.2rem 0.5rem;
         line-height: 1; /* Allinea meglio l'icona */
    }
     /* Stile per bottone reset disabilitato */
     .stApp .stButton>button:disabled {
        cursor: not-allowed;
        opacity: 0.5;
     }
    .stApp {
        padding-top: 2rem;
    }
    .stDataFrame td {
        text-align: center !important;
    }
    /* Allinea verticalmente titolo e bottone reset */
    [data-testid="stHorizontalBlock"] {
        align-items: center;
    }
</style>
""", unsafe_allow_html=True)

# --- TITOLO E HEADER CON BOTTONE RESET ACCANTO ---
col_title, col_reset = st.columns([0.9, 0.1]) # Diamo più spazio al titolo
with col_title:
    st.markdown("## 🚆 InfraTrack v1.7") # Version updated
    st.caption("La tua centrale di controllo per progetti infrastrutturali")

# --- GESTIONE RESET ---
if 'widget_key_counter' not in st.session_state:
    st.session_state.widget_key_counter = 0
if 'file_processed_success' not in st.session_state:
    st.session_state.file_processed_success = False # Flag per abilitare il reset

# Bottone Reset (solo icona, disabilitato finché un file non è processato)
with col_reset:
    if st.button("🔄", key="reset_button", help="Reset Completo", disabled=not st.session_state.file_processed_success):
        st.session_state.widget_key_counter += 1
        st.session_state.file_processed_success = False # Resetta il flag
        if 'uploaded_file_state' in st.session_state:
            del st.session_state['uploaded_file_state']
        st.rerun()

# --- CARICAMENTO FILE ---
st.markdown("---")
st.markdown("#### 1. Carica la Baseline di Riferimento")
uploader_key = f"file_uploader_{st.session_state.widget_key_counter}"
uploaded_file = st.file_uploader(
    "Seleziona il file .XML esportato da MS Project",
    type=["xml"],
    label_visibility="collapsed",
    key=uploader_key
)

# --- Messaggio di Successo Caricamento ---
# Mostra il messaggio qui SE un file è stato caricato E processato con successo
if st.session_state.file_processed_success and 'uploaded_file_state' in st.session_state :
     st.success('File XML analizzato con successo!')


# --- Mantenimento stato file caricato ---
if uploaded_file is not None:
    st.session_state['uploaded_file_state'] = uploaded_file
elif 'uploaded_file_state' in st.session_state:
     uploaded_file = st.session_state['uploaded_file_state']

# --- INIZIO ANALISI (Solo se un file è stato caricato) ---
if uploaded_file is not None:
    # Controlla se abbiamo già processato questo file (evita ricalcoli inutili)
    if not st.session_state.file_processed_success:
        with st.spinner('Caricamento e analisi del file in corso...'):
            try:
                uploaded_file.seek(0)
                file_content_bytes = uploaded_file.read()
                parser = etree.XMLParser(recover=True)
                tree = etree.fromstring(file_content_bytes, parser=parser)
                ns = {'msp': 'http://schemas.microsoft.com/project'}

                # --- Estrazione Dati ---
                # (Questa parte viene eseguita solo la prima volta che il file viene processato)

                # Dati Generali
                project_name = "Attività con UID 1 non trovata"
                formatted_cost = "€ 0,00"
                task_uid_1 = tree.find(".//msp:Task[msp:UID='1']", namespaces=ns)
                if task_uid_1 is not None:
                    project_name = task_uid_1.findtext('msp:Name', namespaces=ns) or "Nome non trovato"
                    total_cost_str = task_uid_1.findtext('msp:Cost', namespaces=ns) or "0"
                    total_cost_cents = float(total_cost_str)
                    total_cost_euros = total_cost_cents / 100.0
                    formatted_cost = f"€ {total_cost_euros:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                st.session_state['project_name'] = project_name # Salva in sessione
                st.session_state['formatted_cost'] = formatted_cost # Salva in sessione

                # TUP/TUF
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
                    st.session_state['df_milestones_display'] = df_milestones[["Nome Completo", "Durata", "Data Inizio", "Data Fine"]] # Salva in sessione
                else:
                    st.session_state['df_milestones_display'] = None # Salva None in sessione

                # Salvataggio dati grezzi per debug
                uploaded_file.seek(0)
                debug_content_bytes = uploaded_file.read(2000)
                try:
                    raw_text = debug_content_bytes.decode('utf-8', errors='ignore')
                    st.session_state['debug_raw_text'] = '\n'.join(raw_text.splitlines()[:50])
                except Exception as decode_err:
                     st.session_state['debug_raw_text'] = f"Errore nella decodifica per il debug: {decode_err}"

                # Imposta il flag per indicare che l'elaborazione è completa
                st.session_state.file_processed_success = True
                # Forza un rerun per mostrare il messaggio di successo e i dati
                st.rerun()

            except etree.XMLSyntaxError as e:
                 st.error(f"Errore di sintassi XML: {e}")
                 st.error("Il file XML sembra essere malformato o incompleto. Prova a riesportarlo da MS Project.")
                 # Non impostare il flag di successo
                 st.session_state.file_processed_success = False
                 try:
                     uploaded_file.seek(0); error_content_bytes = uploaded_file.read(1000)
                     raw_text = error_content_bytes.decode('utf-8', errors='ignore'); st.code('\n'.join(raw_text.splitlines()[:20]), language='xml')
                 except Exception: st.error("Impossibile leggere l'inizio del file per il debug.")
            except Exception as e:
                # Non impostare il flag di successo
                st.session_state.file_processed_success = False
                st.error(f"Errore imprevisto durante l'analisi del file XML: {e}")
                st.error("Verifica che il file sia un XML valido esportato da MS Project.")

    # --- VISUALIZZAZIONE DATI (DOPO L'ELABORAZIONE) ---
    # Questa parte viene eseguita SE file_processed_success è True
    if st.session_state.file_processed_success:
        st.markdown("---")
        st.markdown("#### 2. Analisi Preliminare")
        st.markdown("##### 📄 Informazioni Generali del Progetto")

        # Recupera i dati dalla sessione
        project_name = st.session_state.get('project_name', "N/D")
        formatted_cost = st.session_state.get('formatted_cost', "N/D")

        col1_disp, col2_disp = st.columns(2)
        with col1_disp: st.markdown(f"**Nome Appalto:** {project_name}")
        with col2_disp: st.markdown(f"**Importo Totale Lavori:** {formatted_cost}")

        st.markdown("##### 🗓️ Termini Utili Contrattuali (TUP/TUF)")

        # Recupera il DataFrame dalla sessione
        df_display = st.session_state.get('df_milestones_display')

        if df_display is not None and not df_display.empty:
            st.dataframe(df_display, use_container_width=True, hide_index=True)

            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_display.to_excel(writer, index=False, sheet_name='TerminiUtili')
            excel_data = output.getvalue()
            st.download_button(
                label="Scarica (Excel)",
                data=excel_data,
                file_name="termini_utili_TUP_TUF.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
             # Mostra l'avviso se df_display è None o vuoto
            st.warning("Nessun Termine Utile (TUP o TUF) trovato nel file.")

        # Mostra debug se presente
        debug_text = st.session_state.get('debug_raw_text')
        if debug_text:
            st.markdown("---")
            with st.expander("🔍 Dati Grezzi per Debug (prime 50 righe del file)"):
                 st.code(debug_text, language='xml')
