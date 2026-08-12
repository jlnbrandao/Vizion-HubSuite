"""ABAC enforcer unit tests."""

from __future__ import annotations

from types import SimpleNamespace

from src.modules.iam.abac.service import PolicyEnforcer


def test_subject_outranks_target() -> None:
    enforcer = PolicyEnforcer()
    policy = SimpleNamespace(
        is_active=True,
        actions=["users.update"],
        resource_types=["user"],
        conditions={"subject_outranks_target": True},
        effect="allow",
        priority=10,
    )
    assert enforcer.enforce(
        policies=[policy],
        subject_attrs={"role_names": ["ADMIN"]},
        action="users.update",
        resource_attrs={"type": "user", "target_role_names": ["VIEWER"]},
        env={},
    )
    assert not enforcer.enforce(
        policies=[policy],
        subject_attrs={"role_names": ["VIEWER"]},
        action="users.update",
        resource_attrs={"type": "user", "target_role_names": ["ADMIN"]},
        env={},
    )


def test_deny_effect() -> None:
    enforcer = PolicyEnforcer()
    policy = SimpleNamespace(
        is_active=True,
        actions=["*"],
        resource_types=["*"],
        conditions={},
        effect="deny",
        priority=1,
    )
    assert not enforcer.enforce(
        policies=[policy],
        subject_attrs={},
        action="anything",
        resource_attrs={"type": "x"},
        env={},
    )
