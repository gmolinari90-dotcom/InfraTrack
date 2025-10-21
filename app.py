# --- v17.0 (Logica Curva S: Stima Aggregata con Filtro WBS Gerarchico) ---
import streamlit as st
from lxml import etree
import pandas as pd
from datetime import datetime, date, timedelta
import re
import isodate
from io import BytesIO
import math
import plotly.graph_objects as go # Importa Graph Objects per grafici combinati
import traceback # Per debug avanzato

# --- CONFIGURAZIONE DELLA PAGINA ---
st.set_page_config(page_title="InfraTrack v17.0", page_icon="🚆", layout="wide") # Version updated

# --- CSS ---
st.markdown("""
<style>
    /* ... (CSS Identico - omesso per brevità) ... */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, .stApp p, .stApp .stDataFrame, .stApp .stButton>button { font-size: 0.85rem !important; }
    .stApp h2 { font-size: 1.5rem !important; }
    .stApp .stMarkdown h4 { font-size: 1.1rem !important; margin-bottom: 0.5rem; margin-top: 1rem; }
    .stApp .stMarkdown h5 { font-size: 0.90rem !important; margin-bottom: 0.5rem; margin-top: 0.8rem; }
    .stApp .stMarkdown h6 { font-size: 0.88rem !important; margin-bottom: 0.4rem; margin-top: 0.8rem; font-weight: bold;}
    
    button[data-testid="stButton"][kind="primary"][key="reset_button"],
    button[data-testid="stButton"][kind="secondary"][key="clear_cache_button"] { 
        padding: 0.2rem 0.5rem !important; 
        line-height: 1.2 !important; 
        font-size: 1.0rem !important; 
        border-radius: 0.25rem !important; 
        margin-right: 5px; 
    }
    button[data-testid="stButton"][kind="primary"][key="reset_button"]:disabled { cursor: not-allowed; opacity: 0.5; }
    
    .stApp { padding-top: 2rem; }
    .stDataFrame td { text-align: center !important; }
    div[data-testid="stDateInput"] label { font-size: 0.85rem !important; }
    div[data-testid="stDateInput"] input { font-size: 0.85rem !important; padding: 0.3rem 0.5rem !important;}
    .stCaptionContainer { font-size: 0.75rem !important; margin-top: -0.5rem; margin-bottom: 1rem;}
</style>
""", unsafe_allow_html=True)


# --- TITOLO E HEADER ---
st.markdown("## 🚆 InfraTrack v17.0") # Version updated
st.caption("La tua centrale di controllo per progetti infrastrutturali")

# --- GESTIONE RESET E CACHE ---
if 'widget_key_counter' not in st.session_state: st.session_state.widget_key_counter = 0
if 'file_processed_success' not in st.session_state: st.session_state.file_processed_success = False

col_btn_1, col_btn_2, col_btn_3 = st.columns([0.1, 0.2, 0.7]) 

with col_btn_1:
    if st.button("🔄", key="reset_button", help="Resetta l'analisi (Svuota Sessione)", disabled=not st.session_state.file_processed_success):
        st.session_state.widget_key_counter += 1; st.session_state.file_processed_success = False
        keys_to_reset = list(st.session_state.keys())
        for key in keys_to_reset:
            if not key.startswith("_"): del st.session_state[key]
        st.session_state.widget_key_counter = 1
        st.session_state.file_processed_success = False
        st.rerun()

with col_btn_2:
    if st.button("🗑️ Svuota Cache", key="clear_cache_button", help="Elimina i dati temporanei (Forza ri-analisi @st.cache_data)"):
        st.cache_data.clear()
        st.toast("Cache dei dati svuotata!", icon="✅")


# --- CARICAMENTO FILE ---
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
@st.cache_data
def get_minutes_per_day(_tree, _ns):
    # ... (Funzione invariata) ...
    minutes_per_day = 480 
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
    # ... (Funzione invariata) ...
    minutes_per_day = st.session_state.get('minutes_per_day', 480)
    if not duration_str or minutes_per_day <= 0: return "0g"
    try:
        if duration_str.startswith('T'): duration_str = 'P' + duration_str
        elif not duration_str.startswith('P'): return "N/D"
        duration = isodate.parse_duration(duration_str); total_hours = duration.total_seconds() / 3600
        if total_hours == 0: return "0g"
        work_days = total_hours / (minutes_per_day / 60.0); return f"{round(work_days)}g"
    except Exception: return "N/D"

