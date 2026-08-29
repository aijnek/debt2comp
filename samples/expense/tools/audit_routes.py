"""公開ルートが認可の依存性を通っているかを検査する。

app.deps.require_role() が返す依存性には __is_role_guard__ が立っている。
登録済みの全ルートについて依存性の木を辿り、これを1つも通らないルートを
違反として報告する。ルートを足したときの認可の付け忘れはここで落ちる。

    uv run python tools/audit_routes.py

違反があれば終了コード 1。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.routing import APIRoute  # noqa: E402

from app.main import app  # noqa: E402


def _guards_in(dependant) -> bool:
    if getattr(dependant.call, "__is_role_guard__", False):
        return True
    return any(_guards_in(child) for child in dependant.dependencies)


def unguarded_routes() -> list[str]:
    offenders = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not _guards_in(route.dependant):
            methods = ",".join(sorted(route.methods or []))
            offenders.append(f"{methods} {route.path} -> {route.endpoint.__qualname__}")
    return offenders


def main() -> int:
    offenders = unguarded_routes()
    for line in offenders:
        print(f"認可なし: {line}")
    print(f"{len(offenders)} 件")
    return 1 if offenders else 0


if __name__ == "__main__":
    raise SystemExit(main())
