from fastapi import FastAPI

app = FastAPI(
    title="HireOS Brain",
    version="0.1.0",
    description="Recruiting analytics prototype: initial project setup.",
)


@app.get("/", tags=["status"])
def index() -> dict[str, str]:
    return {"application": "HireOS Brain", "milestone": "project_setup", "api_reference": "/docs"}


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
