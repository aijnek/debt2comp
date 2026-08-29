"""アップロードされた領収書の保存。

ファイル名はこちらで採番する。利用者から届いた名前をそのままパスに使うと、
上位ディレクトリへ抜ける名前を渡されたときに保存先を乗っ取られるため。
"""

from __future__ import annotations

import uuid
from pathlib import Path

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"

ALLOWED_SUFFIXES = frozenset({".pdf", ".png", ".jpg", ".jpeg", ".heic"})
MAX_BYTES = 5 * 1024 * 1024


class UploadError(Exception):
    """受け付けられない添付ファイル。"""


def store_receipt(data: bytes, original_name: str) -> str:
    """領収書を保存し、保存名を返す。"""
    if len(data) > MAX_BYTES:
        raise UploadError(f"領収書は {MAX_BYTES // (1024 * 1024)}MB までです")
    if not data:
        raise UploadError("空のファイルです")

    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise UploadError(
            f"領収書は {'/'.join(sorted(ALLOWED_SUFFIXES))} のいずれかで添付してください"
        )

    stored = f"{uuid.uuid4().hex}{suffix}"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIR / stored).write_bytes(data)
    return stored


def receipt_path(stored_name: str) -> Path | None:
    """保存名から実ファイルの場所を返す。無ければ None。"""
    candidate = (UPLOAD_DIR / stored_name).resolve()
    if candidate.parent != UPLOAD_DIR.resolve() or not candidate.is_file():
        return None
    return candidate
