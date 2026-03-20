FROM python:3.11-slim

WORKDIR /app

# 1. On installe les dépendances d'abord (plus rapide pour les futurs builds)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. CRUCIAL : On copie TOUT le contenu du dossier actuel vers le container
# Cela inclut app.py, config.py et massive_engine.py
COPY . .

# 3. On expose le port 8502
EXPOSE 8502

# 4. On lance Streamlit sur le port 8502
CMD ["streamlit", "run", "app.py", "--server.port=8502", "--server.address=0.0.0.0"]
