from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError

from app.auth.principal import Principal
from app.config import get_settings

bearer = HTTPBearer(auto_error=False)


def get_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Principal:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="A valid demo bearer token is required.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    settings = get_settings()
    try:
        claims = jwt.decode(
            credentials.credentials,
            settings.jwt_secret.get_secret_value(),
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={
                "require": ["exp", "iss", "aud", "sub", "tenant_id", "role"],
                "strict_aud": True,
            },
        )
        return Principal(tenant_id=claims["tenant_id"], user_id=claims["sub"], role=claims["role"])
    except (jwt.InvalidTokenError, ValidationError, KeyError) as exc:
        raise unauthorized from exc


AuthenticatedPrincipal = Annotated[Principal, Depends(get_principal)]
