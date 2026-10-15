from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Source(Base):
    """Tenant-scoped provenance registry, ready for the ingestion milestone."""

    __tablename__ = "sources"
    __table_args__ = (
        CheckConstraint("source_type IN ('csv', 'policy', 'outcome')", name="source_type_valid"),
        CheckConstraint("min_role IN ('viewer', 'recruiter', 'admin')", name="min_role_valid"),
        {"schema": "hireos"},
    )
    tenant_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    source_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(16))
    min_role: Mapped[str] = mapped_column(String(16), default="viewer", server_default="viewer")
    created_by: Mapped[UUID] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    content_sha256: Mapped[str | None] = mapped_column(String(64))


class RecordMixin:
    tenant_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    record_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(128))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict] = mapped_column(JSONB)


def source_fk():
    return ForeignKeyConstraint(
        ["tenant_id", "source_id"], ["hireos.sources.tenant_id", "hireos.sources.source_id"]
    )


class Job(RecordMixin, Base):
    __tablename__ = "jobs"
    __table_args__ = (source_fk(), {"schema": "hireos"})
    title: Mapped[str] = mapped_column(String(120))


class Submission(RecordMixin, Base):
    __tablename__ = "submissions"
    __table_args__ = (
        source_fk(),
        ForeignKeyConstraint(
            ["tenant_id", "job_id"], ["hireos.jobs.tenant_id", "hireos.jobs.record_id"]
        ),
        {"schema": "hireos"},
    )
    job_id: Mapped[str] = mapped_column(String(160))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Outcome(RecordMixin, Base):
    __tablename__ = "outcomes"
    __table_args__ = (
        source_fk(),
        ForeignKeyConstraint(
            ["tenant_id", "submission_id"],
            ["hireos.submissions.tenant_id", "hireos.submissions.record_id"],
        ),
        CheckConstraint("kind IN ('interview', 'start')", name="outcome_kind_valid"),
        {"schema": "hireos"},
    )
    submission_id: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(16))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PolicyChunk(RecordMixin, Base):
    __tablename__ = "policy_chunks"
    __table_args__ = (source_fk(), {"schema": "hireos"})
    body: Mapped[str] = mapped_column(String(2000))


class RetrievalLog(Base):
    __tablename__ = "retrieval_logs"
    __table_args__ = ({"schema": "hireos"},)
    tenant_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    record_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid)
    role: Mapped[str] = mapped_column(String(16))
    question: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(32))
    evidence_ids: Mapped[list] = mapped_column(JSONB)
    metrics: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
