from __future__ import annotations
from typing import Any, Optional, Sequence
import asyncpg

class YogaFeedbackRepo:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def upsert_blank(self, user_id: int, subscription_id: int) -> None:
        sql = """
        INSERT INTO yoga_feedback (user_id, subscription_id)
        VALUES ($1, $2)
        ON CONFLICT (user_id, subscription_id) DO NOTHING
        """
        async with self.pool.acquire() as conn:
            await conn.execute(sql, user_id, subscription_id)

    async def set_answer(self, user_id: int, subscription_id: int, field: str, value: Any) -> None:
        # field контролируем строго (whitelist)
        allowed = {
            "q1_difficulty", "q2_pace", "q3_state", "q4_format", "q5_frequency", "q6_preferences"
        }
        if field not in allowed:
            raise ValueError(f"Invalid field: {field}")

        sql = f"""
        UPDATE yoga_feedback
        SET {field} = $3, updated_at = now()
        WHERE user_id = $1 AND subscription_id = $2
        """
        async with self.pool.acquire() as conn:
            await conn.execute(sql, user_id, subscription_id, value)

    async def get(self, user_id: int, subscription_id: int) -> Optional[dict]:
        sql = """
        SELECT *
        FROM yoga_feedback
        WHERE user_id = $1 AND subscription_id = $2
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(sql, user_id, subscription_id)
            return dict(row) if row else None
