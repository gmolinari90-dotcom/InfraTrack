# Fase 1: Partiamo da un'immagine base ufficiale di Conda/Mamba
FROM condaforge/mambaforge:latest

# Fase 2: Impostiamo la cartella di lavoro
WORKDIR /app

# --- STRATEGIA A DUE FASI ---

# FASE 1: Creare l'ambiente base con Conda e il pacchetto complesso
COPY environment.yml .
RUN mamba env create -f environment.yml

# FASE 2: Installare i pacchetti restanti con Pip dentro l'ambiente appena creato
COPY app.py . # Copiamo un file dummy per creare lo strato dopo
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
