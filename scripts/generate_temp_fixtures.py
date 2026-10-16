"""Small temporary fixtures: one row per submission, using the agreed 13-column schema."""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "temporary"
COLUMNS = [
    "submission_id",
    "job_id",
    "client_name",
    "specialty",
    "candidate_ref",
    "submitted_at",
    "status",
    "rejection_reason",
    "interview_id",
    "interviewed_at",
    "start_id",
    "started_at",
    "updated_at",
]


def main():
    for tenant in ("a", "b"):
        folder = ROOT / f"tenant_{tenant}"
        folder.mkdir(parents=True, exist_ok=True)
        prefix = tenant.upper()
        rows = []
        sizes = (10, 20) if tenant == "a" else (2, 3)
        interviews = (6, 4) if tenant == "a" else (1, 1)
        for month, size, interviewed in zip((5, 6), sizes, interviews, strict=True):
            code = "M" if month == 5 else "J"
            for number in range(1, size + 1):
                has_interview = number <= interviewed
                has_start = has_interview and number == 1 and (tenant == "a" or month == 5)
                status = (
                    "started"
                    if has_start
                    else "interviewed"
                    if has_interview
                    else ("awaiting_documents" if number % 2 else "awaiting_client_review")
                )
                rows.append(
                    {
                        "submission_id": f"SUB-{prefix}-{code}{number:02d}",
                        "job_id": f"JOB-{prefix}-ICU",
                        "client_name": f"Synthetic facility {prefix}",
                        "specialty": "ICU RN",
                        "candidate_ref": f"Synthetic-{prefix}-{code}{number:02d}",
                        "submitted_at": f"2026-{month:02d}-10T09:00:00Z",
                        "status": status,
                        "rejection_reason": "",
                        "interview_id": f"INT-{prefix}-{code}{number:02d}" if has_interview else "",
                        "interviewed_at": f"2026-{month:02d}-15T10:00:00Z" if has_interview else "",
                        "start_id": f"START-{prefix}-{code}{number:02d}" if has_start else "",
                        "started_at": f"2026-{month:02d}-20T10:00:00Z" if has_start else "",
                        # Newer than the original development fixtures; enriches existing records.
                        "updated_at": "2026-07-01T00:00:00Z",
                    }
                )
        with (folder / f"operations_{tenant}.csv").open(
            "w", newline="", encoding="utf-8"
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        (folder / f"policy_{tenant}.md").write_text(
            f"# Temporary development policy — Tenant {prefix}\n\n"
            "This policy is entirely synthetic and exists only to exercise evidence retrieval.\n\n"
            "## ICU RN interview preparation\n\n"
            "Before an ICU RN interview is scheduled, the demo recruiter checks the submitted "
            "document packet. Records awaiting documents remain in a preparation queue.\n\n"
            "## Client review\n\n"
            "After submission, a synthetic client reviewer approves interview scheduling. "
            "Records awaiting client review remain queued. A recorded queue is not proof of "
            "why an individual interview did not occur.\n\n"
            "## Recorded reasons\n\n"
            "The status and rejection_reason fields contain recorded workflow facts and "
            "explanations. A queue status alone does not establish the cause of a delay "
            "or rejection.\n",
            encoding="utf-8",
        )
    outcome = {
        "tenant_id": "11111111-1111-4111-8111-111111111111",
        "source_id": "manual-outcomes",
        "record_id": "INT-A-NEW-01",
        "submission_id": "SUB-A-J05",
        "kind": "interview",
        "occurred_at": "2026-06-25T10:00:00Z",
        "updated_at": "2026-06-25T10:00:00Z",
        "min_role": "viewer",
    }
    (ROOT / "new_outcome.json").write_text(json.dumps(outcome, indent=2) + "\n", encoding="utf-8")
    print("Temporary 13-column fixtures generated: Tenant A 30 rows, Tenant B 5 rows.")


if __name__ == "__main__":
    main()
