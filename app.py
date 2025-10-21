# --- v12.0 (Nuova Logica Calcolo SIL) ---
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
st.set_page_config(page_title="InfraTrack v12.0", page_icon="🚆", layout="wide") # Version updated

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
st.markdown("## 🚆 InfraTrack v12.0") # Version updated
st.caption("La tua centrale di controllo per progetti infrastrutturali")

# --- GESTIONE RESET ---
# ... (Identico a v11.6) ...
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
# ... (Identico a v11.6) ...
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
    # ... (Identica, omessa per brevità) ...
    minutes_per_day = 480
    try: #...
        if default_calendar is not None: #...
             if working_day is not None: #...
                  working_minutes = 0
                  for working_time in working_day.findall(".//msp:WorkingTime", namespaces=_ns): #...
                       if from_time_str and to_time_str: #...
                            try: #...
                                 working_minutes += delta.total_seconds() / 60
                            except ValueError: pass
                  if working_minutes > 0: minutes_per_day = working_minutes
    except Exception: pass
    return minutes_per_day

def format_duration_from_xml(duration_str):
     # ... (Identica, omessa per brevità) ...
     mpd = st.session_state.get('minutes_per_day', 480)
     if not duration_str or mpd <= 0: return "0g"
     try: #...
        work_days = total_hours / (mpd / 60.0); return f"{round(work_days)}g"
     except Exception: return "N/D"

# --- NUOVA FUNZIONE PER CALCOLARE SIL DA DATI TASK ---
@st.cache_data
def calculate_linear_scurve(tasks_df):
    """
    Calcola la distribuzione giornaliera dei costi assumendo una distribuzione lineare.
    Input: DataFrame all_tasks_data.
    Output: DataFrame [Date, Value (Costo giornaliero)]
    """
    daily_cost_data = []
    
    # Assicurati che le date siano nel formato corretto (potrebbero essere già oggetti date)
    tasks_df['Start'] = pd.to_datetime(tasks_df['Start'], errors='coerce').dt.date
    tasks_df['Finish'] = pd.to_datetime(tasks_df['Finish'], errors='coerce').dt.date
    
    # Filtra attività senza date o costo
    tasks_df = tasks_df.dropna(subset=['Start', 'Finish', 'Cost'])
    tasks_df = tasks_df[tasks_df['Cost'] > 0]

    for _, task in tasks_df.iterrows():
        start_date = task['Start']
        finish_date = task['Finish']
        total_cost = task['Cost']
        
        # Calcola la durata in giorni
        duration_days = (finish_date - start_date).days + 1
        
        if duration_days > 0 and total_cost > 0:
            cost_per_day = total_cost / duration_days
            
            # Genera un range di date e assegna il costo giornaliero
            for i in range(duration_days):
                current_date = start_date + timedelta(days=i)
                daily_cost_data.append({'Date': current_date, 'Value': cost_per_day})

    if not daily_cost_data:
        return pd.DataFrame(columns=['Date', 'Value'])

    # Raggruppa e somma i costi per giorno (se più attività cadono nello stesso giorno)
    daily_df = pd.DataFrame(daily_cost_data)
    daily_df['Date'] = pd.to_datetime(daily_df['Date'])
    aggregated_daily_df = daily_df.groupby('Date')['Value'].sum().reset_index()
    
    return aggregated_daily_df
# --- FINE NUOVA FUNZIONE ---


# --- INIZIO ANALISI ---
current_file_to_process = st.session_state.get('uploaded_file_state')

