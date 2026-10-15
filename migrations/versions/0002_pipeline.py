"""Operational evidence, policies and append-only retrieval audit."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def record_table(name, *extra):
    op.create_table(
        name,
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("record_id", sa.String(160), nullable=False),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        *extra,
        sa.PrimaryKeyConstraint("tenant_id", "record_id"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "source_id"], ["hireos.sources.tenant_id", "hireos.sources.source_id"]
        ),
        schema="hireos",
    )
    op.create_index(f"ix_{name}_source", name, ["tenant_id", "source_id"], schema="hireos")


def protect(name, parent=None):
    visible = (
        "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid AND "
        f"EXISTS (SELECT 1 FROM hireos.sources s WHERE s.tenant_id = {name}.tenant_id "
        f"AND s.source_id = {name}.source_id)"
    )
    if parent:
        table, column = parent
        visible += (
            f" AND EXISTS (SELECT 1 FROM hireos.{table} p WHERE p.tenant_id = {name}.tenant_id "
            f"AND p.record_id = {name}.{column})"
        )
    writable = f"({visible}) AND current_setting('app.role', true) IN ('recruiter', 'admin')"
    op.execute(f"ALTER TABLE hireos.{name} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE hireos.{name} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY evidence_read ON hireos.{name} FOR SELECT TO hireos_app USING ({visible})"
    )
    op.execute(
        f"CREATE POLICY evidence_insert ON hireos.{name} FOR INSERT TO hireos_app "
        f"WITH CHECK ({writable})"
    )
    op.execute(
        f"CREATE POLICY evidence_update ON hireos.{name} FOR UPDATE TO hireos_app "
        f"USING ({writable}) WITH CHECK ({writable})"
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON hireos.{name} TO hireos_app")
    if name == "policy_chunks":
        op.execute(
            f"CREATE POLICY evidence_delete ON hireos.{name} FOR DELETE TO hireos_app "
            f"USING ({writable})"
        )
        op.execute(f"GRANT DELETE ON hireos.{name} TO hireos_app")


def upgrade():
    op.drop_constraint("source_type_valid", "sources", schema="hireos", type_="check")
    op.create_check_constraint(
        "source_type_valid", "sources", "source_type IN ('csv','policy','outcome')", schema="hireos"
    )
    op.add_column(
        "sources",
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        schema="hireos",
    )
    op.add_column("sources", sa.Column("content_sha256", sa.String(64)), schema="hireos")
    record_table("jobs", sa.Column("title", sa.String(120), nullable=False))
    record_table(
        "submissions",
        sa.Column("job_id", sa.String(160), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "job_id"], ["hireos.jobs.tenant_id", "hireos.jobs.record_id"]
        ),
    )
    record_table(
        "outcomes",
        sa.Column("submission_id", sa.String(160), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "submission_id"],
            ["hireos.submissions.tenant_id", "hireos.submissions.record_id"],
        ),
        sa.CheckConstraint("kind IN ('interview', 'start')", name="outcome_kind_valid"),
    )
    record_table("policy_chunks", sa.Column("body", sa.String(2000), nullable=False))
    protect("jobs")
    protect("submissions", ("jobs", "job_id"))
    protect("outcomes", ("submissions", "submission_id"))
    protect("policy_chunks")
    op.execute(
        "CREATE INDEX ix_policy_search ON hireos.policy_chunks "
        "USING gin (to_tsvector('english', body))"
    )
    op.create_index(
        "ix_submissions_period", "submissions", ["tenant_id", "submitted_at"], schema="hireos"
    )
    op.create_index(
        "ix_outcomes_submission", "outcomes", ["tenant_id", "submission_id"], schema="hireos"
    )
    op.create_table(
        "retrieval_logs",
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("record_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("question", sa.String(1000), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("evidence_ids", JSONB(), nullable=False),
        sa.Column("metrics", JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("tenant_id", "record_id"),
        sa.CheckConstraint("role IN ('viewer','recruiter','admin')", name="log_role_valid"),
        schema="hireos",
    )
    op.execute("ALTER TABLE hireos.retrieval_logs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE hireos.retrieval_logs FORCE ROW LEVEL SECURITY")
    tenant = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
    actor = "user_id = NULLIF(current_setting('app.user_id', true), '')::uuid"
    rank = (
        "CASE current_setting('app.role', true) WHEN 'viewer' THEN 1 "
        "WHEN 'recruiter' THEN 2 WHEN 'admin' THEN 3 ELSE 0 END"
    )
    log_rank = "CASE role WHEN 'viewer' THEN 1 WHEN 'recruiter' THEN 2 ELSE 3 END"
    op.execute(
        "CREATE POLICY audit_read ON hireos.retrieval_logs FOR SELECT TO hireos_app "
        f"USING ({tenant} AND (current_setting('app.role', true) = 'admin' "
        f"OR ({actor} AND ({rank}) >= ({log_rank}))))"
    )
    op.execute(
        "CREATE POLICY audit_insert ON hireos.retrieval_logs FOR INSERT TO hireos_app "
        f"WITH CHECK ({tenant} AND {actor} AND role = current_setting('app.role', true))"
    )
    op.execute("GRANT SELECT, INSERT ON hireos.retrieval_logs TO hireos_app")


def downgrade():
    for name in ("retrieval_logs", "policy_chunks", "outcomes", "submissions", "jobs"):
        op.drop_table(name, schema="hireos")
    op.drop_column("sources", "content_sha256", schema="hireos")
    op.drop_column("sources", "updated_at", schema="hireos")
    # Outcome sources must be removed by an authorized operator before downgrading.
    op.drop_constraint("source_type_valid", "sources", schema="hireos", type_="check")
    op.create_check_constraint(
        "source_type_valid", "sources", "source_type IN ('csv','policy')", schema="hireos"
    )
