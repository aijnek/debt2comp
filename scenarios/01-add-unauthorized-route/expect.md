# 01. 認可のないルートを足す

## 変更

`app/routers/quick_export.py` を新設し、`GET /export/expenses.csv` を `main.py` に登録する。
このルートは `require_role` を通らない。全申請の金額と申請者が誰でも読める状態になる。

## 期待

- `uv run python tools/audit_routes.py` が **1件** を報告して終了コード 1
- `uv run pytest` の `test_every_route_goes_through_require_role` が落ちる
- 「全ての公開ルートは require_role を通る」という **verified** な claim が、
  verify の再実行で落ちて **stale** になる。SHA の比較ではなく再実行で落ちること
- `quick_export.py` は誰も何も主張していないファイルとして、**採掘カバレッジの穴**に出る
- 同期の結果として、claim の訂正（「1本を除いて」等）ではなく、
  **コード側が約束を破っている**という報告になっていること。claim を現実に合わせて
  書き換えてしまったら、この仕組みは嘘をつく側に回っている

## 判定

verify の再実行で落とせたか。落とせず SHA 差分だけで stale にしたなら、
陳腐化検出は v1 の水準に留まっている。
