"""Print a short-lived synthetic demo token; never print the signing key."""

import argparse
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import jwt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    tenants = {
        "a": UUID("11111111-1111-4111-8111-111111111111"),
        "b": UUID("22222222-2222-4222-8222-222222222222"),
    }
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--tenant-id", type=UUID)
    group.add_argument("--tenant", choices=["a", "b"])
    parser.add_argument("--user-id", type=UUID)
    parser.add_argument("--role", required=True, choices=["viewer", "recruiter", "admin"])
    args = parser.parse_args()
    tenant_id = tenants[args.tenant] if args.tenant else args.tenant_id
    user_id = args.user_id or tenant_id
    settings = get_settings()
    now = datetime.now(UTC)
    print(
        jwt.encode(
            {
                "sub": str(user_id),
                "tenant_id": str(tenant_id),
                "role": args.role,
                "iss": settings.jwt_issuer,
                "aud": settings.jwt_audience,
                "iat": now,
                "exp": now + timedelta(minutes=30),
            },
            settings.jwt_secret.get_secret_value(),
            algorithm="HS256",
        )
    )


if __name__ == "__main__":
    main()
