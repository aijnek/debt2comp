#!/usr/bin/env bash
# README とコメントだけを触る。挙動にも構造にも影響しない。
set -euo pipefail
cd "$(dirname "$0")/../.."

target="samples/expense/README.md"
grep -q "## テスト" "$target" || {
  echo "README の形が変わっている。シナリオを更新すること" >&2; exit 2; }

python3 - <<'PY'
import pathlib
p = pathlib.Path("samples/expense/README.md")
s = p.read_text()
s = s.replace("## テスト", "## テスト\n\n新しく入った人はまずここから読むとよい。\n")
p.write_text(s)

p = pathlib.Path("samples/expense/app/money.py")
s = p.read_text()
s = s.replace("# 通貨コード -> 最小通貨単位の指数。JPY は補助単位を持たないので 0。",
              "# 通貨コード -> 最小通貨単位の指数（exponent）。\n# JPY は補助単位を持たないので 0。")
p.write_text(s)
PY

echo "適用した: README に1行、money.py のコメントを2行に分割"
