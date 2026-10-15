from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, String, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Source(Base):
    """Tenant-scoped provenance registry, ready for the ingestion milestone."""

    __tablename__ = "sources"
    __table_args__ = (
        CheckConstraint("source_type IN ('csv', 'policy')", name="source_type_valid"),
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
