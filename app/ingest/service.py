"""Atomic, bounded imports used by both HTTP uploads and the demo seed script."""

import csv
import hashlib
import io
from datetime import UTC, datetime
from pathlib import PurePath

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import delete, select

from app.auth.principal import Principal
from app.db import tenant_session
from app.ingest.schemas import JobRow, OutcomeInput, OutcomeRow, SubmissionRow
from app.models import Job, Outcome, PolicyChunk, Source, Submission

MAX_BYTES = 2 * 1024 * 1024
ROW_TYPES = {
    "jobs": JobRow,
    "submissions": SubmissionRow,
    "interviews": OutcomeRow,
    "starts": OutcomeRow,
}
MODELS = {"jobs": Job, "submissions": Submission, "interviews": Outcome, "starts": Outcome}


def require_writer(principal: Principal):
    if principal.role not in ("recruiter", "admin"):
        raise HTTPException(403, "Your role cannot ingest data.")


def decode(data: bytes) -> str:
    if not data or len(data) > MAX_BYTES:
        raise HTTPException(422, "Upload must contain 1 byte to 2 MiB.")
    try:
        return data.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    except UnicodeDecodeError as exc:
        raise HTTPException(422, "Use UTF-8 text.") from exc


def parse_csv(data: bytes, kind: str, principal: Principal, source_id: str):
    if kind not in ROW_TYPES:
        raise HTTPException(422, "CSV type must be jobs, submissions, interviews or starts.")
    reader = csv.DictReader(io.StringIO(decode(data)), strict=True)
    fields = reader.fieldnames or []
    schema_fields = ROW_TYPES[kind].model_fields
    required = {name for name, field in schema_fields.items() if field.is_required()}
    if (
        len(set(fields)) != len(fields)
        or not required.issubset(fields)
        or not set(fields).issubset(schema_fields)
    ):
        raise HTTPException(422, f"Required CSV columns: {', '.join(ROW_TYPES[kind].model_fields)}")
    rows, identifiers = [], set()
    try:
        for line, raw in enumerate(reader, start=2):
            if len(rows) >= 5000:
                raise HTTPException(422, "Maximum 5,000 rows per upload.")
            try:
                row = ROW_TYPES[kind].model_validate(raw)
            except ValidationError as exc:
                # Return field names, never the original sensitive input or database errors.
                fields = ", ".join(str(e["loc"][0]) for e in exc.errors())
                raise HTTPException(422, f"Invalid row {line}; check: {fields}") from exc
            if row.tenant_id != principal.tenant_id:
                raise HTTPException(403, "CSV tenant does not match your authenticated tenant.")
            if row.source_id != source_id:
                raise HTTPException(422, f"Row {line}: source_id must match the upload source.")
            if row.record_id in identifiers:
                raise HTTPException(422, f"Row {line}: duplicate record_id.")
            identifiers.add(row.record_id)
            rows.append(row)
    except csv.Error as exc:
        raise HTTPException(422, "Malformed CSV.") from exc
    if not rows:
        raise HTTPException(422, "CSV must contain at least one data row.")
    return rows


def ensure_source(session, principal, source_id, filename, source_type, min_role):
    ranks = {"viewer": 1, "recruiter": 2, "admin": 3}
    if ranks[min_role] > ranks[principal.role]:
        raise HTTPException(403, "Cannot create a source above your access level.")
    source = session.get(Source, (principal.tenant_id, source_id))
    if source:
        if source.min_role != min_role or source.source_type != source_type:
            raise HTTPException(409, "Existing source type and access level cannot be changed.")
        return source
    source = Source(
        tenant_id=principal.tenant_id,
        source_id=source_id,
        filename=PurePath(filename.replace("\\", "/")).name[:255],
        source_type=source_type,
        min_role=min_role,
        created_by=principal.user_id,
    )
    session.add(source)
    session.flush()
    return source


