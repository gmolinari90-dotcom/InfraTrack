# --- v9.1 (Base Stabile Definitiva + Selezione Date) ---
import streamlit as st
from lxml import etree
import pandas as pd
from datetime import datetime, date, timedelta
import re
import isodate
from io import BytesIO
import math

# --- CONFIGURAZIONE DELLA PAGINA ---
st.set_page_config(page_title="InfraTrack v9.1", page_icon="🚆", layout="wide") # Version updated

# --- CSS ---
# ... (CSS Identico a v9.0 - omesso per brevità) ...
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
st.markdown("## 🚆 InfraTrack v9.1") # Version updated
st.caption("La tua centrale di controllo per progetti infrastrutturali")

# --- GESTIONE RESET ---
if 'widget_key_counter' not in st.session_state: st.session_state.widget_key_counter = 0
if 'file_processed_success' not in st.session_state: st.session_state.file_processed_success = False
if st.button("🔄", key="reset_button", help="Resetta l'analisi", disabled=not st.session_state.file_processed_success):
    st.session_state.widget_key_counter += 1; st.session_state.file_processed_success = False
    # Rimuovi TUTTE le chiavi salvate per un reset pulito
    keys_to_reset = list(st.session_state.keys()) # Prendi tutte le chiavi attuali
    for key in keys_to_reset:
        # Non cancellare chiavi interne di Streamlit
        if not key.startswith("_"):
             del st.session_state[key]
    st.session_state.widget_key_counter = 1 # Reimposta il contatore chiave
    st.session_state.file_processed_success = False # Reimposta flag
    st.rerun()


# --- CARICAMENTO FILE ---
st.markdown("---"); st.markdown("#### 1. Carica la Baseline di Riferimento")
uploader_key = f"file_uploader_{st.session_state.widget_key_counter}"
# Forza il rerender del widget cambiando la chiave dopo il reset
uploaded_file = st.file_uploader("Seleziona il file .XML...", type=["xml"], label_visibility="collapsed", key=uploader_key)
if st.session_state.file_processed_success and 'uploaded_file_state' in st.session_state : st.success('File XML analizzato con successo!')
# Gestione stato file (necessaria perché st.rerun mantiene lo stato dei widget se la key non cambia)
if uploaded_file is not None and uploaded_file != st.session_state.get('uploaded_file_state'):
     st.session_state['uploaded_file_state'] = uploaded_file
     # Se carichiamo un NUOVO file, resettiamo lo stato di processamento
     st.session_state.file_processed_success = False
elif 'uploaded_file_state' not in st.session_state:
     # Caso iniziale o dopo reset VERO
     uploaded_file = None


# --- INIZIO ANALISI ---
current_file_to_process = st.session_state.get('uploaded_file_state') # Usa sempre il file in sessione

