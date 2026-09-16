"""Start a local PostgreSQL 16 without Docker or an installer.

Binaries: zonkyio Windows amd64 bundle (PostgreSQL 16.15).
Data dir: %LOCALAPPDATA%\ai-report-pg  (ASCII path; repo path has CJK).
Listen: 127.0.0.1:55432 only.

Usage (from backend/):
  .venv/Scripts/python.exe scripts/pg_local.py up
  .venv/Scripts/python.exe scripts/pg_local.py stop
"""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import tarfile
import time
import urllib.request
import zipfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO_CACHE = BACKEND / ".pg" / "cache"
JAR_NAME = "embedded-postgres-binaries-windows-amd64-16.15.0.jar"
JAR_URL = (
    "https://repo1.maven.org/maven2/io/zonky/test/postgres/"
    "embedded-postgres-binaries-windows-amd64/16.15.0/" + JAR_NAME
)
TXZ_NAME = "postgres-windows-x86_64.txz"

LOCAL = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "ai-report-pg"
DIST = LOCAL / "dist"
DATA = LOCAL / "data"
LOG_DIR = LOCAL / "log"
LOG_FILE = LOG_DIR / "postgresql.log"
ENV_PS1 = LOCAL / "env.ps1"

HOST = "127.0.0.1"
PORT = 55432
SUPER_USER = "postgres"
SUPER_PASSWORD = "postgres"
DB_NAME = "ai_report"
APP_USER = "ai_report_app"
APP_PASSWORD = "ai_report_app"
MIGRATOR_USER = "ai_report_migrator"
MIGRATOR_PASSWORD = "ai_report_migrator"
JWT_SECRET = "please-change-me-to-a-32-byte-secret!!"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "change-me-now-12"
CREATE_NO_WINDOW = 0x08000000


def app_url() -> str:
    return f"postgresql+asyncpg://{APP_USER}:{APP_PASSWORD}@{HOST}:{PORT}/{DB_NAME}"


def migrator_url() -> str:
    return (
        f"postgresql+psycopg://{MIGRATOR_USER}:{MIGRATOR_PASSWORD}@{HOST}:{PORT}/{DB_NAME}"
    )


def super_dsn(dbname: str = "postgres") -> str:
    return f"host={HOST} port={PORT} user={SUPER_USER} password={SUPER_PASSWORD} dbname={dbname}"


def find_pg_home() -> Path | None:
    for cand in (DIST, DIST / "pgsql", DIST / "pgsql" / "pgsql"):
        if (cand / "bin" / "postgres.exe").is_file():
            return cand
    matches = list(DIST.rglob("postgres.exe")) if DIST.exists() else []
    if matches:
        return matches[0].parent.parent
    return None


def bin_dir() -> Path:
    home = find_pg_home()
    if home is None:
        raise SystemExit("postgres.exe not found; run extract first")
    return home / "bin"


def pg_env() -> dict[str, str]:
    env = os.environ.copy()
    home = find_pg_home()
    assert home is not None
    path = str(home / "bin") + os.pathsep + str(home / "lib") + os.pathsep + env.get("PATH", "")
    env["PATH"] = path
    env["PGDATA"] = str(DATA)
    env["PGHOST"] = HOST
    env["PGPORT"] = str(PORT)
    env["PGUSER"] = SUPER_USER
    env["PGCLIENTENCODING"] = "UTF8"
    env["PGPASSWORD"] = SUPER_PASSWORD
    return env


def run_pg(args: list[str]) -> subprocess.CompletedProcess[str]:
    exe = bin_dir() / args[0]
    if not exe.suffix:
        exe = exe.with_suffix(".exe")
    return subprocess.run(
        [str(exe), *args[1:]],
        env=pg_env(),
        cwd=str(bin_dir()),
        text=True,
        capture_output=True,
        creationflags=CREATE_NO_WINDOW,
    )


