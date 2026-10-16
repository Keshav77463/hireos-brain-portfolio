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

Upload one operational CSV with multipart fields file and min_role (viewer default).
kind defaults to operational. Upload as recruiter or admin. File limit: 2 MiB;
request limit: 3 MiB; maximum 5,000 submission rows.
Use UTF-8 and timezone-aware timestamps such as 2026-06-10T09:00:00Z.

The exact 13-column header is:

```csv
submission_id,job_id,client_name,specialty,candidate_ref,submitted_at,status,rejection_reason,interview_id,interviewed_at,start_id,started_at,updated_at
```

One row represents one submission. All columns must exist; optional values use empty cells.

| Fields | Rules |
| --- | --- |
| submission_id | Required, unique in the CSV |
| job_id, client_name, specialty | Required; repeated jobs need consistent client/specialty |
| candidate_ref | Required; synthetic candidate reference for the demo |
| submitted_at, updated_at | Required; updated_at cannot precede any recorded event |
| status | submitted, awaiting_documents, awaiting_client_review, withdrawn, rejected, interviewed, started |
| rejection_reason | Required for rejected, empty for other statuses |
| interview_id, interviewed_at | Both supplied together for an interview that occurred, or both empty |
| start_id, started_at | Both supplied together, or both empty |

Identifiers accept letters, digits, dots, underscores and hyphens, maximum 128 characters.
Client/specialty are at most 120 characters; rejection reason 500.
Dates are timezone-aware. Interview cannot precede submission; start cannot precede
interview. A started status requires interview and start details. Interviewed
requires interview details. Pre-interview statuses cannot contain completed interviews.
Interview/start IDs share an outcomes table and must not collide.

Tenant comes only from the verified token. tenant_id, source_id and record_type are
not CSV columns. Optional multipart source_id supplies the namespace for new records
(default operations). Existing accessible records retain their source IDs and minimum
role. Imports cannot lower visibility. Source filename/hash describe the latest upload.

Repeated jobs are deduplicated and use the latest updated_at in their group. Normalized
jobs, submissions and outcomes are saved atomically. Blank outcome cells or absent rows
never delete previously stored data. Unchanged rows are idempotent; older timestamps
are reported as stale; conflicting content at the same timestamp returns 409.
Submission job/time and outcome links/kind/event time are immutable.

### Database mapping

| CSV information | Storage |
| --- | --- |
| job_id | jobs.record_id, linked from submissions.job_id |
| specialty | jobs.title and job payload |
| client_name | Job payload; location is not invented |
| submission_id | submissions.record_id |
| candidate_ref | Submission payload, also candidate_alias for existing evidence consumers |
| status/rejection_reason | Submission JSON payload |
| All 13 validated fields | submissions.payload.csv_row |
| Interview/start IDs and dates | Separate outcomes linked to the submission |
| tenant/source/updated_at | Attached to each normalized record |

Existing JSONB columns store metadata; migrations 0001/0002 remain sufficient.
The CSV covers jobs with submissions and one interview/start per row. The outcome
API can append additional events. Status is a source snapshot; newer outcomes may
exist even when an older CSV status is unchanged.

For compatibility, kind=jobs/submissions/interviews/starts accepts the original
type-specific CSV headers and source_id. Only those formats accept an explicit
tenant_id, which must match the verified token. The browser uses the 13-column schema.

Policy upload requires source_id, min_role and file. Use a source ID distinct from
the operational sources. UTF-8 text/Markdown is chunked; identical bytes are idempotent,
and changed content replaces chunks.

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