if current_file_to_process is not None:
    if not st.session_state.get('file_processed_success', False): # Usa .get() per sicurezza
        with st.spinner('Caricamento e analisi completa del file in corso...'):
            try:
                current_file_to_process.seek(0); file_content_bytes = current_file_to_process.read()
                parser = etree.XMLParser(recover=True); tree = etree.fromstring(file_content_bytes, parser=parser)
                ns = {'msp': 'http://schemas.microsoft.com/project'}
                project_name = "N/D"; formatted_cost = "€ 0,00"; project_start_date = None; project_finish_date = None; minutes_per_day = 480
                default_calendar = tree.find(".//msp:Calendar[msp:UID='1']", namespaces=ns)
                if default_calendar is not None:
                     working_day = default_calendar.find(".//msp:WeekDay[msp:DayType='1']", namespaces=ns)
                     if working_day is not None:
                          working_minutes = 0
                          for working_time in working_day.findall(".//msp:WorkingTime", namespaces=ns):
                               from_time_str = working_time.findtext('msp:FromTime', namespaces=ns); to_time_str = working_time.findtext('msp:ToTime', namespaces=ns)
                               if from_time_str and to_time_str:
                                    try:
                                         from_time = datetime.strptime(from_time_str, '%H:%M:%S').time(); to_time = datetime.strptime(to_time_str, '%H:%M:%S').time()
                                         dummy_date = date(1, 1, 1); delta = datetime.combine(dummy_date, to_time) - datetime.combine(dummy_date, from_time)
                                         working_minutes += delta.total_seconds() / 60
                                    except ValueError: pass
                          if working_minutes > 0: minutes_per_day = working_minutes
                st.session_state['minutes_per_day'] = minutes_per_day
                task_uid_1 = tree.find(".//msp:Task[msp:UID='1']", namespaces=ns)
                if task_uid_1 is not None:
                    project_name = task_uid_1.findtext('msp:Name', namespaces=ns) or "N/D"; total_cost_str = task_uid_1.findtext('msp:Cost', namespaces=ns) or "0"; total_cost_euros = float(total_cost_str) / 100.0
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
                def format_duration_from_xml(duration_str):
                     mpd = st.session_state.get('minutes_per_day', 480)
                     if not duration_str or mpd <= 0: return "0g"
                     try:
                         if duration_str.startswith('T'): duration_str = 'P' + duration_str
                         elif not duration_str.startswith('P'): return "N/D"
                         duration = isodate.parse_duration(duration_str); total_hours = duration.total_seconds() / 3600
                         if total_hours == 0: return "0g"
                         work_days = total_hours / (mpd / 60.0); return f"{round(work_days)}g"
                     except Exception: return "N/D"

                for task in all_tasks:
                    uid = task.findtext('msp:UID', namespaces=ns); name = task.findtext('msp:Name', namespaces=ns) or "";
                    start_str = task.findtext('msp:Start', namespaces=ns); finish_str = task.findtext('msp:Finish', namespaces=ns)
                    start_date = datetime.fromisoformat(start_str).date() if start_str else None; finish_date = datetime.fromisoformat(finish_str).date() if finish_str else None
                    duration_str = task.findtext('msp:Duration', namespaces=ns); cost_str = task.findtext('msp:Cost', namespaces=ns) or "0"
                    duration_formatted = format_duration_from_xml(duration_str)
                    cost_euros = float(cost_str) / 100.0 if cost_str else 0.0
                    is_milestone_text = (task.findtext('msp:Milestone', namespaces=ns) or '0').lower(); is_milestone = is_milestone_text == '1' or is_milestone_text == 'true'
                    wbs = task.findtext('msp:WBS', namespaces=ns) or ""
                    total_slack_minutes_str = task.findtext('msp:TotalSlack', namespaces=ns) or "0"

                    total_slack_days = 0
                    if total_slack_minutes_str:
                        try:
                            slack_minutes = float(total_slack_minutes_str)
                            mpd = st.session_state.get('minutes_per_day', 480)
                            if mpd > 0:
                                total_slack_days = math.ceil(slack_minutes / mpd)
                        except ValueError:
                            total_slack_days = 0

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
                         # Assicurati che 'start_date' (oggetto date) sia sempre presente per DataInizioObj
                         current_task_data = {"Nome Completo": name, "Data Inizio": start_date_formatted, "Data Fine": finish_date_formatted, "Durata": duration_formatted, "DurataSecondi": duration_seconds, "DataInizioObj": start_date}
                         existing_duration_seconds = potential_milestones.get(tup_tuf_key, {}).get("DurataSecondi", -1)
                         if tup_tuf_key not in potential_milestones: potential_milestones[tup_tuf_key] = current_task_data
                         elif not is_pure_milestone_duration:
                              if existing_duration_seconds == 0: potential_milestones[tup_tuf_key] = current_task_data
                              elif duration_seconds > existing_duration_seconds: potential_milestones[tup_tuf_key] = current_task_data

                # --- Correzione Definitiva KeyError ---
                final_milestones_data = []
                for key in potential_milestones:
                     data = potential_milestones[key]
                     # Aggiungi DataInizioObj SEMPRE, anche se None
                     final_milestones_data.append({
                         "Nome Completo": data.get("Nome Completo", ""),
                         "Data Inizio": data.get("Data Inizio", "N/D"),
                         "Data Fine": data.get("Data Fine", "N/D"),
                         "Durata": data.get("Durata", "N/D"),
                         "DataInizioObj": data.get("DataInizioObj") # Fondamentale che sia qui
                     })

                if final_milestones_data:
                    df_milestones = pd.DataFrame(final_milestones_data)
                    min_date_for_sort = date.min
                    # Converti e gestisci None PRIMA di ordinare
                    df_milestones['DataInizioObj'] = pd.to_datetime(df_milestones['DataInizioObj'], errors='coerce').dt.date
                    df_milestones['DataInizioObj'] = df_milestones['DataInizioObj'].fillna(min_date_for_sort)
                    df_milestones = df_milestones.sort_values(by="DataInizioObj").reset_index(drop=True)
                    # Salva il DF senza la colonna di ordinamento
                    st.session_state['df_milestones_display'] = df_milestones.drop(columns=['DataInizioObj'])
                else:
                    st.session_state['df_milestones_display'] = None
                # --- Fine Correzione ---

                st.session_state['all_tasks_data'] = pd.DataFrame(all_tasks_data_list)
                uploaded_file.seek(0); debug_content_bytes = uploaded_file.read(2000);
                try: st.session_state['debug_raw_text'] = '\n'.join(debug_content_bytes.decode('utf-8', errors='ignore').splitlines()[:50])
                except Exception as decode_err: st.session_state['debug_raw_text'] = f"Errore decodifica debug: {decode_err}"
                st.session_state.file_processed_success = True
                st.rerun() # Forza rerun per mostrare i dati correttamente

            except etree.XMLSyntaxError as e: st.error(f"Errore Sintassi XML: {e}"); st.error("File malformato?"); st.session_state.file_processed_success = False;
            except KeyError as ke: st.error(f"Errore interno: Chiave mancante {ke}"); st.error("Problema estrazione dati."); st.session_state.file_processed_success = False;
            except Exception as e: st.error(f"Errore Analisi durante elaborazione iniziale: {e}"); st.error("Verifica file XML."); st.session_state.file_processed_success = False;

    # --- VISUALIZZAZIONE DATI E SELEZIONE PERIODO ---
    if st.session_state.get('file_processed_success', False): # Usa .get() per sicurezza
        # --- Sezione 2: Analisi Preliminare ---
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
            output = BytesIO();
            with pd.ExcelWriter(output, engine='openpyxl') as writer: df_display.to_excel(writer, index=False, sheet_name='TerminiUtili')
            excel_data = output.getvalue(); st.download_button(label="Scarica (Excel)", data=excel_data, file_name="...", mime="...")
        else: st.warning("Nessun Termine Utile (TUP o TUF) trovato nel file.")

        # --- Sezione 3: Selezione Periodo ---
        st.markdown("---"); st.markdown("#### 3. Analisi Avanzata")
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

        # --- Placeholder per analisi future ---
        st.markdown("---"); st.markdown("##### 📊 Analisi Dettagliate")
        st.info("Seleziona il periodo desiderato. Le prossime analisi (Curva S, Istogrammi) useranno questo intervallo.")

        # --- Debug Section ---
        debug_text = st.session_state.get('debug_raw_text')
        if debug_text:
            st.markdown("---")
            with st.expander("🔍 Dati Grezzi per Debug (prime 50 righe del file)"):
                st.code(debug_text, language='xml')
