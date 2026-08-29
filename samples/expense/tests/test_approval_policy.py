from __future__ import annotations

import pytest

from app import config
from app.domain import approval_policy
from app.money import Money


def test_small_amounts_need_one_approval():
    assert approval_policy.required_steps(Money(1)) == 1
    assert approval_policy.required_steps(config.TWO_STEP_THRESHOLD) == 1


def test_amounts_above_the_threshold_need_two_approvals():
    over = Money(config.TWO_STEP_THRESHOLD.minor + 1)
    assert approval_policy.required_steps(over) == 2


def test_very_large_amounts_need_three_approvals():
    over = Money(config.THREE_STEP_THRESHOLD.minor + 1)
    assert approval_policy.required_steps(over) == 3
    assert approval_policy.required_steps(config.THREE_STEP_THRESHOLD) == 2


def test_the_first_step_is_decided_by_the_reporting_line():
    assert approval_policy.resolved_by_reporting_line(1)
    assert not approval_policy.resolved_by_reporting_line(2)
    with pytest.raises(ValueError):
        approval_policy.role_for_step(1)


def test_later_steps_map_to_a_role():
    assert approval_policy.role_for_step(2) == "finance"
    assert approval_policy.role_for_step(3) == "admin"
    with pytest.raises(ValueError):
        approval_policy.role_for_step(9)
