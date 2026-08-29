"""層の約束事を検査する。

  1. SQL は app/repository/ の中にしか書かない
  2. db.connect() を呼ぶのは接続の入口だけ（app/deps.py と app/bootstrap.py）

    uv run python tools/audit_layering.py

違反があれば終了コード 1。
"""

from __future__ import annotations

import ast
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1] / "app"
REPOSITORY_DIR = APP_DIR / "repository"

SQL_KEYWORDS = ("select ", "insert ", "update ", "delete ", "create table", "create index")
CONNECT_ALLOWED = {APP_DIR / "deps.py", APP_DIR / "bootstrap.py"}


def _looks_like_sql(value: str) -> bool:
    head = value.strip().lower()
    return any(head.startswith(keyword) for keyword in SQL_KEYWORDS)


def sql_outside_repository() -> list[str]:
    offenders = []
    for path in sorted(APP_DIR.rglob("*.py")):
        if REPOSITORY_DIR in path.parents:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if _looks_like_sql(node.value):
                    offenders.append(f"{path.relative_to(APP_DIR.parent)}:{node.lineno} SQL")
    return offenders


def _is_db_connect(node: ast.AST) -> bool:
    """db.connect(...) または import した connect(...) の呼び出しか。"""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr == "connect":
        return isinstance(func.value, ast.Name) and func.value.id == "db"
    return isinstance(func, ast.Name) and func.id == "connect"


def connect_outside_entrypoints() -> list[str]:
    offenders = []
    for path in sorted(APP_DIR.rglob("*.py")):
        if path in CONNECT_ALLOWED or REPOSITORY_DIR in path.parents:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if _is_db_connect(node):
                offenders.append(
                    f"{path.relative_to(APP_DIR.parent)}:{node.lineno} db.connect()"
                )
    return offenders


def main() -> int:
    offenders = sql_outside_repository() + connect_outside_entrypoints()
    for line in offenders:
        print(f"層の逸脱: {line}")
    print(f"{len(offenders)} 件")
    return 1 if offenders else 0


if __name__ == "__main__":
    raise SystemExit(main())
