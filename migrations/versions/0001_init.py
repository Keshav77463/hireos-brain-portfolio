"""Create a tenant- and role-protected source registry."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

TENANT_CHECK = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
ROLE_RANK = (
    "CASE current_setting('app.role', true) "
    "WHEN 'viewer' THEN 1 WHEN 'recruiter' THEN 2 WHEN 'admin' THEN 3 ELSE 0 END"
)
SOURCE_RANK = "CASE min_role WHEN 'viewer' THEN 1 WHEN 'recruiter' THEN 2 ELSE 3 END"
VISIBLE_CHECK = f"({TENANT_CHECK}) AND ({ROLE_RANK}) >= ({SOURCE_RANK})"
WRITE_CHECK = f"({VISIBLE_CHECK}) AND current_setting('app.role', true) IN ('recruiter', 'admin')"


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(16), nullable=False),
        sa.Column("min_role", sa.String(16), server_default="viewer", nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("tenant_id", "source_id"),
        sa.CheckConstraint("source_type IN ('csv', 'policy')", name="source_type_valid"),
        sa.CheckConstraint("min_role IN ('viewer', 'recruiter', 'admin')", name="min_role_valid"),
        schema="hireos",
    )
    op.execute("ALTER TABLE hireos.sources ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE hireos.sources FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY source_read ON hireos.sources FOR SELECT TO hireos_app "
        f"USING ({VISIBLE_CHECK})"
    )
    op.execute(
        f"CREATE POLICY source_insert ON hireos.sources FOR INSERT TO hireos_app "
        f"WITH CHECK ({WRITE_CHECK})"
    )
    op.execute(
        f"CREATE POLICY source_update ON hireos.sources FOR UPDATE TO hireos_app "
        f"USING ({WRITE_CHECK}) WITH CHECK ({WRITE_CHECK})"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE ON hireos.sources TO hireos_app")
    op.execute("GRANT SELECT ON hireos.alembic_version TO hireos_app")


def downgrade() -> None:
    op.drop_table("sources", schema="hireos")
