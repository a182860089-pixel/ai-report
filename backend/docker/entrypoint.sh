#!/bin/sh
set -eu

python - <<'PY'
import os
import sys
import time

import psycopg

raw = (os.environ.get("ALEMBIC_DATABASE_URL") or os.environ.get("DATABASE_URL") or "").strip()
for prefix, repl in (
    ("postgresql+psycopg://", "postgresql://"),
    ("postgresql+asyncpg://", "postgresql://"),
    ("postgres://", "postgresql://"),
):
    if raw.startswith(prefix):
        raw = repl + raw[len(prefix):]
        break
if not raw:
    sys.exit("DATABASE_URL missing")

last = None
for _ in range(60):
    try:
        with psycopg.connect(raw, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
        print("postgres ready", flush=True)
        break
    except Exception as exc:  # noqa: BLE001
        last = exc
        time.sleep(1)
else:
    sys.exit(f"postgres not ready: {last}")
PY

alembic upgrade head
python -m app.adapters.db.seed
exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
