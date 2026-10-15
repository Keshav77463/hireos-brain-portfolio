import re
from typing import Protocol
from uuid import uuid4

from sqlalchemy import func, select

from app.metrics.service import evidence
from app.models import PolicyChunk, RetrievalLog, Source


class Retriever(Protocol):
    def retrieve(self, session, principal, terms: str) -> list[dict]: ...


class FullTextRetriever:
    def retrieve(self, session, principal, terms: str) -> list[dict]:
        vector = func.to_tsvector("english", PolicyChunk.body)
        words = re.findall(r"[A-Za-z0-9]+", terms)
        query = func.websearch_to_tsquery("english", " OR ".join(words))
        base = (
            select(PolicyChunk, Source.filename)
            .join(
                Source,
                (Source.tenant_id == PolicyChunk.tenant_id)
                & (Source.source_id == PolicyChunk.source_id),
            )
            .where(PolicyChunk.tenant_id == principal.tenant_id)
        )
        rows = session.execute(
            base.where(vector.op("@@")(query))
            .order_by(func.ts_rank(vector, query).desc(), PolicyChunk.record_id)
            .limit(5)
        ).all()
        method = "full_text"
        if not rows:
            rows = session.execute(base.order_by(PolicyChunk.record_id).limit(5)).all()
            method = "authorized_context_fallback"
        return [
            {**evidence(row, "policy", filename), "retrieval_method": method}
            for row, filename in rows
        ]


def write_log(session, principal, question, status, evidence_ids, metrics):
    log_id = uuid4()
    session.add(
        RetrievalLog(
            tenant_id=principal.tenant_id,
            record_id=log_id,
            user_id=principal.user_id,
            role=principal.role,
            question=question,
            status=status,
            evidence_ids=evidence_ids,
            metrics=metrics,
        )
    )
    session.flush()
    return str(log_id)
