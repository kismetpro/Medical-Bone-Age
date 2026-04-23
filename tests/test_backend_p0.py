import secrets
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

import app.main as main


@asynccontextmanager
async def _noop_lifespan(app):
    yield


def _configure_temp_databases(monkeypatch, tmp_path, super_admin_password="AdminPass123"):
    auth_db = tmp_path / "auth.db"
    prediction_db = tmp_path / "predictions.db"
    monkeypatch.setattr(main, "AUTH_DB_PATH", str(auth_db))
    monkeypatch.setattr(main, "PREDICTION_DB_PATH", str(prediction_db))
    monkeypatch.setattr(main, "SUPER_ADMIN_INIT_PASSWORD", super_admin_password)
    return auth_db, prediction_db


def _insert_user(username, role, password):
    salt_hex = secrets.token_hex(16)
    password_hash = main.hash_password(password, salt_hex, main.PBKDF2_ITERATIONS)
    now_iso = main._to_iso(main._utc_now())
    with main.get_auth_conn() as conn:
        conn.execute(
            """
            INSERT INTO users (username, role, password_hash, password_salt, iterations, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                username,
                role,
                password_hash,
                salt_hex,
                main.PBKDF2_ITERATIONS,
                now_iso,
            ),
        )
        user_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        session = main.create_session(conn, user_id, role)
    return {
        "user_id": user_id,
        "token": session["token"],
        "password_hash": password_hash,
        "password_salt": salt_hex,
    }


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def _request_for_host(host):
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/auth/login",
        "raw_path": b"/auth/login",
        "query_string": b"",
        "headers": [],
        "client": (host, 12345),
        "server": ("testserver", 80),
    }
    return Request(scope)


@pytest.fixture
def client(monkeypatch, tmp_path):
    _configure_temp_databases(monkeypatch, tmp_path)
    monkeypatch.setattr(main.app.router, "lifespan_context", _noop_lifespan)
    main.init_auth_db()
    main.init_prediction_db()
    with TestClient(main.app) as test_client:
        yield test_client


def test_init_auth_db_requires_explicit_super_admin_password(monkeypatch, tmp_path):
    _configure_temp_databases(monkeypatch, tmp_path, super_admin_password="")

    with pytest.raises(RuntimeError, match="SUPER_ADMIN_INIT_PASSWORD"):
        main.init_auth_db()


def test_init_auth_db_preserves_existing_builtin_account_credentials(monkeypatch, tmp_path):
    _configure_temp_databases(monkeypatch, tmp_path, super_admin_password="AdminPass123")

    with main.get_auth_conn() as conn:
        main._create_users_table(conn)
        main._create_sessions_table(conn)
        conn.commit()

    doctor = _insert_user("doctor", main.ROLE_DOCTOR, "CustomDoctor123")
    with main.get_auth_conn() as conn:
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (doctor["user_id"],))
        conn.execute(
            """
            INSERT INTO sessions (token, user_id, role, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "existing-session-token",
                doctor["user_id"],
                main.ROLE_DOCTOR,
                main._to_iso(main._utc_now() + main.timedelta(hours=1)),
                main._to_iso(main._utc_now()),
            ),
        )
        conn.commit()

    main.init_auth_db()

    with main.get_auth_conn() as conn:
        row = conn.execute(
            """
            SELECT password_hash, password_salt
            FROM users
            WHERE username = ?
            """,
            ("doctor",),
        ).fetchone()
        session_count = int(
            conn.execute(
                "SELECT COUNT(1) FROM sessions WHERE token = ?",
                ("existing-session-token",),
            ).fetchone()[0]
        )

    assert row["password_hash"] == doctor["password_hash"]
    assert row["password_salt"] == doctor["password_salt"]
    assert session_count == 1


def test_auth_rate_limit_blocks_after_configured_attempts(monkeypatch, tmp_path):
    _configure_temp_databases(monkeypatch, tmp_path, super_admin_password="AdminPass123")
    monkeypatch.setattr(main, "AUTH_RATE_LIMIT_MAX_ATTEMPTS", 2)
    monkeypatch.setattr(main, "AUTH_RATE_LIMIT_WINDOW_SECONDS", 60)
    main.init_auth_db()

    request = _request_for_host("198.51.100.24")
    main._check_auth_rate_limit(request, "login")
    main._check_auth_rate_limit(request, "login")

    with pytest.raises(main.HTTPException) as exc:
        main._check_auth_rate_limit(request, "login")

    with main.get_auth_conn() as conn:
        row_count = int(
            conn.execute(
                "SELECT COUNT(1) FROM auth_rate_limits WHERE scope = ? AND client_key = ?",
                ("login", "198.51.100.24"),
            ).fetchone()[0]
        )

    assert exc.value.status_code == 429
    assert row_count == 2


