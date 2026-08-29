# 05. 新しいモジュールを足す

## 変更

部門別の月次集計を、4層すべてに1ファイルずつ足して実装する。認可も層の約束事も
守っているので、既存の verify は全て通ったままになる。

- `app/repository/reporting.py` — 集計の SQL
- `app/services/reporting.py` — Money への詰め替えと合計
- `app/routers/reports.py` — `GET /reports/monthly`（finance と admin だけ）
- `app/templates/report_monthly.html`
- `tests/test_reporting.py`

## 期待

- `uv run pytest` は全て通る。`tools/` の監査も 0件のまま
- 既存の claim は1つも stale にならない（04 と同じく、ここでも誤検知はしないこと）
- **新しい claim が追加抽出される**こと。特に
  「月次集計は支払い済み（paid）だけを数える」は、
  `test_unpaid_expenses_are_not_counted` をそのまま verify に使える **verified** claim
  になるはず。既存テストを verified claim の供給源として収穫できるかの検査になる
- **オリエンテーション地図に集計の節が増える**こと。既存の節（承認の流れ、認可、
  層の分け方）は書き換わらないのが望ましい。地図全体を毎回書き直す作りだと、
  読み手から見て何が新しいのか分からなくなる
- **採掘カバレッジの分母と分子が両方増える**こと。追加抽出をせずに分母だけ増えて
  カバレッジが下がった、という結果でも構わない。分母の外に消えないことが要件

## 判定

追加抽出が走ったか。既存 claim を巻き添えにしていないか。
地図が差分更新できているか、それとも毎回まるごと書き直しているか。
