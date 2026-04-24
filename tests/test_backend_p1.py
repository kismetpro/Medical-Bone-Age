import secrets
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
import pytest
import torch
import torch.nn as nn


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
    monkeypatch.setattr(main.app.router, "lifespan_context", _noop_lifespan)
    return auth_db, prediction_db


def _init_temp_auth_db(monkeypatch, tmp_path):
    _configure_temp_databases(monkeypatch, tmp_path)
    main.init_auth_db()


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
    return {"user_id": user_id, "token": session["token"]}


def test_joint_grader_predict_accepts_preprocessed_tensor(monkeypatch):
    grader = main.JointGrader("unused", torch.device("cpu"))

    class DummyJointModel(nn.Module):
        def forward(self, x, lambda_grl=0.0):
            logits = torch.tensor([[0.1, 0.9]], dtype=torch.float32, device=x.device)
            return logits, None, None

    grader.models = {
        "Radius": {
            "model": DummyJointModel(),
            "idx_to_class": {0: 3, 1: 4},
        }
    }

    monkeypatch.setattr(
        grader,
        "preprocess",
        lambda image_bytes, img_size, mean, std: torch.zeros(
            (1, 3, img_size, img_size), dtype=torch.float32
        ),
    )

    result = grader.predict(
        b"ignored",
        224,
        np.zeros(3, dtype=np.float32),
        np.ones(3, dtype=np.float32),
    )

    assert result["Radius"]["grade_raw"] == 4
    assert result["Radius"]["grade_idx"] == 1


def test_get_session_does_not_trigger_cleanup_on_read(monkeypatch, tmp_path):
    _init_temp_auth_db(monkeypatch, tmp_path)
    inserted = _insert_user("doctor_reader", main.ROLE_DOCTOR, "Doctor123A")

    def _unexpected_cleanup(conn):
        raise AssertionError("cleanup_expired_sessions should not run during get_session")

    monkeypatch.setattr(main, "cleanup_expired_sessions", _unexpected_cleanup)

    with main.get_auth_conn() as conn:
        row = main.get_session(conn, inserted["token"])

    assert row is not None
    assert row["username"] == "doctor_reader"


def test_resolve_hand_side_uses_single_consistent_rule():
    assert main._resolve_hand_side(200.0, 100.0) == "left"
    assert main._resolve_hand_side(100.0, 200.0) == "right"
    assert main._resolve_hand_side(None, 200.0) == "unknown"
    assert main._resolve_hand_side(None, 200.0, fallback="left") == "left"


def test_resolve_hand_side_from_regions_delegates_to_helper():
    regions = [
        {"label": "Radius", "centroid": (320.0, 100.0), "confidence": 0.8},
        {"label": "Ulna", "centroid": (120.0, 100.0), "confidence": 0.7},
    ]
    assert main._resolve_hand_side_from_regions(regions) == "left"


def test_render_with_plt_returns_base64_plot():
    recognizer = object.__new__(main.SmallJointRecognizer)
    image = np.zeros((64, 64, 3), dtype=np.uint8)
    joints = {
        "Radius": {
            "bbox_xyxy": [5.0, 6.0, 25.0, 28.0],
            "score": 0.95,
        }
    }

    rendered = recognizer._render_with_plt(
        image,
        joints,
        hand_side="left",
        grades={"Radius": {"grade_raw": 4}},
    )

    assert rendered is not None
    assert rendered.startswith("data:image/jpeg;base64,")


def test_build_gradcam_heatmap_preserves_unrelated_hooks(monkeypatch):
    class FakeBackbone(nn.Module):
        def __init__(self):
            super().__init__()
            self.layer4 = nn.Sequential(
                nn.Conv2d(3, 4, kernel_size=3, padding=1),
                nn.Conv2d(4, 4, kernel_size=3, padding=1),
            )
            self.pool = nn.AdaptiveAvgPool2d((1, 1))

        def forward(self, x):
            x = self.layer4(x)
            return self.pool(x).flatten(1)

    class FakeBoneAgeModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.backbone = FakeBackbone()
            self.regressor = nn.Linear(5, 1)

        def forward(self, x, gender):
            feat = self.backbone(x)
            combined = torch.cat((feat, gender), dim=1)
            return self.regressor(combined)

    fake_model = FakeBoneAgeModel()
    target = fake_model.backbone.layer4[-1]
    forward_handle = target.register_forward_hook(lambda module, inputs, output: None)
    backward_handle = target.register_full_backward_hook(
        lambda module, grad_input, grad_output: None
    )
    expected_forward_hooks = len(target._forward_hooks)
    expected_backward_hooks = len(target._backward_hooks)

    monkeypatch.setattr(main, "models_ensemble", [{"model": fake_model}])

    heatmap = main.build_gradcam_heatmap(
        torch.rand((1, 3, 64, 64), dtype=torch.float32),
        torch.ones((1, 1), dtype=torch.float32),
    )

    assert heatmap is not None
    assert heatmap.startswith("data:image/jpeg;base64,")
    assert len(target._forward_hooks) == expected_forward_hooks
    assert len(target._backward_hooks) == expected_backward_hooks

    forward_handle.remove()
    backward_handle.remove()
