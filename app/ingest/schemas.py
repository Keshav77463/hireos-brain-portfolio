from datetime import UTC
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")]
AccessRole = Literal["viewer", "recruiter", "admin"]


class RecordRow(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    tenant_id: UUID
    source_id: Identifier
    record_id: Identifier
    updated_at: AwareDatetime


class JobRow(RecordRow):
    title: str = Field(min_length=1, max_length=120)
    location: str | None = Field(default=None, min_length=1, max_length=120)


class SubmissionRow(RecordRow):
    job_id: Identifier
    candidate_alias: str = Field(min_length=1, max_length=128)
    submitted_at: AwareDatetime
    reason: Literal[
        "ready",
        "submitted",
        "awaiting_documents",
        "awaiting_client_review",
        "withdrawn",
        "rejected",
        "interviewed",
        "started",
    ]

    @model_validator(mode="after")
    def check_time(self):
        if self.updated_at < self.submitted_at:
            raise ValueError("updated_at cannot precede submitted_at")
        return self


class OutcomeRow(RecordRow):
    submission_id: Identifier
    occurred_at: AwareDatetime

    @model_validator(mode="after")
    def check_time(self):
        if self.updated_at < self.occurred_at:
            raise ValueError("updated_at cannot precede occurred_at")
        return self


class OutcomeInput(OutcomeRow):
    kind: Literal["interview", "start"]
    min_role: AccessRole = "viewer"


class OperationalRow(BaseModel):
    """One submission and its optional completed interview/start, exactly 13 CSV columns."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    submission_id: Identifier
    job_id: Identifier
    client_name: str = Field(min_length=1, max_length=120)
    specialty: str = Field(min_length=1, max_length=120)
    candidate_ref: Identifier
    submitted_at: AwareDatetime
    status: Literal[
        "submitted",
        "awaiting_documents",
        "awaiting_client_review",
        "withdrawn",
        "rejected",
        "interviewed",
        "started",
    ]
    rejection_reason: str | None = Field(max_length=500)
    interview_id: Identifier | None
    interviewed_at: AwareDatetime | None
    start_id: Identifier | None
    started_at: AwareDatetime | None
    updated_at: AwareDatetime

    @field_validator("submitted_at", "interviewed_at", "started_at", "updated_at")
    @classmethod
    def normalize_utc(cls, value):
        return value.astimezone(UTC) if value is not None else None

    @field_validator(
        "rejection_reason",
        "interview_id",
        "interviewed_at",
        "start_id",
        "started_at",
        mode="before",
    )
    @classmethod
    def blank_to_none(cls, value):
        return None if isinstance(value, str) and not value.strip() else value

    @model_validator(mode="after")
    def check_consistency(self):
        interview = (self.interview_id, self.interviewed_at)
        start = (self.start_id, self.started_at)
        if any(interview) and not all(interview):
            raise ValueError("Fill both interview fields together.")
        if any(start) and not all(start):
            raise ValueError("Fill both start fields together.")
        if self.interviewed_at and self.interviewed_at < self.submitted_at:
            raise ValueError("Interview cannot precede submission.")
        if self.started_at and (not self.interviewed_at or self.started_at < self.interviewed_at):
            raise ValueError("A start requires an earlier or same-time interview.")
        if self.updated_at < max(
            time for time in (self.submitted_at, self.interviewed_at, self.started_at) if time
        ):
            raise ValueError("updated_at cannot precede a recorded event.")
        if self.status == "rejected" and not self.rejection_reason:
            raise ValueError("Rejected submissions require rejection_reason.")
        if self.status != "rejected" and self.rejection_reason:
            raise ValueError("rejection_reason is only used for rejected submissions.")
        if self.status == "interviewed" and not self.interview_id:
            raise ValueError("Interviewed status requires interview details.")
        if (self.status == "started") != bool(self.start_id):
            raise ValueError("Started status and start details must be supplied together.")
        if self.interview_id and self.status in (
            "submitted",
            "awaiting_documents",
            "awaiting_client_review",
        ):
            raise ValueError("Pre-interview statuses cannot contain a completed interview.")
        return self
