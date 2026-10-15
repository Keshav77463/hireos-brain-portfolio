# API reference

Interactive OpenAPI reference: /docs. Machine-readable schema: /openapi.json.
All /api endpoints require Authorization: Bearer TOKEN. JWT claims determine identity;
headers or payload values cannot switch tenants. The root HTML and health endpoints
are public and disclose no records.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | /api/me | Verified tenant, user and role |
| POST | /api/ingest/csv | Atomic multipart CSV import |
| POST | /api/ingest/policy | Multipart UTF-8 text/Markdown policy |
| POST | /api/outcomes | Add interview/start to an accessible submission |
| POST | /api/ask | SQL metrics, mock interpretation, evidence and audit ID |
| POST | /api/metrics | Same scoped calculation and evidence without interpretation |
| GET | /api/sources | Authorized source provenance |
| GET | /api/retrieval-logs | Latest 30 authorized retrieval entries |
| GET | /health | Database and migration readiness |
| GET | /health/live | Process liveness |

## Uploads

Multipart fields: source_id, min_role (viewer default), file. CSV also requires
kind: jobs, submissions, interviews or starts. Upload as recruiter or admin.
Identifiers accept letters, digits, dots, underscores and hyphens; maximum 128 characters.
Each file is limited to 2 MiB; total request body to 3 MiB; CSV to 5,000 rows.
UTC timestamps must include an explicit offset, for example 2026-06-10T09:00:00Z.
Whitespace is stripped. The CSV header must match the documented schema exactly.

Common required CSV columns:
tenant_id, source_id, record_id, updated_at.

| kind | Additional required columns |
| --- | --- |
| jobs | title, location |
| submissions | job_id, candidate_alias, submitted_at, reason |
| interviews | submission_id, occurred_at |
| starts | submission_id, occurred_at |

Submission reason: ready, awaiting_documents, awaiting_client_review or withdrawn.
The tenant_id must match the JWT, and every source_id must match the multipart field.
Jobs must exist before submissions; submissions before outcomes.
Outcome times cannot precede submission time. updated_at cannot precede an event.
Submission job/time and outcome links/kind/time are immutable; other content can be
updated using a newer updated_at. Unchanged records are skipped, older updates are
reported as stale, and conflicting content at an equal timestamp returns 409.
Changing an existing source's type or minimum role returns 409.
An invalid row rolls back the complete file, including its newly created source.

Policy source IDs must be distinct from CSV source IDs. Plain text is stored in
bounded paragraph chunks, with stable source-based chunk IDs and updated_at.
Identical policy bytes are idempotent; changed policy content replaces its chunks.

## Ask request

```json
{
  "question": "Why did ICU RN submissions increase while interviews decreased?",
  "job_title": "ICU RN",
  "baseline_start": "2026-05-01",
  "baseline_end": "2026-05-31",
  "current_start": "2026-06-01",
  "current_end": "2026-06-30",
  "as_of": "2026-07-01"
}
```

Question and structured job_title are independent: this bounded demo takes the
subject from job_title, rather than guessing a different subject from prose.
Leave all four period fields empty to compare the latest accessible submission
month with its preceding month. as_of defaults to today's UTC date.
Dates are inclusive and use UTC; periods must be ordered and non-overlapping.
Supported dates are 1970 through 2100.
Maximum 500 matching submissions per answer; narrow the dates for larger data.
target_tenant_id can be supplied for an isolation test: another tenant returns 403.
Questions explicitly naming another demo tenant/UUID or all tenants are also denied.
Other wording never widens the authenticated database scope.

The response separates metrics (provider deterministic_sql) from interpretation
(provider deterministic_mock). evidence contains source/record identifiers,
timestamps, filenames, original validated payloads, policy chunks and computed
metric references. Each interpretation claim has citations validated against this set.
log_id identifies the persisted retrieval snapshot. status can be answered,
no_data or citation_rejected; the last two provide no generated interpretation.

## New outcome

```json
{
  "tenant_id": "11111111-1111-4111-8111-111111111111",
  "source_id": "manual-outcomes",
  "record_id": "INT-A-NEW-01",
  "submission_id": "SUB-A-J05",
  "kind": "interview",
  "occurred_at": "2026-06-25T10:00:00Z",
  "updated_at": "2026-06-25T10:00:00Z",
  "min_role": "viewer"
}
```

POST this JSON to /api/outcomes. It adds an outcome source if necessary.
Reusing the same record is idempotent. Different interview events attached to
one submission still count as one interviewed submission.

HTTP errors: 401 invalid/missing token; 403 access denied; 409 record/source conflict;
413 request too large; 422 invalid schema/link/question/dates; 503 database unavailable.
Database errors are sanitized and do not expose SQL, credentials or hidden rows.
