"""Generate small, replaceable synthetic development fixtures, not final demo data."""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "temporary"
TENANTS = {
    "a": "11111111-1111-4111-8111-111111111111",
    "b": "22222222-2222-4222-8222-222222222222",
}


def write_csv(folder, kind, tenant, records):
    source_id = f"{kind}_{tenant}"
    rows = [
        {
            "tenant_id": TENANTS[tenant],
            "source_id": source_id,
            "record_id": record.pop("record_id"),
            "updated_at": record.pop("updated_at"),
            **record,
        }
        for record in records
    ]
    with (folder / f"{source_id}.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    for tenant in ("a", "b"):
        folder = ROOT / f"tenant_{tenant}"
        folder.mkdir(parents=True, exist_ok=True)
        prefix = tenant.upper()
        job_id = f"JOB-{prefix}-ICU"
        write_csv(
            folder,
            "jobs",
            tenant,
            [
                {
                    "record_id": job_id,
                    "updated_at": "2026-05-01T00:00:00Z",
                    "title": "ICU RN",
                    "location": f"Synthetic facility {prefix}",
                },
                {
                    "record_id": f"JOB-{prefix}-ER",
                    "updated_at": "2026-05-01T00:00:00Z",
                    "title": "ER RN",
                    "location": f"Synthetic facility {prefix}",
                },
            ],
        )
        submissions, interviews, starts = [], [], []
        sizes = (10, 20) if tenant == "a" else (2, 3)
        interview_counts = (6, 4) if tenant == "a" else (1, 1)
        for month, size, interviewed in zip((5, 6), sizes, interview_counts, strict=True):
            code = "M" if month == 5 else "J"
            for number in range(1, size + 1):
                sub_id = f"SUB-{prefix}-{code}{number:02d}"
                submitted = f"2026-{month:02d}-10T09:00:00Z"
                reason = (
                    "ready"
                    if number <= interviewed
                    else ("awaiting_documents" if number % 2 else "awaiting_client_review")
                )
                submissions.append(
                    {
                        "record_id": sub_id,
                        "updated_at": submitted,
                        "job_id": job_id,
                        "candidate_alias": f"Synthetic-{prefix}-{code}{number:02d}",
                        "submitted_at": submitted,
                        "reason": reason,
                    }
                )
                if number <= interviewed:
                    event = f"2026-{month:02d}-15T10:00:00Z"
                    interviews.append(
                        {
                            "record_id": f"INT-{prefix}-{code}{number:02d}",
                            "updated_at": event,
                            "submission_id": sub_id,
                            "occurred_at": event,
                        }
                    )
                    if number == 1 and (tenant == "a" or month == 5):
                        start = f"2026-{month:02d}-20T10:00:00Z"
                        starts.append(
                            {
                                "record_id": f"START-{prefix}-{code}{number:02d}",
                                "updated_at": start,
                                "submission_id": sub_id,
                                "occurred_at": start,
                            }
                        )
        for kind, rows in (
            ("submissions", submissions),
            ("interviews", interviews),
            ("starts", starts),
        ):
            write_csv(folder, kind, tenant, rows)
        (folder / f"policy_{tenant}.md").write_text(
            f"# Temporary development policy — Tenant {prefix}\n\n"
            "This policy is entirely synthetic and exists only to exercise evidence retrieval.\n\n"
            "## ICU RN interview preparation\n\n"
            "Before an ICU RN interview is scheduled, the demo recruiter checks the submitted "
            "document packet. Records awaiting documents remain in a preparation queue.\n\n"
            "## Client review\n\n"
            "After submission, a synthetic client reviewer approves interview scheduling. "
            "Records awaiting client review remain queued. A recorded queue is not proof of "
            "why an individual interview did not occur.\n",
            encoding="utf-8",
        )
    outcome = {
        "tenant_id": TENANTS["a"],
        "source_id": "manual-outcomes",
        "record_id": "INT-A-NEW-01",
        "submission_id": "SUB-A-J05",
        "kind": "interview",
        "occurred_at": "2026-06-25T10:00:00Z",
        "updated_at": "2026-06-25T10:00:00Z",
        "min_role": "viewer",
    }
    (ROOT / "new_outcome.json").write_text(json.dumps(outcome, indent=2) + "\n", encoding="utf-8")
    print("Temporary synthetic fixtures generated: Tenant A 30 submissions, Tenant B 5.")


if __name__ == "__main__":
    main()
