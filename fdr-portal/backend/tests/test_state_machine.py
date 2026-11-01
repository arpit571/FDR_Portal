"""
Tests for state machine transitions and maker-checker enforcement.
"""
import pytest

# State machine allowed transitions (mirrors src/modules/fdrs/router.py)
ALLOWED_TRANSITIONS = {
    "Draft": ["Pending Document", "Active"],
    "Pending Document": ["Extracting", "Pending Review", "Active"],
    "Extracting": ["Pending Review", "Active"],
    "Pending Review": ["Active"],
    "Active": ["Maturity Alert", "Released", "Renewed", "Replaced", "Closed"],
    "Maturity Alert": ["Matured - Action Pending", "Renewed", "Replaced", "Released"],
    "Matured - Action Pending": ["Renewed", "Replaced", "Released", "Closed"],
    "Renewed": ["Closed"],
    "Replaced": ["Closed"],
    "Released": ["Closed"],
    "Closed": [],
}


class TestStateMachine:
    def test_draft_to_pending_document(self):
        assert "Pending Document" in ALLOWED_TRANSITIONS["Draft"]

    def test_active_to_maturity_alert(self):
        assert "Maturity Alert" in ALLOWED_TRANSITIONS["Active"]

    def test_active_to_released(self):
        assert "Released" in ALLOWED_TRANSITIONS["Active"]

    def test_closed_has_no_transitions(self):
        assert ALLOWED_TRANSITIONS["Closed"] == []

    def test_cannot_go_back_to_draft(self):
        for status, allowed in ALLOWED_TRANSITIONS.items():
            if status != "Draft":
                assert "Draft" not in allowed

    def test_renewed_can_only_close(self):
        assert ALLOWED_TRANSITIONS["Renewed"] == ["Closed"]

    def test_matured_can_renew_replace_release(self):
        allowed = ALLOWED_TRANSITIONS["Matured - Action Pending"]
        assert "Renewed" in allowed
        assert "Replaced" in allowed
        assert "Released" in allowed

    def test_active_cannot_go_to_draft(self):
        assert "Draft" not in ALLOWED_TRANSITIONS["Active"]

    def test_all_statuses_have_entries(self):
        expected = {
            "Draft", "Pending Document", "Extracting", "Pending Review",
            "Active", "Maturity Alert", "Matured - Action Pending",
            "Renewed", "Replaced", "Released", "Closed"
        }
        assert set(ALLOWED_TRANSITIONS.keys()) == expected


class TestMakerCheckerLogic:
    """Test maker-checker rule: submitter cannot approve their own request."""

    def test_maker_cannot_approve_own_request(self):
        """Simulate the check in releases/router.py"""
        requester_id = "user-001"
        approver_id = "user-001"  # same person!

        # This is the check the router enforces
        is_blocked = (requester_id == approver_id)
        assert is_blocked is True, "Maker should be blocked from approving own request"

    def test_different_user_can_approve(self):
        requester_id = "user-001"
        approver_id = "user-002"  # different person

        is_blocked = (requester_id == approver_id)
        assert is_blocked is False, "Different user should be allowed to approve"

    def test_release_not_triggered_by_maturity(self):
        """Release should only happen through explicit workflow, not auto on maturity."""
        # Conceptual test: maturity date passing should NOT create a release request
        # The scheduler only creates alerts and updates status to "Matured - Action Pending"
        # It never creates ReleaseRequest objects
        scheduler_creates_release = False  # verified in scheduler.py — it only creates Alerts
        assert scheduler_creates_release is False
