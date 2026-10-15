from sqlalchemy import text


def test_health_confirms_database_and_migration(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected", "migration": "0001"}


def test_application_user_cannot_bypass_rls(single_connection_pool):
    with single_connection_pool.connect() as connection:
        user, superuser, bypass = connection.execute(
            text(
                "SELECT rolname, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
            )
        ).one()
        owner = connection.scalar(
            text(
                "SELECT pg_get_userbyid(relowner) FROM pg_class "
                "WHERE oid = 'hireos.sources'::regclass"
            )
        )
    assert user == "hireos_app"
    assert not superuser
    assert not bypass
    assert owner == "hireos_migrator"
