from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db import get_engine

router = APIRouter(tags=["health"])


@router.get("/health/live")
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health")
def readiness() -> dict[str, str]:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
            revision = connection.scalar(text("SELECT version_num FROM hireos.alembic_version"))
            vector_version = connection.scalar(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            )
            app_role = connection.execute(
                text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
            ).one()
            row_security = connection.execute(
                text(
                    "SELECT relrowsecurity, relforcerowsecurity "
                    "FROM pg_class WHERE oid = 'hireos.sources'::regclass"
                )
            ).one()
        if revision != "0002" or not vector_version or any(app_role) or not all(row_security):
            raise HTTPException(status_code=503, detail="Database foundation is not ready.")
        return {"status": "ok", "database": "connected", "migration": revision}
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database foundation is not ready.") from exc
