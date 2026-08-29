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