if current_file_to_process is not None:
    if not st.session_state.get('file_processed_success', False):
        with st.spinner('Caricamento e analisi completa del file in corso...'):
            try:
                current_file_to_process.seek(0); file_content_bytes = current_file_to_process.read()
                parser = etree.XMLParser(recover=True); tree = etree.fromstring(file_content_bytes, parser=parser)
                ns = {'msp': 'http://schemas.microsoft.com/project'}

                minutes_per_day = get_minutes_per_day(tree, ns)
                st.session_state['minutes_per_day'] = minutes_per_day

                # Inizializza variabili
                project_name = "N/D"; formatted_cost = "€ 0,00"; project_start_date = None; project_finish_date = None
                task_uid_1 = tree.find(".//msp:Task[msp:UID='1']", namespaces=ns)
                if task_uid_1 is not None:
                    # ... (Estrazione dati UID 1) ...
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

                # --- Estrazione Dati Attività e TUP/TUF ---
                potential_milestones = {}; all_tasks = tree.findall('.//msp:Task', namespaces=ns)
                tup_tuf_pattern = re.compile(r'(?i)(TUP|TUF)\s*\d*'); all_tasks_data_list = []

                for task in all_tasks:
                    uid = task.findtext('msp:UID', namespaces=ns); name = task.findtext('msp:Name', namespaces=ns) or "";
                    start_str = task.findtext('msp:Start', namespaces=ns); finish_str = task.findtext('msp:Finish', namespaces=ns);
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
                            if mpd > 0: total_slack_days = math.ceil(slack_minutes / mpd)
                        except ValueError: total_slack_days = 0

                    if uid != '0':
                         all_tasks_data_list.append({"UID": uid, "Name": name, "Start": start_date, "Finish": finish_date, "Duration": duration_formatted, "Cost": cost_euros, "Milestone": is_milestone, "WBS": wbs, "TotalSlackDays": total_slack_days})

                    # Logica TUP/TUF (con indentazione CORRETTA)
                    match = tup_tuf_pattern.search(name)
                    if match:
                         # ... (Logica TUP/TUF corretta, omessa per brevità) ...
                         current_task_data = {...}
                         if tup_tuf_key not in potential_milestones: #...
                         elif not is_pure_milestone_duration: #...
                              elif duration_seconds > existing_duration_seconds:
                                   potential_milestones[tup_tuf_key] = current_task_data

                # Salvataggio dati TUP/TUF
                final_milestones_data = []
                # ... (omissis)
                if final_milestones_data:
                    # ... (omissis creazione df e salvataggio in sessione) ...
                    st.session_state['df_milestones_display'] = df_milestones.drop(columns=['DataInizioObj'])
                else: st.session_state['df_milestones_display'] = None

                # Salvataggio TUTTE le attività
                st.session_state['all_tasks_data'] = pd.DataFrame(all_tasks_data_list)
                
                # --- NON ESTRARRE PIU' DATI TIMEPHASED VECCHI ---
                # (Rimuoviamo le chiamate a parse_timephased_data_from_assignments)
                # st.session_state['scurve_data'] = ... (Rimosso)
                # st.session_state['baseline_work_data'] = ... (Rimosso)

                # Estrazione Dati Risorse (Invariato)
                resources_node = tree.find('msp:Resources', ns); resources_data = []
                if resources_node is not None:
                    for resource in resources_node.findall('msp:Resource', ns):
                        res_uid = resource.findtext('msp:UID', namespaces=ns)
                        res_name = resource.findtext('msp:Name', namespaces=ns) or "Senza Nome"
                        res_type_num = resource.findtext('msp:Type', namespaces=ns)
                        res_type = "Manodopera" if res_type_num == '1' else "Mezzo/Materiale"
                        resources_data.append({'ResourceUID': res_uid, 'ResourceName': res_name, 'ResourceType': res_type})
                st.session_state['resources_data'] = pd.DataFrame(resources_data)
                
                # Debug
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
        # --- Sezione 2: Analisi Preliminare ---
        st.markdown("---"); st.markdown("#### 2. Analisi Preliminare"); st.markdown("##### 📄 Informazioni Generali dell'Appalto")
        project_name = st.session_state.get('project_name', "N/D"); formatted_cost = st.session_state.get('formatted_cost', "N/D")
        col1_disp, col2_disp = st.columns(2); 
        with col1_disp: st.markdown(f"**Nome:** {project_name}")
        with col2_disp: st.markdown(f"**Importo Totale Lavori:** {formatted_cost}")
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
        col_date1, col_date2 = st.columns(2);
        with col_date1: selected_start_date = st.date_input("Data Inizio", value=default_start, min_value=default_start, max_value=default_finish + timedelta(days=5*365), format="DD/MM/YYYY", key="start_date_selector")
        with col_date2:
            min_end_date = selected_start_date; actual_default_finish = max(default_finish, min_end_date)
            reasonable_max_date = actual_default_finish + timedelta(days=10*365)
            selected_finish_date = st.date_input("Data Fine", value=actual_default_finish, min_value=min_end_date, max_value=reasonable_max_date, format="DD/MM/YYYY", key="finish_date_selector")

        # --- Analisi Dettagliate ---
        st.markdown("---"); st.markdown("##### 📊 Analisi Dettagliate")
        
        all_tasks_df = st.session_state.get('all_tasks_data')
        
        # Bottone per avviare l'analisi (come richiesto)
        if st.button("📈 Avvia Analisi Curva S", key="analyze_scurve"):
            if all_tasks_df is None or all_tasks_df.empty:
                 st.error("Errore: Dati delle attività non trovati. Impossibile calcolare la Curva S.")
            else:
                try:
                    # --- CURVA S (SIL) - NUOVA LOGICA ---
                    st.markdown("###### Curva S (Costo Cumulato - Stima Lineare)")
                    
                    # 1. Calcola i costi giornalieri
                    with st.spinner("Calcolo distribuzione costi..."):
                        daily_cost_df = calculate_linear_scurve(all_tasks_df)
                    
                    if not daily_cost_df.empty:
                        # 2. Filtra per periodo selezionato
                        mask_cost = (daily_cost_df['Date'].dt.date >= selected_start_date) & (daily_cost_df['Date'].dt.date <= selected_finish_date)
                        filtered_cost = daily_cost_df.loc[mask_cost]
                        
                        if not filtered_cost.empty:
                            # 3. Aggrega per Mese
                            monthly_cost = filtered_cost.set_index('Date').resample('ME')['Value'].sum().reset_index()
                            monthly_cost['Costo Cumulato (€)'] = monthly_cost['Value'].cumsum()
                            monthly_cost['Mese'] = monthly_cost['Date'].dt.strftime('%Y-%m')
                            
                            # --- PASSO INTERMEDIO: Mostra tabella dati ---
                            st.markdown("###### Tabella Dati SIL Mensili Aggregati")
                            df_display_sil = monthly_cost[['Mese', 'Value', 'Costo Cumulato (€)']].rename(columns={'Value': 'Costo Mensile (€)'})
                            st.dataframe(df_display_sil, use_container_width=True, hide_index=True)
                            
                            # --- GRAFICO COMBINATO (Barre + Linea) ---
                            st.markdown("###### Grafico Curva S")
                            fig_sil = go.Figure()
                            # Aggiungi Barre (Costo Mensile)
                            fig_sil.add_trace(go.Bar(
                                x=monthly_cost['Mese'],
                                y=monthly_cost['Value'],
                                name='Costo Mensile'
                            ))
                            # Aggiungi Linea (Costo Cumulato)
                            fig_sil.add_trace(go.Scatter(
                                x=monthly_cost['Mese'],
                                y=monthly_cost['Costo Cumulato (€)'],
                                name='Costo Cumulato',
                                mode='lines+markers',
                                yaxis='y2' # Usa un asse Y secondario
                            ))
                            # Configura layout con doppio asse Y
                            fig_sil.update_layout(
                                title='Curva S - Costo Mensile e Cumulato (Stima Lineare)',
                                xaxis_title="Mese",
                                yaxis=dict(title="Costo Mensile (€)"),
                                yaxis2=dict(
                                    title="Costo Cumulato (€)",
                                    overlaying="y",
                                    side="right"
                                ),
                                legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
                            )
                            st.plotly_chart(fig_sil, use_container_width=True)
                            # --- FINE GRAFICO COMBINATO ---
                            
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
