from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

Role = Literal["viewer", "recruiter", "admin"]


class Principal(BaseModel):
    model_config = ConfigDict(frozen=True)

    tenant_id: UUID
    user_id: UUID
    role: Role