# --- HELPER PER WBS ---
def get_parent_wbs(wbs_string):
    """Estrae il WBS genitore (es. da '1.2.1' a '1.2')."""
    if wbs_string is None or "." not in wbs_string:
        return None
    return wbs_string.rsplit('.', 1)[0]
    
# --- FUNZIONE PER CALCOLARE SIL (Logica WBS Gerarchica) ---
@st.cache_data
def calculate_daily_distribution_wbs(_tasks_dataframe):
    """
    Calcola la distribuzione giornaliera dei costi (Stima Aggregata)
    leggendo il Costo TOTALE e le date Start/Finish.
    
    Usa la logica WBS (Top-Down) per evitare doppio conteggio.
    """
    daily_cost_data = []
    
    tasks_dataframe = _tasks_dataframe.copy()
    
    tasks_dataframe['Start'] = pd.to_datetime(tasks_dataframe['Start'], errors='coerce').dt.date
    tasks_dataframe['Finish'] = pd.to_datetime(tasks_dataframe['Finish'], errors='coerce').dt.date
    
    # --- FILTRO GERARCHICO (WBS) ---
    
    # 1. Rimuovi attività senza date valide o WBS
    filtered_tasks_dataframe = tasks_dataframe.dropna(subset=['Start', 'Finish', 'Cost', 'WBS'])
    
    # 2. Considera solo attività con costo > 0
    filtered_tasks_dataframe = filtered_tasks_dataframe[filtered_tasks_dataframe['Cost'] > 0]
    
    # 3. Identifica i WBS di *tutte* le attività che hanno un costo
    cost_wbs_string_set = set(filtered_tasks_dataframe['WBS'].dropna().astype(str))
    
    # 4. Trova il WBS genitore per ogni attività
    filtered_tasks_dataframe['Parent_WBS'] = filtered_tasks_dataframe['WBS'].astype(str).apply(get_parent_wbs)
    
    # 5. Controlla se il genitore è *anch'esso* nel set di attività con costo
    filtered_tasks_dataframe['Parent_Has_Cost'] = filtered_tasks_dataframe['Parent_WBS'].isin(cost_wbs_string_set)
    
    # 6. Il dataframe finale da distribuire contiene SOLO le attività
    #    il cui genitore NON ha un costo. (Questa è la logica anti-doppio-conteggio)
    tasks_to_distribute = filtered_tasks_dataframe[filtered_tasks_dataframe['Parent_Has_Cost'] == False]
    # --- FINE FILTRO ---

    st.session_state['debug_task_count'] = len(tasks_to_distribute) 
    st.session_state['debug_total_cost'] = tasks_to_distribute['Cost'].sum() 

    for _, task in tasks_to_distribute.iterrows():
        start_date = task['Start']
        finish_date = task['Finish']
        total_cost = task['Cost'] # Già in Euro
        
        duration_days = (finish_date - start_date).days
        
        if duration_days < 0: 
            continue 
        
        number_of_days_in_period = duration_days + 1
        
        if number_of_days_in_period <= 0:
             value_per_day = total_cost 
             number_of_days_in_period = 1
        else:
             value_per_day = total_cost / number_of_days_in_period
        
        for i in range(number_of_days_in_period):
            current_date = start_date + timedelta(days=i)
            daily_cost_data.append({'Date': current_date, 'Value': value_per_day})

    if not daily_cost_data:
        return pd.DataFrame(columns=['Date', 'Value'])

    # Aggregazione finale
    daily_dataframe = pd.DataFrame(daily_cost_data)
    daily_dataframe['Date'] = pd.to_datetime(daily_dataframe['Date'])
    aggregated_daily_dataframe = daily_dataframe.groupby('Date')['Value'].sum().reset_index()
    
    return aggregated_daily_dataframe
# --- FINE FUNZIONE ---


