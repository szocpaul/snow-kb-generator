FROM python:3.12-slim

WORKDIR /app

# Rendszer csomagok
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copying the dependencies and installing them
COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir -e ".[deploy,pi-auth]"

# Copying the source code
COPY src/ ./src/
COPY config.yaml ./
# The .env and data/ are mounted separately (docker-compose)

# Port
EXPOSE 8000

# Starting the FastAPI server
CMD ["uvicorn", "snow_kb.server:app", "--host", "0.0.0.0", "--port", "8000"]
