"""Measure chat dispatch latency: direct call vs MCP ClientSession.

Three paths, same work (list the user's tasks), same database:

  A. in-process direct   — ``call_mcp_tool("list_tasks", ...)`` exactly as
     ``chat_router`` dispatches today (no MCP protocol at all).
  B. in-process MCP      — ``Client(create_server(...))`` over an in-memory
     transport: a real ``ClientSession`` with validation, JSON-RPC framing
     and session dispatch, but no process hop.
  C. stdio MCP           — spawns ``python -m src.mcp.server`` and talks to it
     with ``ClientSession`` over pipes. The subprocess uses ``database_engine``,
     which refuses SQLite, so C only runs when ``DATABASE_URL`` is a reachable
     PostgreSQL URL; otherwise it is reported as skipped.

A and B share one throwaway in-memory SQLite database, so B − A isolates MCP
protocol overhead rather than storage differences.

Usage:
    cd backend
    .venv/bin/python scripts/mcp_latency_benchmark.py
    .venv/bin/python scripts/mcp_latency_benchmark.py --iterations 200 --tasks 200
"""

from __future__ import annotations

import argparse
import asyncio
import os
import statistics
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv

# Path C needs DATABASE_URL (the subprocess uses database_engine, which
# refuses SQLite); load the repo .env explicitly instead of relying on the
# load_dotenv() side-effect inside src.mcp.server.
load_dotenv(BACKEND_ROOT.parent / ".env")

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from src.agents.todo_agent import call_mcp_tool
from src.models import User
from src.services.task_service import TaskService


def _build_engine():
    return create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )


def _seed(engine, task_count: int) -> int:
    User.metadata.create_all(bind=engine)
    with Session(engine) as session:
        suffix = uuid4().hex[:10]
        user = User(
            email=f"bench-{suffix}@example.com",
            username=f"bench_{suffix}",
            password_hash="not-used",
            full_name="Latency Benchmark",
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        for index in range(task_count):
            TaskService.create(session, user_id=user.id, title=f"Bench task {index}")
        return user.id


def _wire_chat_db(engine) -> None:
    """Point todo_agent's database_engine.get_session at the shared SQLite DB."""
    from src.agents import todo_agent

    @contextmanager
    def _session():
        session = Session(bind=engine)
        try:
            yield session
        finally:
            session.close()

    todo_agent.database_engine.get_session = _session


def _summarize(name: str, samples: list[float] | None) -> None:
    if samples is None:
        print(f"{name:<26} skipped (unavailable)")
        return
    ordered = sorted(samples)
    p95 = ordered[max(0, int(len(ordered) * 0.95) - 1)]
    print(
        f"{name:<26} n={len(ordered):<4} "
        f"min={ordered[0]:7.2f}ms  "
        f"median={statistics.median(ordered):7.2f}ms  "
        f"mean={statistics.fmean(ordered):7.2f}ms  "
        f"p95={p95:7.2f}ms  "
        f"max={ordered[-1]:7.2f}ms"
    )


def bench_direct(user_id: int, iterations: int, warmup: int) -> list[float]:
    args = {"user_id": str(user_id)}
    for _ in range(warmup):
        call_mcp_tool("list_tasks", args)
    samples = []
    for _ in range(iterations):
        started = time.perf_counter()
        call_mcp_tool("list_tasks", args)
        samples.append((time.perf_counter() - started) * 1000)
    return samples


async def bench_inproc_client(
    user_id: int, iterations: int, warmup: int, engine
) -> list[float]:
    from mcp import Client
    from src.mcp.server import create_server

    @contextmanager
    def session_factory():
        session = Session(bind=engine)
        try:
            yield session
        finally:
            session.close()

    server = create_server(session_factory)
    samples = []
    async with Client(server) as client:
        for _ in range(warmup):
            await client.call_tool("todo_list_tasks", {})
        for _ in range(iterations):
            started = time.perf_counter()
            await client.call_tool("todo_list_tasks", {})
            samples.append((time.perf_counter() - started) * 1000)
    return samples


async def bench_stdio_client(
    user_id: int, iterations: int, warmup: int
) -> list[float] | None:
    from mcp.client.session import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    db_url = os.getenv("DATABASE_URL", "")
    if not db_url.startswith("postgresql://"):
        return None

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.mcp.server"],
        cwd=BACKEND_ROOT,
        env={"MCP_USER_ID": str(user_id), "DATABASE_URL": db_url},
    )
    samples = []
    try:
        async with (
            stdio_client(params) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            for _ in range(warmup):
                await session.call_tool("todo_list_tasks", {})
            for _ in range(iterations):
                started = time.perf_counter()
                await session.call_tool("todo_list_tasks", {})
                samples.append((time.perf_counter() - started) * 1000)
    except Exception as exc:  # noqa: BLE001 - report, never crash the benchmark
        print(f"  stdio detail: {type(exc).__name__}: {exc}")
        return None
    return samples


async def _run(args: argparse.Namespace) -> None:
    engine = _build_engine()
    user_id = _seed(engine, args.tasks)
    _wire_chat_db(engine)

    previous_mcp_user = os.environ.get("MCP_USER_ID")
    os.environ["MCP_USER_ID"] = str(user_id)
    try:
        print(
            f"tasks={args.tasks}  iterations={args.iterations}  warmup={args.warmup}\n"
        )
        direct = bench_direct(user_id, args.iterations, args.warmup)
        inproc = await bench_inproc_client(
            user_id, args.iterations, args.warmup, engine
        )
        stdio = await bench_stdio_client(user_id, args.iterations, args.warmup)

        _summarize("A direct call_mcp_tool", direct)
        _summarize("B in-process ClientSession", inproc)
        _summarize("C stdio ClientSession", stdio)

        if direct and inproc:
            delta = statistics.median(inproc) - statistics.median(direct)
            ratio = statistics.median(inproc) / statistics.median(direct)
            print(
                f"\nMCP protocol overhead (B - A): {delta:+.2f} ms/call "
                f"({ratio:.1f}x direct)"
            )
    finally:
        if previous_mcp_user is None:
            os.environ.pop("MCP_USER_ID", None)
        else:
            os.environ["MCP_USER_ID"] = previous_mcp_user


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--tasks", type=int, default=50)
    asyncio.run(_run(parser.parse_args()))


if __name__ == "__main__":
    main()
