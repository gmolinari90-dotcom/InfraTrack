# --- v3.8 ---
import streamlit as st
from lxml import etree
import pandas as pd
from datetime import datetime, date, timedelta
import re
import isodate
from io import BytesIO

# --- CONFIGURAZIONE DELLA PAGINA ---
st.set_page_config(page_title="InfraTrack v3.8", page_icon="🚆", layout="wide") # Version updated

# --- CSS ---
# ... (CSS Identico a v3.7) ...
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
st.markdown("## 🚆 InfraTrack v3.8") # Version updated
st.caption("La tua centrale di controllo per progetti infrastrutturali")

# --- GESTIONE RESET ---
# ... (Identico a v3.7) ...
if 'widget_key_counter' not in st.session_state: st.session_state.widget_key_counter = 0
if 'file_processed_success' not in st.session_state: st.session_state.file_processed_success = False
if st.button("🔄", key="reset_button", help="Resetta l'analisi", disabled=not st.session_state.file_processed_success):
    st.session_state.widget_key_counter += 1; st.session_state.file_processed_success = False
    keys_to_reset = ['uploaded_file_state', 'project_name', 'formatted_cost','df_milestones_display', 'debug_raw_text', 'project_start_date','project_finish_date', 'all_tasks_data', 'slider_value']
    for key in keys_to_reset:
        if key in st.session_state: del st.session_state[key]
    st.rerun()


# --- CARICAMENTO FILE ---
# ... (Identico a v3.7) ...
st.markdown("---"); st.markdown("#### 1. Carica la Baseline di Riferimento")
uploader_key = f"file_uploader_{st.session_state.widget_key_counter}"
uploaded_file = st.file_uploader("Seleziona il file .XML...", type=["xml"], label_visibility="collapsed", key=uploader_key)
if st.session_state.file_processed_success and 'uploaded_file_state' in st.session_state : st.success('File XML analizzato con successo!')
if uploaded_file is not None: st.session_state['uploaded_file_state'] = uploaded_file
elif 'uploaded_file_state' in st.session_state: uploaded_file = st.session_state['uploaded_file_state']

