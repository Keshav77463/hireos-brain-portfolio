from fastapi import FastAPI

from app.api.health import router as health_router
from app.auth.jwt import AuthenticatedPrincipal
from app.auth.principal import Principal

app = FastAPI(
    title="HireOS Brain",
    version="0.1.0",
    description="Tenant-isolated recruiting analytics foundation.",
)
app.include_router(health_router)


@app.get("/", tags=["status"])
def index() -> dict[str, str]:
    return {"application": "HireOS Brain", "milestone": "foundation", "api_reference": "/docs"}


@app.get("/api/me", response_model=Principal, tags=["authentication"])
def who_am_i(principal: AuthenticatedPrincipal) -> Principal:
    return principal
