import calendar
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func, select, text

from app.models import Job, Outcome, Source, Submission

COHORT = """
SELECT s.record_id, s.submitted_at, s.payload,
       CASE WHEN s.submitted_at >= :baseline_start AND s.submitted_at < :baseline_end
            THEN 'baseline' ELSE 'current' END AS period,
       EXISTS (
          SELECT 1 FROM hireos.outcomes o
          WHERE o.tenant_id = :tenant_id AND o.submission_id = s.record_id
            AND o.kind = 'interview' AND o.occurred_at < :cutoff
       ) AS interviewed,
       EXISTS (
          SELECT 1 FROM hireos.outcomes o
          WHERE o.tenant_id = :tenant_id AND o.submission_id = s.record_id
            AND o.kind = 'start' AND o.occurred_at < :cutoff
       ) AS started
FROM hireos.submissions s
JOIN hireos.jobs j ON j.tenant_id = s.tenant_id AND j.record_id = s.job_id
WHERE s.tenant_id = :tenant_id AND lower(j.title) = lower(:job_title)
  AND s.submitted_at < :cutoff
  AND ((s.submitted_at >= :baseline_start AND s.submitted_at < :baseline_end)
    OR (s.submitted_at >= :current_start AND s.submitted_at < :current_end))
"""


def month_dates(day):
    return day.replace(day=1), day.replace(day=calendar.monthrange(day.year, day.month)[1])


def midnight(day):
    return datetime.combine(day, datetime.min.time(), tzinfo=UTC)


def evidence(record, kind, filename):
    return {
        "id": f"{kind}:{record.source_id}:{record.record_id}",
        "kind": kind,
        "source_id": record.source_id,
        "record_id": record.record_id,
        "filename": filename,
        "tenant_id": str(record.tenant_id),
        "updated_at": record.updated_at.isoformat(),
        "data": record.payload,
    }


def calculate(session, principal, request):
    as_of = request.as_of or datetime.now(UTC).date()
    cutoff = midnight(as_of + timedelta(days=1))
    periods = (
        request.baseline_start,
        request.baseline_end,
        request.current_start,
        request.current_end,
    )
    if any(periods) and not all(periods):
        raise HTTPException(422, "Supply all four period dates, or leave all four empty.")
    if all(periods):
        a_start, a_end, b_start, b_end = periods
        if not a_start <= a_end < b_start <= b_end <= as_of:
            raise HTTPException(422, "Periods must be ordered, non-overlapping and end by as_of.")
    else:
        latest = session.scalar(
            select(func.max(Submission.submitted_at))
            .join(
                Job,
                (Job.tenant_id == Submission.tenant_id) & (Job.record_id == Submission.job_id),
            )
            .where(
                Submission.tenant_id == principal.tenant_id,
                func.lower(Job.title) == request.job_title.lower(),
                Submission.submitted_at < cutoff,
            )
        )
        if not latest:
            return None, []
        b_start, b_end = month_dates(latest.date())
        a_start, a_end = month_dates(b_start - timedelta(days=1))
        b_end = min(b_end, as_of)
    params = {
        "tenant_id": principal.tenant_id,
        "job_title": request.job_title,
        "baseline_start": midnight(a_start),
        "baseline_end": midnight(a_end + timedelta(days=1)),
        "current_start": midnight(b_start),
        "current_end": midnight(b_end + timedelta(days=1)),
        "cutoff": cutoff,
    }
    counts = (
        session.execute(
            text(
                f"""WITH cohort AS ({COHORT})
            SELECT period, count(*) AS submissions,
                   count(*) FILTER (WHERE interviewed) AS interviews,
                   count(*) FILTER (WHERE started) AS starts,
                   count(*) FILTER (
                     WHERE NOT interviewed AND payload->>'reason' = 'awaiting_documents'
                   ) AS awaiting_documents,
                   count(*) FILTER (
                     WHERE NOT interviewed AND payload->>'reason' = 'awaiting_client_review'
                   ) AS awaiting_client_review
            FROM cohort GROUP BY period"""
            ),
            params,
        )
        .mappings()
        .all()
    )
    if sum(c["submissions"] for c in counts) > 500:
        raise HTTPException(422, "More than 500 submissions match; narrow the comparison periods.")
    metrics = {
        "job_title": request.job_title,
        "as_of": as_of.isoformat(),
        "formula": "distinct submissions with an interview / distinct submissions × 100",
        "interview_definition": "Submissions in each cohort with any visible interview by as_of.",
        "provider": "deterministic_sql",
    }
    for key, start, end in (("baseline", a_start, a_end), ("current", b_start, b_end)):
        row = next((dict(c) for c in counts if c["period"] == key), {})
        metrics[key] = {
            "start": start.isoformat(),
            "end": end.isoformat(),
            **{
                name: int(row.get(name, 0))
                for name in (
                    "submissions",
                    "interviews",
                    "starts",
                    "awaiting_documents",
                    "awaiting_client_review",
                )
            },
        }
        count = metrics[key]["submissions"]
        metrics[key]["conversion_percent"] = (
            round(metrics[key]["interviews"] / count * 100, 2) if count else None
        )
    a, b = metrics["baseline"], metrics["current"]
    metrics["conversion_change_pp"] = (
        round(b["conversion_percent"] - a["conversion_percent"], 2)
        if a["conversion_percent"] is not None and b["conversion_percent"] is not None
        else None
    )
    metrics["submission_change"] = b["submissions"] - a["submissions"]
    metrics["interview_change"] = b["interviews"] - a["interviews"]
    # The session uses REPEATABLE READ: these records and the aggregates share a snapshot.
    matched_ids = list(
        session.scalars(text(f"WITH cohort AS ({COHORT}) SELECT record_id FROM cohort"), params)
    )
    records = []
    if matched_ids:
        submissions = session.scalars(
            select(Submission)
            .where(
                Submission.tenant_id == principal.tenant_id, Submission.record_id.in_(matched_ids)
            )
            .order_by(Submission.record_id)
        ).all()
        job_ids = {s.job_id for s in submissions}
        jobs = session.scalars(
            select(Job)
            .where(Job.tenant_id == principal.tenant_id, Job.record_id.in_(job_ids))
            .order_by(Job.record_id)
        ).all()
        outcomes = session.scalars(
            select(Outcome)
            .where(
                Outcome.tenant_id == principal.tenant_id,
                Outcome.submission_id.in_(matched_ids),
                Outcome.occurred_at < cutoff,
            )
            .order_by(Outcome.record_id)
        ).all()
        filenames = dict(
            session.execute(
                select(Source.source_id, Source.filename).where(
                    Source.tenant_id == principal.tenant_id
                )
            ).all()
        )
        for kind, collection in (("job", jobs), ("submission", submissions), ("outcome", outcomes)):
            records.extend(evidence(r, kind, filenames[r.source_id]) for r in collection)
        cohorts = {
            s.record_id: (
                "baseline"
                if params["baseline_start"] <= s.submitted_at < params["baseline_end"]
                else "current"
            )
            for s in submissions
        }
        for entry in records:
            if entry["kind"] == "submission":
                entry["period"] = cohorts[entry["record_id"]]
            elif entry["kind"] == "outcome":
                entry["period"] = cohorts[entry["data"]["submission_id"]]
    return metrics, records
