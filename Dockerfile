# Fase 1: Partiamo da un'immagine base stabile di Conda
FROM condaforge/mambaforge:latest

# Fase 2: Impostiamo la cartella di lavoro
WORKDIR /app

# Fase 3: Copiamo il file di configurazione dell'ambiente base
COPY environment.yml .

# Fase 4: ESEGUIAMO TUTTO IN UN UNICO BLOCCO ATOMICO
# 1. Crea l'ambiente minimale (SUCCESS).
# 2. Usa Pip DENTRO l'ambiente per installare il pacchetto difficile (SUCCESS).
# 3. Usa Pip DENTRO l'ambiente per installare il resto (SUCCESS).
RUN mamba env create -f environment.yml && \
    conda run -n infratrack pip install python-mpxj && \
    conda run -n infratrack pip install streamlit pandas plotly

# Fase 5: Copiamo il resto del codice della nostra applicazione
COPY . .

# Fase 6: Definiamo la porta
EXPOSE 8501

# Fase 7: Definiamo il comando di avvio usando il PERCORSO ASSOLUTO.
CMD ["/opt/conda/envs/infratrack/bin/streamlit", "run", "app.py"]
