# HireOS Brain

An evidence-backed recruiting analytics application built with Python 3.12,
FastAPI, PostgreSQL 16, and Docker Compose.

Multiple organizations share the application and database. Verified JWT identities,
tenant-aware records, role checks, and PostgreSQL row-level security keep their
data separated. Recruiting metrics come from SQL; the shipped interpretation
provider is a deterministic mock with validated evidence citations.

## Explore the implementation

| Start here | What it explains |
| --- | --- |
| [File-by-file guide](docs/FILE_GUIDE.md) | Every tracked file, its purpose, the reading order, request flow, and implementation commits. |
| [Design and security](docs/DESIGN.md) | Multi-tenancy, database policies, conversion semantics, retrieval, and demo boundaries. |
| [API reference](docs/API.md) | Endpoints, the 13-column CSV contract, request examples, and error behavior. |
| [Demo walkthrough](docs/DEMO.md) | Setup, uploads, cited answers, outcome freshness, and tenant/role checks. |

For a code walkthrough, follow `app/main.py` -> `app/api/pipeline.py` -> the
ingestion or Ask services. Read `app/auth/jwt.py`, `app/db.py`, the migrations,
and `tests/test_isolation.py` together to understand how tenant isolation works.

## Features

The local pipeline supports CSV/policy uploads, tenant and role checks,
deterministic conversion, policy retrieval, cited mock answers, new outcomes,
and retrieval history. The browser interface runs from the same FastAPI service.
Bundled synthetic fixtures cover two comparison months and separate tenant workflows.
An additional seven-submission sample demonstrates a third tenant.

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

## Sample dataset and first question

Upload one CSV, `fixtures/temporary/tenant_a/operations_a.csv`, in the browser.
It has the required 13 columns and one row per submission, with job, interview
and start details on that row. Then upload `policy_a.md` separately.
Alternatively, load both tenants using:

```powershell
docker compose exec api python scripts/seed.py
```

The script uses the same ingestion service as HTTP uploads. Repeating it is safe;
it does not automatically ingest the separate new outcome. No data is seeded at startup.
All fixtures are clearly synthetic, with candidate aliases rather than real people.
The importer validates the entire file and saves normalized records in one transaction.
Tenant identity comes from the token; source references are attached by the backend.
Existing record/source IDs are retained. Newer fixture rows enrich prior records;
blank interview/start cells never delete existing outcomes. All 13 validated values
are retained in the submission's JSON payload. No schema migration is needed.
See [the exact schema and mapping](docs/API.md).

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

For a smaller seven-submission sample, see [Tenant C](fixtures/temporary/tenant_c/README.md).
The [CSV correction example](fixtures/temporary/examples/README.md) demonstrates the
difference between a fresh import and an update that preserves prior outcomes.

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

Without Docker, run the independent checks after creating the local .env:

```powershell
uv run pytest -m unit -q
```

These validate CSV rules, authentication, citations and the page shell. They do not
verify SQL aggregation, migrations or database isolation. Run the full Compose suite
to verify those database behaviors.

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

## Roadmap

- Expand synthetic datasets to cover more recruiting scenarios and longer comparison periods.
- Add an external interpretation-provider adapter with claim-level grounding evaluation.
- Add pagination and background processing for larger imports.

## Current limits

The demo deliberately uses a deterministic mock; no external LLM key is needed.
Vector search and a BYO LLM adapter are optional and currently not implemented.
Policy uploads support UTF-8 text/Markdown; binary PDF/Word parsing is not included.

## References

- [Docker Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/)
- [PostgreSQL 16 row security](https://www.postgresql.org/docs/16/ddl-rowsecurity.html)
- [pgvector](https://github.com/pgvector/pgvector)
