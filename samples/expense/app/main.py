"""アプリケーションの組み立て。

ルータの登録はここに1箇所だけ置く。登録漏れと認可の付け忘れを
tools/audit_routes.py がここから辿れるようにするため。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.bootstrap import ensure_database
from app.routers import approvals, expenses, notifications, payments, session


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    ensure_database()
    yield


app = FastAPI(title="経費精算ワークフロー", lifespan=lifespan)

app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).parent / "static")),
    name="static",
)

app.include_router(expenses.router)
app.include_router(approvals.router)
app.include_router(payments.router)
app.include_router(notifications.router)
app.include_router(session.router)
