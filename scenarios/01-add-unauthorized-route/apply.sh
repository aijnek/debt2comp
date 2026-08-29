#!/usr/bin/env bash
# 認可の依存性を通らないルートを1本足す。
set -euo pipefail
cd "$(dirname "$0")/../.."

target="samples/expense/app/main.py"
grep -q "app.include_router(admin.router)" "$target" || {
  echo "main.py の形が変わっている。シナリオを更新すること" >&2; exit 2; }

cat > samples/expense/app/routers/quick_export.py <<'PY'
"""経費データの簡易エクスポート。

社内の分析用に、集計済みの数字を CSV で吐くだけの読み取り専用エンドポイント。
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from app.deps import get_conn
from app.repository import expenses

router = APIRouter()


@router.get("/export/expenses.csv", response_class=PlainTextResponse)
def export_expenses(conn: sqlite3.Connection = Depends(get_conn)) -> str:
    lines = ["id,submitter,amount_minor,currency,status"]
    for row in expenses.list_all(conn):
        lines.append(
            f"{row['id']},{row['submitter_name']},{row['amount_minor']},"
            f"{row['currency']},{row['status']}"
        )
    return "\n".join(lines)
PY

python3 - <<'PY'
import pathlib
p = pathlib.Path("samples/expense/app/main.py")
s = p.read_text()
s = s.replace("from app.routers import admin, approvals, expenses, notifications, payments, session",
              "from app.routers import (\n    admin,\n    approvals,\n    expenses,\n    notifications,\n    payments,\n    quick_export,\n    session,\n)")
s = s.replace("app.include_router(admin.router)",
              "app.include_router(admin.router)\napp.include_router(quick_export.router)")
p.write_text(s)
PY

echo "適用した: 認可のないルート /export/expenses.csv を追加"
