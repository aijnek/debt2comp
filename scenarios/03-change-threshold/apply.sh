#!/usr/bin/env bash
# 二段承認のしきい値を 30,000 円から 50,000 円に変える。
set -euo pipefail
cd "$(dirname "$0")/../.."

target="samples/expense/app/config.py"
grep -q "TWO_STEP_THRESHOLD = Money(30_000)" "$target" || {
  echo "config.py のしきい値の形が変わっている。シナリオを更新すること" >&2; exit 2; }

perl -pi -e 's/TWO_STEP_THRESHOLD = Money\(30_000\)/TWO_STEP_THRESHOLD = Money(50_000)/' "$target"

echo "適用した: TWO_STEP_THRESHOLD 30,000 -> 50,000"
