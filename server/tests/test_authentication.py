from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

from app.auth.security import create_access_token
from app.config import settings
from app.main import app
from tests.helpers import seed_chat

client = TestClient(app)


def test_auth_me_with_valid_jwt(conn, db_url, monkeypatch):
    monkeypatch.setattr(settings, "database_url", db_url)

    users = seed_chat(conn)

    user_id = users["alice"]
    tenant_id = users["tenant"]
    device_id = uuid4()

    conn.execute(
        """
        INSERT INTO devices (
            id, user_id, platform, refresh_hash, refresh_family
        )
        VALUES (%s, %s, 'web', %s, %s)
        """,
        (device_id, user_id, b"test-refresh-hash", uuid4()),
    )
    conn.commit()

    token = create_access_token(
        user_id=str(user_id),
        tenant_id=str(tenant_id),
        device_id=str(device_id),
    )

    response = client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "user_id": str(user_id),
        "tenant_id": str(tenant_id),
        "device_id": str(device_id),
    }


def test_auth_me_without_token_returns_401():
    response = client.get("/v1/auth/me")

    assert response.status_code == 401


def test_auth_me_with_invalid_signature_returns_401():
    token = create_access_token(
        user_id=str(uuid4()),
        tenant_id=str(uuid4()),
        device_id=str(uuid4()),
    )

    invalid_token = token[:-1] + ("a" if token[-1] != "a" else "b")

    response = client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {invalid_token}"},
    )

    assert response.status_code == 401


def test_auth_me_with_expired_jwt_returns_401():
    now = datetime.now(UTC)

    payload = {
        "sub": str(uuid4()),
        "tenant_id": str(uuid4()),
        "device_id": str(uuid4()),
        "jti": str(uuid4()),
        "iat": now - timedelta(minutes=10),
        "exp": now - timedelta(minutes=5),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "token_type": "access",
    }

    expired_token = jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    response = client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401


def test_create_conversation_with_valid_jwt(conn, db_url, monkeypatch):
    monkeypatch.setattr(settings, "database_url", db_url)

    users = seed_chat(conn)
    device_id = uuid4()

    conn.execute(
        """
        INSERT INTO devices (
            id, user_id, platform, refresh_hash, refresh_family
        )
        VALUES (%s, %s, 'web', %s, %s)
        """,
        (device_id, users["alice"], b"test-refresh-hash", uuid4()),
    )
    conn.commit()

    token = create_access_token(
        user_id=str(users["alice"]),
        tenant_id=str(users["tenant"]),
        device_id=str(device_id),
    )

    response = client.post(
        "/v1/conversations",
        json={
            "kind": "private",
            "title": "Test conversation",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Test conversation"
    assert response.json()["tenant_id"] == str(users["tenant"])
    assert response.json()["created_by"] == str(users["alice"])


def test_create_conversation_without_tenant_membership_returns_403(conn, db_url, monkeypatch):
    monkeypatch.setattr(settings, "database_url", db_url)

    users = seed_chat(conn)

    outsider_id = conn.execute(
        """
        INSERT INTO users (email, display_name)
        VALUES (%s, %s)
        RETURNING id
        """,
        (f"outsider-{uuid4().hex}@example.com", "Outsider"),
    ).fetchone()[0]

    device_id = uuid4()

    conn.execute(
        """
        INSERT INTO devices (
            id, user_id, platform, refresh_hash, refresh_family
        )
        VALUES (%s, %s, 'web', %s, %s)
        """,
        (device_id, outsider_id, b"test-refresh-hash", uuid4()),
    )
    conn.commit()

    token = create_access_token(
        user_id=str(outsider_id),
        tenant_id=str(users["tenant"]),
        device_id=str(device_id),
    )

    response = client.post(
        "/v1/conversations",
        json={
            "kind": "private",
            "title": "Unauthorized conversation",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Active tenant membership required"


def test_auth_me_with_revoked_device_returns_401(conn, db_url, monkeypatch):
    monkeypatch.setattr(settings, "database_url", db_url)

    users = seed_chat(conn)
    device_id = uuid4()

    conn.execute(
        """
        INSERT INTO devices (
            id, user_id, platform, refresh_hash, refresh_family
        )
        VALUES (%s, %s, 'web', %s, %s)
        """,
        (device_id, users["alice"], b"test-refresh-hash", uuid4()),
    )
    conn.commit()

    token = create_access_token(
        user_id=str(users["alice"]),
        tenant_id=str(users["tenant"]),
        device_id=str(device_id),
    )

    conn.execute(
        """
        UPDATE devices
        SET revoked_at = now()
        WHERE id = %s
        """,
        (device_id,),
    )
    conn.commit()

    response = client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Device session is invalid or revoked"


def _token_with(**overrides) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(uuid4()),
        "tenant_id": str(uuid4()),
        "device_id": str(uuid4()),
        "jti": str(uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "token_type": "access",
    }
    payload.update(overrides)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def test_auth_me_with_wrong_audience_returns_401():
    response = client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {_token_with(aud='other-client')}"},
    )

    assert response.status_code == 401


def test_auth_me_with_wrong_issuer_returns_401():
    response = client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {_token_with(iss='someone-else')}"},
    )

    assert response.status_code == 401


def test_auth_me_with_refresh_token_type_returns_401():
    response = client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {_token_with(token_type='refresh')}"},
    )

    assert response.status_code == 401
