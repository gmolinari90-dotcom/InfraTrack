# --- v9.4 (Base v3.10 Corretta + Selezione Date) ---
import streamlit as st
from lxml import etree
import pandas as pd
from datetime import datetime, date, timedelta
import re
import isodate
from io import BytesIO
import math # Importato per calcolo slack futuro, anche se non usato ora

# --- CONFIGURAZIONE DELLA PAGINA ---
st.set_page_config(page_title="InfraTrack v9.4", page_icon="🚆", layout="wide") # Version updated

# --- CSS ---
# Stili CSS dalla v3.10
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
st.markdown("## 🚆 InfraTrack v9.4") # Version updated
st.caption("La tua centrale di controllo per progetti infrastrutturali")

# --- GESTIONE RESET (dalla v3.10, aggiornato) ---
if 'widget_key_counter' not in st.session_state: st.session_state.widget_key_counter = 0
if 'file_processed_success' not in st.session_state: st.session_state.file_processed_success = False
if st.button("🔄", key="reset_button", help="Resetta l'analisi", disabled=not st.session_state.file_processed_success):
    st.session_state.widget_key_counter += 1; st.session_state.file_processed_success = False
    # Reset chiavi come in v3.10 + aggiunte necessarie
    keys_to_reset = ['uploaded_file_state', 'project_name', 'formatted_cost','df_milestones_display',
                     'debug_raw_text', 'project_start_date','project_finish_date',
                     'all_tasks_data', 'minutes_per_day'] # Rimuovi slider_value se non serve
    for key in keys_to_reset:
        if key in st.session_state: del st.session_state[key]
    st.rerun()


# --- CARICAMENTO FILE (dalla v3.10) ---
st.markdown("---"); st.markdown("#### 1. Carica la Baseline di Riferimento")
uploader_key = f"file_uploader_{st.session_state.widget_key_counter}"
uploaded_file = st.file_uploader("Seleziona il file .XML...", type=["xml"], label_visibility="collapsed", key=uploader_key)
if st.session_state.get('file_processed_success', False) and 'uploaded_file_state' in st.session_state : st.success('File XML analizzato con successo!')
if uploaded_file is not None and uploaded_file != st.session_state.get('uploaded_file_state'):
     st.session_state['uploaded_file_state'] = uploaded_file
     st.session_state.file_processed_success = False
elif 'uploaded_file_state' not in st.session_state:
     uploaded_file = None

# --- FUNZIONI HELPER (definite globalmente) ---
# Necessarie per l'estrazione dati
@st.cache_data
def get_minutes_per_day(_tree, _ns):
    minutes_per_day = 480 # Default 8 ore
    try:
        default_calendar = _tree.find(".//msp:Calendar[msp:UID='1']", namespaces=_ns)
        if default_calendar is not None:
             working_day = default_calendar.find(".//msp:WeekDay[msp:DayType='1']", namespaces=_ns)
             if working_day is not None:
                  working_minutes = 0
                  for working_time in working_day.findall(".//msp:WorkingTime", namespaces=_ns):
                       from_time_str = working_time.findtext('msp:FromTime', namespaces=_ns); to_time_str = working_time.findtext('msp:ToTime', namespaces=_ns)
                       if from_time_str and to_time_str:
                            try:
                                 from_time = datetime.strptime(from_time_str, '%H:%M:%S').time(); to_time = datetime.strptime(to_time_str, '%H:%M:%S').time()
                                 dummy_date = date(1, 1, 1); delta = datetime.combine(dummy_date, to_time) - datetime.combine(dummy_date, from_time)
                                 working_minutes += delta.total_seconds() / 60
                            except ValueError: pass
                  if working_minutes > 0: minutes_per_day = working_minutes
    except Exception:
        pass
    return minutes_per_day

def format_duration_from_xml(duration_str):
     mpd = st.session_state.get('minutes_per_day', 480) # Usa valore salvato
     if not duration_str or mpd <= 0: return "0g"
     try:
         if duration_str.startswith('T'): duration_str = 'P' + duration_str
         elif not duration_str.startswith('P'): return "N/D"
         duration = isodate.parse_duration(duration_str); total_hours = duration.total_seconds() / 3600
         if total_hours == 0: return "0g"
         work_days = total_hours / (mpd / 60.0); return f"{round(work_days)}g"
     except Exception: return "N/D"

# --- INIZIO ANALISI ---
current_file_to_process = st.session_state.get('uploaded_file_state')

