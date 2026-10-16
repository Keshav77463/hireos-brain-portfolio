from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from app.config import get_settings

pytestmark = pytest.mark.unit


def claims():
    settings = get_settings()
    return {
        "sub": str(uuid4()),
        "tenant_id": str(uuid4()),
        "role": "recruiter",
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "exp": datetime.now(UTC) + timedelta(minutes=5),
    }


def token(payload, signing_key=None):
    key = signing_key or get_settings().jwt_secret.get_secret_value()
    return jwt.encode(payload, key, algorithm="HS256")


def test_verified_identity_ignores_tenant_and_role_headers(client):
    payload = claims()
    response = client.get(
        "/api/me",
        headers={
            "Authorization": f"Bearer {token(payload)}",
            "X-Tenant-ID": str(uuid4()),
            "X-Role": "admin",
        },
    )
    assert response.status_code == 200
    assert response.json() == {
        "user_id": payload["sub"],
        "tenant_id": payload["tenant_id"],
        "role": "recruiter",
    }


@pytest.mark.parametrize(
    "change",
    [
        {"iss": "another-issuer"},
        {"aud": "another-api"},
        {"exp": datetime.now(UTC) - timedelta(minutes=1)},
        {"role": "superuser"},
        {"tenant_id": "not-a-uuid"},
        {"sub": "not-a-uuid"},
    ],
)
def test_invalid_claims_are_rejected(client, change):
    payload = claims() | change
    response = client.get("/api/me", headers={"Authorization": f"Bearer {token(payload)}"})
    assert response.status_code == 401


def test_forged_signature_is_rejected(client):
    response = client.get(
        "/api/me",
        headers={"Authorization": f"Bearer {token(claims(), 'different-test-key' * 3)}"},
    )
    assert response.status_code == 401


def test_missing_token_and_expiry_are_rejected(client):
    assert client.get("/api/me").status_code == 401
    payload = claims()
    del payload["exp"]
    response = client.get("/api/me", headers={"Authorization": f"Bearer {token(payload)}"})
    assert response.status_code == 401
