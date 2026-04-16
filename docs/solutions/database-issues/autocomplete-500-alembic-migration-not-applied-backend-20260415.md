---
module: YGO Meta Check Backend
date: 2026-04-15
problem_type: database_issue
component: database
symptoms:
  - "GET /api/autocomplete returns HTTP 500 Internal Server Error"
  - "sqlalchemy.exc.ProgrammingError: relation 'cards' does not exist"
  - "alembic upgrade head in Docker: OSError: Connect call failed 127.0.0.1:5432"
  - "RuntimeWarning: coroutine 'run_async_migrations' was never awaited on startup"
root_cause: config_error
resolution_type: code_fix
severity: high
tags: [alembic, asyncio, fastapi, docker, migrations, startup]
---

# Troubleshooting: Autocomplete 500 — Alembic Migration Not Applied in Docker

## Problem

After adding a `cards` table (migration 0002), the `/api/autocomplete` endpoint returned HTTP 500 on every request. The migration had never been applied because `alembic upgrade head` failed inside the Docker container, and the autocomplete code did not guard against a missing table.

## Environment

- Module: YGO Meta Check Backend
- Stack: FastAPI + SQLAlchemy (asyncpg) + Alembic + Docker Compose
- Affected Components: `backend/app/api/autocomplete.py`, `backend/alembic/env.py`, `backend/app/main.py`
- Date: 2026-04-15

## Symptoms

- `GET /api/autocomplete?q=<query>` → `HTTP 500 Internal Server Error`
- Backend logs: `sqlalchemy.exc.ProgrammingError: (asyncpg.exceptions.UndefinedTableError): relation "cards" does not exist`
- Running `docker compose exec backend alembic upgrade head` → `OSError: Multiple exceptions: [Errno 111] Connect call failed ('::1', 5432), Connect call failed ('127.0.0.1', 5432)`
- After adding startup auto-migration via Alembic Python API: `RuntimeWarning: coroutine 'run_async_migrations' was never awaited`
- Server process hangs at `INFO [alembic.runtime.migration] Will assume transactional DDL.` with no completion

## What Didn't Work

**Attempted Solution 1:** Run `alembic upgrade head` inside the Docker container.

- **Why it failed:** `alembic/env.py` read the DB URL from `alembic.ini`, which hardcoded `localhost:5432`. Inside the Docker network the database hostname is `db`, not `localhost`. The `DATABASE_URL` environment variable (correctly set to `db:5432`) was never consulted.

**Attempted Solution 2:** Call Alembic's Python API directly in the FastAPI `@app.on_event("startup")` handler.

```python
# BROKEN — asyncio.run() inside an already-running event loop
from alembic import command
from alembic.config import Config

@app.on_event("startup")
async def startup():
    command.upgrade(Config("alembic.ini"), "head")  # internally calls asyncio.run()
```

- **Why it failed:** Alembic's async `env.py` calls `asyncio.run(run_async_migrations())`. Calling `asyncio.run()` from within FastAPI's startup (which itself runs inside an event loop) raises `RuntimeWarning: coroutine 'run_async_migrations' was never awaited` and prevents startup completion.

**Attempted Solution 3:** Wrap the Python API call in `run_in_executor` to give it a thread.

```python
loop = asyncio.get_event_loop()
await loop.run_in_executor(None, lambda: command.upgrade(cfg, "head"))
```

- **Why it failed:** Hot-reload cycles (uvicorn `--reload`) kill server processes mid-migration, leaving asyncpg connections open. PostgreSQL holds a lock on the `alembic_version` table for the orphaned transaction. The next process hangs indefinitely waiting to acquire the lock.

## Solution

Three coordinated fixes:

### Fix 1 — `alembic/env.py`: read `DATABASE_URL` from the environment

```python
import os

def _get_url() -> str:
    """Read DATABASE_URL from the environment, falling back to alembic.ini."""
    return os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")

async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _get_url()   # was: config.get_main_option(...)
    ...
```

### Fix 2 — `autocomplete.py`: catch `UndefinedTableError` and fall back gracefully

```python
@router.get("/autocomplete", response_model=list[CardSuggestion])
async def autocomplete(q: str = ..., db: AsyncSession = ...):
    try:
        count = (await db.execute(select(func.count()).select_from(Card))).scalar_one()
    except Exception:
        # Table doesn't exist yet (migration pending) — fall back to live API
        await db.rollback()
        return await _remote_autocomplete(q)

    if count > 0:
        return await _local_autocomplete(q, db)
    return await _remote_autocomplete(q)
```

### Fix 3 — `main.py`: run Alembic as a subprocess to avoid event loop conflicts

```python
import subprocess, sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).parent.parent

def _run_migrations() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=_BACKEND_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Alembic migration failed: {result.stderr}")

@app.on_event("startup")
async def startup():
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _run_migrations)  # subprocess in thread pool
    ...
```

## Why This Works

1. **`DATABASE_URL` in env.py:** The subprocess inherits the container's environment, so `os.environ.get("DATABASE_URL")` returns `postgresql+asyncpg://ygo:...@db:5432/ygo_meta` — the correct Docker network hostname.

2. **Graceful fallback in autocomplete:** SQLAlchemy's connection is in a bad state after a failed query. Rolling back the session before falling back to the remote API prevents `InvalidRequestError` on the next operation in the same request.

3. **Subprocess isolation:** `subprocess.run()` creates a fresh process with its own event loop. `asyncio.run()` inside `env.py` works correctly there. If the subprocess is killed (e.g., by a SIGKILL), the OS closes the TCP connection, PostgreSQL detects the disconnect, and releases the lock — no orphaned transactions.

## Prevention

- **Always read `DATABASE_URL` from the environment in `alembic/env.py`** — never rely solely on `alembic.ini` in projects that run in Docker. The pattern `os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")` works for both local and containerized runs.

- **Guard any endpoint that queries a table added in a non-initial migration** — new tables may not exist on older deployments or fresh installs before migrations run. Catch `ProgrammingError` / `UndefinedTableError` and return a safe fallback or `503`.

- **Never call `asyncio.run()` from within a running event loop** — use `run_in_executor` to run blocking/asyncio-hostile code in a thread, or spawn a subprocess if the code itself calls `asyncio.run()` internally (as Alembic does).

- **After adding `run_in_executor` migrations:** use `subprocess.run()` rather than the Alembic Python API directly — the subprocess boundary prevents lock hangs from hot-reload process churn.

## Related Issues

No related issues documented yet.