def run_pgctl(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Do not capture stdout: Windows postmaster inherits pipes and deadlocks wait()."""
    exe = bin_dir() / "pg_ctl.exe"
    return subprocess.run(
        [str(exe), *args],
        env=pg_env(),
        cwd=str(bin_dir()),
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        creationflags=CREATE_NO_WINDOW,
    )


def download_jar() -> Path:
    REPO_CACHE.mkdir(parents=True, exist_ok=True)
    dest = REPO_CACHE / JAR_NAME
    if dest.is_file() and dest.stat().st_size > 1_000_000:
        print(f"jar cache hit: {dest} ({dest.stat().st_size} bytes)")
        return dest
    print(f"downloading {JAR_URL}")
    tmp = dest.with_suffix(".part")
    urllib.request.urlretrieve(JAR_URL, tmp)
    tmp.replace(dest)
    print(f"saved {dest} ({dest.stat().st_size} bytes)")
    return dest


def extract_binaries() -> Path:
    existing = find_pg_home()
    if existing is not None:
        print(f"binaries already extracted: {existing}")
        return existing
    jar = download_jar()
    LOCAL.mkdir(parents=True, exist_ok=True)
    DIST.mkdir(parents=True, exist_ok=True)
    txz = REPO_CACHE / TXZ_NAME
    with zipfile.ZipFile(jar) as zf:
        print("jar members:", zf.namelist())
        zf.extract(TXZ_NAME, REPO_CACHE)
    print(f"extracting {txz} -> {DIST}")
    with tarfile.open(txz, "r:xz") as tf:
        try:
            tf.extractall(DIST, filter="data")
        except TypeError:
            tf.extractall(DIST)
    home = find_pg_home()
    if home is None:
        raise SystemExit(f"extract finished but postgres.exe missing under {DIST}")
    print(f"pg home: {home}")
    return home


def write_conf() -> None:
    conf = DATA / "postgresql.conf"
    hba = DATA / "pg_hba.conf"
    conf.write_text(
        "\n".join(
            [
                "listen_addresses = '127.0.0.1'",
                f"port = {PORT}",
                "max_connections = 40",
                "shared_buffers = 32MB",
                "timezone = 'Asia/Shanghai'",
                "log_destination = 'stderr'",
                "logging_collector = off",
                "client_encoding = 'UTF8'",
                "lc_messages = 'C'",
                "",
            ]
        ),
        encoding="utf-8",
    )
    hba.write_text(
        "\n".join(
            [
                "# Local AI report Postgres 16 — 127.0.0.1 only.",
                "host    all    all    127.0.0.1/32    scram-sha-256",
                "host    all    all    ::1/128         reject",
                "",
            ]
        ),
        encoding="utf-8",
    )


def initdb() -> None:
    if (DATA / "PG_VERSION").is_file():
        print(f"data dir exists: {DATA}")
        return
    DATA.parent.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    pwfile = LOCAL / "pwfile"
    pwfile.write_text(SUPER_PASSWORD + "\n", encoding="ascii")
    try:
        base = [
            "initdb",
            "--pgdata",
            str(DATA),
            "--username",
            SUPER_USER,
            "--pwfile",
            str(pwfile),
            "--auth-local",
            "trust",
            "--auth-host",
            "scram-sha-256",
            "--encoding",
            "UTF8",
            "--no-sync",
        ]
        proc = run_pg([*base, "--locale", "C"])
        if proc.returncode != 0:
            print("initdb --locale=C failed, retry --no-locale")
            print(proc.stderr)
            if DATA.exists():
                shutil.rmtree(DATA, ignore_errors=True)
            proc = run_pg([*base, "--no-locale"])
        if proc.returncode != 0:
            raise SystemExit(f"initdb failed:\n{proc.stdout}\n{proc.stderr}")
        print(proc.stdout)
    finally:
        if pwfile.exists():
            pwfile.unlink()
    write_conf()


def is_running() -> bool:
    try:
        with socket.create_connection((HOST, PORT), 0.4):
            return True
    except OSError:
        return False


def wait_tcp(timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    last_err: OSError | None = None
    while time.time() < deadline:
        try:
            with socket.create_connection((HOST, PORT), 1.0):
                print(f"tcp {HOST}:{PORT} open")
                return
        except OSError as exc:
            last_err = exc
            time.sleep(0.25)
    raise SystemExit(f"postgres did not accept {HOST}:{PORT}: {last_err}")


def start() -> None:
    if is_running():
        print(f"already running on {HOST}:{PORT}")
        return
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    write_conf()
    proc = run_pgctl(["start", "-D", str(DATA), "-l", str(LOG_FILE)])
    if proc.returncode != 0:
        tail = ""
        if LOG_FILE.is_file():
            tail = LOG_FILE.read_text(encoding="utf-8", errors="replace")[-4000:]
        raise SystemExit(f"pg_ctl start failed:\n{proc.stderr}\n{tail}")
    wait_tcp()


def stop() -> None:
    if not (DATA / "PG_VERSION").is_file():
        print("no data dir; nothing to stop")
        return
    proc = run_pgctl(["stop", "-m", "fast", "-D", str(DATA)])
    print(proc.stderr or "stopped")


def split_sql(sql: str) -> list[str]:
    import re

    parts: list[str] = []
    buf: list[str] = []
    i = 0
    n = len(sql)
    while i < n:
        if sql[i] == "$":
            match = re.match(r"\$[A-Za-z0-9_]*\$", sql[i:])
            if match:
                tag = match.group(0)
                end = sql.find(tag, i + len(tag))
                if end < 0:
                    raise ValueError("unterminated dollar-quote")
                buf.append(sql[i : end + len(tag)])
                i = end + len(tag)
                continue
        if sql[i] == ";":
            stmt = "".join(buf).strip()
            if stmt:
                parts.append(stmt)
            buf = []
            i += 1
            continue
        buf.append(sql[i])
        i += 1
    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return parts


def bootstrap() -> None:
    import psycopg

    with psycopg.connect(super_dsn("postgres"), autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,)
        ).fetchone()
        if exists is None:
            created = False
            for stmt in (
                "CREATE DATABASE ai_report OWNER postgres ENCODING 'UTF8' "
                "LC_COLLATE 'C' LC_CTYPE 'C' TEMPLATE template0",
                "CREATE DATABASE ai_report OWNER postgres ENCODING 'UTF8' TEMPLATE template0",
            ):
                try:
                    conn.execute(stmt)
                    created = True
                    print(f"created database {DB_NAME}")
                    break
                except Exception as exc:
                    print(f"create database retry: {exc}")
            if not created:
                raise SystemExit("CREATE DATABASE failed")
        else:
            print(f"database {DB_NAME} exists")

    init_sql = (BACKEND / "docker" / "init.sql").read_text(encoding="utf-8")
    with psycopg.connect(super_dsn(DB_NAME), autocommit=True) as conn:
        for stmt in split_sql(init_sql):
            conn.execute(stmt)
        from psycopg import sql as pg_sql

        conn.execute(
            pg_sql.SQL("ALTER ROLE postgres WITH PASSWORD {}").format(
                pg_sql.Literal(SUPER_PASSWORD)
            )
        )
        conn.execute(
            pg_sql.SQL("ALTER ROLE ai_report_app WITH PASSWORD {}").format(
                pg_sql.Literal(APP_PASSWORD)
            )
        )
        conn.execute(
            pg_sql.SQL("ALTER ROLE ai_report_migrator WITH PASSWORD {}").format(
                pg_sql.Literal(MIGRATOR_PASSWORD)
            )
        )
        conn.execute("GRANT CONNECT ON DATABASE ai_report TO ai_report_app")
        conn.execute("GRANT CONNECT ON DATABASE ai_report TO ai_report_migrator")
        conn.execute("GRANT USAGE, CREATE ON SCHEMA public TO ai_report_migrator")
    print("bootstrap roles + pg_trgm done")


def migrate() -> None:
    env = os.environ.copy()
    env["ALEMBIC_DATABASE_URL"] = migrator_url()
    env.pop("DATABASE_URL", None)
    print("alembic upgrade head")
    proc = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND),
        env=env,
        text=True,
        capture_output=True,
        creationflags=CREATE_NO_WINDOW,
    )
    if proc.returncode != 0:
        raise SystemExit(f"alembic failed:\n{proc.stdout}\n{proc.stderr}")
    print(proc.stdout or "alembic ok")


def seed_data() -> None:
    sys.path.insert(0, str(BACKEND))
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.adapters.db.seed import seed
    from app.config import Settings

    settings = Settings(
        _env_file=None,
        repository="postgres",
        database_url=app_url(),
        alembic_database_url=None,
        jwt_secret=JWT_SECRET,
        admin_email=ADMIN_EMAIL,
        admin_password=ADMIN_PASSWORD,
        allowed_origins="http://localhost:3000",
        debug=True,
        trust_proxy=False,
    )
    engine = create_engine(settings.sync_database_url())
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as session:
        seed(session, settings)
    engine.dispose()
    print("seed complete")


def write_env_ps1() -> None:
    LOCAL.mkdir(parents=True, exist_ok=True)
    ENV_PS1.write_text(
        "\n".join(
            [
                '$env:REPOSITORY = "postgres"',
                f'$env:DATABASE_URL = "{app_url()}"',
                f'$env:ALEMBIC_DATABASE_URL = "{migrator_url()}"',
                f'$env:AI_REPORT_PG_TEST_URL = "{app_url()}"',
                f'$env:JWT_SECRET = "{JWT_SECRET}"',
                f'$env:ADMIN_EMAIL = "{ADMIN_EMAIL}"',
                f'$env:ADMIN_PASSWORD = "{ADMIN_PASSWORD}"',
                '$env:ALLOWED_ORIGINS = "http://localhost:3000"',
                '$env:DEBUG = "true"',
                '$env:PIPELINE_SCHEDULER_ENABLED = "true"',
                '$env:PIPELINE_SCHEDULE = "06:30,12:30,18:30"',
                '$env:PIPELINE_AUTO_CLUSTER = "true"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"wrote {ENV_PS1}")


def verify() -> None:
    import psycopg

    with psycopg.connect(super_dsn(DB_NAME)) as conn:
        version = conn.execute("SHOW server_version").fetchone()[0]
        stories = conn.execute("SELECT COUNT(*) FROM stories").fetchone()[0]
        briefings = conn.execute("SELECT COUNT(*) FROM briefings").fetchone()[0]
        topics = conn.execute("SELECT COUNT(*) FROM topics").fetchone()[0]
        sources = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        admins = conn.execute("SELECT COUNT(*) FROM admin_users").fetchone()[0]
        today = conn.execute(
            "SELECT title_zh FROM briefings WHERE date = DATE '2026-09-14'"
        ).fetchone()
    print(f"server_version={version}")
    print(
        f"counts briefings={briefings} stories={stories} "
        f"topics={topics} sources={sources} admins={admins}"
    )
    if today:
        print(f"today title_zh={today[0]}")
    if stories != 53 or briefings != 14 or topics != 10 or sources != 12 or admins != 1:
        raise SystemExit("seed counts do not match V1 fixtures (14/53/10/12/1)")


def print_urls() -> None:
    print(f"PGDATA={DATA}")
    print(f"listen={HOST}:{PORT}")
    print(f"DATABASE_URL={app_url()}")
    print(f"ALEMBIC_DATABASE_URL={migrator_url()}")
    print(f"AI_REPORT_PG_TEST_URL={app_url()}")
    print(f"env file={ENV_PS1}")


def status() -> None:
    print(f"pg home={find_pg_home()}")
    print(f"data={DATA} exists={DATA.exists()}")
    print(f"running={is_running()}")
    print_urls()


def up() -> None:
    extract_binaries()
    initdb()
    start()
    bootstrap()
    migrate()
    seed_data()
    write_env_ps1()
    verify()
    print_urls()
    print("up complete")


def main() -> None:
    parser = argparse.ArgumentParser(description="Local PostgreSQL 16 for AI Report")
    parser.add_argument(
        "command",
        choices=["up", "start", "stop", "status", "migrate", "seed", "verify"],
    )
    args = parser.parse_args()
    commands = {
        "up": up,
        "start": lambda: (extract_binaries(), initdb(), start(), print_urls()),
        "stop": stop,
        "status": status,
        "migrate": migrate,
        "seed": seed_data,
        "verify": verify,
    }
    commands[args.command]()


if __name__ == "__main__":
    main()