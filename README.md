# HireOS Brain

Python 3.12 / FastAPI / PostgreSQL 16 recruiting analytics API.

## Run locally

Install Docker Desktop and Python 3.12, then:

```powershell
py -3.12 scripts/create_env.py
docker compose up --build -d
docker compose exec api python scripts/seed.py
docker compose exec api python scripts/demo_token.py --tenant a --role admin
```

On Linux/macOS use python3 for the environment generator. The ignored .env contains
random local-only credentials; .env.example contains no secrets. Never commit .env.
The seed script uses the upload ingestion service. Fixtures are temporary and synthetic.
No data is seeded automatically and the separate new outcome is not seeded.

Open http://localhost:8000/docs and paste the token into Authorize.
The browser dashboard and expanded reference documentation will follow.

## API workflow

POST /api/ingest/csv accepts multipart kind, source_id, min_role and file.
Kinds: jobs, submissions, interviews, starts. Upload in that order, then send
the UTF-8 policy to /api/ingest/policy. Fixture headers show the required columns.
Rows require tenant/source/record IDs and updated_at. Imports are bounded,
validated, atomic and idempotent. Verified JWT claims determine tenant and role.

POST /api/ask with:

```json
{"question":"Why did ICU RN submissions increase while interviews decreased?","job_title":"ICU RN"}
```

The default compares the latest submission month against the previous month.
SQL counts distinct cohort submissions with interviews by as_of and divides by
submissions. Temporary Tenant A: 6/10 = 60%, then 4/20 = 20%.
The response separates metrics, mock interpretation and evidence. Policy retrieval
uses full-text search; citations are checked against authorized evidence.

POST fixtures/temporary/new_outcome.json to /api/outcomes, then ask again: 5/20 = 25%.
GET /api/sources and /api/retrieval-logs inspect provenance and retrieval snapshots.
Other-tenant target_tenant_id requests return 403. Viewers cannot ingest.
All six source/evidence/audit tables force RLS; identity settings are transaction-local.
The app is a non-owner without RLS bypass; migrations use a separate user.
Audit rows are append-only for the app. Metrics and evidence share a repeatable-read snapshot.

## Checks and limits

```powershell
docker compose --profile test run --rm tests
docker compose run --rm api ruff check .
docker compose run --rm api ruff format --check .
```

Tests exercise real PostgreSQL as the app user. The API binds to localhost only;
the database has no host port. Stop with docker compose down to retain data.
Bootstrap runs only on the first initialization of the database volume.

The mock describes predefined evidence factors; it cannot establish causation or
answer arbitrary business questions. Recent cohorts have less follow-up time.
Vector search, real LLM integration and PDF/Word parsing are not implemented.
Final synthetic data, browser UI, expanded documentation and a 5–10 minute recorded
demo remain for the following milestones.
