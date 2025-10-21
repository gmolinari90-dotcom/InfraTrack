# --- v14.1 (Logica di Stima Lineare CORRETTA con filtro WBS, No Abbreviazioni) ---
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
# Versione aggiornata per riflettere la nuova logica WBS
st.set_page_config(page_title="InfraTrack v14.1", page_icon="🚆", layout="wide") 

# --- CSS ---
st.markdown("""
<style>
    /* ... (CSS Identico - omesso per brevità) ... */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, .stApp p, .stApp .stDataFrame, .stApp .stButton>button { font-size: 0.85rem !important; }
    .stApp h2 { font-size: 1.5rem !important; }
    .stApp .stMarkdown h4 { font-size: 1.1rem !important; margin-bottom: 0.5rem; margin-top: 1rem; }
    .stApp .stMarkdown h5 { font-size: 0.90rem !important; margin-bottom: 0.5rem; margin-top: 0.8rem; }
    .stApp .stMarkdown h6 { font-size: 0.88rem !important; margin-bottom: 0.4rem; margin-top: 0.8rem; font-weight: bold;}
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
st.markdown("## 🚆 InfraTrack v14.1") # Versione aggiornata
st.caption("La tua centrale di controllo per progetti infrastrutturali")

# --- GESTIONE RESET ---
if 'widget_key_counter' not in st.session_state: st.session_state.widget_key_counter = 0
if 'file_processed_success' not in st.session_state: st.session_state.file_processed_success = False
if st.button("🔄", key="reset_button", help="Resetta l'analisi", disabled=not st.session_state.file_processed_success):
    st.session_state.widget_key_counter += 1; st.session_state.file_processed_success = False
    keys_to_reset = list(st.session_state.keys())
    for key in keys_to_reset:
        if not key.startswith("_"): del st.session_state[key]
    st.session_state.widget_key_counter = 1
    st.session_state.file_processed_success = False
    st.rerun()


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
def get_minutes_per_day(_xml_tree, _namespaces):
    """Estrae i minuti lavorativi giornalieri dal calendario di default (UID 1)."""
    minutes_per_day = 480 # Default 8 ore
    try:
        default_calendar = _xml_tree.find(".//msp:Calendar[msp:UID='1']", namespaces=_namespaces)
        if default_calendar is not None:
            working_day = default_calendar.find(".//msp:WeekDay[msp:DayType='1']", namespaces=_namespaces) # Cerca un giorno lavorativo (es. Lunedì)
            if working_day is not None:
                working_minutes = 0
                for working_time in working_day.findall(".//msp:WorkingTime", namespaces=_namespaces):
                    from_time_string = working_time.findtext('msp:FromTime', namespaces=_namespaces)
                    to_time_string = working_time.findtext('msp:ToTime', namespaces=_namespaces)
                    if from_time_string and to_time_string:
                        try:
                            from_time = datetime.strptime(from_time_string, '%H:%M:%S').time()
                            to_time = datetime.strptime(to_time_string, '%H:%M:%S').time()
                            dummy_date = date(1, 1, 1)
                            delta = datetime.combine(dummy_date, to_time) - datetime.combine(dummy_date, from_time)
                            working_minutes += delta.total_seconds() / 60
                        except ValueError: 
                            pass # Ignora formati ora non validi
                if working_minutes > 0: 
                    minutes_per_day = working_minutes
    except Exception:
        pass # Ritorna il default 480 in caso di errore
    return minutes_per_day

def format_duration_from_xml(duration_string):
    """Converte la stringa di durata ISO (es. PT8H0M0S) in giorni (es. '1g')."""
    minutes_per_day = st.session_state.get('minutes_per_day', 480) # Recupera i minuti/giorno
    if not duration_string or minutes_per_day <= 0: 
        return "0g"
    
    try:
        if duration_string.startswith('T'): 
            duration_string = 'P' + duration_string # Corregge formato non standard
        elif not duration_string.startswith('P'): 
            return "N/D" # Formato non riconosciuto
            
        duration_object = isodate.parse_duration(duration_string)
        total_hours = duration_object.total_seconds() / 3600
        
        if total_hours == 0: 
            return "0g"
            
        work_days = total_hours / (minutes_per_day / 60.0)
        return f"{round(work_days)}g"
        
    except Exception:
        return "N/D"

def get_parent_wbs(wbs_string):
    """Estrae il WBS genitore (es. da '1.2.1' a '1.2')."""
    if wbs_string is None or "." not in wbs_string:
        return None
    # Rimuove l'ultima parte del WBS (es. '1.2.1' -> '1.2')
    return wbs_string.rsplit('.', 1)[0]
    
# --- FUNZIONE PER CALCOLARE SIL DA DATI TASK (Logica v14.1 - Anti Doppio Conteggio) ---
@st.cache_data
def calculate_linear_distribution(_tasks_dataframe):
    """
    Calcola la distribuzione giornaliera dei costi.
    Logica anti-doppio-conteggio (v14.1): identifica le attività con costo > 0
    e distribuisce solo quelle che non hanno un "genitore" (parent)
    anch'esso con costo > 0. Questo gestisce sia i roll-up normali
    sia i casi in cui il costo è solo sul riepilogo.
    """
    daily_cost_data = []
    
    # Crea una copia per evitare di modificare il dataframe originale in cache
    tasks_dataframe = _tasks_dataframe.copy()
    
    tasks_dataframe['Start'] = pd.to_datetime(tasks_dataframe['Start'], errors='coerce').dt.date
    tasks_dataframe['Finish'] = pd.to_datetime(tasks_dataframe['Finish'], errors='coerce').dt.date
    
    # --- NUOVO FILTRO CHIAVE (Anti-Doppio-Conteggio basato su WBS) ---
    
    # 1. Rimuovi attività senza date valide o costo
    filtered_tasks_dataframe = tasks_dataframe.dropna(subset=['Start', 'Finish', 'Cost'])
    
    # 2. Considera solo attività con costo > 0
    filtered_tasks_dataframe = filtered_tasks_dataframe[filtered_tasks_dataframe['Cost'] > 0]
    
    # 3. Identifica i WBS di *tutte* le attività che hanno un costo
    #    (Assicurati che i WBS siano stringhe e unici)
    cost_wbs_string_set = set(filtered_tasks_dataframe['WBS'].dropna().astype(str))
    
    # 4. Trova il WBS genitore per ogni attività usando la funzione helper
    filtered_tasks_dataframe['Parent_WBS'] = filtered_tasks_dataframe['WBS'].astype(str).apply(get_parent_wbs)
    
    # 5. Controlla se il genitore è *anch'esso* nel set di attività con costo
    filtered_tasks_dataframe['Parent_Has_Cost'] = filtered_tasks_dataframe['Parent_WBS'].isin(cost_wbs_string_set)
    
    # 6. Il dataframe finale da distribuire contiene SOLO le attività
    #    con costo > 0 E il cui genitore NON ha un costo.
    #    (Se Parent_Has_Cost è False, l'attività viene inclusa per il calcolo)
    tasks_to_distribute = filtered_tasks_dataframe[filtered_tasks_dataframe['Parent_Has_Cost'] == False]
    # --- FINE NUOVO FILTRO ---

    # Salvataggio dati per il debug
    st.session_state['debug_task_count'] = len(tasks_to_distribute) 
    st.session_state['debug_total_cost'] = tasks_to_distribute['Cost'].sum() 

    # Loop solo sulle attività filtrate correttamente
    for _, task in tasks_to_distribute.iterrows():
        start_date = task['Start']
        finish_date = task['Finish']
        total_cost = task['Cost']
        
        # Calcola la durata in giorni (calendario solare)
        duration_days = (finish_date - start_date).days
        
        # Salta attività con date incoerenti
        if duration_days < 0: 
            continue 
        
        # Il numero di giorni in cui spalmare il costo è (durata + 1)
        # Esempio: 10/10 -> 10/10 è 1 giorno (0 giorni durata)
        number_of_days_in_period = duration_days + 1
        
        # Assicura di non dividere per zero
        if number_of_days_in_period <= 0:
             # Gestisce le milestone con costo
             if duration_days == -1: # Raro, ma ignora
                 continue
             value_per_day = total_cost # Assegna tutto al primo giorno
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
                current_file_to_process.seek(0)
                file_content_bytes = current_file_to_process.read()
                
                parser = etree.XMLParser(recover=True) # Parser flessibile
                xml_tree = etree.fromstring(file_content_bytes, parser=parser)
                namespaces = {'msp': 'http://schemas.microsoft.com/project'}

                # Calcola i minuti per giorno dal calendario
                minutes_per_day = get_minutes_per_day(xml_tree, namespaces)
                st.session_state['minutes_per_day'] = minutes_per_day

                # Inizializza variabili
                project_name = "N/D"
                formatted_cost = "€ 0,00"
                project_start_date = None
                project_finish_date = None
                
                # Estrae dati generali dal Task UID 1 (Riepilogo Progetto)
                task_uid_1 = xml_tree.find(".//msp:Task[msp:UID='1']", namespaces=namespaces)
                if task_uid_1 is not None:
                    project_name = task_uid_1.findtext('msp:Name', namespaces=namespaces) or "N/D"
                    total_cost_string = task_uid_1.findtext('msp:Cost', namespaces=namespaces) or "0"
                    total_cost_euros = float(total_cost_string) / 100.0
                    
                    # Formattazione costo
                    formatted_cost = f"€ {total_cost_euros:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    
                    start_string = task_uid_1.findtext('msp:Start', namespaces=namespaces)
                    finish_string = task_uid_1.findtext('msp:Finish', namespaces=namespaces)
                    
                    if start_string: 
                        project_start_date = datetime.fromisoformat(start_string).date()
                    if finish_string: 
                        project_finish_date = datetime.fromisoformat(finish_string).date()
                
                # Gestione date di fallback
                if not project_start_date: 
                    project_start_date = date.today()
                if not project_finish_date: 
                    project_finish_date = project_start_date + timedelta(days=365)
                if project_start_date > project_finish_date: 
                    project_finish_date = project_start_date + timedelta(days=1)
                
                # Salva dati generali in sessione
                st.session_state['project_name'] = project_name
                st.session_state['formatted_cost'] = formatted_cost
                st.session_state['project_start_date'] = project_start_date
                st.session_state['project_finish_date'] = project_finish_date

                # Inizializza estrazione Task
                potential_milestones = {}
                all_tasks = xml_tree.findall('.//msp:Task', namespaces=namespaces)
                tup_tuf_pattern = re.compile(r'(?i)(TUP|TUF)\s*\d*')
                all_tasks_data_list = []

                # --- INIZIO LOOP SUI TASK ---
                for task in all_tasks:
                    uid = task.findtext('msp:UID', namespaces=namespaces)
                    name = task.findtext('msp:Name', namespaces=namespaces) or ""
                    
                    start_string = task.findtext('msp:Start', namespaces=namespaces)
                    finish_string = task.findtext('msp:Finish', namespaces=namespaces)
                    
                    start_date = datetime.fromisoformat(start_string).date() if start_string else None
                    finish_date = datetime.fromisoformat(finish_string).date() if finish_string else None
                    
                    duration_string = task.findtext('msp:Duration', namespaces=namespaces)
                    cost_string = task.findtext('msp:Cost', namespaces=namespaces) or "0"
                    
                    duration_formatted = format_duration_from_xml(duration_string)
                    cost_euros = float(cost_string) / 100.0 if cost_string else 0.0
                    
                    is_milestone_text = (task.findtext('msp:Milestone', namespaces=namespaces) or '0').lower()
                    is_milestone = is_milestone_text == '1' or is_milestone_text == 'true'
                    
                    wbs = task.findtext('msp:WBS', namespaces=namespaces) or ""
                    
                    total_slack_minutes_string = task.findtext('msp:TotalSlack', namespaces=namespaces) or "0"
                    
                    is_summary_string = task.findtext('msp:Summary', namespaces=namespaces) or '0'
                    is_summary = is_summary_string == '1'
                    
                    # Calcolo Slack
                    total_slack_days = 0
                    if total_slack_minutes_string:
                        try:
                            slack_minutes = float(total_slack_minutes_string)
                            # Recupera i minuti/giorno dalla sessione
                            minutes_per_day_from_session = st.session_state.get('minutes_per_day', 480) 
                            if minutes_per_day_from_session > 0: 
                                total_slack_days = math.ceil(slack_minutes / minutes_per_day_from_session)
                        except ValueError:
                            total_slack_days = 0

                    # Aggiunge il task alla lista per il DataFrame (tranne il riepilogo UID 0)
                    if uid != '0':
                        all_tasks_data_list.append({
                            "UID": uid, 
                            "Name": name, 
                            "Start": start_date, 
                            "Finish": finish_date, 
                            "Duration": duration_formatted, 
                            "Cost": cost_euros, 
                            "Milestone": is_milestone, 
                            "Summary": is_summary, # Campo chiave per la logica SIL
                            "WBS": wbs,             # Campo chiave per la logica SIL
                            "TotalSlackDays": total_slack_days
                        })

                    # --- Logica TUP/TUF (Milestones) ---
                    match = tup_tuf_pattern.search(name)
                    if match:
                        tup_tuf_key = match.group(0).upper().strip()
                        duration_string_tup = task.findtext('msp:Duration', namespaces=namespaces)
                        
                        try:
                            _duration_string = duration_string_tup
                            if _duration_string and _duration_string.startswith('T'): 
                                _duration_string = 'P' + _duration_string
                                
                            duration_object = isodate.parse_duration(_duration_string) if _duration_string and _duration_string.startswith('P') else timedelta()
                            duration_seconds = duration_object.total_seconds()
                            
                        except Exception: 
                            duration_seconds = 0
                            
                        is_pure_milestone_duration = (duration_seconds == 0)
                        
                        start_date_formatted = start_date.strftime("%d/%m/%Y") if start_date else "N/D"
                        finish_date_formatted = finish_date.strftime("%d/%m/%Y") if finish_date else "N/D"
                        
                        current_task_data = {
                            "Nome Completo": name, 
                            "Data Inizio": start_date_formatted, 
                            "Data Fine": finish_date_formatted, 
                            "Durata": duration_formatted, 
                            "DurataSecondi": duration_seconds, 
                            "DataInizioObj": start_date
                        }
                        
                        existing_duration_seconds = potential_milestones.get(tup_tuf_key, {}).get("DurataSecondi", -1)
                        
                        # Logica di sovrascrittura: preferisce attività con durata > 0
                        if tup_tuf_key not in potential_milestones:
                            potential_milestones[tup_tuf_key] = current_task_data
                        elif not is_pure_milestone_duration:
                            if existing_duration_seconds == 0:
                                potential_milestones[tup_tuf_key] = current_task_data
                            elif duration_seconds > existing_duration_seconds:
                                potential_milestones[tup_tuf_key] = current_task_data
                # --- FINE LOOP SUI TASK ---


                # Salvataggio dati TUP/TUF in sessione
                final_milestones_data = []
                for key in potential_milestones:
                    data = potential_milestones[key]
                    final_milestones_data.append({
                        "Nome Completo": data.get("Nome Completo", ""), 
                        "Data Inizio": data.get("Data Inizio", "N/D"),
                        "Data Fine": data.get("Data Fine", "N/D"), 
                        "Durata": data.get("Durata", "N/D"),
                        "DataInizioObj": data.get("DataInizioObj")
                    })
                    
                if final_milestones_data:
                    dataframe_milestones = pd.DataFrame(final_milestones_data)
                    minimum_date_for_sort = date.min
                    
                    dataframe_milestones['DataInizioObj'] = pd.to_datetime(dataframe_milestones['DataInizioObj'], errors='coerce').dt.date
                    dataframe_milestones['DataInizioObj'] = dataframe_milestones['DataInizioObj'].fillna(minimum_date_for_sort)
                    dataframe_milestones = dataframe_milestones.sort_values(by="DataInizioObj").reset_index(drop=True)
                    
                    # Salva il dataframe PRONTO per la visualizzazione
                    st.session_state['dataframe_milestones_display'] = dataframe_milestones.drop(columns=['DataInizioObj'])
                else: 
                    st.session_state['dataframe_milestones_display'] = None

                # Salvataggio TUTTE le attività in sessione
                st.session_state['all_tasks_dataframe'] = pd.DataFrame(all_tasks_data_list)
                
                # Debug (prime 50 righe)
                current_file_to_process.seek(0)
                debug_content_bytes = current_file_to_process.read(2000)
                try: 
                    st.session_state['debug_raw_text'] = '\n'.join(debug_content_bytes.decode('utf-8', errors='ignore').splitlines()[:50])
                except Exception as decode_error: 
                    st.session_state['debug_raw_text'] = f"Errore decodifica debug: {decode_error}"
                
                # Flag di successo
                st.session_state.file_processed_success = True
                st.rerun() # Ricarica l'app per mostrare i risultati

            except Exception as exception:
                st.error(f"Errore Analisi durante elaborazione iniziale: {exception}")
                st.error(f"Traceback: {traceback.format_exc()}")
                st.error("Verifica file XML.")
                st.session_state.file_processed_success = False


    # --- VISUALIZZAZIONE DATI E ANALISI AVANZATA ---
    # Questa sezione viene eseguita solo se il file è stato processato con successo
    
    if st.session_state.get('file_processed_success', False):
    
        # --- Sezione 2: Analisi Preliminare ---
        st.markdown("---"); st.markdown("#### 2. Analisi Preliminare"); st.markdown("##### 📄 Informazioni Generali dell'Appalto")
        
        project_name = st.session_state.get('project_name', "N/D")
        formatted_cost = st.session_state.get('formatted_cost', "N/D")
        
        column_1_display, column_2_display = st.columns(2)
        with column_1_display: 
            st.markdown(f"**Nome:** {project_name}")
        with column_2_display: 
            st.markdown(f"**Importo Totale Lavori:** {formatted_cost}")
            
        st.markdown("##### 🗓️ Termini Utili Contrattuali (TUP/TUF)")
        
        # Recupera il dataframe TUP/TUF dalla sessione
        dataframe_to_display = st.session_state.get('dataframe_milestones_display')
        
        if dataframe_to_display is not None and not dataframe_to_display.empty:
            st.dataframe(dataframe_to_display, use_container_width=True, hide_index=True)
            
            # Creazione bottone Download Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                dataframe_to_display.to_excel(writer, index=False, sheet_name='TerminiUtili')
            excel_data = output.getvalue()
            st.download_button(
                label="Scarica (Excel)", 
                data=excel_data, 
                file_name="termini_utili_TUP_TUF.xlsx", 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("Nessun Termine Utile (TUP o TUF) trovato nel file.")

        # --- Sezione 3: Selezione Periodo e Analisi ---
        st.markdown("---"); st.markdown("#### 3. Analisi Avanzata")
        
        default_start = st.session_state.get('project_start_date', date.today())
        default_finish = st.session_state.get('project_finish_date', date.today() + timedelta(days=365))
        
        # Ulteriore controllo validità date
        if not default_start: default_start = date.today()
        if not default_finish: default_finish = default_start + timedelta(days=365)
        if default_start > default_finish: default_finish = default_start + timedelta(days=1)
        
        st.markdown("##### 📅 Seleziona Periodo di Riferimento")
        st.caption(f"Default: {default_start.strftime('%d/%m/%Y')} - {default_finish.strftime('%d/%m/%Y')}.")
        
        column_date_1, column_date_2 = st.columns(2)
        with column_date_1:
            selected_start_date = st.date_input(
                "Data Inizio", 
                value=default_start, 
                min_value=default_start, 
                max_value=default_finish + timedelta(days=5*365), 
                format="DD/MM/YYYY", 
                key="start_date_selector"
            )
        with column_date_2:
            minimum_end_date = selected_start_date
            actual_default_finish = max(default_finish, minimum_end_date) # La fine default non può essere prima dell'inizio
            reasonable_max_date = actual_default_finish + timedelta(days=10*365)
            
            selected_finish_date = st.date_input(
                "Data Fine", 
                value=actual_default_finish, 
                min_value=minimum_end_date, 
                max_value=reasonable_max_date, 
                format="DD/MM/YYYY", 
                key="finish_date_selector"
            )

        # --- Analisi Dettagliate ---
        st.markdown("---"); st.markdown("##### 📊 Analisi Dettagliate")
        
        # Recupera il dataframe COMPLETO delle attività dalla sessione
        all_tasks_dataframe = st.session_state.get('all_tasks_dataframe')
        
        if st.button("📈 Avvia Analisi Curva S", key="analyze_scurve"):
            if all_tasks_dataframe is None or all_tasks_dataframe.empty:
                st.error("Errore: Dati delle attività non trovati. Impossibile calcolare la Curva S.")
            else:
                try:
                    # --- CURVA S (SIL) - NUOVA LOGICA ---
                    st.markdown("###### Curva S (Costo Cumulato - Stima Lineare con Logica WBS)")
                    
                    with st.spinner("Calcolo distribuzione costi (logica WBS)..."):
                        # Usa la NUOVA funzione per calcolare la distribuzione lineare
                        daily_cost_dataframe = calculate_linear_distribution(all_tasks_dataframe.copy()) # Passa una copia
                    
                    if not daily_cost_dataframe.empty:
                        # Converti le date selezionate in datetime per il filtro pandas
                        selected_start_datetime = datetime.combine(selected_start_date, datetime.min.time())
                        selected_finish_datetime = datetime.combine(selected_finish_date, datetime.max.time())
                        
                        # Filtra i costi giornalieri per il periodo selezionato
                        mask_cost = (daily_cost_dataframe['Date'] >= selected_start_datetime) & (daily_cost_dataframe['Date'] <= selected_finish_datetime)
                        filtered_cost = daily_cost_dataframe.loc[mask_cost]
                        
                        if not filtered_cost.empty:
                            # Raggruppa per Mese (ME = Month End)
                            monthly_cost = filtered_cost.set_index('Date').resample('ME')['Value'].sum().reset_index()
                            monthly_cost['Costo Cumulato (€)'] = monthly_cost['Value'].cumsum() # Calcola cumulato
                            monthly_cost['Mese'] = monthly_cost['Date'].dt.strftime('%Y-%m')
                            
                            st.markdown("###### Tabella Dati SIL Mensili Aggregati")
                            dataframe_display_sil = monthly_cost.copy()
                            dataframe_display_sil['Costo Mensile (€)'] = dataframe_display_sil['Value'].apply(lambda x: f"€ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                            dataframe_display_sil['Costo Cumulato (€)'] = dataframe_display_sil['Costo Cumulato (€)'].apply(lambda x: f"€ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                            
                            st.dataframe(dataframe_display_sil[['Mese', 'Costo Mensile (€)', 'Costo Cumulato (€)']], use_container_width=True, hide_index=True)
                            
                            st.markdown("###### Grafico Curva S")
                            figure_sil = go.Figure()
                            # Asse Y1: Barre Costo Mensile
                            figure_sil.add_trace(go.Bar(
                                x=monthly_cost['Mese'], 
                                y=monthly_cost['Value'], 
                                name='Costo Mensile'
                            ))
                            # Asse Y2: Linea Costo Cumulato
                            figure_sil.add_trace(go.Scatter(
                                x=monthly_cost['Mese'], 
                                y=monthly_cost['Costo Cumulato (€)'], 
                                name='Costo Cumulato', 
                                mode='lines+markers', 
                                yaxis='y2' # Assegna al secondo asse Y
                            ))
                            
                            figure_sil.update_layout(
                                title='Curva S - Costo Mensile e Cumulato (Stima Lineare)',
                                xaxis_title="Mese",
                                yaxis=dict(title="Costo Mensile (€)"),
                                yaxis2=dict(title="Costo Cumulato (€)", overlaying="y", side="right"),
                                legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
                            )
                            st.plotly_chart(figure_sil, use_container_width=True)
                            
                            # Download Excel per Dati SIL
                            output_sil = BytesIO()
                            with pd.ExcelWriter(output_sil, engine='openpyxl') as writer:
                                monthly_cost[['Mese', 'Value', 'Costo Cumulato (€)']].rename(columns={'Value': 'Costo Mensile (€)'}).to_excel(writer, index=False, sheet_name='SIL_Mensile')
                            excel_data_sil = output_sil.getvalue()
                            
                            st.download_button(
                                label="Scarica Dati SIL (Excel)", 
                                data=excel_data_sil, 
                                file_name="dati_sil_mensile.xlsx", 
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                                key="download_sil"
                            )

                            # --- DEBUG SUL COSTO TOTALE (BASATO SULLA NUOVA LOGICA) ---
                            st.markdown("---")
                            st.markdown("##### Diagnostica Dati Calcolati (Logica WBS)")
                            
                            debug_task_count = st.session_state.get('debug_task_count', 0)
                            st.write(f"**Numero attività usate per la distribuzione (WBS):** {debug_task_count}")
                            
                            debug_total_cost = st.session_state.get('debug_total_cost', 0)
                            formatted_debug_cost = f"€ {debug_total_cost:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                            st.write(f"**Costo Totale Calcolato (somma attività WBS valide):** {formatted_debug_cost}")
                            
                            st.caption(f"Questo totale (basato sul filtro WBS) dovrebbe ora corrispondere all'Importo Totale Lavori ({formatted_cost}).")
                            # --- FINE DEBUG ---

                        else:
                            st.warning("Nessun costo trovato nel periodo selezionato.")
                    else:
                        st.warning("Nessun costo trovato nel file per calcolare la Curva S (nessuna attività valida trovata dalla logica WBS).")
                
                except Exception as analysis_error:
                    st.error(f"Errore durante l'analisi avanzata: {analysis_error}")
                    st.error(traceback.format_exc())
            
        # --- Placeholder per Istogrammi ---
        st.markdown("---")
        st.markdown("###### Istogrammi Risorse")
        st.info("Logica istogrammi da implementare (richiederà dati 'Lavoro' e 'Risorse').")

        # --- Debug Section ---
        debug_text = st.session_state.get('debug_raw_text')
        if debug_text:
            st.markdown("---")
            with st.expander("🔍 Dati Grezzi per Debug (prime 50 righe del file)"):
                st.code(debug_text, language='xml')
