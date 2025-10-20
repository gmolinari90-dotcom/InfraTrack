import streamlit as st
from lxml import etree
import pandas as pd
from datetime import datetime, timedelta
import re
import isodate
from io import BytesIO

# --- CONFIGURAZIONE DELLA PAGINA ---
st.set_page_config(page_title="InfraTrack v1.3", page_icon="🚆", layout="wide") # Version updated

# --- CSS ---
st.markdown("""
<style>
    /* ... (CSS omesso per brevità, è lo stesso di prima) ... */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, .stApp p, .stApp .stDataFrame, .stApp .stButton>button {
        font-size: 0.85rem !important;
    }
     .stApp h2 { /* Target per il titolo principale H2 */
        font-size: 1.5rem !important;
     }
     .stApp .stMarkdown h4 { /* Target specifici per header informazioni */
         font-size: 0.95rem !important;
         margin-bottom: 0.5rem;
     }
     .stApp .stMarkdown h5 { /* Target specifici per header milestone */
         font-size: 0.90rem !important;
          margin-bottom: 0.5rem;
     }
    .stApp .stButton>button {
         padding: 0.2rem 0.5rem;
    }
    .stApp {
        padding-top: 2rem;
    }
    .stDataFrame td {
        text-align: center !important;
    }
</style>
""", unsafe_allow_html=True)

# --- TITOLO E HEADER ---
st.markdown("## 🚆 InfraTrack v1.3") # Version updated
st.caption("La tua centrale di controllo per progetti infrastrutturali")

# --- BOTTONE RESET ---
if st.button("🔄 Reset e Ricarica Nuovo File"):
    st.rerun()

# --- CARICAMENTO FILE ---
st.markdown("---")
st.markdown("#### 1. Carica la Baseline di Riferimento")

uploaded_file = st.file_uploader("Seleziona il file .XML esportato da MS Project", type=["xml"], label_visibility="collapsed", key="file_uploader_key")

if uploaded_file is not None:
    with st.spinner('Caricamento e analisi del file in corso...'):
        try:
            file_content_bytes = uploaded_file.getvalue()
            parser = etree.XMLParser(recover=True)
            tree = etree.fromstring(file_content_bytes, parser=parser)
            ns = {'msp': 'http://schemas.microsoft.com/project'}

            st.success('File XML analizzato con successo!')
            st.markdown("---")
            st.markdown("#### 📄 Informazioni Generali del Progetto")

            project_name = "Attività con UID 1 non trovata"
            formatted_cost = "€ 0,00"

            task_uid_1 = tree.find(".//msp:Task[msp:UID='1']", namespaces=ns)

            if task_uid_1 is not None:
                project_name = task_uid_1.findtext('msp:Name', namespaces=ns) or "Nome non trovato"
                total_cost_str = task_uid_1.findtext('msp:Cost', namespaces=ns) or "0"
                total_cost_cents = float(total_cost_str)
                total_cost_euros = total_cost_cents / 100.0
                formatted_cost = f"€ {total_cost_euros:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Nome Appalto:** {project_name}")
            with col2:
                st.markdown(f"**Importo Totale Lavori:** {formatted_cost}")

            st.markdown("##### 🗓️ Milestone Principali (TUP/TUF)")

            potential_milestones = {}
            all_tasks = tree.findall('.//msp:Task', namespaces=ns)
            tup_tuf_pattern = re.compile(r'(?i)(TUP|TUF)\s*\d*')

            def format_duration_from_xml(duration_str, work_hours_per_day=8.0):
                # ... (funzione durata omessa per brevità, è la stessa di prima) ...
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
                    start_date_str = task.findtext('msp:Start', namespaces=ns)
                    finish_date_str = task.findtext('msp:Finish', namespaces=ns)
                    start_date_obj = datetime.fromisoformat(start_date_str) if start_date_str else None
                    finish_date_obj = datetime.fromisoformat(finish_date_str) if finish_date_str else None
                    start_date_formatted = start_date_obj.strftime("%d/%m/%Y") if start_date_obj else "N/D"
                    finish_date_formatted = finish_date_obj.strftime("%d/%m/%Y") if finish_date_obj else "N/D"
                    current_task_data = {
                        "Nome Completo": task_name,
                        "Data Inizio": start_date_formatted,
                        "Data Fine": finish_date_formatted,
                        "Durata": format_duration_from_xml(duration_str),
                        "DurataSecondi": duration_seconds,
                        "DataInizioObj": start_date_obj
                    }
                    if tup_tuf_key not in potential_milestones or duration_seconds > potential_milestones[tup_tuf_key]["DurataSecondi"]:
                         if duration_seconds > 0 or (tup_tuf_key not in potential_milestones):
                              potential_milestones[tup_tuf_key] = current_task_data
                         elif duration_seconds == 0 and tup_tuf_key in potential_milestones and potential_milestones[tup_tuf_key]["DurataSecondi"] == 0:
                              pass

            final_milestones_data = []
            for key in potential_milestones:
                data = potential_milestones[key]
                final_milestones_data.append({
                    "Nome Completo": data["Nome Completo"],
                    "Data Inizio": data["Data Inizio"],
                    "Data Fine": data["Data Fine"],
                    "Durata": data["Durata"],
                    "DataInizioObj": data["DataInizioObj"]
                })

            if final_milestones_data:
                df_milestones = pd.DataFrame(final_milestones_data)
                df_milestones = df_milestones.sort_values(by="DataInizioObj").reset_index(drop=True)
                df_display = df_milestones[["Nome Completo", "Durata", "Data Inizio", "Data Fine"]]

                # --- MODIFICA: NASCONDI INDICE DATAFRAME ---
                st.dataframe(df_display, use_container_width=True, hide_index=True) # Aggiunto hide_index=True

                # --- Bottone Download Excel (invariato) ---
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    # Usiamo df_display che ha le colonne nell'ordine giusto e senza DataInizioObj
                    df_display.to_excel(writer, index=False, sheet_name='Milestones')
                excel_data = output.getvalue()
                st.download_button(
                    label="📄 Scarica Tabella Milestones (Excel)",
                    data=excel_data,
                    file_name="milestones_TUP_TUF.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            else:
                st.warning("Nessuna milestone TUP o TUF trovata nel file.")

            # Manteniamo la sezione di debug
            st.markdown("---")
            with st.expander("🔍 Dati Grezzi per Debug (prime 50 righe del file)"):
                raw_text = file_content_bytes.decode('utf-8', errors='ignore')
                st.code('\n'.join(raw_text.splitlines()[:50]), language='xml')

        # ... (Gestione eccezioni omessa per brevità, è la stessa di prima) ...
        except etree.XMLSyntaxError as e:
             st.error(f"Errore di sintassi XML: {e}")
             st.error("Il file XML sembra essere malformato o incompleto. Prova a riesportarlo da MS Project.")
             try:
                 raw_text = file_content_bytes.decode('utf-8', errors='ignore')
                 st.code('\n'.join(raw_text.splitlines()[:20]), language='xml')
             except Exception:
                 st.error("Impossibile leggere l'inizio del file.")
        except Exception as e:
            st.error(f"Errore imprevisto durante l'analisi del file XML: {e}")
            st.error("Verifica che il file sia un XML valido esportato da MS Project.")
