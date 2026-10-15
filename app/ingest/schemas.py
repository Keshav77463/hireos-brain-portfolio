from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

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
    location: str = Field(min_length=1, max_length=120)


class SubmissionRow(RecordRow):
    job_id: Identifier
    candidate_alias: str = Field(min_length=1, max_length=80)
    submitted_at: AwareDatetime
    reason: Literal["ready", "awaiting_documents", "awaiting_client_review", "withdrawn"]

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
