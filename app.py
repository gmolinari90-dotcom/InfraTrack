# --- v4.11 ---
import streamlit as st
from lxml import etree
import pandas as pd
from datetime import datetime, date, timedelta
import re
import isodate
from io import BytesIO
import math

# --- CONFIGURAZIONE DELLA PAGINA ---
st.set_page_config(page_title="InfraTrack v4.11", page_icon="🚆", layout="wide") # Version updated

# --- CSS ---
# ... (CSS Identico a v4.10) ...
st.markdown("""
<style>
    /* ... */
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
    .stCaptionContainer { font-size: 0.75rem !important; margin-top: -0.5rem; margin-bottom: 1rem;}
</style>
""", unsafe_allow_html=True)


# --- TITOLO E HEADER ---
st.markdown("## 🚆 InfraTrack v4.11") # Version updated
st.caption("La tua centrale di controllo per progetti infrastrutturali")

# --- GESTIONE RESET ---
# ... (Identico a v4.10) ...
if 'widget_key_counter' not in st.session_state: st.session_state.widget_key_counter = 0
if 'file_processed_success' not in st.session_state: st.session_state.file_processed_success = False
if st.button("🔄", key="reset_button", help="Resetta l'analisi", disabled=not st.session_state.file_processed_success):
    st.session_state.widget_key_counter += 1; st.session_state.file_processed_success = False
    keys_to_reset = ['uploaded_file_state', 'project_name', 'formatted_cost','df_milestones_display', 'debug_raw_text', 'project_start_date','project_finish_date', 'all_tasks_data', 'slider_value', 'minutes_per_day']
    for key in keys_to_reset:
        if key in st.session_state: del st.session_state[key]
    st.rerun()


# --- CARICAMENTO FILE ---
# ... (Identico a v4.10) ...
st.markdown("---"); st.markdown("#### 1. Carica la Baseline di Riferimento")
uploader_key = f"file_uploader_{st.session_state.widget_key_counter}"
uploaded_file = st.file_uploader("Seleziona il file .XML...", type=["xml"], label_visibility="collapsed", key=uploader_key)
if st.session_state.file_processed_success and 'uploaded_file_state' in st.session_state : st.success('File XML analizzato con successo!')
if uploaded_file is not None: st.session_state['uploaded_file_state'] = uploaded_file
elif 'uploaded_file_state' in st.session_state: uploaded_file = st.session_state['uploaded_file_state']

