from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.auth.principal import Principal
from app.db import tenant_session
from app.models import Source


def principal(role="recruiter", tenant_id=None):
    return Principal(tenant_id=tenant_id or uuid4(), user_id=uuid4(), role=role)


def source(identity, source_id, min_role="viewer", tenant_id=None):
    return Source(
        tenant_id=tenant_id or identity.tenant_id,
        source_id=source_id,
        filename="synthetic.csv",
        source_type="csv",
        min_role=min_role,
        created_by=identity.user_id,
    )


def test_cross_tenant_reads_and_writes_are_blocked():
    tenant_a = principal("admin")
    tenant_b = principal("admin")
    with tenant_session(tenant_a) as session:
        session.add(source(tenant_a, "a"))
    with tenant_session(tenant_b) as session:
        session.add(source(tenant_b, "b"))
    with tenant_session(tenant_a) as session:
        assert session.scalars(select(Source.source_id)).all() == ["a"]
        assert (
            session.scalars(
                select(Source.source_id).where(Source.tenant_id == tenant_b.tenant_id)
            ).all()
            == []
        )
    with pytest.raises(DBAPIError), tenant_session(tenant_a) as session:
        session.add(source(tenant_a, "forged", tenant_id=tenant_b.tenant_id))
        session.flush()


def test_source_role_visibility_and_viewer_write_denial():
    admin = principal("admin")
    with tenant_session(admin) as session:
        session.add_all([source(admin, "public"), source(admin, "restricted", min_role="admin")])
    viewer = principal("viewer", admin.tenant_id)
    recruiter = principal("recruiter", admin.tenant_id)
    for reader in (viewer, recruiter):
        with tenant_session(reader) as session:
            assert session.scalars(select(Source.source_id)).all() == ["public"]
    with tenant_session(admin) as session:
        assert set(session.scalars(select(Source.source_id))) == {"public", "restricted"}
    with pytest.raises(DBAPIError), tenant_session(viewer) as session:
        session.add(source(viewer, "viewer-write"))
        session.flush()


def test_transaction_context_resets_on_commit_and_rollback(single_connection_pool):
    identity = principal()
    with tenant_session(identity) as session:
        session.add(source(identity, "committed"))
    with single_connection_pool.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM hireos.sources")) == 0
    with pytest.raises(RuntimeError), tenant_session(identity) as session:
        assert session.scalar(select(Source.source_id)) == "committed"
        raise RuntimeError("synthetic rollback")
    with single_connection_pool.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM hireos.sources")) == 0
