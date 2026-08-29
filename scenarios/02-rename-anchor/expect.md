# 02. 挙動を変えずにアンカーの名前を変える

## 変更

`app/deps.py` の `require_role` を `require_any_role` にリネームし、呼び出し側もすべて
追随させる。認可の挙動は一切変わらない。

このシンボルを選んだのには理由がある。`tools/audit_routes.py` はルートの依存性の木を
`__is_role_guard__` という**属性**で辿っており、関数名を見ていない。だから名前が変わっても
verify は通り続ける。

## 期待

- `uv run python tools/audit_routes.py` は **0件** のまま。`uv run pytest` も全て通る
- 「全ての公開ルートは require_role を通る」という **verified** claim は、
  verify の再実行が通るので **生き残る**。本文中の関数名だけが訂正される
- 一方、`deps.py :: require_role` を**アンカーとして持つだけの asserted claim** は、
  アンカー先が消えたので **orphaned** に落ちる
- この差が出ることが、この仕掛けの中心。verified と asserted で陳腐化検出の
  精度が違うことが、同じ1つの変更で観測できる

## 判定

verified claim を stale にしてしまったら誤検知。asserted claim を生かしたままにしたら
見逃し。両方が正しく分かれたときだけ通過。

## 補足

`state_machine.transition` を同じようにリネームすると結果が変わる。
`tools/audit_status_writes.py` は呼び出しを **名前で** 照合しているため、
挙動が一切変わっていなくても「遷移検査なしの status 書き込み 1件」を報告する。
verify スクリプト自身がアンカーを持っており、それが外れると偽の違反を出す、という実例。

確認するなら呼び出し側も含めて漏れなくリネームすること（取りこぼすとテストが落ち、
verify の挙動ではなく単なる壊れたコードを見ることになる）。
