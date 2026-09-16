#!/bin/sh
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<EOSQL
CREATE EXTENSION IF NOT EXISTS pg_trgm;

DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ai_report_app') THEN
    CREATE ROLE ai_report_app LOGIN PASSWORD '${APP_DB_PASSWORD}';
  ELSE
    ALTER ROLE ai_report_app LOGIN PASSWORD '${APP_DB_PASSWORD}';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ai_report_migrator') THEN
    CREATE ROLE ai_report_migrator LOGIN PASSWORD '${MIGRATOR_DB_PASSWORD}';
  ELSE
    ALTER ROLE ai_report_migrator LOGIN PASSWORD '${MIGRATOR_DB_PASSWORD}';
  END IF;
END
\$\$;

GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO ai_report_app;
GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO ai_report_migrator;
GRANT USAGE, CREATE ON SCHEMA public TO ai_report_migrator;
ALTER ROLE ai_report_migrator SET search_path TO public;
EOSQL
