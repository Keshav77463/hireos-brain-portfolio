# Design, security and limitations

CSV is the input format; PostgreSQL is the persistent store. A database makes
tenant isolation, relationships, concurrent writes, deterministic aggregation
and repeatable evidence snapshots possible. Files alone would require rebuilding
these controls manually.

Jobs, submissions and outcomes have composite tenant/record keys. Outcome kind
distinguishes interviews and starts. Validated original row fields are retained
as JSON alongside indexed typed fields. Every evidence row links to a source
and keeps updated_at. Sources retain the latest filename and the last uploaded
file's SHA-256; the filename and hash describe the latest upload, not an immutable
version history.

One company uploads one 13-column CSV plus a separate policy document. Each row is a
submission with repeated job metadata and optional completed interview/start details.
The importer validates event groups and date order, deduplicates jobs, then normalizes
records in one transaction. Tenant identity comes from the verified token. Sources
are attached server-side. Existing source IDs and access levels are preserved.

The added metadata and complete validated CSV row live in existing JSONB payloads;
no schema migration is needed. specialty supplies the job title. client_name remains
client metadata rather than an invented location. This format covers jobs with
submissions and one interview/start per row; the outcome API can append more events.
Imports update/append, never delete events because cells are blank. Previously
ingested unused jobs may remain.

The same service implements HTTP and seed ingestion. Imports validate tenant IDs,
schema, links and timestamps and commit atomically. Record updates use timestamps
for idempotency and stale-update detection. The demo does not promise distributed
concurrent-import conflict resolution; conflicting concurrent writes can return
a sanitized error and should be retried after inspecting source versions.

## Conversion semantics

The baseline and current periods are submission cohorts. The numerator counts
distinct cohort submissions with at least one authorized interview event by as_of.
The denominator counts authorized submissions in that cohort. SQL EXISTS prevents
multiple interview events or starts from multiplying submissions. A zero denominator
produces null, not a misleading zero percent. Conversion change is percentage points.
Starts use the same distinct-submission definition.

This differs from counting interview events that occurred within the month.
It is a defensible submission-to-interview conversion definition, explicitly shown
in the answer. Recent cohorts have less follow-up time; ingestion delays and
missing outcomes can change the answer. The as_of filter controls event time;
it is not historical database time travel or policy-version reconstruction.

Ask runs calculations and evidence retrieval under PostgreSQL REPEATABLE READ.
This keeps record references and counts on one snapshot even if another request
adds an outcome concurrently. A subsequent Ask opens a new snapshot.

## Retrieval and reasoning

Operational evidence is selected deterministically from the metric scope.
Policy text uses PostgreSQL English full-text search with parameterized terms
derived from the selected job and conversion task, returning up to five chunks.
If no full-text match exists, up to five authorized chunks are shown as context;
the response labels that fallback. This is deliberately small and explainable.

The provider interface is separate from retrieval. The shipped mock formats actual
computed values, recorded queues and explicit rejection reasons; it never executes
instructions found in a question or document. Citation validation permits only
the current authorized evidence IDs. Rejected provider output releases no interpretation.
Queue statuses alone are not treated as proof of a delay's cause.
Citation checking verifies reference membership, not entailment or factual truth;
a future external LLM would also need claim-level grounding evaluation.

## Security controls

- Signed HS256 tokens require expiry, issuer, audience, tenant, subject and a known role.
  Tenant/role never come from untrusted headers or a chosen upload field.
- The application role is a non-owner without superuser or BYPASSRLS privileges.
  A separate migrator owns the schema. All evidence/source/audit tables force RLS.
- Transaction-local tenant, role and user settings expire on commit or rollback.
  Application queries also include tenant filters. Foreign keys include tenant.
- Source visibility uses viewer < recruiter < admin. Submissions must also have
  accessible jobs; outcomes accessible submissions. An admin cannot cross tenants.
- Viewers can read scoped evidence and Ask, but cannot ingest. Source access levels
  cannot be changed via imports. Restricted source records never enter the numerator,
  denominator, retrieval or citations for an unauthorized role.
- Retrieval logs contain the question, actor, role, timestamp, status, evidence IDs
  and computed snapshot. The app has SELECT/INSERT only on logs. Non-admin users
  read only their own logs at or below their present role; tenant admins read their
  own tenant's logs. Queries are logged, not every lower-level SQL access.
- Upload bounds limit parser/memory use. Parameterized SQL, strict row schemas,
  untrusted-text rendering, CSP, no-store responses and loopback-only binding
  reduce common input and browser risks.
- No real candidate records, credentials, production access or external APIs are used.
  Local secrets are generated into ignored .env; the browser receives only a demo JWT.
  Tokens remain in sessionStorage until disconnect/tab closure/expiry.

## Demo boundaries

This is an assignment demo, not a production recruiting system. Admin represents
the demo tenant owner; viewer is a reviewer role. It does not implement production
hiring-manager company scoping, user provisioning, token revocation, centralized
identity management, policy approval, job-based recruiter ownership or a full audit sink.
Application compromise could issue arbitrary local RLS session settings, so PostgreSQL
RLS complements trusted server authentication rather than replacing it.

Temporary fixtures are explicitly replaceable. Full PDF/DOCX parsing, vector retrieval,
BYO LLM credentials, broad natural-language planning, background import jobs, pagination
for large datasets, production hosting/rate limiting and monitoring are out of scope.
The pgvector extension is installed but not used; full-text retrieval needs no downloads.
No external model can establish causation from these records alone.
