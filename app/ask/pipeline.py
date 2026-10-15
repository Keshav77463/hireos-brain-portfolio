import re
from uuid import UUID

from fastapi import HTTPException

from app.ask.citation_validator import validate_citations
from app.db import tenant_session
from app.llm.mock import MockProvider
from app.metrics.service import calculate
from app.retrieval.service import FullTextRetriever, write_log

DEMO_TENANTS = {
    "a": UUID("11111111-1111-4111-8111-111111111111"),
    "b": UUID("22222222-2222-4222-8222-222222222222"),
}


def denied_scope(principal, request):
    if request.target_tenant_id and request.target_tenant_id != principal.tenant_id:
        return True
    mentioned = re.findall(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        request.question.lower(),
    )
    if any(UUID(value) != principal.tenant_id for value in mentioned):
        return True
    aliases = re.findall(r"\btenant[\s_-]+([ab])\b", request.question.lower())
    if any(DEMO_TENANTS[alias] != principal.tenant_id for alias in aliases):
        return True
    return bool(re.search(r"\b(all|other|cross)[\s-]+tenants?\b", request.question.lower()))


def answer(principal, request, provider=None):
    status = None
    if denied_scope(principal, request):
        status = "denied"
    elif not re.search(r"\b(conversion|submissions?|interviews?)\b", request.question.lower()):
        status = "unsupported"
    if status:
        with tenant_session(principal) as session:
            write_log(session, principal, request.question, status, [], {})
        raise HTTPException(
            403 if status == "denied" else 422,
            "Cross-tenant questions are denied."
            if status == "denied"
            else "This demo supports submission-to-interview conversion questions. "
            "Choose the job title and comparison dates using the structured fields.",
        )
    provider = provider or MockProvider()
    with tenant_session(principal, snapshot=True) as session:
        metrics, records = calculate(session, principal, request)
        if metrics is None or not (
            metrics["baseline"]["submissions"] + metrics["current"]["submissions"]
        ):
            log_id = write_log(session, principal, request.question, "no_data", [], metrics or {})
            return {
                "status": "no_data",
                "tenant_id": str(principal.tenant_id),
                "message": "No authorized submissions match this comparison.",
                "metrics": metrics,
                "interpretation": [],
                "evidence": [],
                "log_id": log_id,
            }
        policies = FullTextRetriever().retrieve(
            session, principal, f"{request.job_title} interview documents client review"
        )
        computed = [
            {
                "id": f"metric:{period}",
                "kind": "computed_metric",
                "record_id": period,
                "source_id": "deterministic_sql",
                "data": metrics[period],
                "supporting_record_ids": [
                    r["id"] for r in records if r["kind"] == "job" or r.get("period") == period
                ],
            }
            for period in ("baseline", "current")
        ]
        evidence = [*computed, *records, *policies]
        claims = provider.explain(metrics, evidence)
        try:
            validate_citations(claims, evidence)
        except ValueError:
            log_id = write_log(session, principal, request.question, "citation_rejected", [], {})
            return {
                "status": "citation_rejected",
                "message": "Provider output failed citation validation; no answer was released.",
                "metrics": metrics,
                "interpretation": [],
                "evidence": evidence,
                "log_id": log_id,
            }
        log_id = write_log(
            session, principal, request.question, "answered", [e["id"] for e in evidence], metrics
        )
        return {
            "status": "answered",
            "tenant_id": str(principal.tenant_id),
            "metrics": metrics,
            "interpretation_provider": provider.name,
            "interpretation": claims,
            "evidence": evidence,
            "log_id": log_id,
            "limitations": [
                "Cohort conversion counts submissions with any visible interview by as_of; "
                "it is not the number of interview events occurring within each month.",
                "Recent cohorts have less follow-up time. "
                "Late or missing outcomes can change rates.",
                "Reasons are source labels, not independently verified causal explanations.",
                "Metrics include only records visible to your tenant and role.",
                "Question parsing is bounded; job and dates come from structured fields.",
            ],
        }