def write_row(session, principal, kind, row, *, extra_payload=None, preserve_payload=False):
    model = MODELS[kind]
    payload = row.model_dump(mode="json", exclude_none=True)
    if kind in ("interviews", "starts"):
        payload["kind"] = "interview" if kind == "interviews" else "start"
    existing = session.get(model, (principal.tenant_id, row.record_id))
    if existing and preserve_payload:
        payload = {**existing.payload, **payload}
    if extra_payload:
        payload.update(extra_payload)
    if existing:
        if existing.source_id != row.source_id:
            raise HTTPException(409, "Record ID already belongs to another source.")
        if row.updated_at < existing.updated_at:
            return "stale"
        if row.updated_at == existing.updated_at:
            if existing.payload != payload:
                raise HTTPException(409, "Conflicting content at the same updated_at timestamp.")
            return "unchanged"
    values = {
        "source_id": row.source_id,
        "updated_at": row.updated_at,
        "payload": payload,
    }
    if kind == "jobs":
        values["title"] = row.title
    elif kind == "submissions":
        if not session.get(Job, (principal.tenant_id, row.job_id)):
            raise HTTPException(422, "Referenced job is unavailable under your access scope.")
        values.update(job_id=row.job_id, submitted_at=row.submitted_at)
        if existing and (
            existing.job_id != row.job_id or existing.submitted_at != row.submitted_at
        ):
            raise HTTPException(409, "A submission's job and submission time are immutable.")
    else:
        submission = session.get(Submission, (principal.tenant_id, row.submission_id))
        if not submission or row.occurred_at < submission.submitted_at:
            raise HTTPException(
                422, "Outcome needs an accessible submission and a later event time."
            )
        values.update(
            submission_id=row.submission_id,
            occurred_at=row.occurred_at,
            kind=payload["kind"],
        )
        if existing and (
            existing.submission_id != row.submission_id
            or existing.kind != payload["kind"]
            or existing.occurred_at != row.occurred_at
        ):
            raise HTTPException(409, "Outcome links, kind and event time are immutable.")
    if existing:
        for key, value in values.items():
            setattr(existing, key, value)
        status = "updated"
    else:
        session.add(model(tenant_id=principal.tenant_id, record_id=row.record_id, **values))
        status = "inserted"
    session.flush()
    return status


def ingest_csv(principal, kind, source_id, min_role, filename, data):
    require_writer(principal)
    rows = parse_csv(data, kind, principal, source_id)
    counts = {"inserted": 0, "updated": 0, "unchanged": 0, "stale": 0}
    with tenant_session(principal) as session:
        source = ensure_source(session, principal, source_id, filename, "csv", min_role)
        for row in rows:
            counts[write_row(session, principal, kind, row)] += 1
        source.content_sha256 = hashlib.sha256(data).hexdigest()
        source.updated_at = datetime.now(UTC)
    return {"source_id": source_id, "rows": len(rows), **counts}


def ingest_policy(principal, source_id, min_role, filename, data):
    require_writer(principal)
    text = decode(data)
    if len(text) > 32000:
        raise HTTPException(422, "Policy text must be at most 32,000 characters.")
    digest = hashlib.sha256(data).hexdigest()
    # Fixed paragraph chunks: no execution, tools, URLs or instructions are followed.
    chunks = []
    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()
        chunks.extend(paragraph[i : i + 1500] for i in range(0, len(paragraph), 1500))
    if not chunks or len(chunks) > 100:
        raise HTTPException(422, "Policy must contain 1 to 100 text chunks.")
    with tenant_session(principal) as session:
        source = ensure_source(session, principal, source_id, filename, "policy", min_role)
        stored = session.scalars(
            select(PolicyChunk).where(
                PolicyChunk.tenant_id == principal.tenant_id, PolicyChunk.source_id == source_id
            )
        ).all()
        if source.content_sha256 == digest and len(stored) == len(chunks):
            return {"source_id": source_id, "chunks": len(chunks), "status": "unchanged"}
        session.execute(
            delete(PolicyChunk).where(
                PolicyChunk.tenant_id == principal.tenant_id, PolicyChunk.source_id == source_id
            )
        )
        now = datetime.now(UTC)
        for number, body in enumerate(chunks, 1):
            session.add(
                PolicyChunk(
                    tenant_id=principal.tenant_id,
                    source_id=source_id,
                    record_id=f"{source_id}-{number:03d}",
                    updated_at=now,
                    body=body,
                    payload={"body": body},
                )
            )
        source.content_sha256 = digest
        source.updated_at = now
    return {"source_id": source_id, "chunks": len(chunks), "status": "ingested"}


def ingest_outcome(principal: Principal, row: OutcomeInput):
    require_writer(principal)
    if row.tenant_id != principal.tenant_id:
        raise HTTPException(403, "Outcome tenant does not match your authenticated tenant.")
    with tenant_session(principal) as session:
        source = ensure_source(
            session, principal, row.source_id, "manual-outcomes", "outcome", row.min_role
        )
        clean = OutcomeRow.model_validate(row.model_dump(exclude={"kind", "min_role"}))
        status = write_row(
            session, principal, "interviews" if row.kind == "interview" else "starts", clean
        )
        if status in ("inserted", "updated"):
            source.updated_at = datetime.now(UTC)
    return {"record_id": row.record_id, "status": status}


def list_sources(principal):
    with tenant_session(principal) as session:
        sources = session.scalars(
            select(Source).where(Source.tenant_id == principal.tenant_id).order_by(Source.source_id)
        )
        return [
            {
                "source_id": s.source_id,
                "filename": s.filename,
                "type": s.source_type,
                "min_role": s.min_role,
                "updated_at": s.updated_at.isoformat(),
                "content_sha256": s.content_sha256,
            }
            for s in sources
        ]
