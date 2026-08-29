#!/usr/bin/env bash
# 挙動を変えずに require_role を require_any_role にリネームする。
set -euo pipefail
cd "$(dirname "$0")/../.."

grep -q "def require_role" samples/expense/app/deps.py || {
  echo "deps.py の形が変わっている。シナリオを更新すること" >&2; exit 2; }

files=$(grep -rl "require_role" samples/expense/app samples/expense/tests samples/expense/README.md)
for f in $files; do
  perl -pi -e 's/\brequire_role\b/require_any_role/g' "$f"
done

echo "適用した: require_role -> require_any_role （挙動は変えていない）"
