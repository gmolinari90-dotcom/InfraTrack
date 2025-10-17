# Fase 1: Partiamo da un'immagine base ufficiale di Conda/Mamba
FROM condaforge/mambaforge:latest

# Fase 2: Impostiamo la cartella di lavoro
WORKDIR /app

# Fase 3: Copiamo il file di configurazione dell'ambiente Conda
COPY environment.yml .

# Fase 4: Creiamo l'ambiente Conda.
RUN mamba env create -f environment.yml

# Fase 5: Copiamo tutto il resto (il nostro codice e lo script di avvio)
COPY . .

# Fase 6: Rendiamo lo script di avvio eseguibile
RUN chmod +x /app/entrypoint.sh

# Fase 7: Definiamo lo script come punto di ingresso del container
ENTRYPOINT ["/app/entrypoint.sh"]

# Fase 8: Definiamo la porta
EXPOSE 8501

# Fase 9: Definiamo il comando da passare all'entrypoint
CMD ["streamlit", "run", "app.py"]