def test_auth_rate_limit_cleans_expired_entries(monkeypatch, tmp_path):
    _configure_temp_databases(monkeypatch, tmp_path, super_admin_password="AdminPass123")
    monkeypatch.setattr(main, "AUTH_RATE_LIMIT_WINDOW_SECONDS", 1)
    main.init_auth_db()

    old_time = main._to_iso(main._utc_now() - main.timedelta(seconds=5))
    with main.get_auth_conn() as conn:
        conn.execute(
            """
            INSERT INTO auth_rate_limits (scope, client_key, attempted_at)
            VALUES (?, ?, ?)
            """,
            ("login", "203.0.113.50", old_time),
        )
        conn.commit()

    main._check_auth_rate_limit(_request_for_host("203.0.113.50"), "login")

    with main.get_auth_conn() as conn:
        row_count = int(
            conn.execute(
                "SELECT COUNT(1) FROM auth_rate_limits WHERE client_key = ?",
                ("203.0.113.50",),
            ).fetchone()[0]
        )

    assert row_count == 1


def test_send_notification_requires_doctor_session(client):
    response = client.post(
        "/send_notification",
        json={
            "report_id": "r1",
            "method": "email",
            "recipient": "doctor@example.com",
            "report_data": {"gender": "male", "predicted_age_years": 10},
        },
    )

    assert response.status_code == 401


def test_send_notification_rejects_non_doctor_and_invalid_targets(client, monkeypatch):
    patient = _insert_user("patient1", main.ROLE_USER, "Patient123")
    doctor = _insert_user("doctor1", main.ROLE_DOCTOR, "Doctor123A")

    user_response = client.post(
        "/send_notification",
        headers=_auth_headers(patient["token"]),
        json={
            "report_id": "r1",
            "method": "email",
            "recipient": "doctor@example.com",
            "report_data": {"gender": "male", "predicted_age_years": 10},
        },
    )
    assert user_response.status_code == 403

    invalid_email = client.post(
        "/send_notification",
        headers=_auth_headers(doctor["token"]),
        json={
            "report_id": "r1",
            "method": "email",
            "recipient": "bad-email",
            "report_data": {"gender": "male", "predicted_age_years": 10},
        },
    )
    assert invalid_email.status_code == 400

    invalid_webhook = client.post(
        "/send_notification",
        headers=_auth_headers(doctor["token"]),
        json={
            "report_id": "r1",
            "method": "wechat",
            "recipient": "https://127.0.0.1/webhook",
            "report_data": {"gender": "male", "predicted_age_years": 10},
        },
    )
    assert invalid_webhook.status_code == 400

    captured = {}

    async def _fake_send_email(**kwargs):
        captured.update(kwargs)
        return {"success": True}

    monkeypatch.setattr(main.NotificationService, "send_email", _fake_send_email)

    valid_response = client.post(
        "/send_notification",
        headers=_auth_headers(doctor["token"]),
        json={
            "report_id": "r1",
            "method": "email",
            "recipient": " valid.doctor@example.com ",
            "remarks": "ok",
            "report_data": {"gender": "male", "predicted_age_years": 10},
        },
    )

    assert valid_response.status_code == 200
    assert captured["recipient"] == "valid.doctor@example.com"


def test_doctor_ai_assistant_streams_with_async_http_client(client, monkeypatch):
    doctor = _insert_user("doctor_stream", main.ROLE_DOCTOR, "Doctor123A")
    monkeypatch.setattr(main, "DEEPSEEK_API_KEY", "test-api-key")

    calls = []

    class FakeStreamResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield 'data: {"choices":[{"delta":{"content":"第一段"}}]}'
            yield "data: [DONE]"

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, method, url, headers=None, json=None):
            calls.append(
                {
                    "method": method,
                    "url": url,
                    "headers": headers,
                    "json": json,
                }
            )
            return FakeStreamResponse()

    monkeypatch.setattr(main.httpx, "AsyncClient", FakeAsyncClient)

    response = client.post(
        "/doctor/ai-assistant",
        headers=_auth_headers(doctor["token"]),
        json={"message": "请总结"},
    )

    assert response.status_code == 200
    assert 'data: {"content": "第一段"}' in response.text
    assert "data: [DONE]" in response.text
    assert calls[0]["method"] == "POST"
    assert calls[0]["json"]["stream"] is True
