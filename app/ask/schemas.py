from datetime import date
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

DemoDate = Annotated[date, Field(ge=date(1970, 1, 1), le=date(2100, 12, 31))]


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question: str = Field(min_length=3, max_length=1000)
    job_title: str = Field(default="ICU RN", min_length=1, max_length=120)
    baseline_start: DemoDate | None = None
    baseline_end: DemoDate | None = None
    current_start: DemoDate | None = None
    current_end: DemoDate | None = None
    as_of: DemoDate | None = None
    target_tenant_id: UUID | None = None
