# HireOS Brain

Python 3.12 / FastAPI / PostgreSQL 16 foundation for tenant-isolated recruiting analytics.

## Run locally

Install Docker Desktop with its Linux engine running and Python 3.12.

```powershell
py -3.12 scripts/create_env.py
docker compose up --build -d
```

On Linux/macOS use python3 for the first command. It creates an ignored .env with
random local credentials without printing them or overwriting an existing file.
.env.example lists the required variables without secrets.

Open http://localhost:8000/docs. /health checks database readiness and migration 0001.
Compose starts PostgreSQL, runs Alembic as a separate migrator, then starts the API.
The API binds only to 127.0.0.1; the database has no host port.

## Demo identity and isolation

```powershell
docker compose exec api python scripts/demo_token.py --tenant a --role admin
```

Paste the token into Swagger Authorize and call /api/me. Tokens verify HS256
signature, expiry, issuer and audience. Tenant/user/role come only from verified claims.
Roles are viewer, recruiter and admin. Token generation is a local demo tool.

The app database user is a non-owner without superuser/BYPASSRLS. Sources enforce
tenant and minimum-role visibility using FORCE ROW LEVEL SECURITY. Identity settings
are transaction-local and reset on commit/rollback. Migrations use a separate owner.
The pgvector extension is installed; vector search is not implemented.

## Checks

```powershell
docker compose --profile test run --rm tests
docker compose run --rm api ruff check .
```

Tests use real PostgreSQL and the app user, covering JWT failures, tenant/role
isolation and pooled-connection context reset. Stop services with docker compose down
to retain data. Bootstrap runs only on the first initialization of the database volume.

## Next

Operational ingestion, deterministic metrics, retrieved evidence, cited mock answers,
retrieval logs, a browser interface and temporary synthetic fixtures.
Use synthetic data only. Never commit .env or real credentials.
