import pytest

from app.domain import state_machine as sm


def test_submitted_can_be_approved_or_rejected():
    assert sm.transition(sm.SUBMITTED, sm.APPROVED) == sm.APPROVED
    assert sm.transition(sm.SUBMITTED, sm.REJECTED) == sm.REJECTED


def test_only_approved_expenses_can_be_paid():
    assert sm.transition(sm.APPROVED, sm.PAID) == sm.PAID
    with pytest.raises(sm.TransitionError):
        sm.transition(sm.SUBMITTED, sm.PAID)


def test_rejected_and_paid_are_terminal():
    assert sm.is_terminal(sm.REJECTED)
    assert sm.is_terminal(sm.PAID)
    with pytest.raises(sm.TransitionError):
        sm.transition(sm.REJECTED, sm.APPROVED)
    with pytest.raises(sm.TransitionError):
        sm.transition(sm.PAID, sm.APPROVED)


def test_unknown_status_is_rejected():
    with pytest.raises(sm.TransitionError):
        sm.transition("draft", sm.SUBMITTED)
    with pytest.raises(sm.TransitionError):
        sm.transition(sm.SUBMITTED, "archived")
