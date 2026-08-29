from __future__ import annotations

import pytest

from app.util import uploads


def test_stored_name_is_generated_not_taken_from_the_upload(tmp_path, monkeypatch):
    monkeypatch.setattr(uploads, "UPLOAD_DIR", tmp_path)
    stored = uploads.store_receipt(b"%PDF-1.4", "../../etc/passwd.pdf")
    assert "/" not in stored
    assert stored.endswith(".pdf")
    assert (tmp_path / stored).read_bytes() == b"%PDF-1.4"


def test_unsupported_suffixes_are_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(uploads, "UPLOAD_DIR", tmp_path)
    with pytest.raises(uploads.UploadError):
        uploads.store_receipt(b"MZ", "payload.exe")


def test_oversized_and_empty_files_are_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(uploads, "UPLOAD_DIR", tmp_path)
    with pytest.raises(uploads.UploadError):
        uploads.store_receipt(b"x" * (uploads.MAX_BYTES + 1), "big.png")
    with pytest.raises(uploads.UploadError):
        uploads.store_receipt(b"", "empty.png")


def test_receipt_path_refuses_to_escape_the_upload_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(uploads, "UPLOAD_DIR", tmp_path)
    (tmp_path.parent / "outside.pdf").write_bytes(b"x")
    assert uploads.receipt_path("../outside.pdf") is None
    assert uploads.receipt_path("missing.pdf") is None
