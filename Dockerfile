# Fase 1: Partiamo da un'immagine base stabile di Conda
FROM condaforge/mambaforge:latest

# Fase 2: Impostiamo la cartella di lavoro
WORKDIR /app

# --- STRATEGIA "ISOLA E CONQUISTA" ---

# FASE A: Creare un ambiente base MINIMALE con Conda
COPY environment.yml .
RUN mamba env create -f environment.yml

# FASE B: Usare Pip DENTRO l'ambiente per installare le librerie in due passaggi separati
# Questo bypassa il "solver" di Conda per i pacchetti in conflitto.

# 1. Installiamo prima il pacchetto problematico e le sue dipendenze
RUN conda run -n infratrack pip install python-mpxj

# 2. Poi installiamo il resto dell'ecosistema moderno
RUN conda run -n infratrack pip install streamlit pandas plotly

# --- CONFIGURAZIONE FINALE ---

# Fase 3: Copiamo il resto del codice della nostra applicazione
COPY . .

# Fase 4: Definiamo la porta
EXPOSE 8501

# Fase 5: Definiamo il comando di avvio usando il PERCORSO ASSOLUTO all'eseguibile
# Questa è la forma più robusta e a prova di errore.
CMD ["/opt/conda/envs/infratrack/bin/streamlit", "run", "app.py"]
