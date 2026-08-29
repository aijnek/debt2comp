"""tools/ の監査スクリプトが今も通ることを、テストとしても押さえておく。

監査は手で走らせるものだが、壊れたことにテストで気づけるようにしておく。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import audit_layering  # noqa: E402
import audit_routes  # noqa: E402
import audit_status_writes  # noqa: E402


def test_every_route_goes_through_require_role():
    assert audit_routes.unguarded_routes() == []


def test_sql_lives_only_in_the_repository_layer():
    assert audit_layering.sql_outside_repository() == []


def test_connections_are_opened_only_at_the_entrypoints():
    assert audit_layering.connect_outside_entrypoints() == []


def test_status_writes_go_through_the_state_machine():
    assert audit_status_writes.unchecked_status_writes() == []
