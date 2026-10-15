from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, UploadFile
from sqlalchemy import select

from app.ask.pipeline import answer
from app.ask.schemas import AskRequest
from app.auth.jwt import AuthenticatedPrincipal
from app.db import tenant_session
from app.ingest.schemas import AccessRole, Identifier, OutcomeInput
from app.ingest.service import MAX_BYTES, ingest_csv, ingest_outcome, ingest_policy, list_sources
from app.models import RetrievalLog

router = APIRouter(prefix="/api", tags=["evidence pipeline"])


@router.post("/ingest/csv")
def upload_csv(
    principal: AuthenticatedPrincipal,
    kind: Annotated[Literal["jobs", "submissions", "interviews", "starts"], Form()],
    source_id: Annotated[Identifier, Form()],
    file: Annotated[UploadFile, File()],
    min_role: Annotated[AccessRole, Form()] = "viewer",
):
    return ingest_csv(
        principal,
        kind,
        source_id,
        min_role,
        file.filename or "data.csv",
        file.file.read(MAX_BYTES + 1),
    )


@router.post("/ingest/policy")
def upload_policy(
    principal: AuthenticatedPrincipal,
    source_id: Annotated[Identifier, Form()],
    file: Annotated[UploadFile, File()],
    min_role: Annotated[AccessRole, Form()] = "viewer",
):
    return ingest_policy(
        principal, source_id, min_role, file.filename or "policy.md", file.file.read(MAX_BYTES + 1)
    )


@router.post("/outcomes")
def new_outcome(principal: AuthenticatedPrincipal, row: OutcomeInput):
    return ingest_outcome(principal, row)


@router.post("/ask")
def ask(principal: AuthenticatedPrincipal, request: AskRequest):
    return answer(principal, request)


@router.post("/metrics")
def metrics(principal: AuthenticatedPrincipal, request: AskRequest):
    # Use the same scope validation, log and snapshot as Ask, with interpretation removed.
    result = answer(principal, request)
    return {
        "metrics": result["metrics"],
        "evidence": result["evidence"],
        "log_id": result["log_id"],
    }


@router.get("/sources")
def sources(principal: AuthenticatedPrincipal):
    return list_sources(principal)


@router.get("/retrieval-logs")
def logs(principal: AuthenticatedPrincipal):
    with tenant_session(principal) as session:
        entries = session.scalars(
            select(RetrievalLog)
            .where(RetrievalLog.tenant_id == principal.tenant_id)
            .order_by(RetrievalLog.created_at.desc(), RetrievalLog.record_id)
            .limit(30)
        )
        return [
            {
                "id": str(e.record_id),
                "tenant_id": str(e.tenant_id),
                "user_id": str(e.user_id),
                "role": e.role,
                "question": e.question,
                "status": e.status,
                "evidence_ids": e.evidence_ids,
                "metrics": e.metrics,
                "created_at": e.created_at.isoformat(),
            }
            for e in entries
        ]
