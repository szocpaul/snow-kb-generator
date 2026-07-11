FROM python:3.12-slim

WORKDIR /app

# Rendszer csomagok
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Függőségek másolása és telepítés
COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir -e ".[deploy,pi-auth]"

# Forráskód másolása
COPY src/ ./src/
COPY config.yaml ./
# A .env és data/ külön mountolva lesz (docker-compose)

# Port
EXPOSE 8000

# FastAPI szerver indítása
CMD ["uvicorn", "snow_kb.server:app", "--host", "0.0.0.0", "--port", "8000"]
