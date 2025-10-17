# Fase 1: Partiamo da un'immagine base stabile di Conda
FROM condaforge/mambaforge:latest

# Fase 2: Impostiamo la cartella di lavoro
WORKDIR /app

# Fase 3: Copiamo il file di configurazione dell'ambiente
COPY environment.yml .

# Fase 4: Creiamo l'ambiente. Ora funzionerà senza problemi.
RUN mamba env create -f environment.yml

# Fase 5: Copiamo il resto del codice della nostra applicazione
COPY . .

# Fase 6: Definiamo la porta
EXPOSE 8501

# Fase 7: Definiamo il comando di avvio usando il PERCORSO ASSOLUTO.
CMD ["/opt/conda/envs/infratrack/bin/streamlit", "run", "app.py"]