# --- INIZIO ANALISI ---
if uploaded_file is not None:
    # --- Elaborazione Dati (solo se non già fatta) ---
    if not st.session_state.file_processed_success:
        with st.spinner('Caricamento e analisi completa del file in corso...'):
            try:
                # ... (Logica parsing e estrazione dati completa identica a v3.7) ...
                uploaded_file.seek(0); file_content_bytes = uploaded_file.read()
                parser = etree.XMLParser(recover=True); tree = etree.fromstring(file_content_bytes, parser=parser)
                ns = {'msp': 'http://schemas.microsoft.com/project'}
                project_name = "N/D"; formatted_cost = "€ 0,00"; project_start_date = None; project_finish_date = None
                task_uid_1 = tree.find(".//msp:Task[msp:UID='1']", namespaces=ns)
                if task_uid_1 is not None:
                    project_name = task_uid_1.findtext('msp:Name', namespaces=ns) or "N/D"
                    total_cost_str = task_uid_1.findtext('msp:Cost', namespaces=ns) or "0"; total_cost_euros = float(total_cost_str) / 100.0
                    formatted_cost = f"€ {total_cost_euros:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    start_str = task_uid_1.findtext('msp:Start', namespaces=ns); finish_str = task_uid_1.findtext('msp:Finish', namespaces=ns)
                    if start_str: project_start_date = datetime.fromisoformat(start_str).date()
                    if finish_str: project_finish_date = datetime.fromisoformat(finish_str).date()
                if not project_start_date: project_start_date = date.today()
                if not project_finish_date: project_finish_date = project_start_date + timedelta(days=365)
                if project_start_date > project_finish_date: project_finish_date = project_start_date + timedelta(days=1)
                st.session_state['project_name'] = project_name; st.session_state['formatted_cost'] = formatted_cost
                st.session_state['project_start_date'] = project_start_date; st.session_state['project_finish_date'] = project_finish_date
                potential_milestones = {}; all_tasks = tree.findall('.//msp:Task', namespaces=ns)
                tup_tuf_pattern = re.compile(r'(?i)(TUP|TUF)\s*\d*'); all_tasks_data_list = []
                def format_duration_from_xml(duration_str, work_hours_per_day=8.0):
                     if not duration_str or work_hours_per_day <= 0: return "0g"
                     try:
                         if duration_str.startswith('T'): duration_str = 'P' + duration_str
                         elif not duration_str.startswith('P'): return "N/D"
                         duration = isodate.parse_duration(duration_str); total_hours = duration.total_seconds() / 3600
                         if total_hours == 0: return "0g"
                         work_days = total_hours / work_hours_per_day; return f"{round(work_days)}g"
                     except Exception: return "N/D"
                for task in all_tasks:
                    uid = task.findtext('msp:UID', namespaces=ns); name = task.findtext('msp:Name', namespaces=ns) or ""
                    start_str = task.findtext('msp:Start', namespaces=ns); finish_str = task.findtext('msp:Finish', namespaces=ns)
                    duration_str = task.findtext('msp:Duration', namespaces=ns); cost_str = task.findtext('msp:Cost', namespaces=ns) or "0"
                    is_milestone_text = (task.findtext('msp:Milestone', namespaces=ns) or '0').lower(); is_milestone = is_milestone_text == '1' or is_milestone_text == 'true'
                    wbs = task.findtext('msp:WBS', namespaces=ns) or ""; total_slack_str = task.findtext('msp:TotalSlack', namespaces=ns) or "0"
                    start_date = datetime.fromisoformat(start_str).date() if start_str else None; finish_date = datetime.fromisoformat(finish_str).date() if finish_str else None
                    cost_euros = float(cost_str) / 100.0 if cost_str else 0.0; duration_formatted = format_duration_from_xml(duration_str)
                    # Converti TotalSlack in giorni (controlla se il valore è presente)
                    total_slack_days = 0
                    if total_slack_str and total_slack_str != "0":
                         try:
                              # La durata in XML è tipo PT108000S, usiamo isodate
                              slack_duration = isodate.parse_duration('PT' + total_slack_str + 'S') # Assume formato secondi
                              total_slack_days = round(slack_duration.total_seconds() / (8 * 3600)) # Converti secondi in giorni lavorativi
                         except ValueError: # Gestisce caso in cui TotalSlack non sia un numero/durata valida
                              # Prova a interpretarlo come minuti (vecchio metodo)
                              try:
                                   total_slack_days = round(float(total_slack_str) / (8 * 60))
                              except ValueError:
                                   total_slack_days = 0 # Default a 0 se non interpretabile


                    if uid != '0':
                         all_tasks_data_list.append({"UID": uid, "Name": name, "Start": start_date, "Finish": finish_date, "Duration": duration_formatted, "Cost": cost_euros, "Milestone": is_milestone, "WBS": wbs, "TotalSlackDays": total_slack_days})
                    match = tup_tuf_pattern.search(name)
                    if match:
                        tup_tuf_key = match.group(0).upper().strip(); duration_str_tup = task.findtext('msp:Duration', namespaces=ns)
                        try:
                            _ds = duration_str_tup
                            if _ds and _ds.startswith('T'): _ds = 'P' + _ds
                            duration_obj = isodate.parse_duration(_ds) if _ds and _ds.startswith('P') else timedelta(); duration_seconds = duration_obj.total_seconds()
                        except Exception: duration_seconds = 0
                        is_pure_milestone_duration = (duration_seconds == 0)
                        start_date_formatted = start_date.strftime("%d/%m/%Y") if start_date else "N/D"; finish_date_formatted = finish_date.strftime("%d/%m/%Y") if finish_date else "N/D"
                        current_task_data = {"Nome Completo": name, "Data Inizio": start_date_formatted, "Data Fine": finish_date_formatted, "Durata": duration_formatted, "DurataSecondi": duration_seconds, "DataInizioObj": start_date}
                        if tup_tuf_key not in potential_milestones: potential_milestones[tup_tuf_key] = current_task_data
                        elif not is_pure_milestone_duration:
                             if potential_milestones[tup_tuf_key]["DurataSecondi"] == 0: potential_milestones[tup_tuf_key] = current_task_data
                             elif duration_seconds > potential_milestones[tup_tuf_key]["DurataSecondi"]: potential_milestones[tup_tuf_key] = current_task_data
                final_milestones_data = []
                for key in potential_milestones: final_milestones_data.append({...}) # Omissis
                if final_milestones_data:
                    df_milestones = pd.DataFrame(final_milestones_data).sort_values(by="DataInizioObj").reset_index(drop=True)
                    st.session_state['df_milestones_display'] = df_milestones[["Nome Completo", "Durata", "Data Inizio", "Data Fine"]]
                else: st.session_state['df_milestones_display'] = None
                st.session_state['all_tasks_data'] = pd.DataFrame(all_tasks_data_list)
                uploaded_file.seek(0); debug_content_bytes = uploaded_file.read(2000); # ... (omissis debug text)
                try: st.session_state['debug_raw_text'] = '\n'.join(debug_content_bytes.decode('utf-8', errors='ignore').splitlines()[:50])
                except Exception as decode_err: st.session_state['debug_raw_text'] = f"Errore decodifica debug: {decode_err}"
                st.session_state.file_processed_success = True
                st.rerun()

            except etree.XMLSyntaxError as e: st.error(f"Errore Sintassi XML: {e}"); st.error("File malformato?"); st.session_state.file_processed_success = False; #...
            except Exception as e: st.error(f"Errore Analisi: {e}"); st.error("Verifica file XML."); st.session_state.file_processed_success = False; #...

    # --- VISUALIZZAZIONE DATI E ANALISI AVANZATA ---
    if st.session_state.file_processed_success:
        # --- Sezione 2: Analisi Preliminare (Identica a v3.7) ---
        st.markdown("---")
        st.markdown("#### 2. Analisi Preliminare")
        st.markdown("##### 📄 Informazioni Generali dell'Appalto")
        # ... (Visualizzazione dati generali e TUP/TUF + download identica a v3.7) ...
        project_name = st.session_state.get('project_name', "N/D"); formatted_cost = st.session_state.get('formatted_cost', "N/D")
        col1_disp, col2_disp = st.columns(2); with col1_disp: st.markdown(f"**Nome:** {project_name}"); with col2_disp: st.markdown(f"**Importo Totale Lavori:** {formatted_cost}")
        st.markdown("##### 🗓️ Termini Utili Contrattuali (TUP/TUF)")
        df_display = st.session_state.get('df_milestones_display')
        if df_display is not None and not df_display.empty:
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            output = BytesIO(); #... (download excel)
            with pd.ExcelWriter(output, engine='openpyxl') as writer: df_display.to_excel(writer, index=False, sheet_name='TerminiUtili')
            excel_data = output.getvalue(); st.download_button(label="Scarica (Excel)", data=excel_data, file_name="...", mime="...")
        else: st.warning("Nessun Termine Utile (TUP o TUF) trovato nel file.")


        # --- Sezione 3: Analisi Avanzata ---
        st.markdown("---")
        st.markdown("#### 3. Analisi Avanzata")
        default_start = st.session_state.get('project_start_date', date.today())
        default_finish = st.session_state.get('project_finish_date', date.today() + timedelta(days=365))
        if not default_start: default_start = date.today()
        if not default_finish: default_finish = default_start + timedelta(days=365)
        if default_start > default_finish: default_finish = default_start + timedelta(days=1)

        st.markdown("##### 📅 Seleziona Periodo di Riferimento")
        st.caption(f"Default: {default_start.strftime('%d/%m/%Y')} - {default_finish.strftime('%d/%m/%Y')}.")
        col_date1, col_date2 = st.columns(2)
        with col_date1:
            # Leggiamo SEMPRE il valore corrente del widget
            selected_start_date = st.date_input("Data Inizio", value=default_start, min_value=default_start, max_value=default_finish + timedelta(days=5*365), format="DD/MM/YYYY", key="start_date_selector")
        with col_date2:
            min_end_date = selected_start_date; actual_default_finish = max(default_finish, min_end_date)
            reasonable_max_date = actual_default_finish + timedelta(days=10*365)
            # Leggiamo SEMPRE il valore corrente del widget
            selected_finish_date = st.date_input("Data Fine", value=actual_default_finish, min_value=min_end_date, max_value=reasonable_max_date, format="DD/MM/YYYY", key="finish_date_selector")

        # --- Analisi Dettagliate ---
        st.markdown("---")
        st.markdown("##### 📊 Analisi Dettagliate")
        all_tasks_df = st.session_state.get('all_tasks_data')

        if all_tasks_df is not None and not all_tasks_df.empty:
            try:
                tasks_to_filter = st.session_state['all_tasks_data'].copy()
                # Assicurati che le colonne Start/Finish siano oggetti date
                tasks_to_filter['Start'] = pd.to_datetime(tasks_to_filter['Start'], errors='coerce').dt.date
                tasks_to_filter['Finish'] = pd.to_datetime(tasks_to_filter['Finish'], errors='coerce').dt.date
                tasks_to_filter_cleaned = tasks_to_filter.dropna(subset=['Start', 'Finish'])

                # Applica il filtro per data AD OGNI ESECUZIONE
                filtered_tasks_df = tasks_to_filter_cleaned[
                    (tasks_to_filter_cleaned['Start'] <= selected_finish_date) &
                    (tasks_to_filter_cleaned['Finish'] >= selected_start_date)
                ].copy()

                st.markdown("###### Analisi Percorso Critico / Sub-critico")
                if not filtered_tasks_df.empty:
                    max_slack = int(filtered_tasks_df['TotalSlackDays'].max()); max_slack = max(0, max_slack); slider_max = min(max_slack, 60)

                    # Leggi il valore dello slider AD OGNI ESECUZIONE
                    selected_slack = st.slider(
                        "Seleziona Margine Flessibilità Totale (giorni)",
                        min_value=0, max_value=slider_max,
                        # Usiamo la chiave dello slider per recuperare il valore, o 0 se non esiste
                        value=st.session_state.get('slack_slider_value', 0),
                        step=1,
                        key="slack_slider" # Key dello slider
                    )
                    # Aggiorna il valore in session state
                    st.session_state['slack_slider_value'] = selected_slack


                    # Bottone per triggerare l'analisi
                    if st.button("📈 Analizza Criticità", key="analyze_critical_path"):
                        # --- DEBUG: Stampa valori usati nel filtro ---
                        st.write(f"DEBUG: Filtraggio con Slack <= {selected_slack} nel periodo {selected_start_date.strftime('%d/%m/%Y')} - {selected_finish_date.strftime('%d/%m/%Y')}")
                        st.write(f"DEBUG: Numero attività nel periodo prima del filtro slack: {len(filtered_tasks_df)}")
                        # --- FINE DEBUG ---

                        # Applica il filtro slack SOLO AL CLICK
                        critical_subcritical_tasks = filtered_tasks_df[
                            filtered_tasks_df['TotalSlackDays'] <= selected_slack
                        ]
                        st.write(f"DEBUG: Numero attività dopo filtro slack: {len(critical_subcritical_tasks)}") # DEBUG


                        if not critical_subcritical_tasks.empty:
                            st.write(f"Attività critiche/sub-critiche (Slack <= {selected_slack} giorni):")
                            display_critical_df = critical_subcritical_tasks[["WBS", "Name", "Duration", "Start", "Finish", "TotalSlackDays"]].rename(columns={"Name": "Nome Attività", "Duration": "Durata", "Start": "Inizio", "Finish": "Fine", "TotalSlackDays": "Slack (g)"})
                            display_critical_df['Inizio'] = pd.to_datetime(display_critical_df['Inizio']).dt.strftime('%d/%m/%Y'); display_critical_df['Fine'] = pd.to_datetime(display_critical_df['Fine']).dt.strftime('%d/%m/%Y')
                            st.dataframe(display_critical_df, use_container_width=True, hide_index=True)

                            output_crit = BytesIO() # ... (download excel)
                            with pd.ExcelWriter(output_crit, engine='openpyxl') as writer: display_critical_df.to_excel(writer, index=False, sheet_name='PercorsoCritico')
                            excel_data_crit = output_crit.getvalue(); st.download_button(label="Scarica Analisi Criticità (Excel)", data=excel_data_crit, file_name=f"...", mime="...", key="download_criticita")
                        else:
                            st.warning(f"Nessuna attività trovata con Slack <= {selected_slack} giorni nel periodo selezionato.")
                else:
                    st.warning("Nessuna attività nel periodo selezionato per l'analisi di criticità.")

            except Exception as analysis_error:
                st.error(f"Errore durante l'analisi avanzata: {analysis_error}")
                # Aggiungi traceback per debug più approfondito se necessario
                # import traceback
                # st.error(traceback.format_exc())
        else:
             st.error("Errore: Dati delle attività non trovati in sessione.")


        # Debug (invariato)
        # ... (omissis)
        debug_text = st.session_state.get('debug_raw_text');
        if debug_text: st.markdown("---"); # ...
