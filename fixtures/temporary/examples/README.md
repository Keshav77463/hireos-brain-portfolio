# CSV correction example

`operations_a_corrected.csv` preserves the manually edited Tenant A sample.
Submission `SUB-A-M02` is awaiting documents, its interview cells are empty,
and its `updated_at` is July 2, 2026. The standard Tenant A sample retains the
original interview so its tests and acceptance walkthrough are reproducible.

Uploaded to a fresh authorized tenant, this example produces May 5/10 = 50%
and June 4/20 = 20%. Uploaded after the standard Tenant A sample, it changes
the submission status but retains the existing `INT-A-M02` outcome, so May
remains 6/10 = 60%. Empty cells do not delete previously ingested outcomes.

Use a fresh custom tenant token to compare both scenarios without deleting data.
The example is synthetic, manually maintained, and not loaded by `scripts/seed.py`.
