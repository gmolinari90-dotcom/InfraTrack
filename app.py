# --- v11.0 (Logica Estrazione SIL/Risorse Corretta) ---
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
st.set_page_config(page_title="InfraTrack v11.0", page_icon="🚆", layout="wide") # Version updated

# --- CSS ---
# ... (CSS Identico - omesso per brevità) ...
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
st.markdown("## 🚆 InfraTrack v11.0") # Version updated
st.caption("La tua centrale di controllo per progetti infrastrutturali")

# --- GESTIONE RESET ---
# ... (Identico a v10.4) ...
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
# ... (Identico a v10.4) ...
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
def format_duration_from_xml(duration_str):
    # ... (Identica a v10.4) ...
    mpd = st.session_state.get('minutes_per_day', 480)
    if not duration_str or mpd <= 0: return "0g"
    try:
        if duration_str.startswith('T'): duration_str = 'P' + duration_str
        elif not duration_str.startswith('P'): return "N/D"
        duration = isodate.parse_duration(duration_str); total_hours = duration.total_seconds() / 3600
        if total_hours == 0: return "0g"
        work_days = total_hours / (mpd / 60.0); return f"{round(work_days)}g"
    except Exception: return "N/D"

# --- FUNZIONE DI ESTRAZIONE DATI TEMPORIZZATI CORRETTA ---
def parse_timephased_data_from_assignments(assignments_node, ns, data_type, is_cost=False):
    """
    Estrae dati timephased (Lavoro o Costo) dal NODO ASSIGNMENTS.
    data_type: '1' (Lavoro), '2' (Costo), '8' (Lavoro Baseline), '9' (Costo Baseline)
    """
    data = []
    if assignments_node is None:
        #st.warning("Nodo <Assignments> non trovato nel file XML.") # Debug
        return pd.DataFrame(data, columns=['TaskUID', 'ResourceUID', 'Date', 'Value'])

    for assignment in assignments_node.findall('msp:Assignment', ns):
        task_uid = assignment.findtext('msp:TaskUID', namespaces=ns)
        resource_uid = assignment.findtext('msp:ResourceUID', namespaces=ns)
        
        # Cerca il blocco TimephasedData per il tipo specificato
        timephased_data_block = assignment.find(f"msp:TimephasedData[msp:Type='{data_type}']", ns)
        
        if timephased_data_block is not None:
            for period in timephased_data_block.findall('msp:Value', ns):
                try:
                    start_str = period.findtext('msp:Start', namespaces=ns)
                    value_str = period.findtext('msp:Value', namespaces=ns)

                    if start_str and value_str and value_str != "0":
                        start_date = datetime.fromisoformat(start_str).date()
                        value = 0.0
                        
                        if is_cost:
                            value = float(value_str) / 100.0 # Costo è in centesimi
                        else: # È Lavoro
                            duration_obj = isodate.parse_duration(value_str) # Lavoro è in formato PT...H...M...S
                            value = duration_obj.total_seconds() / 3600 # Converti in ore
                        
                        if value > 0:
                            data.append({
                                'TaskUID': task_uid,
                                'ResourceUID': resource_uid,
                                'Date': start_date, # Data di inizio del periodo (di solito giornaliero)
                                'Value': value
                            })
                except Exception as e:
                    # st.warning(f"Skipping invalid timephased data: {e} | Valore: {value_str}") # Debug
                    continue
                    
    if not data:
        #st.warning(f"Nessun dato Timephased di Tipo '{data_type}' trovato in <Assignments>.") # Debug
        return pd.DataFrame(data, columns=['TaskUID', 'ResourceUID', 'Date', 'Value'])

    return pd.DataFrame(data)
# --- FINE FUNZIONE CORRETTA ---


# --- INIZIO ANALISI ---
current_file_to_process = st.session_state.get('uploaded_file_state')

