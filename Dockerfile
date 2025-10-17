# Fase 1: Scegliamo un'immagine base ufficiale di Python
FROM python:3.11.9-slim

# Fase 2: Installiamo le dipendenze di sistema (Java e strumenti di build)
RUN apt-get update && apt-get install -y default-jre build-essential && apt-get clean

# Imposta la variabile d'ambiente JAVA_HOME per una migliore compatibilità
ENV JAVA_HOME /usr/lib/jvm/java-17-openjdk-amd64

# Fase 3: Impostiamo la cartella di lavoro all'interno del container
WORKDIR /app

# Fase 4: Copiamo i file dei requisiti e li installiamo
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Fase 5: Copiamo il resto del codice della nostra applicazione
COPY . .

# Fase 6: Esponiamo la porta che Streamlit usa di default
EXPOSE 8501

# Fase 7: Definiamo il comando per avviare l'applicazione quando il container parte
CMD ["streamlit", "run", "app.py"]
