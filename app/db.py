from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from app.auth.principal import Principal
from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    return create_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={"connect_timeout": 5},
    )


@contextmanager
def tenant_session(principal: Principal, *, snapshot: bool = False) -> Iterator[Session]:
    """Set identity for one transaction; never leave it on a pooled connection."""
    with Session(get_engine()) as session, session.begin():
        if snapshot:
            session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
        session.execute(
            text(
                "SELECT set_config('app.tenant_id', :tenant_id, true), "
                "set_config('app.role', :role, true), "
                "set_config('app.user_id', :user_id, true)"
            ),
            {
                "tenant_id": str(principal.tenant_id),
                "role": principal.role,
                "user_id": str(principal.user_id),
            },
        )
        yield session
