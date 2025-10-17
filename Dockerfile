# Fase 1: Partiamo da un'immagine base ufficiale di Conda/Mamba
FROM condaforge/mambaforge:latest

# Fase 2: Impostiamo la cartella di lavoro
WORKDIR /app

# --- STRATEGIA A DUE FASI ---

# FASE 1: Creare un ambiente base MINIMALE con Conda
COPY environment.yml .
RUN mamba env create -f environment.yml

# FASE 2: Usare Pip DENTRO l'ambiente per installare le librerie una per una
# Questo bypassa il "solver" di Conda per i pacchetti complessi
# Mettiamo il pacchetto più difficile per primo
RUN conda run -n infratrack pip install python-mpxj
RUN conda run -n infratrack pip install streamlit pandas plotly

# --- CONFIGURAZIONE FINALE ---

# Fase 3: Attiviamo la shell per eseguire i comandi DENTRO il nostro ambiente Conda
SHELL ["conda", "run", "-n", "infratrack", "/bin/bash", "-c"]

# Fase 4: Copiamo il resto del codice della nostra applicazione
COPY . .

# Fase 5: Esponiamo la porta che Streamlit usa di default
EXPOSE 8501

# Fase 6: Definiamo il comando per avviare l'applicazione
CMD ["streamlit", "run", "app.py"]