# --- INIZIO ANALISI ---
if uploaded_file is not None:
    if not st.session_state.file_processed_success:
        with st.spinner('Caricamento e analisi completa del file in corso...'):
            try:
                # ... (Logica parsing e estrazione dati generali/date progetto/minuti_giorno identica a v4.10) ...
                uploaded_file.seek(0); file_content_bytes = uploaded_file.read()
                parser = etree.XMLParser(recover=True); tree = etree.fromstring(file_content_bytes, parser=parser)
                ns = {'msp': 'http://schemas.microsoft.com/project'}
                project_name = "N/D"; formatted_cost = "€ 0,00"; project_start_date = None; project_finish_date = None; minutes_per_day = 480
                default_calendar = tree.find(".//msp:Calendar[msp:UID='1']", namespaces=ns)
                if default_calendar is not None: # ... (calcolo minutes_per_day omesso per brevità) ...
                     working_day = default_calendar.find(".//msp:WeekDay[msp:DayType='1']", namespaces=ns)
                     if working_day is not None:
                          working_minutes = 0; #... omitted calculation ...
                          if working_minutes > 0: minutes_per_day = working_minutes
                st.session_state['minutes_per_day'] = minutes_per_day
                task_uid_1 = tree.find(".//msp:Task[msp:UID='1']", namespaces=ns)
                if task_uid_1 is not None: # ... (estrazione nome/costo/date progetto omessa) ...
                    project_name = task_uid_1.findtext('msp:Name', namespaces=ns) or "N/D"; total_cost_str = task_uid_1.findtext('msp:Cost', namespaces=ns) or "0"; total_cost_euros = float(total_cost_str) / 100.0
                    formatted_cost = f"€ {total_cost_euros:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    start_str = task_uid_1.findtext('msp:Start', namespaces=ns); finish_str = task_uid_1.findtext('msp:Finish', namespaces=ns)
                    if start_str: project_start_date = datetime.fromisoformat(start_str).date()
                    if finish_str: project_finish_date = datetime.fromisoformat(finish_str).date()
                if not project_start_date: project_start_date = date.today(); #... (fallback date) ...
                if not project_finish_date: project_finish_date = project_start_date + timedelta(days=365)
                if project_start_date > project_finish_date: project_finish_date = project_start_date + timedelta(days=1)
                st.session_state['project_name'] = project_name; st.session_state['formatted_cost'] = formatted_cost
                st.session_state['project_start_date'] = project_start_date; st.session_state['project_finish_date'] = project_finish_date

                # --- Estrazione Dati Attività e TUP/TUF ---
                potential_milestones = {}; all_tasks = tree.findall('.//msp:Task', namespaces=ns)
                tup_tuf_pattern = re.compile(r'(?i)(TUP|TUF)\s*\d*'); all_tasks_data_list = []
                def format_duration_from_xml(duration_str):
                     # ... (funzione durata identica a v4.10) ...
                     mpd = st.session_state.get('minutes_per_day', 480); #...
                     if not duration_str or mpd <= 0: return "0g"
                     try: #...
                        work_days = total_hours / (mpd / 60.0); return f"{round(work_days)}g"
                     except Exception: return "N/D"

                for task in all_tasks:
                    uid = task.findtext('msp:UID', namespaces=ns); name = task.findtext('msp:Name', namespaces=ns) or ""; #...
                    start_date = datetime.fromisoformat(start_str).date() if start_str else None; finish_date = datetime.fromisoformat(finish_str).date() if finish_str else None
                    duration_formatted = format_duration_from_xml(duration_str)
                    cost_euros = float(cost_str) / 100.0 if cost_str else 0.0
                    is_milestone = is_milestone_text == '1' or is_milestone_text == 'true'
                    wbs = task.findtext('msp:WBS', namespaces=ns) or ""
                    total_slack_minutes_str = task.findtext('msp:TotalSlack', namespaces=ns) or "0"

                    # --- CORREZIONE CALCOLO SLACK try/except ---
                    total_slack_days = 0
                    if total_slack_minutes_str:
                         try: # Questo è il blocco try
                              slack_minutes = float(total_slack_minutes_str)
                              mpd = st.session_state.get('minutes_per_day', 480)
                              if mpd > 0:
                                   total_slack_days = math.ceil(slack_minutes / mpd)
                         except ValueError: # Blocco except CORRETTAMENTE INDENTATO
                              total_slack_days = 0 # Se non è un numero, slack è 0
                    # --- FINE CORREZIONE ---

                    if uid != '0':
                         all_tasks_data_list.append({"UID": uid, "Name": name, "Start": start_date, "Finish": finish_date, "Duration": duration_formatted, "Cost": cost_euros, "Milestone": is_milestone, "WBS": wbs, "TotalSlackDays": total_slack_days})

                    # Logica TUP/TUF (identica a v4.10)
                    match = tup_tuf_pattern.search(name)
                    if match:
                         # ... (omessa per brevità) ...
                         current_task_data = {...} # Omissis data
                         existing_duration_seconds = potential_milestones.get(tup_tuf_key, {}).get("DurataSecondi", -1)
                         if tup_tuf_key not in potential_milestones: potential_milestones[tup_tuf_key] = current_task_data
                         elif not is_pure_milestone_duration: #... (omissis logica selezione)

                # Salvataggio dati TUP/TUF e All Tasks (Identico a v4.10)
                final_milestones_data = [] # ... (omissis)
                for key in potential_milestones: final_milestones_data.append({...})
                if final_milestones_data: # ... (omissis creazione df e salvataggio in sessione) ...
                    st.session_state['df_milestones_display'] = df_milestones.drop(columns=['DataInizioObj'])
                else: st.session_state['df_milestones_display'] = None
                st.session_state['all_tasks_data'] = pd.DataFrame(all_tasks_data_list)
                uploaded_file.seek(0); debug_content_bytes = uploaded_file.read(2000); # ... (omissis debug text)
                try: st.session_state['debug_raw_text'] = '\n'.join(debug_content_bytes.decode('utf-8', errors='ignore').splitlines()[:50])
                except Exception as decode_err: st.session_state['debug_raw_text'] = f"Errore decodifica debug: {decode_err}"
                st.session_state.file_processed_success = True
                st.rerun()

            # --- Gestione Errori ---
            except etree.XMLSyntaxError as e: st.error(f"Errore Sintassi XML: {e}"); st.error("File malformato?"); st.session_state.file_processed_success = False; #...
            except KeyError as ke: st.error(f"Errore interno: Chiave mancante {ke}"); st.error("Problema estrazione TUP/TUF."); st.session_state.file_processed_success = False;
            except Exception as e: st.error(f"Errore Analisi durante elaborazione iniziale: {e}"); st.error("Verifica file XML."); st.session_state.file_processed_success = False; #...

    # --- VISUALIZZAZIONE DATI E ANALISI AVANZATA ---
    if st.session_state.file_processed_success:
        # --- Sezione 2: Analisi Preliminare (Identica a v4.10) ---
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
            excel_data = output.getvalue(); st.download_button(label="Scarica (Excel)", data=excel_data, file_name="...", mime="...")
        else: st.warning("Nessun Termine Utile (TUP o TUF) trovato nel file.")


        # --- Sezione 3: Analisi Avanzata (Identica a v4.10) ---
        st.markdown("---"); st.markdown("#### 3. Analisi Avanzata")
        # ... (Logica date default e date_input identica) ...
        default_start = st.session_state.get('project_start_date', date.today()); default_finish = st.session_state.get('project_finish_date', date.today() + timedelta(days=365))
        if not default_start: default_start = date.today()
        if not default_finish: default_finish = default_start + timedelta(days=365)
        if default_start > default_finish: default_finish = default_start + timedelta(days=1)
        st.markdown("##### 📅 Seleziona Periodo di Riferimento"); st.caption(f"Default: {default_start.strftime('%d/%m/%Y')} - {default_finish.strftime('%d/%m/%Y')}.")
        col_date1, col_date2 = st.columns(2)
        with col_date1: selected_start_date = st.date_input("Data Inizio", value=default_start, min_value=default_start, max_value=default_finish + timedelta(days=5*365), format="DD/MM/YYYY", key="start_date_selector")
        with col_date2:
            min_end_date = selected_start_date; actual_default_finish = max(default_finish, min_end_date)
            reasonable_max_date = actual_default_finish + timedelta(days=10*365)
            selected_finish_date = st.date_input("Data Fine", value=actual_default_finish, min_value=min_end_date, max_value=reasonable_max_date, format="DD/MM/YYYY", key="finish_date_selector")
        st.markdown("---"); st.markdown("##### 📊 Analisi Dettagliate")
        all_tasks_df = st.session_state.get('all_tasks_data')
        if all_tasks_df is not None and not all_tasks_df.empty:
            try:
                # ... (Logica filtro data e analisi criticità identica a v4.10) ...
                tasks_to_filter = st.session_state['all_tasks_data'].copy()
                tasks_to_filter['Start'] = pd.to_datetime(tasks_to_filter['Start'], errors='coerce').dt.date
                tasks_to_filter['Finish'] = pd.to_datetime(tasks_to_filter['Finish'], errors='coerce').dt.date
                tasks_to_filter_cleaned = tasks_to_filter.dropna(subset=['Start', 'Finish'])
                filtered_tasks_df = tasks_to_filter_cleaned[ (tasks_to_filter_cleaned['Start'] <= selected_finish_date) & (tasks_to_filter_cleaned['Finish'] >= selected_start_date) ].copy()
                st.markdown("###### Analisi Percorso Critico / Sub-critico")
                if not filtered_tasks_df.empty:
                    max_slack = int(filtered_tasks_df['TotalSlackDays'].max()); max_slack = max(0, max_slack); slider_max = min(max_slack, 365)
                    selected_slack = st.slider("Seleziona Margine Flessibilità Totale (giorni)", min_value=0, max_value=slider_max, value=st.session_state.get('slider_value', 0), step=1, key="slack_slider", help="...")
                    st.session_state['slider_value'] = selected_slack
                    if st.button("📈 Analizza Criticità", key="analyze_critical_path"):
                        # ... (Debug prints omessi) ...
                        critical_subcritical_tasks = filtered_tasks_df[ filtered_tasks_df['TotalSlackDays'] <= selected_slack ]
                        if not critical_subcritical_tasks.empty:
                            st.write(f"Attività critiche/sub-critiche (Slack <= {selected_slack} giorni):")
                            display_critical_df = critical_subcritical_tasks[["WBS", "Name", "Duration", "Start", "Finish", "TotalSlackDays"]].rename(columns={"Name": "Nome Attività", "Duration": "Durata", "Start": "Inizio", "Finish": "Fine", "TotalSlackDays": "Slack (g)"})
                            display_critical_df['Inizio'] = pd.to_datetime(display_critical_df['Inizio']).dt.strftime('%d/%m/%Y'); display_critical_df['Fine'] = pd.to_datetime(display_critical_df['Fine']).dt.strftime('%d/%m/%Y')
                            st.dataframe(display_critical_df, use_container_width=True, hide_index=True)
                            output_crit = BytesIO() # ... (download excel)
                            with pd.ExcelWriter(output_crit, engine='openpyxl') as writer: display_critical_df.to_excel(writer, index=False, sheet_name='PercorsoCritico')
                            excel_data_crit = output_crit.getvalue(); st.download_button(label="Scarica Analisi Criticità (Excel)", data=excel_data_crit, file_name=f"...", mime="...", key="download_criticita")
                        else: st.warning(f"Nessuna attività trovata con Slack <= {selected_slack} giorni nel periodo.")
                else: st.warning("Nessuna attività nel periodo per analisi criticità.")
            except Exception as analysis_error: st.error(f"Errore analisi avanzata: {analysis_error}")
        else: st.error("Errore: Dati attività non trovati.")
        debug_text = st.session_state.get('debug_raw_text'); # ... (debug section)
        if debug_text: st.markdown("---"); # ...
