# Demo walkthrough (5–10 minutes)

Follow this walkthrough to demonstrate ingestion, evidence-backed calculations,
outcome freshness, and tenant isolation using the bundled synthetic fixtures.

1. **Setup and identity (1 minute).** Show Compose services and /health. Explain
   app versus migrator DB users. Generate a Tenant A admin token locally and connect
   at http://localhost:8000. Keep .env and keys out of screen sharing or recordings.
2. **Upload evidence (1–2 minutes).** Using the browser, upload Tenant A's single
   operations_a.csv, then policy_a.md from fixtures/temporary/tenant_a.
   Explain one row per submission and optional interview/start fields. Show how
   tenant/source references are attached by the backend and inspect updated_at.
   Begin from an unseeded demo tenant so the upload is observable.
3. **Ask and inspect (2 minutes).** Ask the conversion question. Show baseline
   6/10 = 60%, current 4/20 = 20%, and the -40 percentage-point change.
   Explain the submission-cohort definition and the one-count-per-submission numerator.
   Show the separate mock interpretation, a computed metric citation, an operational
   source record and a policy chunk. Explain that queues suggest possible factors,
   not proven causes, and that recent cohorts have less follow-up time.
4. **Freshness (1 minute).** Add the interview for SUB-A-J05 with the outcome form.
   Ask again. Show current 5/20 = 25% and the new outcome citation. Show both old and
   new metric snapshots in the retrieval log. Repeat ingestion to show idempotency.
5. **Tenant and role checks (1–2 minutes).** Click the cross-tenant test: HTTP 403
   and an empty-evidence denied log. Connect a Tenant B token and show its distinct
   result or empty state if not yet uploaded. Connect a viewer token; attempts to
   upload/add an outcome must fail. Existing evidence remains readable within scope.
6. **Explain implementation (1 minute).** Walk through ingestion/service.py,
   metrics/service.py, ask/pipeline.py and migration 0002. Show automated test results.
   State the mock-provider choice, temporary fixture status and remaining limitations.

Use the browser upload steps to demonstrate ingestion; the seed script is convenient
for preparing a local development environment. New outcomes persist in the database;
rerunning seed does not erase them. For a repeatable fresh walkthrough, generate files
for a fresh synthetic tenant ID and mint a token for it instead of deleting existing data.
