-- Local bootstrap only. Passwords here are for docker-compose, not production.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ai_report_app') THEN
    CREATE ROLE ai_report_app LOGIN PASSWORD 'ai_report_app';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ai_report_migrator') THEN
    CREATE ROLE ai_report_migrator LOGIN PASSWORD 'ai_report_migrator';
  END IF;
END
$$;

GRANT CONNECT ON DATABASE ai_report TO ai_report_app;
GRANT CONNECT ON DATABASE ai_report TO ai_report_migrator;
GRANT USAGE, CREATE ON SCHEMA public TO ai_report_migrator;
ALTER ROLE ai_report_migrator SET search_path TO public;
