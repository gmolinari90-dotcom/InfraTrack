# --- v10.3 (Correzione SyntaxError in px.bar) ---
import streamlit as st
from lxml import etree
import pandas as pd
from datetime import datetime, date, timedelta
import re
import isodate
from io import BytesIO
import math
import plotly.express as px
import traceback # Per debug avanzato

# --- CONFIGURAZIONE DELLA PAGINA ---
st.set_page_config(page_title="InfraTrack v10.3", page_icon="🚆", layout="wide") # Version updated

# --- CSS ---
# ... (CSS Identico a v10.2 - omesso per brevità) ...
st.markdown("""
<style>
    /* ... */
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
st.markdown("## 🚆 InfraTrack v10.3") # Version updated
st.caption("La tua centrale di controllo per progetti infrastrutturali")

# --- GESTIONE RESET ---
# ... (Identico a v10.2) ...
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
# ... (Identico a v10.2) ...
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
# ... (Identiche a v10.2) ...
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

def parse_timephased_data(assignments_node, ns, data_type, unit_conversion=1.0, is_cost=False):
    # ... (Identica a v10.2) ...
    data = []
    if assignments_node is None: return pd.DataFrame(data)
    for assignment in assignments_node.findall('msp:Assignment', ns):
        task_uid = assignment.findtext('msp:TaskUID', namespaces=ns); resource_uid = assignment.findtext('msp:ResourceUID', namespaces=ns)
        baseline_data = assignment.find(f"msp:TimephasedData[msp:Type='{data_type}']", ns)
        if baseline_data is not None:
            for period in baseline_data.findall('msp:Value', ns):
                try:
                    start_str = period.findtext('msp:Start', namespaces=ns); finish_str = period.findtext('msp:Finish', namespaces=ns); value_str = period.findtext('msp:Value', namespaces=ns)
                    if start_str and value_str:
                        start_date = datetime.fromisoformat(start_str).date(); value = 0
                        if is_cost: value = float(value_str) / 100.0
                        else: duration_obj = isodate.parse_duration(value_str); value = duration_obj.total_seconds() / 3600
                        value *= unit_conversion
                        data.append({'TaskUID': task_uid, 'ResourceUID': resource_uid, 'Date': start_date, 'Value': value})
                except Exception as e: continue
    return pd.DataFrame(data)


# --- INIZIO ANALISI ---
current_file_to_process = st.session_state.get('uploaded_file_state')

if current_file_to_process is not None:
    if not st.session_state.get('file_processed_success', False):
        with st.spinner('Caricamento e analisi completa del file in corso...'):
            try:
                # ... (Logica parsing e estrazione dati identica a v10.2, incluso calcolo slack corretto) ...
                current_file_to_process.seek(0); file_content_bytes = current_file_to_process.read()
                parser = etree.XMLParser(recover=True); tree = etree.fromstring(file_content_bytes, parser=parser)
                ns = {'msp': 'http://schemas.microsoft.com/project'}
                minutes_per_day = 480; #... (calcolo minutes_per_day omesso) ...
                st.session_state['minutes_per_day'] = minutes_per_day
                task_uid_1 = tree.find(".//msp:Task[msp:UID='1']", namespaces=ns)
                if task_uid_1 is not None: # ... (estrazione nome/costo/date progetto omessa) ...
                    project_name = task_uid_1.findtext('msp:Name', namespaces=ns) or "N/D"; #...
                if not project_start_date: project_start_date = date.today() # ... (Fallback date) ...
                st.session_state['project_name'] = project_name; st.session_state['formatted_cost'] = formatted_cost
                st.session_state['project_start_date'] = project_start_date; st.session_state['project_finish_date'] = project_finish_date
                potential_milestones = {}; all_tasks = tree.findall('.//msp:Task', namespaces=ns)
                tup_tuf_pattern = re.compile(r'(?i)(TUP|TUF)\s*\d*'); all_tasks_data_list = []
                for task in all_tasks:
                    # ... (Estrazione dati base attività come v10.2) ...
                    uid = task.findtext('msp:UID', namespaces=ns); #...
                    total_slack_minutes_str = task.findtext('msp:TotalSlack', namespaces=ns) or "0"
                    total_slack_days = 0
                    if total_slack_minutes_str:
                        try: # Blocco try
                            slack_minutes = float(total_slack_minutes_str)
                            mpd = st.session_state.get('minutes_per_day', 480)
                            if mpd > 0: total_slack_days = math.ceil(slack_minutes / mpd)
                        except ValueError: # Blocco except
                            total_slack_days = 0
                    if uid != '0': all_tasks_data_list.append({...}) # Omissis
                    match = tup_tuf_pattern.search(name)
                    if match:
                         # ... (Logica TUP/TUF corretta, omessa per brevità) ...
                         current_task_data = {...}
                         if tup_tuf_key not in potential_milestones: #...
                         elif not is_pure_milestone_duration: #...
                              elif duration_seconds > existing_duration_seconds:
                                   potential_milestones[tup_tuf_key] = current_task_data
                final_milestones_data = [] # ... (omissis)
                if final_milestones_data: # ... (omissis)
                    st.session_state['df_milestones_display'] = df_milestones.drop(columns=['DataInizioObj'])
                else: st.session_state['df_milestones_display'] = None
                st.session_state['all_tasks_data'] = pd.DataFrame(all_tasks_data_list)
                # ... (Estrazione Timephased e Resources identica a v10.2) ...
                assignments_node = tree.find('msp:Assignments', ns)
                st.session_state['baseline_cost_data'] = parse_timephased_data(assignments_node, ns, '9', is_cost=True)
                st.session_state['baseline_work_data'] = parse_timephased_data(assignments_node, ns, '8', is_cost=False)
                resources_node = tree.find('msp:Resources', ns); resources_data = []
                if resources_node is not None: #... (omissis loop risorse) ...
                st.session_state['resources_data'] = pd.DataFrame(resources_data)
                # ... (Debug text e rerun identici a v10.2) ...
                current_file_to_process.seek(0); debug_content_bytes = current_file_to_process.read(2000);
                try: st.session_state['debug_raw_text'] = '\n'.join(debug_content_bytes.decode('utf-8', errors='ignore').splitlines()[:50])
                except Exception as decode_err: st.session_state['debug_raw_text'] = f"Errore decodifica debug: {decode_err}"
                st.session_state.file_processed_success = True
                st.rerun()

            except etree.XMLSyntaxError as e: st.error(f"Errore Sintassi XML: {e}"); st.error("File malformato?"); st.session_state.file_processed_success = False;
            except KeyError as ke: st.error(f"Errore interno: Chiave mancante {ke}"); st.error("Problema estrazione dati."); st.session_state.file_processed_success = False;
            except Exception as e: st.error(f"Errore Analisi durante elaborazione iniziale: {e}"); st.error(f"Traceback: {traceback.format_exc()}"); st.error("Verifica file XML."); st.session_state.file_processed_success = False;


    # --- VISUALIZZAZIONE DATI E ANALISI AVANZATA ---
    if st.session_state.get('file_processed_success', False):
        # --- Sezione 2: Analisi Preliminare (Identica a v10.2) ---
        st.markdown("---"); st.markdown("#### 2. Analisi Preliminare"); st.markdown("##### 📄 Informazioni Generali dell'Appalto")
        project_name = st.session_state.get('project_name', "N/D"); formatted_cost = st.session_state.get('formatted_cost', "N/D")
        col1_disp, col2_disp = st.columns(2); with col1_disp: st.markdown(f"**Nome:** {project_name}"); with col2_disp: st.markdown(f"**Importo Totale Lavori:** {formatted_cost}")
        st.markdown("##### 🗓️ Termini Utili Contrattuali (TUP/TUF)")
        df_display = st.session_state.get('df_milestones_display')
        if df_display is not None and not df_display.empty: #... (dataframe + download) ...
        else: st.warning("Nessun Termine Utile (TUP o TUF) trovato nel file.")

        # --- Sezione 3: Selezione Periodo e Analisi (Identica a v10.2) ---
        st.markdown("---"); st.markdown("#### 3. Analisi Avanzata")
        default_start = st.session_state.get('project_start_date', date.today()); default_finish = st.session_state.get('project_finish_date', date.today() + timedelta(days=365))
        # ... (Logica date default e date_input identica) ...
        st.markdown("##### 📅 Seleziona Periodo di Riferimento"); st.caption(f"Default: {default_start.strftime('%d/%m/%Y')} - {default_finish.strftime('%d/%m/%Y')}.")
        col_date1, col_date2 = st.columns(2); # ... (date_input widgets) ...
        st.markdown("---"); st.markdown("##### 📊 Analisi Dettagliate")
        baseline_cost_df = st.session_state.get('baseline_cost_data'); baseline_work_df = st.session_state.get('baseline_work_data'); resources_df = st.session_state.get('resources_data')
        all_tasks_df = st.session_state.get('all_tasks_data')

        if baseline_cost_df is None or baseline_work_df is None or resources_df is None:
             st.error("Errore: Dati temporizzati o dati risorse non trovati. Il file XML potrebbe essere incompleto.")
        else:
            try:
                # --- CURVA S (SIL) ---
                st.markdown("###### Curva S (SIL - Costo Cumulato Baseline)")
                if not baseline_cost_df.empty:
                    cost_df_dated = baseline_cost_df.copy(); cost_df_dated['Date'] = pd.to_datetime(cost_df_dated['Date'])
                    mask_cost = (cost_df_dated['Date'] >= pd.to_datetime(selected_start_date)) & (cost_df_dated['Date'] <= pd.to_datetime(selected_finish_date))
                    filtered_cost = cost_df_dated.loc[mask_cost]
                    if not filtered_cost.empty:
                        monthly_cost = filtered_cost.set_index('Date').resample('ME')['Value'].sum().reset_index()
                        monthly_cost['Costo Cumulato (€)'] = monthly_cost['Value'].cumsum()
                        monthly_cost['Mese'] = monthly_cost['Date'].dt.strftime('%Y-%m')
                        
                        # --- CORREZIONE SYNTAX ERROR ---
                        fig_sil = px.line(monthly_cost, x='Mese', y='Costo Cumulato (€)',
                                          title='Curva S - Costo Cumulato Baseline', markers=True)
                        st.plotly_chart(fig_sil, use_container_width=True)
                        # --- FINE CORREZIONE ---
                        
                        output_sil = BytesIO(); #... (download) ...; st.download_button(label="Scarica Dati SIL (Excel)", ...)
                    else: st.warning("Nessun dato di costo baseline trovato nel periodo selezionato.")
                else: st.warning("Nessun dato di costo baseline trovato nel file.")


                # --- ISTOGRAMMI MANODOPERA E MEZZI ---
                st.markdown("###### Istogrammi Risorse (Ore Lavoro Baseline)")
                if not baseline_work_df.empty and not resources_df.empty:
                    work_df_dated = baseline_work_df.copy(); work_df_dated['Date'] = pd.to_datetime(work_df_dated['Date'])
                    mask_work = (work_df_dated['Date'] >= pd.to_datetime(selected_start_date)) & (work_df_dated['Date'] <= pd.to_datetime(selected_finish_date))
                    filtered_work = work_df_dated.loc[mask_work]
                    if not filtered_work.empty:
                         work_with_resources = pd.merge(filtered_work, resources_df, on='ResourceUID', how='left')
                         monthly_work = work_with_resources.set_index('Date').groupby([pd.Grouper(freq='ME'), 'ResourceType'])['Value'].sum().reset_index(); monthly_work['Mese'] = monthly_work['Date'].dt.strftime('%Y-%m')
                         manodopera_df = monthly_work[monthly_work['ResourceType'] == 'Manodopera']; mezzi_df = monthly_work[monthly_work['ResourceType'] == 'Mezzo/Materiale']
                         
                         if not manodopera_df.empty:
                             # --- CORREZIONE SYNTAX ERROR ---
                             fig_manodopera = px.bar(manodopera_df, x='Mese', y='Value', title='Istogramma Manodopera (Ore Baseline)')
                             st.plotly_chart(fig_manodopera, use_container_width=True)
                             # --- FINE CORREZIONE ---
                             output_mano = BytesIO(); #... (download) ...; st.download_button(label="Scarica Dati Manodopera (Excel)", ...)
                         else: st.warning("Nessun dato manodopera baseline nel periodo.")
                         
                         if not mezzi_df.empty:
                             # --- CORREZIONE SYNTAX ERROR ---
                             fig_mezzi = px.bar(mezzi_df, x='Mese', y='Value', title='Istogramma Mezzi/Materiali (Ore/Unità Baseline)')
                             st.plotly_chart(fig_mezzi, use_container_width=True)
                             # --- FINE CORREZIONE ---
                             output_mezzi = BytesIO(); #... (download) ...; st.download_button(label="Scarica Dati Mezzi (Excel)", ...)
                         else: st.warning("Nessun dato mezzi/materiali baseline nel periodo.")
                    else: st.warning("Nessun dato di lavoro baseline trovato nel periodo selezionato.")
                else: st.warning("Nessun dato di lavoro baseline trovato nel file o risorse non definite.")

            except Exception as analysis_error:
                st.error(f"Errore durante l'analisi avanzata: {analysis_error}")
                # st.error(traceback.format_exc()) # Uncomment for detailed error

        # --- Debug Section ---
        # ... (Identica a v10.2) ...
        debug_text = st.session_state.get('debug_raw_text')
        if debug_text: st.markdown("---"); #...
