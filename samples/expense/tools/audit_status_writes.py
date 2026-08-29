"""status の書き換えが状態遷移の検査を通っているかを検査する。

expenses.update_status() を呼ぶ関数は、同じ関数の中で
state_machine.transition() も呼んでいなければならない。遷移表を迂回した
status の書き込みはここで落ちる。

    uv run python tools/audit_status_writes.py

違反があれば終了コード 1。
"""

from __future__ import annotations

import ast
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1] / "app"


def _called_names(node: ast.AST) -> set[str]:
    names = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
            names.add(child.func.attr)
    return names


def unchecked_status_writes() -> list[str]:
    offenders = []
    for path in sorted(APP_DIR.rglob("*.py")):
        if path.parent.name == "repository":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            called = _called_names(node)
            if "update_status" in called and "transition" not in called:
                offenders.append(
                    f"{path.relative_to(APP_DIR.parent)}:{node.lineno} {node.name}()"
                )
    return offenders


def main() -> int:
    offenders = unchecked_status_writes()
    for line in offenders:
        print(f"遷移検査なしの status 書き込み: {line}")
    print(f"{len(offenders)} 件")
    return 1 if offenders else 0


if __name__ == "__main__":
    raise SystemExit(main())
