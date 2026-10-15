#!/usr/bin/env bash
set -euo pipefail

# Runs once as bootstrap. psql quotes password values safely.
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set=ON_ERROR_STOP=1 \
  --set=database_name="$POSTGRES_DB" \
  --set=app_password="$APP_DB_PASSWORD" \
  --set=migrator_password="$MIGRATOR_DB_PASSWORD" <<'SQL'
CREATE ROLE hireos_migrator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD :'migrator_password';
CREATE ROLE hireos_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD :'app_password';
CREATE SCHEMA hireos AUTHORIZATION hireos_migrator;
CREATE EXTENSION vector WITH SCHEMA public;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO hireos_migrator, hireos_app;
GRANT USAGE ON SCHEMA hireos TO hireos_app;
REVOKE ALL ON DATABASE :"database_name" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"database_name" TO hireos_migrator, hireos_app;
SQL
