"""Generate demo credentials without printing them or overwriting a file."""

import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    destination = ROOT / ".env"
    content = "\n".join(
        [
            "POSTGRES_DB=hireos",
            "POSTGRES_USER=hireos_bootstrap",
            f"POSTGRES_PASSWORD={secrets.token_urlsafe(32)}",
            f"MIGRATOR_DB_PASSWORD={secrets.token_urlsafe(32)}",
            f"APP_DB_PASSWORD={secrets.token_urlsafe(32)}",
            f"JWT_SECRET={secrets.token_urlsafe(48)}",
            "JWT_ISSUER=hireos-demo",
            "JWT_AUDIENCE=hireos-api",
            "API_PORT=8000",
            "",
        ]
    )
    try:
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
            output.write(content)
    except FileExistsError:
        print(".env already exists; left unchanged.")
        return
    print("Created git-ignored .env with random local demo credentials. No credentials printed.")


if __name__ == "__main__":
    main()
