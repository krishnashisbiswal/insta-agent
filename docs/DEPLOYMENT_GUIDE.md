# Insta-Agent: Production Deployment Guide

## 1. Prerequisites

- Python 3.10, 3.11, or 3.12 (Python 3.11 recommended).
- FFmpeg installed and available on system PATH.
- (Optional) Blender 3.6+ or 4.x installed for headless 3D rendering.
- PostgreSQL database (or local SQLite for single-node deployments).

---

## 2. Docker Deployment

### 2.1 Dockerfile
```dockerfile
FROM python:3.11-slim

# Install system dependencies & ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2.2 Docker Compose
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/insta_agent
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - AUTO_PUBLISH=false
      - TOKEN_ENCRYPTION_KEY=${TOKEN_ENCRYPTION_KEY}
    depends_on:
      - db
    volumes:
      - ./storage:/app/storage
      - ./output:/app/output

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: insta_agent
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

---

## 3. Production Readiness Checklist

1. Ensure `AUTO_PUBLISH=false` during initial staging deployments.
2. Confirm `GEMINI_API_KEY` is provisioned with Google GenAI access.
3. Generate a secure 32-byte base64 token key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` and set as `TOKEN_ENCRYPTION_KEY`.
4. Run `pytest -v` before pointing live traffic to the API.
