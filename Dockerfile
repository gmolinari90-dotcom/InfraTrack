# Fase 1: Partiamo da un'immagine base stabile di Conda
FROM condaforge/mambaforge:latest

# Fase 2: Impostiamo la cartella di lavoro
WORKDIR /app

# Fase 3: Copiamo il file di configurazione dell'ambiente con le versioni bloccate
COPY environment.yml .

# Fase 4: Creiamo l'ambiente. Ora il solver avrà un compito possibile da risolvere.
RUN mamba env create -f environment.yml

# Fase 5: Copiamo il resto del codice della nostra applicazione
COPY . .

# Fase 6: Definiamo la porta
EXPOSE 8501

# Fase 7: Definiamo il comando di avvio usando il PERCORSO ASSOLUTO all'eseguibile.
# Questa è la forma più robusta e a prova di errore.
CMD ["/opt/conda/envs/infratrack/bin/streamlit", "run", "app.py"]
