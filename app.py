import streamlit as st
from lxml import etree
import pandas as pd
from datetime import datetime, timedelta
import re
import isodate
from io import BytesIO

# --- CONFIGURAZIONE DELLA PAGINA ---
st.set_page_config(page_title="InfraTrack v2.13", page_icon="🚆", layout="wide") # Version updated

# --- CSS ---
st.markdown("""
<style>
    /* ... (Stili generali omessi per brevità) ... */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, .stApp p, .stApp .stDataFrame, .stApp .stButton>button {
        font-size: 0.85rem !important;
    }
     .stApp h2 { font-size: 1.5rem !important; }
     .stApp .stMarkdown h4 { font-size: 1.1rem !important; margin-bottom: 0.5rem; margin-top: 1rem; }
     .stApp .stMarkdown h5 { font-size: 0.90rem !important; margin-bottom: 0.5rem; margin-top: 0.8rem; }

    /* ---- STILI BOTTONE RESET (Come in v2.11) ---- */
    button[data-testid="stButton"][kind="primary"][key="reset_button"] {
        padding: 0.2rem 0.5rem !important; /* Padding originale v1.9/v2.11 */
        line-height: 1.2 !important;
        font-size: 1.1rem !important;       /* Dimensione icona v1.9/v2.11 */
        border-radius: 0.25rem !important;
        display: inline-flex !important;    /* Assicura flex per centrare */
        align-items: center !important;
        justify-content: center !important;
        min-width: auto !important;         /* Permetti al bottone di adattarsi */
        width: auto !important;
    }
     button[data-testid="stButton"][kind="primary"][key="reset_button"]:disabled {
        cursor: not-allowed; opacity: 0.5;
     }
     /* Allinea verticalmente titolo e bottone nelle colonne */
     div[data-testid="stHorizontalBlock"] > div[style*="flex-direction: row"] {
        display: flex; align-items: center;
     }
     /* ---- FINE STILI BOTTONE ---- */

    .stApp { padding-top: 2rem; }
    .stDataFrame td { text-align: center !important; }
</style>
""", unsafe_allow_html=True)

# --- TITOLO E HEADER CON BOTTONE RESET ACCANTO ---
# Ripristiniamo le colonne per affiancare
col_title, col_reset = st.columns([0.95, 0.05], vertical_alignment="center")

with col_title:
    st.markdown("## 🚆 InfraTrack v2.13") # Version updated
    st.caption("La tua centrale di controllo per progetti infrastrutturali")

# --- GESTIONE RESET ---
if 'widget_key_counter' not in st.session_state: st.session_state.widget_key_counter = 0
if 'file_processed_success' not in st.session_state: st.session_state.file_processed_success = False

# Bottone Reset (solo icona) nella colonna destra
with col_reset:
    if st.button("🔄", key="reset_button", help="Resetta l'analisi", disabled=not st.session_state.file_processed_success):
        st.session_state.widget_key_counter += 1
        st.session_state.file_processed_success = False
        if 'uploaded_file_state' in st.session_state: del st.session_state['uploaded_file_state']
        st.rerun()

# --- CARICAMENTO FILE ---
# ... (Il resto del codice rimane invariato rispetto alla v2.12) ...
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

