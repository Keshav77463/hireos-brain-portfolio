# HireOS Brain

An evidence-backed recruiting analytics application built with Python 3.12,
FastAPI, PostgreSQL 16, and Docker Compose.

## Current milestone

The local pipeline supports CSV/policy uploads, tenant and role checks,
deterministic conversion, policy retrieval, cited mock answers, new outcomes,
and retrieval history. The browser interface runs from the same FastAPI service.
Small **temporary** synthetic fixtures cover two comparison months and two tenants.
The proper final dataset and the recorded demo video remain to be prepared.

See [API reference](docs/API.md), [design and security](docs/DESIGN.md),
and [demo walkthrough](docs/DEMO.md).

## Start locally

Install Docker Desktop with its Linux engine running and Python 3.12.
From this repository:

```powershell
py -3.12 scripts/create_env.py
docker compose up --build -d
```

On Linux/macOS, use `python3 scripts/create_env.py`.
The first command creates a git-ignored `.env` with random local-only credentials.
It never overwrites an existing file or prints its contents.
`.env.example` documents the variables without credentials.

Open http://localhost:8000 for the application, or http://localhost:8000/docs
for the interactive API reference.

```powershell
Invoke-RestMethod http://localhost:8000/health
docker compose ps -a
docker compose logs migrate
```

Compose starts the database, waits for its healthcheck, runs the one-shot
migrator, and starts the API after migrations succeed.
The database has no host port; the API binds to `127.0.0.1`.

## Authentication

Generate a short-lived token for a synthetic tenant and user:

```powershell
docker compose exec api python scripts/demo_token.py --tenant a --role admin
```

Paste the token into the application's connection field or Swagger's **Authorize** dialog.
`GET /api/me` shows the
verified identity. Roles are `viewer`, `recruiter`, and `admin`.
The API verifies signature, expiry, issuer, audience, and identity claims.
Tenant and role come only from the verified token.
HS256 and local token generation are demo conveniences, not a production
identity service. Use synthetic data and local credentials only.

## Temporary dataset and first question

Either upload the files from `fixtures/temporary/tenant_a/` in the browser
(jobs, submissions, interviews, starts, then policy), or use:

```powershell
docker compose exec api python scripts/seed.py
```

The script uses the same ingestion service as HTTP uploads. Repeating it is safe;
it does not automatically ingest the separate new outcome. No data is seeded at startup.
All fixtures are clearly synthetic, with candidate aliases rather than real people.

Connect a Tenant A token and ask:
**Why did ICU RN submissions increase while interviews decreased?**
The default comparison selects the latest accessible submission month (June 2026)
and its preceding month (May 2026).

Expected calculation: baseline 6/10 = 60%; current 4/20 = 20%.
Add the interview for `SUB-A-J05` using the outcome form (or the JSON example
in `fixtures/temporary/new_outcome.json`). Ask again: current 5/20 = 25%.
Repeated ingestion of the same record is idempotent.
The answer shows SQL metrics, separately labelled deterministic mock interpretation,
source records, policy chunks, limitations, and a retrieval log ID.

Generate a `--tenant b` token to view its distinct data. The cross-tenant test
button requests the other tenant and must receive HTTP 403 with no evidence.
Generate a `--role viewer` token to verify read-only behavior.

## Security foundation

- Bootstrap credentials stay in the database service. The API receives only
  `hireos_app` credentials: no superuser, ownership, or RLS bypass privileges.
- `hireos_migrator` owns the application schema and runs migrations separately.
- All six source, evidence and audit tables have FORCE ROW LEVEL SECURITY.
- `tenant_session` sets `app.tenant_id`, `app.role` and `app.user_id` with transaction-local
  `set_config(..., true)` values that expire on commit or rollback.
- Sources have minimum-role visibility. Viewers cannot write sources, and
  administrators remain restricted to their own tenant.
- Evidence visibility follows its source and parent job/submission visibility.
  App-level tenant filters are applied alongside database row policies.
- Citation validation rejects references outside the evidence retrieved for the request.
- Audit entries are append-only to the app user. Viewers cannot read past admin answers.
- Uploads are bounded and validated atomically; the UI renders untrusted text as text.
- The pgvector extension is enabled; vector search is optional and not implemented.

## Tests and lint

Run tests against the real Compose PostgreSQL as the application database user:

```powershell
docker compose --profile test run --rm tests
docker compose run --rm api ruff check .
docker compose run --rm api ruff format --check .
```

Tests cover readiness, JWT failures, application-user privileges, tenant/role
isolation, denied writes, pooled-connection context reset, conversion, citations,
freshness, duplicate outcomes, atomic uploads, timestamp cutoffs and policy injection.
Test rows have random synthetic tenant IDs in the local database.

For local Python work:

```powershell
uv sync --locked
uv run ruff check .
```

Dependency versions are recorded in `uv.lock`.

## Database changes and lifecycle

Migrations are in `migrations/versions/`. Run them as the migrator:

```powershell
docker compose run --rm migrate
```

Stop services while retaining the database:

```powershell
docker compose down
```

The named PostgreSQL volume persists. `docker compose down -v` deletes its data;
use it only when deliberately resetting this synthetic local demo.
Bootstrap scripts run only when the volume is first initialized.
Changing `.env` does not rotate existing database passwords.

## Remaining assignment work

- Replace temporary development fixtures with the agreed final synthetic dataset.
- Record the 5–10 minute acceptance walkthrough in `docs/DEMO.md`.
- Review the implementation and explain the design choices and known limits.
- Commit the reviewed work to the company repository as instructed.

The demo deliberately uses a deterministic mock; no external LLM key is needed.
Vector search and a BYO LLM adapter are optional and currently not implemented.
Policy uploads support UTF-8 text/Markdown; binary PDF/Word parsing is not included.

Keep the company repository private. Daily commits are required by the brief;
commit and push only when explicitly authorized.

## References

- [Docker Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/)
- [PostgreSQL 16 row security](https://www.postgresql.org/docs/16/ddl-rowsecurity.html)
- [pgvector](https://github.com/pgvector/pgvector)
