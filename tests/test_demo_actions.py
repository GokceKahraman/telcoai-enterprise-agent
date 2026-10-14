"""The synthetic support journey must require approval and survive restarts."""

import sqlite3
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.demo_actions import DemoTimeout

ROOT = Path(__file__).resolve().parent.parent
FIRST = {"account_id": "DEMO-1001", "access_code": "PORTFOLIO-1001"}
SECOND = {"account_id": "DEMO-1002", "access_code": "PORTFOLIO-1002"}


def test_confirmed_ticket_is_idempotent_and_durable(tmp_path):
    settings = Settings(demo_action_db_path=tmp_path / "support.sqlite3")
    with TestClient(create_app(settings)) as client:
        bill = client.post("/api/v1/demo/bills", json=FIRST).json()["bills"][0]
        assert bill["amount_try"] == "549.90"
        assert bill["source"] == "synthetic_demo_billing_fixture"
        draft = client.post(
            "/api/v1/demo/tickets/prepare",
            json={**FIRST, "bill_id": bill["bill_id"], "issue": "billing_dispute"},
        ).json()
        assert draft["requires_confirmation"] is True
        assert draft["source"] == "synthetic_demo_billing_fixture"
        assert (
            client.post(
                "/api/v1/demo/tickets/lookup", json={**FIRST, "ticket_id": f"DT-{'0' * 32}"}
            ).status_code
            == 404
        )
        confirm = {**FIRST, "draft_id": draft["draft_id"], "idempotency_key": str(uuid4())}
        first = client.post("/api/v1/demo/tickets/confirm", json=confirm)
        assert first.status_code == 200
        ticket = first.json()
        assert ticket["source"] == "synthetic_demo_ticket_database"
        assert client.post("/api/v1/demo/tickets/confirm", json=confirm).json() == ticket
        assert (
            client.post(
                "/api/v1/demo/tickets/confirm", json={**confirm, "idempotency_key": str(uuid4())}
            ).status_code
            == 409
        )
        another = client.post(
            "/api/v1/demo/tickets/prepare",
            json={**FIRST, "bill_id": bill["bill_id"], "issue": "billing_dispute"},
        ).json()
        assert (
            client.post(
                "/api/v1/demo/tickets/confirm",
                json={**confirm, "draft_id": another["draft_id"]},
            ).status_code
            == 409
        )
    with TestClient(create_app(settings)) as restarted:
        lookup = restarted.post(
            "/api/v1/demo/tickets/lookup", json={**FIRST, "ticket_id": ticket["id"]}
        )
        assert lookup.json() == ticket
        assert (
            restarted.post(
                "/api/v1/demo/tickets/lookup", json={**SECOND, "ticket_id": ticket["id"]}
            ).status_code
            == 404
        )


def test_demo_access_scope_and_validation(tmp_path):
    settings = Settings(demo_action_db_path=tmp_path / "support.sqlite3")
    with TestClient(create_app(settings)) as client:
        assert (
            client.post("/api/v1/demo/bills", json={**FIRST, "access_code": "wrong"}).status_code
            == 403
        )
        assert (
            client.post(
                "/api/v1/demo/tickets/prepare",
                json={**FIRST, "bill_id": "BILL-2026-09-B", "issue": "billing_dispute"},
            ).status_code
            == 404
        )
        assert (
            client.post(
                "/api/v1/demo/tickets/prepare",
                json={**FIRST, "bill_id": "BILL-2026-09-A", "issue": "send_payment"},
            ).status_code
            == 422
        )
        prepared = client.post(
            "/api/v1/demo/tickets/prepare",
            json={**FIRST, "bill_id": "BILL-2026-09-A", "issue": "billing_dispute"},
        ).json()
        assert (
            client.post(
                "/api/v1/demo/tickets/confirm",
                json={**SECOND, "draft_id": prepared["draft_id"], "idempotency_key": str(uuid4())},
            ).status_code
            == 404
        )
        assert (
            client.post(
                "/api/v1/demo/tickets/confirm",
                json={**FIRST, "draft_id": prepared["draft_id"], "idempotency_key": str(uuid4())},
            ).status_code
            == 200
        )


def test_demo_actions_can_be_disabled_and_global_key_still_applies(tmp_path):
    settings = Settings(demo_action_db_path=tmp_path / "support.sqlite3", api_key="api-key")
    with TestClient(create_app(settings)) as client:
        assert client.post("/api/v1/demo/bills", json=FIRST).status_code == 401
        assert (
            client.post(
                "/api/v1/demo/bills", json=FIRST, headers={"Authorization": "Bearer api-key"}
            ).status_code
            == 200
        )
    with TestClient(create_app(Settings(demo_actions_enabled=False))) as client:
        assert client.post("/api/v1/demo/bills", json=FIRST).status_code == 404


def test_expired_draft_and_timeout_have_defined_responses(tmp_path, monkeypatch):
    database = tmp_path / "support.sqlite3"
    with TestClient(create_app(Settings(demo_action_db_path=database))) as client:
        draft = client.post(
            "/api/v1/demo/tickets/prepare",
            json={**FIRST, "bill_id": "BILL-2026-09-A", "issue": "billing_dispute"},
        ).json()
        with sqlite3.connect(database) as db:
            db.execute(
                "UPDATE draft SET expires_at = ? WHERE id = ?",
                ("2000-01-01T00:00:00+00:00", draft["draft_id"]),
            )
        assert (
            client.post(
                "/api/v1/demo/tickets/confirm",
                json={**FIRST, "draft_id": draft["draft_id"], "idempotency_key": str(uuid4())},
            ).status_code
            == 409
        )

        def unavailable(*args, **kwargs):
            raise DemoTimeout

        monkeypatch.setattr(client.app.state.runtime.demo_actions, "list_bills", unavailable)
        assert client.post("/api/v1/demo/bills", json=FIRST).status_code == 504
