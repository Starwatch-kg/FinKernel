# FinKernel 

FinKernel is a Docker-based personal finance platform with:
- React frontend
- FastAPI API gateway
- transaction service
- AI service
- PostgreSQL and Redis

## What Is Kept In This Repo

- `frontend/` production frontend and local dev client
- `microservices/` backend services
- `alembic/` database migrations
- `docker-compose.yml` full local/server deployment
- `deploy.sh` one-command deployment helper
- `README.md` this deployment guide

Extra reports, backups, generated caches, local artifacts, and duplicate docs were removed to keep the repository ready for GitHub.

## Environment

Create `.env` from `.env.example` and fill at least:

```env
DATABASE_URL=postgresql+asyncpg://finuser:finpass123@postgres:5432/financedb
REDIS_URL=redis://redis:6379/0
JWT_SECRET_KEY=change-this-to-a-long-random-secret
GROQ_API_KEY=
OPENROUTER_API_KEY=
ADMIN_EMAILS=admin@example.com
ENVIRONMENT=production
DEBUG=false
```

Optional AI inflation defaults:

```env
FIN_COUNTRY_NAME=Кыргызстан
FIN_COUNTRY_INFLATION_RATE=9.6
FIN_COUNTRY_INFLATION_AS_OF=2026-02-13
FIN_COUNTRY_INFLATION_LABEL=последние доступные данные
```

## Deploy On Server

Requirements:
- Docker
- Docker Compose plugin
- ports `80`, `8000`, `8001`, `8002` open on the server/firewall if needed

Run:

```bash
chmod +x deploy.sh
./deploy.sh
```

After deployment:
- frontend: `http://SERVER_IP`
- API gateway: `http://SERVER_IP:8000`

The frontend is now started by `deploy.sh` and served on `0.0.0.0`, so it is reachable from desktop and phone on the same network or via the server IP.

## Local Development

Backend stack:

```bash
docker compose up -d postgres redis transactions ai gateway frontend
```

Frontend only:

```bash
cd frontend
npm install
npm run dev
```

Vite now listens on `0.0.0.0:5173`, so you can open it from another device with:

```text
http://YOUR_LOCAL_IP:5173
```

## Useful Commands

```bash
docker compose ps
docker compose logs -f frontend
docker compose logs -f gateway
docker compose down
docker compose up -d --build
```

## Notes

- frontend uses `/api` and proxies to the gateway through nginx
- production frontend is served over plain HTTP on port `80`
- if you need HTTPS, put a real reverse proxy in front of this stack
