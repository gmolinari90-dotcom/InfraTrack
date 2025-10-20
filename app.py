import streamlit as st
from lxml import etree
import pandas as pd
from datetime import datetime, date, timedelta # Aggiunto 'date'
import re
import isodate
from io import BytesIO

# --- CONFIGURAZIONE DELLA PAGINA ---
st.set_page_config(page_title="InfraTrack v3.1", page_icon="🚆", layout="wide") # Version updated

# --- CSS ---
# Stili CSS identici a v2.15
st.markdown("""
<style>
    /* ... (CSS omesso per brevità) ... */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, .stApp p, .stApp .stDataFrame, .stApp .stButton>button { font-size: 0.85rem !important; }
    .stApp h2 { font-size: 1.5rem !important; }
    .stApp .stMarkdown h4 { font-size: 1.1rem !important; margin-bottom: 0.5rem; margin-top: 1rem; }
    .stApp .stMarkdown h5 { font-size: 0.90rem !important; margin-bottom: 0.5rem; margin-top: 0.8rem; }
    button[data-testid="stButton"][kind="primary"][key="reset_button"] { padding: 0.2rem 0.5rem !important; line-height: 1.2 !important; font-size: 1.1rem !important; border-radius: 0.25rem !important; }
    button[data-testid="stButton"][kind="primary"][key="reset_button"]:disabled { cursor: not-allowed; opacity: 0.5; }
    .stApp { padding-top: 2rem; }
    .stDataFrame td { text-align: center !important; }
    div[data-testid="stDateInput"] label { font-size: 0.85rem !important; }
    div[data-testid="stDateInput"] input { font-size: 0.85rem !important; padding: 0.3rem 0.5rem !important;}
</style>
""", unsafe_allow_html=True)

# --- TITOLO E HEADER ---
st.markdown("## 🚆 InfraTrack v3.1") # Version updated
st.caption("La tua centrale di controllo per progetti infrastrutturali")

# --- GESTIONE RESET ---
if 'widget_key_counter' not in st.session_state: st.session_state.widget_key_counter = 0
if 'file_processed_success' not in st.session_state: st.session_state.file_processed_success = False
if st.button("🔄", key="reset_button", help="Resetta l'analisi", disabled=not st.session_state.file_processed_success):
    st.session_state.widget_key_counter += 1
    st.session_state.file_processed_success = False
    keys_to_reset = ['uploaded_file_state', 'project_name', 'formatted_cost',
                     'df_milestones_display', 'debug_raw_text', 'project_start_date',
                     'project_finish_date', 'all_tasks_data']
    for key in keys_to_reset:
        if key in st.session_state: del st.session_state[key]
    st.rerun()

# --- CARICAMENTO FILE ---
st.markdown("---")
st.markdown("#### 1. Carica la Baseline di Riferimento")
uploader_key = f"file_uploader_{st.session_state.widget_key_counter}"
uploaded_file = st.file_uploader(
    "Seleziona il file .XML esportato da MS Project", type=["xml"],
    label_visibility="collapsed", key=uploader_key
)

if st.session_state.file_processed_success and 'uploaded_file_state' in st.session_state :
     st.success('File XML analizzato con successo!')

if uploaded_file is not None: st.session_state['uploaded_file_state'] = uploaded_file
elif 'uploaded_file_state' in st.session_state: uploaded_file = st.session_state['uploaded_file_state']


