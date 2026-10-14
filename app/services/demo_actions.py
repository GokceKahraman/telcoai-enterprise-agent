"""Synthetic billing lookup and confirmed, idempotent support tickets.

Demo access codes are published with the fictional fixture. They illustrate an
authorization boundary but are not credentials for real customer data.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from secrets import compare_digest
from uuid import uuid4


class DemoAccessDenied(Exception):
    pass


class DemoNotFound(Exception):
    pass


class DemoConflict(Exception):
    pass


class DemoTimeout(Exception):
    pass


class DemoActionService:
    def __init__(self, records_path: Path, database_path: Path) -> None:
        raw = json.loads(records_path.read_text(encoding="utf-8"))
        self._accounts = {account["account_id"]: account for account in raw["accounts"]}
        self._database_path = database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS draft (
                    id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    bill_id TEXT NOT NULL,
                    issue TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ticket (
                    id TEXT PRIMARY KEY,
                    draft_id TEXT NOT NULL UNIQUE,
                    account_id TEXT NOT NULL,
                    bill_id TEXT NOT NULL,
                    issue TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(account_id, idempotency_key)
                );
                """
            )

    @contextmanager
    def _connect(self):
        try:
            connection = sqlite3.connect(self._database_path, timeout=2)
            connection.row_factory = sqlite3.Row
        except sqlite3.OperationalError as exc:
            raise DemoTimeout from exc
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _account(self, account_id: str, access_code: str) -> dict:
        account = self._accounts.get(account_id)
        if account is None or not compare_digest(account["access_code"], access_code):
            raise DemoAccessDenied
        return account

    @staticmethod
    def _bill(account: dict, bill_id: str) -> dict:
        bill = next((item for item in account["bills"] if item["bill_id"] == bill_id), None)
        if bill is None:
            raise DemoNotFound
        return bill

    def list_bills(self, account_id: str, access_code: str) -> list[dict]:
        account = self._account(account_id, access_code)
        bills = []
        for bill in account["bills"]:
            total = sum((Decimal(item["amount_try"]) for item in bill["items"]), Decimal(0))
            if total != Decimal(bill["amount_try"]):
                raise ValueError("Synthetic bill items do not equal the total")
            bills.append({**bill, "source": "synthetic_demo_billing_fixture"})
        return bills

    def prepare(self, account_id: str, access_code: str, bill_id: str, issue: str) -> dict:
        account = self._account(account_id, access_code)
        bill = self._bill(account, bill_id)
        if issue not in {"billing_dispute", "payment_not_reflected"}:
            raise ValueError("Unsupported demo issue")
        draft_id = str(uuid4())
        expires_at = (datetime.now(UTC) + timedelta(minutes=15)).isoformat()
        try:
            with self._connect() as db:
                db.execute(
                    "INSERT INTO draft VALUES (?, ?, ?, ?, ?)",
                    (draft_id, account_id, bill_id, issue, expires_at),
                )
        except sqlite3.OperationalError as exc:
            raise DemoTimeout from exc
        return {
            "draft_id": draft_id,
            "expires_at": expires_at,
            "account_id": account_id,
            "bill_id": bill["bill_id"],
            "period": bill["period"],
            "amount_try": bill["amount_try"],
            "issue": issue,
            "source": "synthetic_demo_billing_fixture",
            "requires_confirmation": True,
        }

    def confirm(
        self, account_id: str, access_code: str, draft_id: str, idempotency_key: str
    ) -> dict:
        self._account(account_id, access_code)
        try:
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                draft = db.execute("SELECT * FROM draft WHERE id = ?", (draft_id,)).fetchone()
                if draft is None or draft["account_id"] != account_id:
                    raise DemoNotFound
                existing = db.execute(
                    "SELECT * FROM ticket WHERE draft_id = ?", (draft_id,)
                ).fetchone()
                if existing is not None:
                    if existing["idempotency_key"] != idempotency_key:
                        raise DemoConflict
                    return dict(existing)
                if datetime.fromisoformat(draft["expires_at"]) <= datetime.now(UTC):
                    raise DemoConflict
                ticket_id = f"DT-{uuid4().hex.upper()}"
                created_at = datetime.now(UTC).isoformat()
                try:
                    db.execute(
                        "INSERT INTO ticket VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            ticket_id,
                            draft_id,
                            account_id,
                            draft["bill_id"],
                            draft["issue"],
                            idempotency_key,
                            created_at,
                        ),
                    )
                except sqlite3.IntegrityError as exc:
                    raise DemoConflict from exc
                return {
                    "id": ticket_id,
                    "draft_id": draft_id,
                    "account_id": account_id,
                    "bill_id": draft["bill_id"],
                    "issue": draft["issue"],
                    "idempotency_key": idempotency_key,
                    "created_at": created_at,
                }
        except sqlite3.OperationalError as exc:
            raise DemoTimeout from exc

    def get_ticket(self, account_id: str, access_code: str, ticket_id: str) -> dict:
        self._account(account_id, access_code)
        try:
            with self._connect() as db:
                ticket = db.execute(
                    "SELECT * FROM ticket WHERE id = ? AND account_id = ?",
                    (ticket_id, account_id),
                ).fetchone()
        except sqlite3.OperationalError as exc:
            raise DemoTimeout from exc
        if ticket is None:
            raise DemoNotFound
        return dict(ticket)
