from __future__ import annotations
from datetime import date
import asyncpg

class SubscriptionsRepo:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def list_expiring_tomorrow(self, today: date) -> list[dict]:
        # истекают завтра, активны, фидбек ещё не слали
        sql = """
        SELECT id, user_id, expires_at
        FROM subscriptions
        WHERE status = 'active'
          AND expires_at IS NOT NULL
          AND (expires_at::date = ($1::date + INTERVAL '1 day')::date)
          AND feedback_sent_at IS NULL
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql, today)
            return [dict(r) for r in rows]

    async def mark_feedback_sent(self, subscription_id: int) -> None:
        sql = """
        UPDATE subscriptions
        SET feedback_sent_at = now()
        WHERE id = $1
        """
        async with self.pool.acquire() as conn:
            await conn.execute(sql, subscription_id)