# --- INIZIO ANALISI ---
current_file_to_process = st.session_state.get('uploaded_file_state')

if current_file_to_process is not None:
    if not st.session_state.get('file_processed_success', False):
        with st.spinner('Caricamento e analisi completa del file in corso...'):
            try:
                current_file_to_process.seek(0); file_content_bytes = current_file_to_process.read()
                
                parser = etree.XMLParser(recover=True)
                tree = etree.fromstring(file_content_bytes, parser=parser)
                
                ns = {'msp': 'http://schemas.microsoft.com/project'}

                minutes_per_day = get_minutes_per_day(tree, ns)
                st.session_state['minutes_per_day'] = minutes_per_day

                project_name = "N/D"; formatted_cost = "€ 0,00"; project_start_date = None; project_finish_date = None
                
                task_uid_1 = tree.find(".//msp:Task[msp:UID='1']", namespaces=ns)
                if task_uid_1 is not None:
                    project_name = task_uid_1.findtext('msp:Name', namespaces=ns) or "N/D"
                    total_cost_str = task_uid_1.findtext('msp:Cost', namespaces=ns) or "0"
                    total_cost_euros = float(total_cost_str) / 100.0
                    formatted_cost = f"€ {total_cost_euros:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    
                    start_str = task_uid_1.findtext('msp:Start', namespaces=ns); finish_str = task_uid_1.findtext('msp:Finish', namespaces=ns)
                    if start_str: project_start_date = datetime.fromisoformat(start_str).date()
                    if finish_str: project_finish_date = datetime.fromisoformat(finish_str).date()
                
                st.session_state['project_total_cost_from_summary'] = formatted_cost

                if not project_start_date: project_start_date = date.today()
                if not project_finish_date: project_finish_date = project_start_date + timedelta(days=365)
                if project_start_date > project_finish_date: project_finish_date = project_start_date + timedelta(days=1)
                
                st.session_state['project_name'] = project_name; st.session_state['formatted_cost'] = formatted_cost
                st.session_state['project_start_date'] = project_start_date; st.session_state['project_finish_date'] = project_finish_date

                potential_milestones = {}; all_tasks = tree.findall('.//msp:Task', namespaces=ns)
                tup_tuf_pattern = re.compile(r'(?i)(TUP|TUF)\s*\d*'); all_tasks_data_list = []

                for task in all_tasks:
                    uid = task.findtext('msp:UID', namespaces=ns); name = task.findtext('msp:Name', namespaces=ns) or "";
                    start_str = task.findtext('msp:Start', namespaces=ns); finish_str = task.findtext('msp:Finish', namespaces=ns);
                    start_date = datetime.fromisoformat(start_str).date() if start_str else None; finish_date = datetime.fromisoformat(finish_str).date() if finish_str else None
                    duration_str = task.findtext('msp:Duration', namespaces=ns); 
                    
                    cost_str = task.findtext('msp:Cost', namespaces=ns) or "0"
                    cost_euros = float(cost_str) / 100.0 # Costo in Euro
                    
                    duration_formatted = format_duration_from_xml(duration_str)
                    is_milestone_text = (task.findtext('msp:Milestone', namespaces=ns) or '0').lower(); is_milestone = is_milestone_text == '1' or is_milestone_text == 'true'
                    
                    # WBS è fondamentale per la logica Gerarchica
                    wbs = task.findtext('msp:WBS', namespaces=ns) or "" 
                    
                    total_slack_minutes_str = task.findtext('msp:TotalSlack', namespaces=ns) or "0"
                    is_summary_str = task.findtext('msp:Summary', namespaces=ns) or '0'
                    is_summary = is_summary_str == '1'
                    total_slack_days = 0
                    if total_slack_minutes_str:
                        try:
                            slack_minutes = float(total_slack_minutes_str)
                            mpd = st.session_state.get('minutes_per_day', 480)
                            if mpd > 0: total_slack_days = math.ceil(slack_minutes / mpd)
                        except ValueError: total_slack_days = 0
                        
                    if uid != '0':
                        all_tasks_data_list.append({"UID": uid, "Name": name, "Start": start_date, "Finish": finish_date, "Duration": duration_formatted, 
                                                    "Cost": cost_euros, 
                                                    "Milestone": is_milestone, "Summary": is_summary, 
                                                    "WBS": wbs, # WBS è cruciale
                                                    "TotalSlackDays": total_slack_days})
                    
                    # Logica TUP/TUF (invariata)
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
                                potential_milestones[tup_tuf_key] = current_task_data
                
                # Salvataggio dati TUP/TUF (invariato)
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

                st.session_state['all_tasks_data'] = pd.DataFrame(all_tasks_data_list)
                
                # Debug
                current_file_to_process.seek(0); debug_content_bytes = current_file_to_process.read(2000);
                try: st.session_state['debug_raw_text'] = '\n'.join(debug_content_bytes.decode('utf-8', errors='ignore').splitlines()[:50])
                except Exception as decode_err: st.session_state['debug_raw_text'] = f"Errore decodifica debug: {decode_err}"
                
                st.session_state.file_processed_success = True
                st.rerun()

            except Exception as e:
                print(f"Errore Analisi: {e}")
                print(traceback.format_exc())
                st.error(f"Errore Analisi durante elaborazione iniziale: {e}"); 
                st.error(f"Traceback: {traceback.format_exc()}"); 
                st.error("Verifica file XML."); 
                st.session_state.file_processed_success = False;


    # --- VISUALIZZAZIONE DATI E ANALISI AVANZATA ---
    if st.session_state.get('file_processed_success', False):
            
        # --- Sezione 2: Analisi Preliminare (Invariata) ---
        st.markdown("---"); st.markdown("#### 2. Analisi Preliminare"); st.markdown("##### 📄 Informazioni Generali dell'Appalto")
        project_name = st.session_state.get('project_name', "N/D"); formatted_cost = st.session_state.get('formatted_cost', "N/D")
        col1_disp, col2_disp = st.columns(2); 
        with col1_disp: st.markdown(f"**Nome:** {project_name}")
        with col2_disp: st.markdown(f"**Importo Totale Lavori:** {formatted_cost}")
        st.markdown("##### 🗓️ Termini Utili Contrattuali (TUP/TUF)")
        df_display = st.session_state.get('df_milestones_display')
        if df_display is not None and not df_display.empty:
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer: df_display.to_excel(writer, index=False, sheet_name='TerminiUtili')
            excel_data = output.getvalue(); st.download_button(label="Scarica (Excel)", data=excel_data, file_name="termini_utili_TUP_TUF.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else: st.warning("Nessun Termine Utile (TUP o TUF) trovato nel file.")

        # --- Sezione 3: Selezione Periodo e Analisi (Invariata) ---
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

        # --- Analisi Dettagliate ---
        st.markdown("---"); st.markdown("##### 📊 Analisi Dettagliate")
        
        if st.button("📈 Avvia Analisi Curva S", key="analyze_scurve"):
            
            all_tasks_dataframe = st.session_state.get('all_tasks_data')
            
            if all_tasks_dataframe is None or all_tasks_dataframe.empty:
                st.error("Errore: Dati delle attività non trovati. Impossibile calcolare la Curva S.")
            else:
                try:
                    scurve_source = "Stima Aggregata (Logica WBS)" # Nuovo nome
                    st.markdown(f"###### Curva S (Dati: {scurve_source})")
                    
                    with st.spinner(f"Calcolo distribuzione costi ({scurve_source})..."):
                        # Usa la funzione di stima WBS
                        daily_cost_df = calculate_daily_distribution_wbs(all_tasks_dataframe.copy()) 
                    
                    if daily_cost_df.empty:
                        st.error("Errore: Nessun costo trovato nelle attività del file XML.")
                        st.warning("Impossibile calcolare la Curva S. (Nessuna attività trovata con <Cost> > 0).")
                        
                    else:
                        selected_start_dt = datetime.combine(selected_start_date, datetime.min.time())
                        selected_finish_dt = datetime.combine(selected_finish_date, datetime.max.time())
                        
                        mask_cost = (daily_cost_df['Date'] >= selected_start_dt) & (daily_cost_df['Date'] <= selected_finish_dt)
                        filtered_cost = daily_cost_df.loc[mask_cost]
                        
                        if not filtered_cost.empty:
                            monthly_cost = filtered_cost.set_index('Date').resample('ME')['Value'].sum().reset_index()
                            monthly_cost['Costo Cumulato (€)'] = monthly_cost['Value'].cumsum()
                            monthly_cost['Mese'] = monthly_cost['Date'].dt.strftime('%Y-%m')
                            
                            st.markdown(f"###### Tabella Dati SIL Mensili ({scurve_source})")
                            df_display_sil = monthly_cost.copy()
                            df_display_sil['Costo Mensile (€)'] = df_display_sil['Value'].apply(lambda x: f"€ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                            df_display_sil['Costo Cumulato (€)'] = df_display_sil['Costo Cumulato (€)'].apply(lambda x: f"€ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                            st.dataframe(df_display_sil[['Mese', 'Costo Mensile (€)', 'Costo Cumulato (€)']], use_container_width=True, hide_index=True)
                            
                            st.markdown(f"###### Grafico Curva S ({scurve_source})")
                            fig_sil = go.Figure()
                            fig_sil.add_trace(go.Bar(x=monthly_cost['Mese'], y=monthly_cost['Value'], name=f'Costo Mensile ({scurve_source})'))
                            fig_sil.add_trace(go.Scatter(x=monthly_cost['Mese'], y=monthly_cost['Costo Cumulato (€)'], name=f'Costo Cumulato ({scurve_source})', mode='lines+markers', yaxis='y2'))
                            fig_sil.update_layout(
                                title=f'Curva S - Costo Mensile e Cumulato (Dati {scurve_source})',
                                xaxis_title="Mese",
                                yaxis=dict(title="Costo Mensile (€)"),
                                yaxis2=dict(title="Costo Cumulato (€)", overlaying="y", side="right"),
                                legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
                            )
                            st.plotly_chart(fig_sil, use_container_width=True)
                            
                            output_sil = BytesIO()
                            with pd.ExcelWriter(output_sil, engine='openpyxl') as writer:
                                monthly_cost[['Mese', 'Value', 'Costo Cumulato (€)']].rename(columns={'Value': 'Costo Mensile (€)'}).to_excel(writer, index=False, sheet_name='SIL_Mensile')
                            excel_data_sil = output_sil.getvalue()
                            st.download_button(label="Scarica Dati SIL (Excel)", data=excel_data_sil, file_name="dati_sil_mensile.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="download_sil")

                            # DEBUG SUL COSTO TOTALE
                            st.markdown("---")
                            st.markdown(f"##### Diagnostica Dati Calcolati ({scurve_source})")
                            
                            debug_task_count = st.session_state.get('debug_task_count', 0)
                            st.write(f"**Numero attività usate per la distribuzione (filtro WBS):** {debug_task_count}")
                            
                            debug_total = st.session_state.get('debug_total_cost', 0)
                            formatted_debug_cost = f"€ {debug_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                            st.write(f"**Costo Totale Calcolato (somma attività WBS valide):** {formatted_debug_cost}")
                            
                            project_total = st.session_state.get('project_total_cost_from_summary', 'N/D')
                            st.caption(f"Costo Totale Ufficiale (da Riepilogo Progetto): {project_total}")
                            st.caption("I due totali dovrebbero ora corrispondere, grazie al filtro gerarchico WBS.")


                        else:
                            st.warning(f"Nessun dato di costo ({scurve_source}) trovato nel periodo selezionato.")
                
                except Exception as analysis_error:
                    st.error(f"Errore durante l'analisi avanzata: {analysis_error}")
                    st.error(traceback.format_exc())
            
        # --- Placeholder per Istogrammi (Invariato) ---
        st.markdown("---")
        st.markdown("###### Istogrammi Risorse")
        st.info("Logica istogrammi da implementare (richiederà dati 'Lavoro' e 'Risorse').")

        # --- Debug Section (Invariata) ---
        debug_text = st.session_state.get('debug_raw_text')
        if debug_text:
            st.markdown("---")
            with st.expander("🔍 Dati Grezzi per Debug (prime 50 righe del file)"):
                st.code(debug_text, language='xml')
