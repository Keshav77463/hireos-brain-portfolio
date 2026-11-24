# Temporary development fixtures

All people, facilities, records and policy passages are synthetic. These small fixtures
exercise ingestion, conversion calculations, freshness, and tenant isolation.
They cover two comparison months (May and June 2026), not six months.

Tenant A: 10 baseline submissions / 6 interviewed = 60%; 20 current submissions /
4 interviewed = 20%. Eight current submissions without interviews await documents,
and eight await client review. The labels suggest process queues; they do not prove causation.

Tenant B: 2 baseline submissions / 1 interviewed; 3 current submissions / 1 interviewed.
Both tenants deliberately use the same job title to exercise isolation.

The default A/B fixtures contain two ICU jobs, 35 submissions, 12 interviews and three starts.
Tenant A uploads operations_a.csv (30 submission rows); Tenant B uploads operations_b.csv
(5 submission rows). Each uses the required 13-column, one-row-per-submission schema.
Tenant/source references are attached by the backend; those fields are not in the CSV.
Statuses reflect source snapshots and alone do not establish the reason for a delay.
Repeated job details must be consistent; outcome groups are
blank until events occur. Existing old demo records/source IDs are preserved during
newer imports. Older unused jobs and separately added outcomes are not deleted.

The separate new_outcome.json interviews SUB-A-J05, changing Tenant A's current rate
to 5 / 20 = 25%. The seed script does not load this outcome.

Regenerate with Python 3.12: python scripts/generate_temp_fixtures.py.
Load with Docker Compose: docker compose exec api python scripts/seed.py.
Reloading is idempotent and preserves separately added outcomes.

Optional manually uploaded examples:

- [Tenant C](tenant_c/README.md): seven submissions, with conversion 2/3 = 66.67%
  in May and 1/4 = 25% in June, plus a source-recorded rejection reason.
- [Correction example](examples/README.md): preserves the edited Tenant A CSV and
  explains why blank cells do not remove a previously stored interview.

The generator and seed script use only the standard A/B samples. They do not
overwrite or load these optional examples.
