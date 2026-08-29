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


def test_each_step_maps_to_a_role():
    assert approval_policy.role_for_step(1) == "manager"
    assert approval_policy.role_for_step(2) == "finance"
    with pytest.raises(ValueError):
        approval_policy.role_for_step(9)
