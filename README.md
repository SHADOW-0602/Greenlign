# Greenlign

AI-assisted GHG accounting platform.

## Prerequisites

- [Neon](https://console.neon.tech) free account — create a project and grab the connection string
- [Backblaze B2](https://www.backblaze.com/cloud-storage) account (for production) — free 10 GB tier
- [Groq](https://console.groq.com) API key (Phase 2+ only)
- Docker Desktop

## Quick Start (local dev)

```bash
cp backend/.env.example backend/.env
# Edit backend/.env — fill in your Neon DATABASE_URL
# (MinIO runs locally via Docker; no B2 keys needed for local dev)

cp frontend/.env.example frontend/.env

# Run migrations against Neon (one-time per branch):
cd backend && pip install -r requirements.txt && alembic upgrade head && cd ..

# Seed emission factors into Neon:
cd backend && python -m app.seeds.factors && cd ..

# Start local services (Redis, MinIO, backend, worker, frontend):
docker compose -f infra/docker-compose.yml up --build
```

Visit http://localhost:3000 (frontend) and http://localhost:8000/docs (API).

## Production Storage (Backblaze B2)

Set these env vars — no code change required:
```
S3_ENDPOINT_URL=https://s3.us-west-004.backblazeb2.com
S3_ACCESS_KEY=your-b2-keyID
S3_SECRET_KEY=your-b2-applicationKey
S3_BUCKET_NAME=greenlign-raw
```

## Non-negotiable rule

All arithmetic producing a final tCO2e figure MUST be executed by a
deterministic Python function with unit tests, never by an LLM completion.