if uploaded_file is not None:
    if not st.session_state.file_processed_success:
        with st.spinner('Caricamento e analisi del file in corso...'):
            try:
                uploaded_file.seek(0); file_content_bytes = uploaded_file.read()
                parser = etree.XMLParser(recover=True); tree = etree.fromstring(file_content_bytes, parser=parser)
                ns = {'msp': 'http://schemas.microsoft.com/project'}

                project_name = "N/D"; formatted_cost = "€ 0,00"
                task_uid_1 = tree.find(".//msp:Task[msp:UID='1']", namespaces=ns)
                if task_uid_1 is not None:
                    project_name = task_uid_1.findtext('msp:Name', namespaces=ns) or "N/D"
                    total_cost_str = task_uid_1.findtext('msp:Cost', namespaces=ns) or "0"
                    total_cost_euros = float(total_cost_str) / 100.0
                    formatted_cost = f"€ {total_cost_euros:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                st.session_state['project_name'] = project_name
                st.session_state['formatted_cost'] = formatted_cost

                potential_milestones = {}
                all_tasks = tree.findall('.//msp:Task', namespaces=ns)
                tup_tuf_pattern = re.compile(r'(?i)(TUP|TUF)\s*\d*')
                def format_duration_from_xml(duration_str, work_hours_per_day=8.0):
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
                    task_name = task.findtext('msp:Name', namespaces=ns) or ""
                    match = tup_tuf_pattern.search(task_name)
                    if match:
                        tup_tuf_key = match.group(0).upper().strip()
                        duration_str = task.findtext('msp:Duration', namespaces=ns)
                        try:
                            if duration_str and duration_str.startswith('T'): duration_str = 'P' + duration_str
                            duration_obj = isodate.parse_duration(duration_str) if duration_str and duration_str.startswith('P') else timedelta()
                            duration_seconds = duration_obj.total_seconds()
                        except Exception: duration_seconds = 0
                        start_date_str = task.findtext('msp:Start', namespaces=ns); finish_date_str = task.findtext('msp:Finish', namespaces=ns)
                        start_date_obj = datetime.fromisoformat(start_date_str) if start_date_str else None; finish_date_obj = datetime.fromisoformat(finish_date_str) if finish_date_str else None
                        start_date_formatted = start_date_obj.strftime("%d/%m/%Y") if start_date_obj else "N/D"; finish_date_formatted = finish_date_obj.strftime("%d/%m/%Y") if finish_date_obj else "N/D"
                        current_task_data = {"Nome Completo": task_name, "Data Inizio": start_date_formatted, "Data Fine": finish_date_formatted, "Durata": format_duration_from_xml(duration_str), "DurataSecondi": duration_seconds, "DataInizioObj": start_date_obj}
                        if tup_tuf_key not in potential_milestones or duration_seconds > potential_milestones[tup_tuf_key]["DurataSecondi"]:
                             if duration_seconds > 0 or (tup_tuf_key not in potential_milestones): potential_milestones[tup_tuf_key] = current_task_data
                             elif duration_seconds == 0 and tup_tuf_key in potential_milestones and potential_milestones[tup_tuf_key]["DurataSecondi"] == 0: pass
                final_milestones_data = []
                for key in potential_milestones: final_milestones_data.append({"Nome Completo": potential_milestones[key]["Nome Completo"], "Data Inizio": potential_milestones[key]["Data Inizio"], "Data Fine": potential_milestones[key]["Data Fine"], "Durata": potential_milestones[key]["Durata"], "DataInizioObj": potential_milestones[key]["DataInizioObj"]})
                if final_milestones_data:
                    df_milestones = pd.DataFrame(final_milestones_data).sort_values(by="DataInizioObj").reset_index(drop=True)
                    st.session_state['df_milestones_display'] = df_milestones[["Nome Completo", "Durata", "Data Inizio", "Data Fine"]]
                else: st.session_state['df_milestones_display'] = None

                uploaded_file.seek(0); debug_content_bytes = uploaded_file.read(2000)
                try: st.session_state['debug_raw_text'] = '\n'.join(debug_content_bytes.decode('utf-8', errors='ignore').splitlines()[:50])
                except Exception as decode_err: st.session_state['debug_raw_text'] = f"Errore decodifica debug: {decode_err}"

                st.session_state.file_processed_success = True
                st.rerun()

            except etree.XMLSyntaxError as e:
                 st.error(f"Errore Sintassi XML: {e}"); st.error("File malformato?"); st.session_state.file_processed_success = False
                 try: uploaded_file.seek(0); st.code('\n'.join(uploaded_file.read(1000).decode('utf-8', errors='ignore').splitlines()[:20]), language='xml')
                 except Exception: pass
            except Exception as e:
                st.error(f"Errore Analisi: {e}"); st.error("Verifica file XML."); st.session_state.file_processed_success = False

    if st.session_state.file_processed_success:
        st.markdown("---")
        st.markdown("#### 2. Analisi Preliminare")
        st.markdown("##### 📄 Informazioni Generali del Progetto")
        project_name = st.session_state.get('project_name', "N/D")
        formatted_cost = st.session_state.get('formatted_cost', "N/D")
        col1_disp, col2_disp = st.columns(2)
        with col1_disp: st.markdown(f"**Nome Appalto:** {project_name}")
        with col2_disp: st.markdown(f"**Importo Totale Lavori:** {formatted_cost}")

        st.markdown("##### 🗓️ Termini Utili Contrattuali (TUP/TUF)")
        df_display = st.session_state.get('df_milestones_display')
        if df_display is not None and not df_display.empty:
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer: df_display.to_excel(writer, index=False, sheet_name='TerminiUtili')
            excel_data = output.getvalue()
            st.download_button(label="Scarica (Excel)", data=excel_data, file_name="termini_utili_TUP_TUF.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else: st.warning("Nessun Termine Utile (TUP o TUF) trovato nel file.")

        debug_text = st.session_state.get('debug_raw_text')
        if debug_text:
            st.markdown("---")
            with st.expander("🔍 Dati Grezzi per Debug (prime 50 righe del file)"): st.code(debug_text, language='xml')
