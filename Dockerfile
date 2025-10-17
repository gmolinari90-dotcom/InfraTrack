# Fase 1: Partiamo da un'immagine base ufficiale di Conda/Mamba
FROM condaforge/mambaforge:latest

# Fase 2: Impostiamo la cartella di lavoro
WORKDIR /app

# Fase 3: Copiamo il file di configurazione dell'ambiente Conda
COPY environment.yml .

# Fase 4: Creiamo l'ambiente Conda. Il file yml ora contiene tutte le info corrette.
RUN mamba env create -f environment.yml

# Fase 5: Attiviamo la shell per eseguire i comandi DENTRO il nostro ambiente Conda
SHELL ["conda", "run", "-n", "infratrack", "/bin/bash", "-c"]

# Fase 6: Copiamo il resto del codice della nostra applicazione
COPY . .

# Fase 7: Esponiamo la porta che Streamlit usa di default
EXPOSE 8501

# Fase 8: Definiamo il comando per avviare l'applicazione
CMD ["streamlit", "run", "app.py"]
