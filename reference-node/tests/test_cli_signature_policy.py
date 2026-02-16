from __future__ import annotations

from types import SimpleNamespace

import echo_node


def test_signature_policy_guard_rejects_skip_when_required() -> None:
    args = SimpleNamespace(require_signature=True, skip_signature=True)
    assert echo_node._enforce_signature_policy(args, "VALIDATION") is False


def test_signature_policy_guard_allows_strict_mode() -> None:
    args = SimpleNamespace(require_signature=True, skip_signature=False)
    assert echo_node._enforce_signature_policy(args, "VALIDATION") is True


def test_signature_policy_guard_allows_dev_bypass() -> None:
    args = SimpleNamespace(require_signature=False, skip_signature=True)
    assert echo_node._enforce_signature_policy(args, "VALIDATION") is True
