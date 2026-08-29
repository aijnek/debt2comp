# Skill 検査マトリクス

`samples/expense/` は普通に動く社内アプリだが、**debt2comp の Skill を評価するための
検査台**として作ってある。ここには何をどこに仕込んだか、Skill に何を期待するかを書く。

> **このファイルはサンプルの外に置いてある。**
> `samples/expense/` の中に置くと、Skill が答えを読んでから答えることになる。
> Skill を起動するときの作業ディレクトリは `samples/expense/` に限ること。

---

## 1. claim の5型が採れる場所

| 型 | 期待される claim の例 | アンカー |
|---|---|---|
| invariant | 全ての公開ルートは `require_role` を通る | `app/deps.py`, `app/main.py` |
| invariant | SQL は `app/repository/` の中にしか無い | `app/repository/` 全体 |
| invariant | `status` の書き換えは `state_machine.transition()` を通る | `app/domain/state_machine.py` |
| invariant | 金額は最小通貨単位の int で持ち、float を通さない | `app/money.py` |
| decision | 承認しきい値をコードに置き DB に持たない | `docs/adr/0001`, `app/config.py` |
| decision | 通知を同期送信にしキューを挟まない | `docs/adr/0002`, `app/services/notification.py` |
| decision | 接続を `check_same_thread=False` で開く | `app/repository/db.py` |
| dataflow | 申請 → 通知 → 承認（1〜3段）→ 支払い → 監査ログ | services 全体 |
| dataflow | 承認段数は金額から決まり、段ごとに承認者が変わる | `app/domain/approval_policy.py` |
| failure | 申請者本人はどの段でも承認できない | `app/services/approval.py::_authorize` |
| failure | 一次承認は申請者の上長しか通せない | 同上 |
| failure | 却下と支払い済みは終端で、そこから戻れない | `app/domain/state_machine.py` |
| convention | ルータは薄く、ユースケースは services に置く | `app/routers/`, `app/services/` |
| convention | 接続を開くのは `deps.py` と `bootstrap.py` だけ | `app/deps.py` |

**判定**: 5型すべてに claim が付いたか。特に convention と failure は見落とされやすい。

---

## 2. verified になるべき claim（verify 手続きが書けるもの）

| claim | verify |
|---|---|
| 全ての公開ルートが `require_role` を通る | `uv run python tools/audit_routes.py` → 0件 |
| SQL は repository の中だけ | `uv run python tools/audit_layering.py` → 0件 |
| 接続を開くのは deps と bootstrap だけ | 同上 |
| `status` の書き換えは遷移検査を通る | `uv run python tools/audit_status_writes.py` → 0件 |
| 申請者本人は承認できない | `pytest tests/test_authz.py::test_self_approval_is_rejected` |
| 一次承認は申請者の上長だけ | `pytest tests/test_authz.py::test_the_first_step_needs_the_submitters_own_manager` |
| 却下は終端 | `pytest tests/test_approval.py::test_rejection_is_terminal` |
| 金額に float を渡せない | `pytest tests/test_money.py::test_float_is_not_accepted_as_amount` |
| 領収書の保存名は利用者の入力を使わない | `pytest tests/test_uploads.py` |
| 段数は金額で決まる（境界値込み） | `pytest tests/test_approval_policy.py` |

**判定**: これらが asserted のまま残っていたら、既存テストと `tools/` を verify の供給源として
収穫できていない。concept v2 の「既存テストは最初の verified claim の供給源」が働いていない。

### verify の質を見る仕掛け

`tools/audit_routes.py` には、ルートが1本も見つからないときに例外を投げる分岐がある。
これは実際に起きた事故の後で足したもので（`git log` に残っている）、
**空振りしている検査と合格を見分ける**ためにある。

Skill が「この verify は claim が偽なら本当に落ちるか」を自問する手順を持っているなら、
`tools/` の各スクリプトについて同じ問いを立てられるはず。立てられたかを見る。

---

## 3. asserted にしかならない claim（意図の出所ラベルの検査）

| claim | 期待される出所ラベル | 根拠 |
|---|---|---|
| しきい値をコードに置く理由 | `recorded` | `docs/adr/0001` |
| 通知を同期送信にする理由 | `recorded` | `docs/adr/0002` |
| 多段承認を入れた理由（高額の宿泊費の事故） | `recorded` | コミット `Require a second approval...` |
| 自己承認を塞いだ理由 | `recorded` | コミット `Close the self-approval hole...` |
| 監査ログを状態変更と同じトランザクションに入れる理由 | `inferred` | コードのコメントに「不可分にまとめる」とあるが、なぜかは書いていない |
| 楽観ロックを使わず `BEGIN IMMEDIATE` にした理由 | `inferred` / `unknown` | どこにも書いていない |
| `users` テーブルに論理削除が無い理由 | `unknown` | どこにも書いていない |

**判定**: 推定を `recorded` と偽って提示していないか。
`unknown` が正直に `unknown` として残っているか（残った重要 claim の一覧自体が成果物）。

---

## 4. 仕込んだ罠

**Skill には教えないこと。** 抽出結果を人が読んで、以下を掴めたかを採点する。

### 罠1 — `validate_expense` は名前ほど検証していない

`app/services/submission.py::validate_expense` は金額・費目・発生日を見るが、
**領収書の添付は一切見ていない**。領収書の必須判定は `app/routers/expenses.py` の
`create_expense` の中にあり、`app/routers/admin.py::proxy_submit`（代理申請）はそこを通らない。

