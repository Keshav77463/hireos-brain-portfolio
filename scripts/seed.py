"""Load temporary development fixtures through the same ingestion service as uploads."""

import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth.principal import Principal  # noqa: E402
from app.ingest.service import ingest_csv, ingest_policy  # noqa: E402

ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "temporary"


def main():
    for alias, tenant in (
        ("a", "11111111-1111-4111-8111-111111111111"),
        ("b", "22222222-2222-4222-8222-222222222222"),
    ):
        identity = Principal(tenant_id=UUID(tenant), user_id=UUID(tenant), role="admin")
        folder = ROOT / f"tenant_{alias}"
        for kind in ("jobs", "submissions", "interviews", "starts"):
            file = folder / f"{kind}_{alias}.csv"
            result = ingest_csv(identity, kind, file.stem, "viewer", file.name, file.read_bytes())
            print(alias, kind, result)
        file = folder / f"policy_{alias}.md"
        print(
            alias,
            "policy",
            ingest_policy(identity, file.stem, "viewer", file.name, file.read_bytes()),
        )
    print("Temporary fixtures loaded. new_outcome.json is deliberately NOT ingested.")


if __name__ == "__main__":
    main()
