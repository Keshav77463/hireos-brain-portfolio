# Temporary development fixtures

All people, facilities, records and policy passages are synthetic. These small fixtures
exercise the pipeline while the final assignment dataset is being prepared.
They cover two comparison months (May and June 2026), not six months.

Tenant A: 10 baseline submissions / 6 interviewed = 60%; 20 current submissions /
4 interviewed = 20%. Eight current submissions without interviews await documents,
and eight await client review. The labels suggest process queues; they do not prove causation.

Tenant B: 2 baseline submissions / 1 interviewed; 3 current submissions / 1 interviewed.
Both tenants deliberately use the same job title to exercise isolation.

There are four jobs, 35 submissions, 12 interview records, three starts and two policy files.
The separate new_outcome.json interviews SUB-A-J05, changing Tenant A's current rate
to 5 / 20 = 25%. The seed script does not load this outcome.

Regenerate with Python 3.12: python scripts/generate_temp_fixtures.py.
Load with Docker Compose: docker compose exec api python scripts/seed.py.
Reloading is idempotent and preserves separately added outcomes.
