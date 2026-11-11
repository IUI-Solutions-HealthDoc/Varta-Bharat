
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.auth.authorization import ConversationAccess, authorize
from app.auth.dependencies import AuthUser


@pytest.fixture
def user():
    """Create an authenticated test user."""
    return AuthUser(
        id=uuid4(),
        tenant_id=uuid4(),
        device_id=uuid4(),
    )


@pytest.fixture
def access(user):
    """Create an active member's private conversation access."""
    return ConversationAccess(
        tenant_id=user.tenant_id,
        kind="private",
        member_role="member",
        left_at=None,
        user_status="active",
        tenant_member_active=True,
    )


# --------------------------------------------------
# Basic conversation access
# --------------------------------------------------

def test_active_member_can_read(user, access):
    authorize(user, "read", uuid4(), access)


def test_active_member_can_send(user, access):
    authorize(user, "send", uuid4(), access)


def test_non_member_cannot_read_private_conversation(user, access):
    access = replace(access, member_role=None)

    with pytest.raises(HTTPException) as exc:
        authorize(user, "read", uuid4(), access)

    assert exc.value.status_code == 403


def test_non_member_cannot_send_to_private_conversation(user, access):
    access = replace(access, member_role=None)

    with pytest.raises(HTTPException) as exc:
        authorize(user, "send", uuid4(), access)

    assert exc.value.status_code == 403


# --------------------------------------------------
# Public and announcement conversation access
# --------------------------------------------------

@pytest.mark.parametrize("kind", ["public", "announcement"])
def test_tenant_member_can_read_without_conversation_membership(
    user, access, kind
):
    access = replace(
        access,
        kind=kind,
        member_role=None,
    )

    authorize(user, "read", uuid4(), access)


def test_non_member_cannot_send_to_public_conversation(user, access):
    access = replace(
        access,
        kind="public",
        member_role=None,
    )

    with pytest.raises(HTTPException) as exc:
        authorize(user, "send", uuid4(), access)

    assert exc.value.status_code == 403


def test_non_member_cannot_send_to_announcement(user, access):
    access = replace(
        access,
        kind="announcement",
        member_role=None,
    )

    with pytest.raises(HTTPException) as exc:
        authorize(user, "send", uuid4(), access)

    assert exc.value.status_code == 403


# --------------------------------------------------
# Membership and account status
# --------------------------------------------------

def test_member_who_left_cannot_access_conversation(user, access):
    access = replace(
        access,
        left_at=datetime.now(UTC),
    )

    with pytest.raises(HTTPException) as exc:
        authorize(user, "read", uuid4(), access)

    assert exc.value.status_code == 403


def test_suspended_user_cannot_access_conversation(user, access):
    access = replace(
        access,
        user_status="suspended",
    )

    with pytest.raises(HTTPException) as exc:
        authorize(user, "read", uuid4(), access)

    assert exc.value.status_code == 403


def test_deleted_user_cannot_access_conversation(user, access):
    access = replace(
        access,
        user_status="deleted",
    )

    with pytest.raises(HTTPException) as exc:
        authorize(user, "read", uuid4(), access)

    assert exc.value.status_code == 403


def test_inactive_tenant_member_cannot_access_conversation(user, access):
    access = replace(
        access,
        tenant_member_active=False,
    )

    with pytest.raises(HTTPException) as exc:
        authorize(user, "read", uuid4(), access)

    assert exc.value.status_code == 403


# --------------------------------------------------
# Tenant isolation
# --------------------------------------------------

def test_other_tenant_gets_404(user, access):
    access = replace(
        access,
        tenant_id=uuid4(),
    )

    with pytest.raises(HTTPException) as exc:
        authorize(user, "read", uuid4(), access)

    assert exc.value.status_code == 404


def test_missing_conversation_returns_404(user):
    with pytest.raises(HTTPException) as exc:
        authorize(user, "read", uuid4(), None)

    assert exc.value.status_code == 404


# --------------------------------------------------
# Admin permissions
# --------------------------------------------------

def test_only_admin_can_manage_members(user, access):
    with pytest.raises(HTTPException) as exc:
        authorize(user, "manage_members", uuid4(), access)

    assert exc.value.status_code == 403


def test_admin_can_manage_members(user, access):
    access = replace(
        access,
        member_role="admin",
    )

    authorize(user, "manage_members", uuid4(), access)


def test_admin_can_manage_settings(user, access):
    access = replace(
        access,
        member_role="admin",
    )

    authorize(user, "manage_settings", uuid4(), access)


# --------------------------------------------------
# Announcement permissions
# --------------------------------------------------

def test_only_admin_can_send_announcement(user, access):
    access = replace(
        access,
        kind="announcement",
    )

    with pytest.raises(HTTPException) as exc:
        authorize(user, "send", uuid4(), access)

    assert exc.value.status_code == 403


def test_admin_can_send_announcement(user, access):
    access = replace(
        access,
        kind="announcement",
        member_role="admin",
    )

    authorize(user, "send", uuid4(), access)


# --------------------------------------------------
# Unsupported actions
# --------------------------------------------------

def test_unsupported_action_is_rejected(user, access):
    with pytest.raises(HTTPException) as exc:
        authorize(user, "delete_everything", uuid4(), access)

    assert exc.value.status_code == 400
