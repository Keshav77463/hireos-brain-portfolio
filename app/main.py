from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.health import router as health_router
from app.api.middleware import RequestLimitMiddleware
from app.api.pipeline import router as pipeline_router
from app.auth.jwt import AuthenticatedPrincipal
from app.auth.principal import Principal

app = FastAPI(
    title="HireOS Brain",
    version="0.2.0",
    description="Tenant-isolated ingestion, deterministic conversion and cited answers.",
)
app.include_router(health_router)
app.include_router(pipeline_router)
app.add_middleware(RequestLimitMiddleware)


@app.get("/", tags=["status"])
def index() -> dict[str, str]:
    return {"application": "HireOS Brain", "milestone": "pipeline", "api_reference": "/docs"}


@app.exception_handler(IntegrityError)
def conflict(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=409,
        content={"detail": "Import conflicts with an existing or inaccessible record."},
    )


@app.exception_handler(SQLAlchemyError)
def database_error(request: Request, exc: SQLAlchemyError):
    return JSONResponse(status_code=503, content={"detail": "Database request could not complete."})


@app.get("/api/me", response_model=Principal, tags=["authentication"])
def who_am_i(principal: AuthenticatedPrincipal) -> Principal:
    return principal