if current_file_to_process is not None:
    if not st.session_state.get('file_processed_success', False):
        with st.spinner('Caricamento e analisi completa del file in corso...'):
            try:
                # --- Logica parsing e estrazione dati come in v3.10, con correzioni ---
                current_file_to_process.seek(0); file_content_bytes = current_file_to_process.read()
                parser = etree.XMLParser(recover=True); tree = etree.fromstring(file_content_bytes, parser=parser)
                ns = {'msp': 'http://schemas.microsoft.com/project'}

                # Calcola e salva minutes_per_day
                minutes_per_day = get_minutes_per_day(tree, ns)
                st.session_state['minutes_per_day'] = minutes_per_day

                # Inizializza variabili
                project_name = "N/D"; formatted_cost = "€ 0,00"; project_start_date = None; project_finish_date = None
                
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

                    total_slack_days = 0 # Calcolo Slack con try/except corretto
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

                    # --- Logica TUP/TUF con INDENTAZIONE CORRETTA ---
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
                         existing_duration_seconds = potential_milestones.get(tup_tuf_key, {}).get("DurataSecondi", -1)
                         
                         if tup_tuf_key not in potential_milestones:
                              potential_milestones[tup_tuf_key] = current_task_data
                         elif not is_pure_milestone_duration:
                              if existing_duration_seconds == 0:
                                   potential_milestones[tup_tuf_key] = current_task_data
                              elif duration_seconds > existing_duration_seconds:
                                   # Indentazione CORRETTA
                                   potential_milestones[tup_tuf_key] = current_task_data
                    # --- FINE LOGICA TUP/TUF ---

                # Salvataggio dati TUP/TUF
                final_milestones_data = []
                for key in potential_milestones:
                     data = potential_milestones[key]
                     final_milestones_data.append({
                         "Nome Completo": data.get("Nome Completo", ""), "Data Inizio": data.get("Data Inizio", "N/D"),
                         "Data Fine": data.get("Data Fine", "N/D"), "Durata": data.get("Durata", "N/D"),
                         "DataInizioObj": data.get("DataInizioObj")
                     })
                if final_milestones_data:
                    df_milestones = pd.DataFrame(final_milestones_data)
                    min_date_for_sort = date.min
                    df_milestones['DataInizioObj'] = pd.to_datetime(df_milestones['DataInizioObj'], errors='coerce').dt.date
                    df_milestones['DataInizioObj'] = df_milestones['DataInizioObj'].fillna(min_date_for_sort)
                    df_milestones = df_milestones.sort_values(by="DataInizioObj").reset_index(drop=True)
                    st.session_state['df_milestones_display'] = df_milestones.drop(columns=['DataInizioObj'])
                else: st.session_state['df_milestones_display'] = None

                # Salvataggio TUTTE le attività
                st.session_state['all_tasks_data'] = pd.DataFrame(all_tasks_data_list)
                
                # Debug
                current_file_to_process.seek(0); debug_content_bytes = current_file_to_process.read(2000);
                try: st.session_state['debug_raw_text'] = '\n'.join(debug_content_bytes.decode('utf-8', errors='ignore').splitlines()[:50])
                except Exception as decode_err: st.session_state['debug_raw_text'] = f"Errore decodifica debug: {decode_err}"
                
                st.session_state.file_processed_success = True
                st.rerun()

            except Exception as e:
                st.error(f"Errore Analisi durante elaborazione iniziale: {e}"); st.error(f"Traceback: {traceback.format_exc()}"); st.error("Verifica file XML."); st.session_state.file_processed_success = False;


    # --- VISUALIZZAZIONE DATI E SELEZIONE PERIODO ---
    if st.session_state.get('file_processed_success', False):
        # --- Sezione 2: Analisi Preliminare ---
        st.markdown("---"); st.markdown("#### 2. Analisi Preliminare"); st.markdown("##### 📄 Informazioni Generali dell'Appalto")
        project_name = st.session_state.get('project_name', "N/D"); formatted_cost = st.session_state.get('formatted_cost', "N/D")
        
        # --- CORREZIONE DEFINITIVA SYNTAX ERROR ---
        col1_disp, col2_disp = st.columns(2)
        with col1_disp:
            st.markdown(f"**Nome:** {project_name}")
        with col2_disp:
            st.markdown(f"**Importo Totale Lavori:** {formatted_cost}")
        # --- FINE CORREZIONE ---

        st.markdown("##### 🗓️ Termini Utili Contrattuali (TUP/TUF)")
        df_display = st.session_state.get('df_milestones_display')
        if df_display is not None and not df_display.empty:
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer: df_display.to_excel(writer, index=False, sheet_name='TerminiUtili')
            excel_data = output.getvalue(); st.download_button(label="Scarica (Excel)", data=excel_data, file_name="termini_utili_TUP_TUF.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
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

        # --- Inizio Analisi Dettagliate ---
        st.markdown("---"); st.markdown("##### 📊 Analisi Dettagliate")
        
        all_tasks_df = st.session_state.get('all_tasks_data')
        
        # --- Iniziamo con CURVA S (SIL) ---
        st.markdown("###### Curva S (Costo Cumulato - Stima Lineare)")
        
        # Bottone per avviare l'analisi (come richiesto)
        if st.button("📈 Avvia Analisi Curva S", key="analyze_scurve"):
            if all_tasks_df is None or all_tasks_df.empty:
                 st.error("Errore: Dati delle attività non trovati. Impossibile calcolare la Curva S.")
            else:
                try:
                    with st.spinner("Calcolo distribuzione costi..."):
                        # Usiamo la nuova funzione per calcolare la distribuzione lineare
                        daily_cost_df = calculate_linear_distribution(all_tasks_df, value_col='Cost', is_cost=True)
                    
                    if not daily_cost_df.empty:
                        # Converti selected_start_date/finish_date in datetime per il filtro pandas
                        selected_start_dt = datetime.combine(selected_start_date, datetime.min.time())
                        selected_finish_dt = datetime.combine(selected_finish_date, datetime.max.time())

                        mask_cost = (daily_cost_df['Date'] >= selected_start_dt) & (daily_cost_df['Date'] <= selected_finish_dt)
                        filtered_cost = daily_cost_df.loc[mask_cost]
                        
                        if not filtered_cost.empty:
                            monthly_cost = filtered_cost.set_index('Date').resample('ME')['Value'].sum().reset_index()
                            monthly_cost['Costo Cumulato (€)'] = monthly_cost['Value'].cumsum()
                            monthly_cost['Mese'] = monthly_cost['Date'].dt.strftime('%Y-%m')
                            
                            st.markdown("###### Tabella Dati SIL Mensili Aggregati")
                            df_display_sil = monthly_cost[['Mese', 'Value', 'Costo Cumulato (€)']].rename(columns={'Value': 'Costo Mensile (€)'})
                            st.dataframe(df_display_sil, use_container_width=True, hide_index=True)
                            
                            st.markdown("###### Grafico Curva S")
                            fig_sil = go.Figure()
                            fig_sil.add_trace(go.Bar(x=monthly_cost['Mese'], y=monthly_cost['Value'], name='Costo Mensile'))
                            fig_sil.add_trace(go.Scatter(x=monthly_cost['Mese'], y=monthly_cost['Costo Cumulato (€)'], name='Costo Cumulato', mode='lines+markers', yaxis='y2'))
                            fig_sil.update_layout(
                                title='Curva S - Costo Mensile e Cumulato (Stima Lineare)',
                                xaxis_title="Mese",
                                yaxis=dict(title="Costo Mensile (€)"),
                                yaxis2=dict(title="Costo Cumulato (€)", overlaying="y", side="right"),
                                legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
                            )
                            st.plotly_chart(fig_sil, use_container_width=True)
                            
                            output_sil = BytesIO()
                            with pd.ExcelWriter(output_sil, engine='openpyxl') as writer:
                                 df_display_sil.to_excel(writer, index=False, sheet_name='SIL_Mensile')
                            excel_data_sil = output_sil.getvalue()
                            st.download_button(label="Scarica Dati SIL (Excel)", data=excel_data_sil, file_name="dati_sil_mensile.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="download_sil")
                        else:
                            st.warning("Nessun costo trovato nel periodo selezionato.")
                    else:
                        st.warning("Nessun costo trovato nel file per calcolare la Curva S.")
                
                except Exception as analysis_error:
                    st.error(f"Errore durante l'analisi avanzata: {analysis_error}")
                    st.error(traceback.format_exc())

        # --- Debug Section ---
        debug_text = st.session_state.get('debug_raw_text')
        if debug_text:
            st.markdown("---")
            with st.expander("🔍 Dati Grezzi per Debug (prime 50 righe del file)"):
                st.code(debug_text, language='xml')
