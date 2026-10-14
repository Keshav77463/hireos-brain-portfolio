# HireOS Brain

A recruiting analytics prototype built with Python 3.12 and FastAPI.

## Current milestone

This commit establishes the Python project and a minimal runnable API.
It includes an application status endpoint, a basic health endpoint,
and interactive API documentation.

Database integration, authentication, tenant isolation, CSV ingestion,
conversion metrics, and evidence-backed answers are subsequent milestones.

## Run locally

Install Python 3.12 and [uv](https://docs.astral.sh/uv/).
From the repository directory:

```powershell
uv sync --locked
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- Application status: http://localhost:8000/
- Basic health check: http://localhost:8000/health
- API documentation: http://localhost:8000/docs

The health endpoint confirms that the API responds; it does not yet check a database.
This milestone requires no credentials or external APIs.

## Code checks

```powershell
uv run ruff check .
uv run ruff format --check .
```