# --- INIZIO ANALISI ---
if uploaded_file is not None:
    # --- Elaborazione Dati (solo se non già fatta) ---
    if not st.session_state.file_processed_success:
        with st.spinner('Caricamento e analisi completa del file in corso...'):
            try:
                uploaded_file.seek(0); file_content_bytes = uploaded_file.read()
                parser = etree.XMLParser(recover=True); tree = etree.fromstring(file_content_bytes, parser=parser)
                ns = {'msp': 'http://schemas.microsoft.com/project'}

                # -- Estrazione Info Generali e Date Progetto --
                project_name = "N/D"; formatted_cost = "€ 0,00"
                project_start_date = None; project_finish_date = None
                task_uid_1 = tree.find(".//msp:Task[msp:UID='1']", namespaces=ns)
                if task_uid_1 is not None:
                    project_name = task_uid_1.findtext('msp:Name', namespaces=ns) or "N/D"
                    total_cost_str = task_uid_1.findtext('msp:Cost', namespaces=ns) or "0"
                    total_cost_euros = float(total_cost_str) / 100.0
                    formatted_cost = f"€ {total_cost_euros:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    start_str = task_uid_1.findtext('msp:Start', namespaces=ns)
                    finish_str = task_uid_1.findtext('msp:Finish', namespaces=ns)
                    if start_str: project_start_date = datetime.fromisoformat(start_str).date()
                    if finish_str: project_finish_date = datetime.fromisoformat(finish_str).date()
                # Gestione date fallback se non trovate
                if not project_start_date: project_start_date = date.today()
                if not project_finish_date: project_finish_date = project_start_date + timedelta(days=365)
                # Assicura start <= finish
                if project_start_date > project_finish_date: project_finish_date = project_start_date + timedelta(days=1)


                st.session_state['project_name'] = project_name
                st.session_state['formatted_cost'] = formatted_cost
                st.session_state['project_start_date'] = project_start_date # Salvataggio date progetto
                st.session_state['project_finish_date'] = project_finish_date

                # -- Estrazione Dati di Tutte le Attività e TUP/TUF --
                potential_milestones = {}
                all_tasks = tree.findall('.//msp:Task', namespaces=ns)
                tup_tuf_pattern = re.compile(r'(?i)(TUP|TUF)\s*\d*')
                all_tasks_data_list = [] # Lista temporanea per i dati di tutte le attività

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
                    uid = task.findtext('msp:UID', namespaces=ns)
                    # Saltiamo l'attività 0 (Project Summary) per l'analisi dettagliata,
                    # ma la usiamo per TUP/TUF se necessario
                    # if uid == '0': continue # Rimosso per includere eventualmente TUP/TUF su riga 0

                    name = task.findtext('msp:Name', namespaces=ns) or ""
                    start_str = task.findtext('msp:Start', namespaces=ns)
                    finish_str = task.findtext('msp:Finish', namespaces=ns)
                    duration_str = task.findtext('msp:Duration', namespaces=ns)
                    cost_str = task.findtext('msp:Cost', namespaces=ns) or "0"
                    is_milestone_text = (task.findtext('msp:Milestone', namespaces=ns) or '0').lower()
                    is_milestone = is_milestone_text == '1' or is_milestone_text == 'true'
                    wbs = task.findtext('msp:WBS', namespaces=ns) or ""
                    total_slack_str = task.findtext('msp:TotalSlack', namespaces=ns) or "0"

                    start_date = datetime.fromisoformat(start_str).date() if start_str else None
                    finish_date = datetime.fromisoformat(finish_str).date() if finish_str else None
                    cost_euros = float(cost_str) / 100.0 if cost_str else 0.0
                    duration_formatted = format_duration_from_xml(duration_str)
                    total_slack_days = round(float(total_slack_str) / (8 * 60)) if total_slack_str else 0

                    # Aggiungiamo i dati alla lista per il DataFrame generale
                    if uid != '0': # Escludiamo UID 0 dal DF principale se non necessario per analisi
                         all_tasks_data_list.append({
                             "UID": uid, "Name": name, "Start": start_date, "Finish": finish_date,
                             "Duration": duration_formatted, "Cost": cost_euros, "Milestone": is_milestone,
                             "WBS": wbs, "TotalSlackDays": total_slack_days
                         })

                    # Controllo TUP/TUF (include anche UID 0 se è TUP/TUF)
                    match = tup_tuf_pattern.search(name)
                    # Modifica: Non richiediamo più che sia una milestone per essere TUP/TUF
                    # if is_milestone and match:
                    if match: # Cerchiamo TUP/TUF indipendentemente da Milestone flag
                        tup_tuf_key = match.group(0).upper().strip()
                        try:
                            if duration_str and duration_str.startswith('T'): duration_str = 'P' + duration_str
                            duration_obj = isodate.parse_duration(duration_str) if duration_str and duration_str.startswith('P') else timedelta()
                            duration_seconds = duration_obj.total_seconds()
                        except Exception: duration_seconds = 0

                        # Se la durata è 0 secondi, la consideriamo una milestone pura per la logica di selezione
                        is_pure_milestone_duration = (duration_seconds == 0)

                        start_date_formatted = start_date.strftime("%d/%m/%Y") if start_date else "N/D"
                        finish_date_formatted = finish_date.strftime("%d/%m/%Y") if finish_date else "N/D"
                        current_task_data = {
                            "Nome Completo": name, "Data Inizio": start_date_formatted, "Data Fine": finish_date_formatted,
                            "Durata": duration_formatted, "DurataSecondi": duration_seconds, "DataInizioObj": start_date
                        }

                        # Logica di selezione: Prendi quella con durata > 0. Se ce ne sono multiple > 0, prendi la più lunga.
                        # Se ci sono solo milestone pure (durata 0), prendi la prima trovata.
                        if tup_tuf_key not in potential_milestones:
                             # Primo TUP/TUF trovato con questo nome
                             potential_milestones[tup_tuf_key] = current_task_data
                        elif not is_pure_milestone_duration:
                             # Trovato un TUP/TUF con durata > 0
                             if potential_milestones[tup_tuf_key]["DurataSecondi"] == 0:
                                 # Se quello salvato era una milestone pura, sostituiscilo
                                 potential_milestones[tup_tuf_key] = current_task_data
                             elif duration_seconds > potential_milestones[tup_tuf_key]["DurataSecondi"]:
                                 # Se quello salvato aveva durata > 0 ma inferiore, sostituiscilo
                                 potential_milestones[tup_tuf_key] = current_task_data
                        # else: # Se quello attuale è una milestone pura e ne abbiamo già una salvata (pura o no), non fare nulla


                # -- Salvataggio Dati in Session State --
                # TUP/TUF
                final_milestones_data = []
                for key in potential_milestones:
                     data = potential_milestones[key]
                     final_milestones_data.append({"Nome Completo": data["Nome Completo"], "Data Inizio": data["Data Inizio"], "Data Fine": data["Data Fine"],
                                                   "Durata": data["Durata"], "DataInizioObj": data["DataInizioObj"]})
                if final_milestones_data:
                    df_milestones = pd.DataFrame(final_milestones_data).sort_values(by="DataInizioObj").reset_index(drop=True)
                    st.session_state['df_milestones_display'] = df_milestones[["Nome Completo", "Durata", "Data Inizio", "Data Fine"]]
                else: st.session_state['df_milestones_display'] = None

                # Tutte le attività
                st.session_state['all_tasks_data'] = pd.DataFrame(all_tasks_data_list)

                # Debug
                uploaded_file.seek(0); debug_content_bytes = uploaded_file.read(2000)
                try: st.session_state['debug_raw_text'] = '\n'.join(debug_content_bytes.decode('utf-8', errors='ignore').splitlines()[:50])
                except Exception as decode_err: st.session_state['debug_raw_text'] = f"Errore decodifica debug: {decode_err}"

                st.session_state.file_processed_success = True
                st.rerun() # Forza rerun per mostrare tutto

            except etree.XMLSyntaxError as e: st.error(f"Errore Sintassi XML: {e}"); st.error("File malformato?"); st.session_state.file_processed_success = False; #...
            except Exception as e: st.error(f"Errore Analisi: {e}"); st.error("Verifica file XML."); st.session_state.file_processed_success = False; #...

    # --- VISUALIZZAZIONE DATI E ANALISI AVANZATA ---
    if st.session_state.file_processed_success:
        # --- Sezione 2: Analisi Preliminare (Visualizza dati da session state) ---
        st.markdown("---")
        st.markdown("#### 2. Analisi Preliminare")
        st.markdown("##### 📄 Informazioni Generali dell'Appalto")
        project_name = st.session_state.get('project_name', "N/D")
        formatted_cost = st.session_state.get('formatted_cost', "N/D")
        col1_disp, col2_disp = st.columns(2)
        with col1_disp: st.markdown(f"**Nome:** {project_name}")
        with col2_disp: st.markdown(f"**Importo Totale Lavori:** {formatted_cost}")

        st.markdown("##### 🗓️ Termini Utili Contrattuali (TUP/TUF)")
        df_display = st.session_state.get('df_milestones_display')
        if df_display is not None and not df_display.empty:
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            output = BytesIO(); #... (download excel)
            with pd.ExcelWriter(output, engine='openpyxl') as writer: df_display.to_excel(writer, index=False, sheet_name='TerminiUtili')
            excel_data = output.getvalue()
            st.download_button(label="Scarica (Excel)", data=excel_data, file_name="termini_utili_TUP_TUF.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else: st.warning("Nessun Termine Utile (TUP o TUF) trovato nel file.")

        # --- Sezione 3: Analisi Avanzata ---
        st.markdown("---")
        st.markdown("#### 3. Analisi Avanzata")

        # Recupera le date di default CORRETTE dalla sessione
        default_start = st.session_state.get('project_start_date', date.today())
        default_finish = st.session_state.get('project_finish_date', date.today() + timedelta(days=365))
        # Gestisci fallback e assicurati start <= finish
        if not default_start: default_start = date.today()
        if not default_finish: default_finish = default_start + timedelta(days=365)
        if default_start > default_finish: default_finish = default_start + timedelta(days=1)

        st.markdown("##### 📅 Seleziona Periodo di Riferimento")
        col_date1, col_date2 = st.columns(2)
        with col_date1:
            selected_start_date = st.date_input(
                "Data Inizio Analisi",
                value=default_start, # Usa le date salvate
                min_value=default_start,
                max_value=default_finish,
                format="DD/MM/YYYY"
            )
        with col_date2:
            min_end_date = selected_start_date # Fine può essere uguale a inizio
            actual_default_finish = max(default_finish, min_end_date)
            # Calcoliamo una max date ragionevole (es. 10 anni dopo la fine progetto)
            reasonable_max_date = actual_default_finish + timedelta(days=10*365)

            selected_finish_date = st.date_input(
                "Data Fine Analisi",
                value=actual_default_finish, # Usa le date salvate
                min_value=min_end_date,
                max_value=reasonable_max_date, # Limite max flessibile
                format="DD/MM/YYYY"
            )

        st.caption(f"Periodo selezionato: dal {selected_start_date.strftime('%d/%m/%Y')} al {selected_finish_date.strftime('%d/%m/%Y')}")

        # --- Qui verranno inserite le prossime analisi ---
        st.markdown("---")
        st.markdown("##### 📊 Analisi Dettagliate (Prossimi Passi)")
        st.info("Le funzionalità di analisi (Percorso Critico, Curva S, ecc.) verranno implementate qui, basandosi sul periodo selezionato.")


        # Debug (invariato)
        debug_text = st.session_state.get('debug_raw_text')
        if debug_text:
            st.markdown("---")
            with st.expander("🔍 Dati Grezzi per Debug (prime 50 righe del file)"): st.code(debug_text, language='xml')
