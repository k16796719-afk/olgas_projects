from __future__ import annotations

import json

import asyncpg
from typing import Optional, List

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
  id BIGSERIAL PRIMARY KEY,
  tg_user_id BIGINT UNIQUE NOT NULL,
  username TEXT,
  first_name TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS orders (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  direction TEXT NOT NULL,
  payload_json JSONB NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft', -- draft/awaiting_payment/paid/cancelled
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS payments (
  id BIGSERIAL PRIMARY KEY,
  order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  method TEXT NOT NULL, -- rub_card/pix/crypto
  currency TEXT NOT NULL, -- RUB/BRL/USDT
  amount INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending', -- pending/proof_submitted/paid/rejected
  proof_file_id TEXT,
  admin_id_approved BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS subscriptions (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  product TEXT NOT NULL, -- yoga_4/yoga_8/yoga_10_individual
  status TEXT NOT NULL DEFAULT 'active', -- active/expired
  starts_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL,
  last_payment_id BIGINT REFERENCES payments(id)
);

CREATE TABLE IF NOT EXISTS channel_access_log (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  channel_key TEXT NOT NULL,
  invite_link TEXT,
  granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  revoked_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_expires ON subscriptions(expires_at);
"""

class Database:
    def __init__(self, dsn: str):
        self._dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        self.pool = await asyncpg.create_pool(dsn=self._dsn, min_size=1, max_size=10)
        async with self.pool.acquire() as con:
            await con.execute(SCHEMA_SQL)

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()

    async def fetchrow(self, q: str, *args) -> Optional[asyncpg.Record]:
        assert self.pool
        async with self.pool.acquire() as con:
            return await con.fetchrow(q, *args)

    async def fetch(self, q: str, *args) -> List[asyncpg.Record]:
        assert self.pool
        async with self.pool.acquire() as con:
            return await con.fetch(q, *args)

    async def execute(self, q: str, *args) -> str:
        assert self.pool
        async with self.pool.acquire() as con:
            return await con.execute(q, *args)

    # Users
    async def upsert_user(self, tg_user_id: int, username: str | None, first_name: str | None) -> int:
        row = await self.fetchrow("SELECT id FROM users WHERE tg_user_id=$1", tg_user_id)
        if row:
            await self.execute(
                "UPDATE users SET username=$2, first_name=$3 WHERE tg_user_id=$1",
                tg_user_id, username, first_name
            )
            return int(row["id"])
        row2 = await self.fetchrow(
            "INSERT INTO users(tg_user_id, username, first_name) VALUES($1,$2,$3) RETURNING id",
            tg_user_id, username, first_name
        )
        return int(row2["id"])

    async def get_user_id(self, tg_user_id: int) -> Optional[int]:
        row = await self.fetchrow("SELECT id FROM users WHERE tg_user_id=$1", tg_user_id)
        return int(row["id"]) if row else None

    # Orders
    async def create_order(self, user_id: int, direction: str, payload: dict, status: str = "draft") -> int:
        row = await self.fetchrow(
            "INSERT INTO orders(user_id, direction, payload_json, status) VALUES($1,$2,$3,$4) RETURNING id",
            user_id, direction, json.dumps(payload, ensure_ascii=False), status
        )
        return int(row["id"])

    async def set_order_status(self, order_id: int, status: str) -> None:
        await self.execute("UPDATE orders SET status=$2 WHERE id=$1", order_id, status)

    async def get_order(self, order_id: int) -> Optional[dict]:
        row = await self.fetchrow("SELECT * FROM orders WHERE id=$1", order_id)
        return dict(row) if row else None

    # Payments
    async def create_payment(self, order_id: int, method: str, currency: str, amount: int) -> int:
        row = await self.fetchrow(
            "INSERT INTO payments(order_id, method, currency, amount) VALUES($1,$2,$3,$4) RETURNING id",
            order_id, method, currency, amount
        )
        return int(row["id"])

    async def get_payment(self, payment_id: int) -> Optional[dict]:
        row = await self.fetchrow("SELECT * FROM payments WHERE id=$1", payment_id)
        return dict(row) if row else None

    async def update_payment_proof(self, payment_id: int, proof_file_id: str) -> None:
        await self.execute(
            "UPDATE payments SET status='proof_submitted', proof_file_id=$2, updated_at=NOW() WHERE id=$1",
            payment_id, proof_file_id
        )

    async def approve_payment(self, payment_id: int, admin_id: int) -> None:
        await self.execute(
            "UPDATE payments SET status='paid', admin_id_approved=$2, updated_at=NOW() WHERE id=$1",
            payment_id, admin_id
        )

    async def reject_payment(self, payment_id: int, admin_id: int) -> None:
        await self.execute(
            "UPDATE payments SET status='rejected', admin_id_approved=$2, updated_at=NOW() WHERE id=$1",
            payment_id, admin_id
        )

    async def pending_payment_exists_for_user(self, tg_user_id: int) -> bool:
        q = """
        SELECT 1
        FROM payments p
        JOIN orders o ON o.id=p.order_id
        JOIN users u ON u.id=o.user_id
        WHERE u.tg_user_id=$1 AND p.status IN ('pending','proof_submitted')
        LIMIT 1
        """
        row = await self.fetchrow(q, tg_user_id)
        return row is not None

    # Subscriptions (Yoga)
    async def create_yoga_subscription(self, user_id: int, product: str, expires_at, last_payment_id: int) -> int:
        row = await self.fetchrow(
            "INSERT INTO subscriptions(user_id, product, expires_at, last_payment_id) VALUES($1,$2,$3,$4) RETURNING id",
            user_id, product, expires_at, last_payment_id
        )
        return int(row["id"])

    async def expire_subscriptions_due(self):
        q = """
        SELECT s.id, s.user_id, u.tg_user_id, s.product
        FROM subscriptions s
        JOIN users u ON u.id=s.user_id
        WHERE s.status='active' AND s.expires_at <= NOW()
        """
        return [dict(r) for r in await self.fetch(q)]

    async def mark_subscription_expired(self, sub_id: int):
        await self.execute("UPDATE subscriptions SET status='expired' WHERE id=$1", sub_id)

    async def log_channel_access(self, user_id: int, channel_key: str, invite_link: str | None):
        await self.execute(
            "INSERT INTO channel_access_log(user_id, channel_key, invite_link) VALUES($1,$2,$3)",
            user_id, channel_key, invite_link
        )

    async def log_channel_revoke(self, user_id: int, channel_key: str):
        await self.execute(
            "UPDATE channel_access_log SET revoked_at=NOW() WHERE user_id=$1 AND channel_key=$2 AND revoked_at IS NULL",
            user_id, channel_key
        )
# db.py

    async def cancel_order(self, order_id: int) -> None:
        await self.execute(
            "UPDATE orders SET status='cancelled' WHERE id=$1 AND status IN ('pending','created')",
            order_id
        )

    async def cancel_pending_payments_for_order(self, order_id: int) -> None:
        await self.execute(
            "UPDATE payments SET status='cancelled' WHERE order_id=$1 AND status='pending'",
            order_id
        )

    async def get_user_id_by_tg(self, tg_user_id: int) -> int | None:
        row = await self.fetchrow(
            "SELECT id FROM users WHERE tg_user_id=$1",
            tg_user_id,
        )
        if not row:
            return None
        return int(row["id"])
