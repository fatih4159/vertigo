# Deployment Guide

## Local Development

```bash
# Backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd ui && npm install && npm run dev
```

## Docker Compose

```bash
docker compose up --build
```

Services:
- `backend` → `http://localhost:8000`
- `ollama` → `http://localhost:11434` (optional, if not running locally)
- `ui` → build and serve at `http://localhost:5173`

## Production

### Backend

```bash
# Build image
docker build -t aaos-backend .

# Run with production settings
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://user:pass@db/aaos \
  -e SECRET_KEY=$(openssl rand -hex 32) \
  -e OLLAMA_BASE_URL=http://ollama:11434 \
  -v /data/workspace:/app/workspace \
  aaos-backend
```

### Environment Variables (Production)

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/aaos
SECRET_KEY=<random 64-char hex>
OLLAMA_BASE_URL=http://ollama-host:11434
OLLAMA_DEFAULT_MODEL=qwen2.5-coder:latest
WORKSPACE_ROOT=/data/workspace
LOG_LEVEL=WARNING
DEBUG=false
```

### Frontend Build

```bash
cd ui
VITE_API_URL=https://api.example.com/api/v1 npm run build
# Serve dist/ with nginx or any static host
```

### Nginx Config

```nginx
server {
    listen 443 ssl;
    server_name aaos.example.com;

    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
    }

    location /ws {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location / {
        root /usr/share/nginx/html;
        try_files $uri /index.html;
    }
}
```

## Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "add my table"

# Apply
alembic upgrade head

# Rollback one
alembic downgrade -1
```

## Monitoring

Logs are written to `./logs/aaos.log` and stdout. Set `LOG_LEVEL=DEBUG` for verbose output.

The `/health` endpoint returns `{"status": "ok"}` for readiness probes.

## Scaling

- The agent runner uses Python `asyncio` background tasks within a single process.
- For multi-process setups, use Redis as an event bus backend (future extension).
- Database connections are pooled via SQLAlchemy's async engine.
- Ollama can be run on a separate GPU host; point `OLLAMA_BASE_URL` accordingly.
