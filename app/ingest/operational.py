"""One CSV row per submission; identity and provenance are attached by the backend."""

import csv
import hashlib
import io
from datetime import UTC, datetime
from pathlib import PurePath

from fastapi import HTTPException
from pydantic import ValidationError

from app.db import tenant_session
from app.ingest.schemas import JobRow, OperationalRow, OutcomeRow, SubmissionRow
from app.ingest.service import decode, ensure_source, require_writer, write_row
from app.models import Job, Outcome, Source, Submission

CSV_COLUMNS = tuple(OperationalRow.model_fields)


def parse_operational(data):
    reader = csv.DictReader(io.StringIO(decode(data)), strict=True)
    rows, submissions, outcomes, jobs = [], set(), set(), {}
    try:
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)) or set(fields) != set(CSV_COLUMNS):
            raise HTTPException(422, f"Required CSV columns: {', '.join(CSV_COLUMNS)}")
        for line, raw in enumerate(reader, start=2):
            if len(rows) >= 5000:
                raise HTTPException(422, "Maximum 5,000 rows per upload.")
            if None in raw or any(value is None for value in raw.values()):
                raise HTTPException(422, f"Row {line}: number of cells must match the header.")
            try:
                row = OperationalRow.model_validate(raw)
            except ValidationError as exc:
                fields = ", ".join(
                    str(error["loc"][0]) if error["loc"] else error["msg"] for error in exc.errors()
                )
                raise HTTPException(422, f"Invalid row {line}; check: {fields}") from exc
            if row.submission_id in submissions:
                raise HTTPException(422, f"Row {line}: duplicate submission_id.")
            submissions.add(row.submission_id)
            for event_id in (row.interview_id, row.start_id):
                if event_id:
                    if event_id in outcomes:
                        raise HTTPException(
                            422, f"Row {line}: duplicate interview/start identifier."
                        )
                    outcomes.add(event_id)
            metadata = row.client_name, row.specialty
            if row.job_id in jobs and jobs[row.job_id] != metadata:
                raise HTTPException(
                    422, f"Row {line}: inconsistent client or specialty for job_id."
                )
            jobs[row.job_id] = metadata
            rows.append(row)
    except csv.Error as exc:
        raise HTTPException(422, "Malformed CSV.") from exc
    if not rows:
        raise HTTPException(422, "CSV must contain at least one submission.")
    return rows


def ingest_operational(principal, min_role, filename, data, source_id=None):
    require_writer(principal)
    rows = parse_operational(data)
    default_source = source_id or "operations"
    counts = {"inserted": 0, "updated": 0, "unchanged": 0, "stale": 0}
    record_types = {"job": 0, "submission": 0, "interview": 0, "start": 0}
    sources = {}
    jobs = {}
    for row in rows:
        if row.job_id not in jobs or row.updated_at > jobs[row.job_id].updated_at:
            jobs[row.job_id] = row

    with tenant_session(principal) as session:

        def provenance(model, record_id):
            existing = session.get(model, (principal.tenant_id, record_id))
            # Preserve existing evidence/source IDs. New records use the upload's namespace.
            selected = existing.source_id if existing else default_source
            if selected not in sources:
                old_source = session.get(Source, (principal.tenant_id, selected))
                source_type = old_source.source_type if existing and old_source else "csv"
                sources[selected] = ensure_source(
                    session, principal, selected, filename, source_type, min_role
                )
            return selected, existing

        def save(kind, row, extra):
            counts[
                write_row(session, principal, kind, row, extra_payload=extra, preserve_payload=True)
            ] += 1

        for job_id, row in jobs.items():
            origin, existing = provenance(Job, job_id)
            job = JobRow(
                tenant_id=principal.tenant_id,
                source_id=origin,
                record_id=job_id,
                updated_at=row.updated_at,
                title=row.specialty,
                location=existing.payload.get("location") if existing else None,
            )
            save("jobs", job, {"client_name": row.client_name, "specialty": row.specialty})
            record_types["job"] += 1
        for row in rows:
            origin, _ = provenance(Submission, row.submission_id)
            submission = SubmissionRow(
                tenant_id=principal.tenant_id,
                source_id=origin,
                record_id=row.submission_id,
                updated_at=row.updated_at,
                job_id=row.job_id,
                candidate_alias=row.candidate_ref,
                submitted_at=row.submitted_at,
                reason=row.status,
            )
            save(
                "submissions",
                submission,
                {
                    "candidate_ref": row.candidate_ref,
                    "status": row.status,
                    "rejection_reason": row.rejection_reason,
                    "csv_row": row.model_dump(mode="json"),
                },
            )
            record_types["submission"] += 1
            for kind, event_id, occurred_at in (
                ("interviews", row.interview_id, row.interviewed_at),
                ("starts", row.start_id, row.started_at),
            ):
                if not event_id:
                    continue
                origin, _ = provenance(Outcome, event_id)
                event = OutcomeRow(
                    tenant_id=principal.tenant_id,
                    source_id=origin,
                    record_id=event_id,
                    updated_at=row.updated_at,
                    submission_id=row.submission_id,
                    occurred_at=occurred_at,
                )
                save(kind, event, {})
                record_types["interview" if kind == "interviews" else "start"] += 1
        digest, now = hashlib.sha256(data).hexdigest(), datetime.now(UTC)
        for source in sources.values():
            source.filename = PurePath(filename.replace("\\", "/")).name[:255]
            source.content_sha256 = digest
            source.updated_at = now
    return {
        "rows": len(rows),
        "record_types": record_types,
        "source_ids": sorted(sources),
        **counts,
    }