つまり **3,000円超でも領収書なしで申請を作れる経路が admin にだけ存在する**。
`proxy_submit` の docstring には「原本は紙で保管しているので添付を取らない」と
もっともらしい理由が書いてあり、意図的な設計にも読める。

- ❌ 「`validate_expense` が申請内容の検証を行う」で止まる
- △ 「領収書の検査はルータ側にある」まで書ける
- ⭕️ 「代理申請経路は領収書の必須判定を迂回する」を、型 `failure` の claim として立てる

これは verify を書こうとした時点で気づけるはずの罠。書こうとしたか。

### 罠2 — `notify_all_approvers` は全員に通知しない

`app/services/notification.py::notify_all_approvers` はループの末尾で `break` しており、
**候補のうち1人にしか通知しない**。戻り値が `list[int]` なのも誤読を誘う。

docstring は「次の段の承認者に通知する」と正直に書いてあり、
コミットメッセージにも「順番に一人ずつ回す」と理由が残っている。
**嘘をついているのは関数名だけ。**

- ❌ 「該当ロールの全員に通知される」という claim を立てる（最悪。名前だけを読んでいる）
- ⭕️ 「1人ずつ順に通知する」と書き、コミットを根拠に intent を `recorded` にする

### 罠3 — `approval_policy` の docstring が実装に追いついていない

`app/domain/approval_policy.py` の冒頭は
「3万円を超える申請は2段階の承認を必要とする」と書いているが、
実装は 30万円超で**3段階**になる。docstring を書いた後に3段目を足し、更新し忘れている。
テストは実装側の正しい挙動（1〜3段）を検証している。

- ❌ docstring を信じて「2段階承認」と教える（`recorded` ラベル付きだと被害が大きい）
- ⭕️ 実装とテストを根拠に1〜3段と書き、**docstring が古いことを指摘する**

コード中の記述は `recorded` の根拠になるが、**根拠にした記述が嘘のことがある**。
ここが崩れると、出所ラベルという防波堤そのものが機能しない。

---

## 5. claim が付きにくい領域（採掘カバレッジの穴）

- `app/routers/admin.py` — ユーザーの CRUD。主張らしい主張が無い（ただし `proxy_submit` は罠1）
- `app/repository/users.py` — 素の SELECT / INSERT / UPDATE / DELETE
- `app/util/formatting.py` — 表示の整形だけ
- `app/templates/`, `app/static/style.css` — 画面

**判定**: これらが「誰も何も主張していない領域」としてオリエンテーション地図に見えるか。
`app/util/uploads.py` はここに紛れやすいが、**入力検証を持つので claim を立てるべき場所**。
util をまとめて捨ててしまうと `uploads.py` の検証も一緒に落ちる。落としたかどうかを見る。

---

## 6. 差分シナリオ

`scenarios/` に5本。詳細は各 `expect.md` を参照。

| # | 変更 | verify | pytest | 期待される claim の変化 |
|---|---|---|---|---|
| 01 | 認可なしルートを追加 | `audit_routes` が1件 | 1件失敗 | 認可 invariant が **stale**。新規ファイルは un-claimed |
| 02 | `require_role` をリネーム | 全て0件 | 全通過 | verified は**生存**、アンカーだけの asserted は **orphaned** |
| 03 | しきい値 3万 → 5万 | 全て0件 | 全通過 | 落ちる verify が無いまま本文が偽に。訂正して **invalidated** |
| 04 | README とコメントのみ | 全て0件 | 全通過 | **何も起きない**（誤検知の検査） |
| 05 | 月次集計モジュール追加 | 全て0件 | 3件増えて全通過 | **追加抽出**と地図の追随。既存 claim は無傷 |

上の verify / pytest 欄は実際に走らせて確認済み。Skill 側の期待は各 `expect.md` にある。

```bash
scenarios/01-add-unauthorized-route/apply.sh
# Skill の同期を走らせて expect.md と突き合わせる
git checkout -- samples/expense && git clean -fd samples/expense
```

---

## 7. git 履歴を使う教材の検査

`git log --oneline -- samples/expense` は、次の筋になっている。

1. 単一承認で作る
2. 高額の宿泊費が上長ひとりの承認で通った事故 → 2段承認を追加
3. さらに30万超の3段目を追加（このとき docstring を更新し忘れる = 罠3）
4. 一次承認をロールで判定していたため manager が自分の申請を承認できた → 塞ぐ
5. 領収書の必須化（このとき代理申請経路が抜ける = 罠1）
6. 検査スクリプトが1本もルートを見ていなかった事故 → 修正

**判定**: 「なぜ今の形か」の教材が、この筋を辿れているか。
特に 2 と 4 は理由がコミットメッセージに書いてあるので `recorded` にできる。
3 と 5 は理由が書いていないので、そこが穴として見えるのが正しい。

---

## 8. 使い方

```bash
cd samples/expense
uv sync
uv run pytest                                # 60件
uv run python tools/audit_routes.py          # 0件
uv run python tools/audit_layering.py        # 0件
uv run python tools/audit_status_writes.py   # 0件
uv run uvicorn app.main:app --reload         # 画面で一周する
```

Skill はこの `samples/expense` を作業ディレクトリとして起動する。
`.comprehension/` はここにコミットされ、`.learning/` は gitignore される。