if current_file_to_process is not None:
    if not st.session_state.get('file_processed_success', False):
        with st.spinner('Caricamento e analisi completa del file in corso...'):
            try:
                current_file_to_process.seek(0); file_content_bytes = current_file_to_process.read()
                parser = etree.XMLParser(recover=True); tree = etree.fromstring(file_content_bytes, parser=parser)
                ns = {'msp': 'http://schemas.microsoft.com/project'}

                # Calcolo minutes_per_day (Identico a v10.4)
                minutes_per_day = 480; #... (omesso per brevità) ...
                st.session_state['minutes_per_day'] = minutes_per_day

                # Estrazione dati UID 1 (Identico a v10.4)
                project_name = "N/D"; formatted_cost = "€ 0,00"; project_start_date = None; project_finish_date = None
                task_uid_1 = tree.find(".//msp:Task[msp:UID='1']", namespaces=ns)
                # ... (Omissis estrazione nome/costo/date) ...
                st.session_state['project_name'] = project_name; st.session_state['formatted_cost'] = formatted_cost
                st.session_state['project_start_date'] = project_start_date; st.session_state['project_finish_date'] = project_finish_date

                # --- Estrazione Dati Attività e TUP/TUF (CON SINTASSI CORRETTA) ---
                potential_milestones = {}; all_tasks = tree.findall('.//msp:Task', namespaces=ns)
                tup_tuf_pattern = re.compile(r'(?i)(TUP|TUF)\s*\d*'); all_tasks_data_list = []

                for task in all_tasks:
                    # ... (Estrazione dati base attività come v10.4) ...
                    uid = task.findtext('msp:UID', namespaces=ns); name = task.findtext('msp:Name', namespaces=ns) or "";
                    start_date = datetime.fromisoformat(start_str).date() if start_str else None; finish_date = datetime.fromisoformat(finish_str).date() if finish_str else None
                    duration_formatted = format_duration_from_xml(duration_str) #...
                    total_slack_days = 0
                    if total_slack_minutes_str:
                        try: # Blocco try/except corretto
                            slack_minutes = float(total_slack_minutes_str)
                            mpd = st.session_state.get('minutes_per_day', 480)
                            if mpd > 0: total_slack_days = math.ceil(slack_minutes / mpd)
                        except ValueError:
                            total_slack_days = 0

                    if uid != '0':
                         all_tasks_data_list.append({...}) # Omissis

                    # Logica TUP/TUF (indentazione corretta)
                    match = tup_tuf_pattern.search(name)
                    if match:
                         # ... (omessa per brevità) ...
                         current_task_data = {...}
                         if tup_tuf_key not in potential_milestones:
                              potential_milestones[tup_tuf_key] = current_task_data
                         elif not is_pure_milestone_duration:
                              if existing_duration_seconds == 0:
                                   potential_milestones[tup_tuf_key] = current_task_data
                              elif duration_seconds > existing_duration_seconds:
                                   potential_milestones[tup_tuf_key] = current_task_data

                # Salvataggio dati TUP/TUF
                final_milestones_data = [] # ... (omissis)
                if final_milestones_data: # ... (omissis)
                    st.session_state['df_milestones_display'] = df_milestones.drop(columns=['DataInizioObj'])
                else: st.session_state['df_milestones_display'] = None

                # Salvataggio TUTTE le attività
                st.session_state['all_tasks_data'] = pd.DataFrame(all_tasks_data_list)

                # --- ESTRAZIONE DATI TEMPORIZZATI CORRETTA ---
                assignments_node = tree.find('msp:Assignments', ns)
                
                # 1. Cerca Costo Baseline (Type 9) per SIL
                baseline_cost_data = parse_timephased_data_from_assignments(assignments_node, ns, '9', is_cost=True)
                if baseline_cost_data.empty:
                    # 2. Fallback: Cerca Costo Schedulato (Type 2) per SIL
                    st.warning("Dati 'Costo Baseline' (Tipo 9) non trovati. Fallback su 'Costo Schedulato' (Tipo 2) per la Curva S.")
                    baseline_cost_data = parse_timephased_data_from_assignments(assignments_node, ns, '2', is_cost=True)
                st.session_state['scurve_data'] = baseline_cost_data # Salva i dati SIL
                
                # 3. Cerca Lavoro Baseline (Type 8) per Istogrammi
                baseline_work_data = parse_timephased_data_from_assignments(assignments_node, ns, '8', is_cost=False)
                if baseline_work_data.empty:
                     # 4. Fallback: Cerca Lavoro Schedulato (Type 1) per Istogrammi
                     st.warning("Dati 'Lavoro Baseline' (Tipo 8) non trovati. Fallback su 'Lavoro Schedulato' (Tipo 1) per gli Istogrammi.")
                     baseline_work_data = parse_timephased_data_from_assignments(assignments_node, ns, '1', is_cost=False)
                st.session_state['baseline_work_data'] = baseline_work_data
                # --- FINE ESTRAZIONE DATI TEMPORIZZATI ---

                # Estrazione Dati Risorse (Invariato)
                resources_node = tree.find('msp:Resources', ns); resources_data = []
                if resources_node is not None:
                    for resource in resources_node.findall('msp:Resource', ns):
                        res_uid = resource.findtext('msp:UID', namespaces=ns)
                        res_name = resource.findtext('msp:Name', namespaces=ns) or "Senza Nome"
                        res_type_num = resource.findtext('msp:Type', namespaces=ns)
                        # Tipo 1 = Work (Manodopera), 0 = Material (Mezzo/Materiale)
                        res_type = "Manodopera" if res_type_num == '1' else "Mezzo/Materiale"
                        resources_data.append({'ResourceUID': res_uid, 'ResourceName': res_name, 'ResourceType': res_type})
                st.session_state['resources_data'] = pd.DataFrame(resources_data)

                # Debug
                current_file_to_process.seek(0); debug_content_bytes = current_file_to_process.read(2000);
                try: st.session_state['debug_raw_text'] = '\n'.join(debug_content_bytes.decode('utf-8', errors='ignore').splitlines()[:50])
                except Exception as decode_err: st.session_state['debug_raw_text'] = f"Errore decodifica debug: {decode_err}"
                
                st.session_state.file_processed_success = True
                st.rerun()

            # --- Gestione Errori ---
            except etree.XMLSyntaxError as e: st.error(f"Errore Sintassi XML: {e}"); st.error("File malformato?"); st.session_state.file_processed_success = False;
            except KeyError as ke: st.error(f"Errore interno: Chiave mancante {ke}"); st.error("Problema estrazione dati."); st.session_state.file_processed_success = False;
            except Exception as e: st.error(f"Errore Analisi durante elaborazione iniziale: {e}"); st.error(f"Traceback: {traceback.format_exc()}"); st.error("Verifica file XML."); st.session_state.file_processed_success = False;


    # --- VISUALIZZAZIONE DATI E ANALISI AVANZATA ---
    if st.session_state.get('file_processed_success', False):
        # --- Sezione 2: Analisi Preliminare (Identica) ---
        st.markdown("---"); st.markdown("#### 2. Analisi Preliminare"); st.markdown("##### 📄 Informazioni Generali dell'Appalto")
        project_name = st.session_state.get('project_name', "N/D"); formatted_cost = st.session_state.get('formatted_cost', "N/D")
        col1_disp, col2_disp = st.columns(2); with col1_disp: st.markdown(f"**Nome:** {project_name}"); with col2_disp: st.markdown(f"**Importo Totale Lavori:** {formatted_cost}")
        st.markdown("##### 🗓️ Termini Utili Contrattuali (TUP/TUF)")
        df_display = st.session_state.get('df_milestones_display')
        if df_display is not None and not df_display.empty:
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            # ... (download excel omesso per brevità) ...
        else: st.warning("Nessun Termine Utile (TUP o TUF) trovato nel file.")

        # --- Sezione 3: Selezione Periodo e Analisi ---
        st.markdown("---"); st.markdown("#### 3. Analisi Avanzata")
        default_start = st.session_state.get('project_start_date', date.today()); default_finish = st.session_state.get('project_finish_date', date.today() + timedelta(days=365))
        # ... (Logica date default e date_input identica) ...
        st.markdown("##### 📅 Seleziona Periodo di Riferimento"); st.caption(f"Default: {default_start.strftime('%d/%m/%Y')} - {default_finish.strftime('%d/%m/%Y')}.")
        col_date1, col_date2 = st.columns(2); # ... (date_input widgets) ...
        with col_date1: selected_start_date = st.date_input("Data Inizio", value=default_start, min_value=default_start, max_value=default_finish + timedelta(days=5*365), format="DD/MM/YYYY", key="start_date_selector")
        with col_date2:
            min_end_date = selected_start_date; actual_default_finish = max(default_finish, min_end_date)
            reasonable_max_date = actual_default_finish + timedelta(days=10*365)
            selected_finish_date = st.date_input("Data Fine", value=actual_default_finish, min_value=min_end_date, max_value=reasonable_max_date, format="DD/MM/YYYY", key="finish_date_selector")

        # --- Analisi Dettagliate ---
        st.markdown("---"); st.markdown("##### 📊 Analisi Dettagliate")
        
        # --- MODIFICA: Usa 'scurve_data' per SIL ---
        scurve_df = st.session_state.get('scurve_data')
        baseline_work_df = st.session_state.get('baseline_work_data')
        resources_df = st.session_state.get('resources_data')
        all_tasks_df = st.session_state.get('all_tasks_data')

        if scurve_df is None or baseline_work_df is None or resources_df is None:
             st.error("Errore: Dati temporizzati o dati risorse non trovati. Il file XML potrebbe essere incompleto.")
        else:
            try:
                # --- CURVA S (SIL) ---
                st.markdown("###### Curva S (Costo Cumulato)")
                if not scurve_df.empty:
                    cost_df_dated = scurve_df.copy() # Usa il nuovo DataFrame
                    cost_df_dated['Date'] = pd.to_datetime(cost_df_dated['Date'])
                    mask_cost = (cost_df_dated['Date'] >= pd.to_datetime(selected_start_date)) & (cost_df_dated['Date'] <= pd.to_datetime(selected_finish_date))
                    filtered_cost = cost_df_dated.loc[mask_cost]
                    
                    if not filtered_cost.empty:
                        # Aggrega i costi da TUTTE le attività per mese
                        monthly_cost = filtered_cost.set_index('Date').resample('ME')['Value'].sum().reset_index()
                        monthly_cost['Costo Cumulato (€)'] = monthly_cost['Value'].cumsum()
                        monthly_cost['Mese'] = monthly_cost['Date'].dt.strftime('%Y-%m')
                        
                        fig_sil = px.line(monthly_cost, x='Mese', y='Costo Cumulato (€)',
                                          title='Curva S - Costo Cumulato (Baseline o Schedulato)', markers=True)
                        fig_sil.update_layout(xaxis_title="Mese", yaxis_title="Costo Cumulato (€)")
                        st.plotly_chart(fig_sil, use_container_width=True)
                        
                        output_sil = BytesIO()
                        with pd.ExcelWriter(output_sil, engine='openpyxl') as writer:
                             monthly_cost[['Mese', 'Value', 'Costo Cumulato (€)']].rename(columns={'Value': 'Costo Mensile (€)'}).to_excel(writer, index=False, sheet_name='SIL_Mensile')
                        excel_data_sil = output_sil.getvalue()
                        st.download_button(label="Scarica Dati SIL (Excel)", data=excel_data_sil, file_name="dati_sil_mensile.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="download_sil")
                    else: st.warning("Nessun dato di costo trovato nel periodo selezionato.")
                else: st.warning("Nessun dato di costo temporizzato (Baseline o Schedulato) trovato nel file.")


                # --- ISTOGRAMMI MANODOPERA E MEZZI (Logica invariata) ---
                st.markdown("###### Istogrammi Risorse (Ore Lavoro Baseline)")
                if not baseline_work_df.empty and not resources_df.empty:
                    # ... (Logica Istogrammi identica a v10.3) ...
                    work_df_dated = baseline_work_df.copy(); work_df_dated['Date'] = pd.to_datetime(work_df_dated['Date'])
                    mask_work = (work_df_dated['Date'] >= pd.to_datetime(selected_start_date)) & (work_df_dated['Date'] <= pd.to_datetime(selected_finish_date))
                    filtered_work = work_df_dated.loc[mask_work]
                    if not filtered_work.empty:
                         work_with_resources = pd.merge(filtered_work, resources_df, on='ResourceUID', how='left')
                         monthly_work = work_with_resources.set_index('Date').groupby([pd.Grouper(freq='ME'), 'ResourceType'])['Value'].sum().reset_index(); monthly_work['Mese'] = monthly_work['Date'].dt.strftime('%Y-%m')
                         manodopera_df = monthly_work[monthly_work['ResourceType'] == 'Manodopera']; mezzi_df = monthly_work[monthly_work['ResourceType'] == 'Mezzo/Materiale']
                         if not manodopera_df.empty:
                             fig_manodopera = px.bar(manodopera_df, x='Mese', y='Value', title='Istogramma Manodopera (Ore Baseline)')
                             st.plotly_chart(fig_manodopera, use_container_width=True)
                             output_mano = BytesIO(); #... (download) ...; st.download_button(label="Scarica Dati Manodopera (Excel)", ...)
                         else: st.warning("Nessun dato manodopera baseline nel periodo.")
                         if not mezzi_df.empty:
                             fig_mezzi = px.bar(mezzi_df, x='Mese', y='Value', title='Istogramma Mezzi/Materiali (Ore/Unità Baseline)')
                             st.plotly_chart(fig_mezzi, use_container_width=True)
                             output_mezzi = BytesIO(); #... (download) ...; st.download_button(label="Scarica Dati Mezzi (Excel)", ...)
                         else: st.warning("Nessun dato mezzi/materiali baseline nel periodo.")
                    else: st.warning("Nessun dato di lavoro baseline trovato nel periodo selezionato.")
                else: st.warning("Nessun dato di lavoro baseline trovato nel file o risorse non definite.")

            except Exception as analysis_error:
                st.error(f"Errore durante l'analisi avanzata: {analysis_error}")
                # st.error(traceback.format_exc()) # Uncomment for detailed error

        # --- Debug Section ---
        debug_text = st.session_state.get('debug_raw_text')
        if debug_text:
            st.markdown("---")
            with st.expander("🔍 Dati Grezzi per Debug (prime 50 righe del file)"):
                st.code(debug_text, language='xml')
