# 経費精算ワークフロー

社員が経費を申請し、金額に応じた段数の承認を経て、経理が支払いを実行するまでを扱う社内アプリ。

## 起動

```bash
uv sync
uv run uvicorn app.main:app --reload
```

http://127.0.0.1:8000 を開く。画面右上で操作するユーザーを切り替える（社内SSOの手前で止めてあり、認証は入っていない）。

## テスト

```bash
uv run pytest
```

## 構成

- `app/routers/` — HTTP の入口。認可の宣言と入力の受け取りだけを行う
- `app/services/` — ユースケースの手続き。複数のリポジトリとドメインを束ねる
- `app/domain/` — 状態遷移と承認ポリシー。DB もHTTPも知らない
- `app/repository/` — SQLite への読み書き。SQL はここにしか無い
- `tools/` — 構造上の約束事を機械的に検査するスクリプト
- `docs/adr/` — 後から理由を思い出せなくなりそうな判断の記録

## 構造上の約束事

コードレビューで見るのではなく、スクリプトで落とす。

```bash
uv run python tools/audit_routes.py         # 全ルートが require_role を通る
uv run python tools/audit_layering.py       # SQL は repository の中だけ
uv run python tools/audit_status_writes.py  # status の書き換えは遷移表を通る
```

## 承認の流れ

1. 社員が申請する（3,000円超は領収書が要る）
2. 申請者の上長が一次承認する
3. 30,000円超なら経理が二次承認、300,000円超ならさらに管理部門が三次承認する
4. 経理が支払いを実行する

各段の承認待ちは、次の承認者の受信箱に通知として届く。
