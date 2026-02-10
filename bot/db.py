from __future__ import annotations

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Optional, List

import asyncpg

logger = logging.getLogger(__name__)


# Константы для статусов
class OrderStatus(str, Enum):
    """Статусы заказов."""
    DRAFT = "draft"
    AWAITING_PAYMENT = "awaiting_payment"
    PAID = "paid"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    """Статусы платежей."""
    PENDING = "pending"
    PROOF_SUBMITTED = "proof_submitted"
    PAID = "paid"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class SubscriptionStatus(str, Enum):
    """Статусы подписок."""
    ACTIVE = "active"
    EXPIRED = "expired"


# SQL схема базы данных
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
  status TEXT NOT NULL DEFAULT 'draft',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS payments (
  id BIGSERIAL PRIMARY KEY,
  order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  method TEXT NOT NULL,
  currency TEXT NOT NULL,
  amount INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  proof_file_id TEXT,
  admin_id_approved BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS subscriptions (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  product TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  starts_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ,
  last_payment_id BIGINT REFERENCES payments(id),
  channel_id BIGINT,
  joined_at TIMESTAMPTZ DEFAULT NOW(),
  feedback_sent_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS channel_access_log (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  channel_key TEXT NOT NULL,
  invite_link TEXT,
  granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  revoked_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS yoga_feedback (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL,
  subscription_id BIGINT NOT NULL,
  q1_difficulty TEXT,
  q2_pace TEXT,
  q3_state TEXT,
  q4_format TEXT,
  q5_frequency TEXT,
  q6_preferences TEXT[],
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(user_id, subscription_id)
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_users_tg_user_id ON users(tg_user_id);
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_payments_order_id ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_expires_at ON subscriptions(expires_at);
CREATE INDEX IF NOT EXISTS idx_subscriptions_channel_id ON subscriptions(channel_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_product ON subscriptions(product);
CREATE INDEX IF NOT EXISTS idx_yoga_feedback_user_sub ON yoga_feedback(user_id, subscription_id);
CREATE INDEX IF NOT EXISTS idx_channel_access_log_user ON channel_access_log(user_id, channel_key);
"""


class DatabaseError(Exception):
    """Базовое исключение для ошибок БД."""
    pass


class Database:
    """Класс для работы с PostgreSQL базой данных."""

    def __init__(self, dsn: str):
        """
        Инициализация database wrapper.

        Args:
            dsn: PostgreSQL connection string
        """
        self._dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        """Создать connection pool и применить схему БД."""
        try:
            self.pool = await asyncpg.create_pool(
                dsn=self._dsn,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            async with self.pool.acquire() as con:
                await con.execute(SCHEMA_SQL)
            logger.info("Database connected and schema applied")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise DatabaseError(f"Connection failed: {e}") from e

    async def close(self) -> None:
        """Закрыть connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection closed")

    def _ensure_pool(self) -> None:
        """Проверить, что pool инициализирован."""
        if not self.pool:
            raise DatabaseError("Database pool is not initialized. Call connect() first.")

    async def fetchrow(self, q: str, *args) -> Optional[asyncpg.Record]:
        """Выполнить запрос и вернуть одну строку."""
        self._ensure_pool()
        try:
            async with self.pool.acquire() as con:
                return await con.fetchrow(q, *args)
        except Exception as e:
            logger.error(f"fetchrow failed: {e}\nQuery: {q}\nArgs: {args}")
            raise DatabaseError(f"Query failed: {e}") from e

    async def fetch(self, q: str, *args) -> List[asyncpg.Record]:
        """Выполнить запрос и вернуть несколько строк."""
        self._ensure_pool()
        try:
            async with self.pool.acquire() as con:
                return await con.fetch(q, *args)
        except Exception as e:
            logger.error(f"fetch failed: {e}\nQuery: {q}\nArgs: {args}")
            raise DatabaseError(f"Query failed: {e}") from e

    async def execute(self, q: str, *args) -> str:
        """Выполнить запрос без возврата данных."""
        self._ensure_pool()
        try:
            async with self.pool.acquire() as con:
                return await con.execute(q, *args)
        except Exception as e:
            logger.error(f"execute failed: {e}\nQuery: {q}\nArgs: {args}")
            raise DatabaseError(f"Query failed: {e}") from e

    # ==================== Users ====================

    async def upsert_user(
            self,
            tg_user_id: int,
            username: Optional[str],
            first_name: Optional[str]
    ) -> int:
        """
        Создать или обновить пользователя.

        Args:
            tg_user_id: Telegram user ID
            username: Telegram username
            first_name: Имя пользователя

        Returns:
            Internal user ID
        """
        row = await self.fetchrow("SELECT id FROM users WHERE tg_user_id=$1", tg_user_id)
        if row:
            await self.execute(
                "UPDATE users SET username=$2, first_name=$3 WHERE tg_user_id=$1",
                tg_user_id, username, first_name
            )
            user_id = int(row["id"])
            logger.debug(f"Updated user {user_id} (tg_id: {tg_user_id})")
            return user_id

        row2 = await self.fetchrow(
            "INSERT INTO users(tg_user_id, username, first_name) VALUES($1,$2,$3) RETURNING id",
            tg_user_id, username, first_name
        )
        user_id = int(row2["id"])
        logger.info(f"Created new user {user_id} (tg_id: {tg_user_id})")
        return user_id

    async def get_user_id_by_tg(self, tg_user_id: int) -> Optional[int]:
        """
        Получить internal user ID по Telegram ID.

        Args:
            tg_user_id: Telegram user ID

        Returns:
            Internal user ID или None если не найден
        """
        row = await self.fetchrow("SELECT id FROM users WHERE tg_user_id=$1", tg_user_id)
        return int(row["id"]) if row else None

    # ==================== Orders ====================

    async def create_order(
            self,
            user_id: int,
            direction: str,
            payload: dict,
            status: str = OrderStatus.DRAFT
    ) -> int:
        """
        Создать новый заказ.

        Args:
            user_id: Internal user ID
            direction: Направление (yoga, english, etc.)
            payload: Дополнительные данные заказа
            status: Начальный статус

        Returns:
            Order ID
        """
        row = await self.fetchrow(
            """
            INSERT INTO orders(user_id, direction, payload_json, status)
            VALUES($1, $2, $3, $4)
            RETURNING id
            """,
            user_id, direction, json.dumps(payload, ensure_ascii=False), status
        )
        order_id = int(row["id"])
        logger.info(f"Created order {order_id} for user {user_id}, direction: {direction}")
        return order_id

    async def get_order(self, order_id: int) -> Optional[dict]:
        """
        Получить данные заказа.

        Args:
            order_id: Order ID

        Returns:
            Dict с данными заказа или None
        """
        row = await self.fetchrow(
            """
            SELECT id, user_id, direction, payload_json, status, created_at
            FROM orders
            WHERE id=$1
            """,
            order_id
        )
        return dict(row) if row else None

    async def set_order_status(self, order_id: int, status: str) -> None:
        """
        Обновить статус заказа.

        Args:
            order_id: Order ID
            status: Новый статус
        """
        await self.execute(
            "UPDATE orders SET status=$2 WHERE id=$1",
            order_id, status
        )
        logger.info(f"Order {order_id} status changed to {status}")

    async def cancel_order(self, order_id: int) -> None:
        """
        Отменить заказ (только если он в статусе draft или awaiting_payment).

        Args:
            order_id: Order ID
        """
        result = await self.execute(
            """
            UPDATE orders
            SET status=$2
            WHERE id=$1 AND status IN ($3, $4)
            """,
            order_id,
            OrderStatus.CANCELLED,
            OrderStatus.DRAFT,
            OrderStatus.AWAITING_PAYMENT
        )
        logger.info(f"Cancelled order {order_id}: {result}")

    # ==================== Payments ====================

    async def create_payment(
            self,
            order_id: int,
            method: str,
            currency: str,
            amount: int
    ) -> int:
        """
        Создать новый платёж.

        Args:
            order_id: Order ID
            method: Метод оплаты (rub_card, pix, crypto)
            currency: Валюта (RUB, BRL, USDT)
            amount: Сумма в минимальных единицах

        Returns:
            Payment ID
        """
        row = await self.fetchrow(
            """
            INSERT INTO payments(order_id, method, currency, amount)
            VALUES($1, $2, $3, $4)
            RETURNING id
            """,
            order_id, method, currency, amount
        )
        payment_id = int(row["id"])
        logger.info(
            f"Created payment {payment_id} for order {order_id}: "
            f"{amount} {currency} via {method}"
        )
        return payment_id

    async def get_payment(self, payment_id: int) -> Optional[dict]:
        """
        Получить данные платежа.

        Args:
            payment_id: Payment ID

        Returns:
            Dict с данными платежа или None
        """
        row = await self.fetchrow(
            """
            SELECT id, order_id, method, currency, amount, status,
                   proof_file_id, admin_id_approved, created_at, updated_at
            FROM payments
            WHERE id=$1
            """,
            payment_id
        )
        return dict(row) if row else None

    async def update_payment_proof(self, payment_id: int, proof_file_id: str) -> None:
        """
        Сохранить proof (чек) для платежа.

        Args:
            payment_id: Payment ID
            proof_file_id: Telegram file_id скриншота/чека
        """
        await self.execute(
            """
            UPDATE payments
            SET status=$2, proof_file_id=$3, updated_at=NOW()
            WHERE id=$1
            """,
            payment_id, PaymentStatus.PROOF_SUBMITTED, proof_file_id
        )
        logger.info(f"Payment {payment_id} proof submitted")

    async def approve_payment(self, payment_id: int, admin_id: int) -> None:
        """
        Одобрить платёж.

        Args:
            payment_id: Payment ID
            admin_id: ID админа, одобрившего платёж
        """
        await self.execute(
            """
            UPDATE payments
            SET status=$2, admin_id_approved=$3, updated_at=NOW()
            WHERE id=$1
            """,
            payment_id, PaymentStatus.PAID, admin_id
        )
        logger.info(f"Payment {payment_id} approved by admin {admin_id}")

    async def reject_payment(self, payment_id: int, admin_id: int) -> None:
        """
        Отклонить платёж.

        Args:
            payment_id: Payment ID
            admin_id: ID админа, отклонившего платёж
        """
        await self.execute(
            """
            UPDATE payments
            SET status=$2, admin_id_approved=$3, updated_at=NOW()
            WHERE id=$1
            """,
            payment_id, PaymentStatus.REJECTED, admin_id
        )
        logger.info(f"Payment {payment_id} rejected by admin {admin_id}")

    async def cancel_pending_payments_for_order(self, order_id: int) -> None:
        """
        Отменить все незавершённые платежи для заказа.

        Args:
            order_id: Order ID
        """
        result = await self.execute(
            """
            UPDATE payments
            SET status=$2
            WHERE order_id=$1 AND status IN ($3, $4)
            """,
            order_id,
            PaymentStatus.CANCELLED,
            PaymentStatus.PENDING,
            PaymentStatus.PROOF_SUBMITTED
        )
        logger.info(f"Cancelled pending payments for order {order_id}: {result}")

    async def pending_payment_exists_for_user(self, tg_user_id: int) -> bool:
        """
        Проверить, есть ли у пользователя незавершённые платежи.

        Args:
            tg_user_id: Telegram user ID

        Returns:
            True если есть pending/proof_submitted платежи
        """
        row = await self.fetchrow(
            """
            SELECT 1
            FROM payments p
            JOIN orders o ON o.id = p.order_id
            JOIN users u ON u.id = o.user_id
            WHERE u.tg_user_id = $1
              AND p.status IN ($2, $3)
            LIMIT 1
            """,
            tg_user_id,
            PaymentStatus.PENDING,
            PaymentStatus.PROOF_SUBMITTED
        )
        return row is not None

    # ==================== Subscriptions ====================

    async def create_yoga_subscription(
            self,
            user_id: int,
            product: str,
            expires_at: Optional[datetime],
            last_payment_id: int,
            channel_id: Optional[int] = None
    ) -> int:
        """
        Создать новую подписку на йогу.

        Args:
            user_id: Internal user ID
            product: Код продукта (yoga_4, yoga_8, yoga_ind)
            expires_at: Дата окончания подписки
            last_payment_id: ID последнего платежа
            channel_id: ID Telegram канала (опционально)

        Returns:
            Subscription ID
        """
        row = await self.fetchrow(
            """
            INSERT INTO subscriptions(user_id, product, expires_at, last_payment_id, channel_id)
            VALUES($1, $2, $3, $4, $5)
            RETURNING id
            """,
            user_id, product, expires_at, last_payment_id, channel_id
        )
        sub_id = int(row["id"])
        logger.info(
            f"Created yoga subscription {sub_id} for user {user_id}, "
            f"product: {product}, expires: {expires_at}"
        )
        return sub_id

    async def get_active_yoga_subscription(self, user_id: int) -> Optional[dict]:
        """
        Получить активную подписку на йогу.

        Подписка считается активной если expires_at в будущем или NULL.

        Args:
            user_id: Internal user ID

        Returns:
            Dict с данными подписки или None
        """
        row = await self.fetchrow(
            """
            SELECT id, user_id, product, expires_at, last_payment_id, channel_id, status
            FROM subscriptions
            WHERE user_id = $1
              AND product LIKE 'yoga_%'
              AND status = $2
              AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY expires_at DESC NULLS FIRST, id DESC
            LIMIT 1
            """,
            user_id,
            SubscriptionStatus.ACTIVE
        )
        return dict(row) if row else None

    async def upsert_yoga_subscription(
            self,
            user_id: int,
            product: str,
            expires_at: Optional[datetime],
            last_payment_id: int,
            channel_id: Optional[int] = None
    ) -> int:
        """
        Обновить существующую или создать новую подписку на йогу.

        Args:
            user_id: Internal user ID
            product: Код продукта
            expires_at: Дата окончания
            last_payment_id: ID последнего платежа
            channel_id: ID канала (опционально)

        Returns:
            Subscription ID
        """
        # Пытаемся найти существующую подписку
        existing = await self.fetchrow(
            """
            SELECT id FROM subscriptions
            WHERE user_id = $1 AND product LIKE 'yoga_%'
            ORDER BY id DESC
            LIMIT 1
            """,
            user_id
        )

        if existing:
            # Обновляем существующую
            sub_id = int(existing["id"])
            await self.execute(
                """
                UPDATE subscriptions
                SET product = $2, expires_at = $3, last_payment_id = $4,
                    channel_id = $5, status = $6
                WHERE id = $1
                """,
                sub_id, product, expires_at, last_payment_id, channel_id,
                SubscriptionStatus.ACTIVE
            )
            logger.info(f"Updated yoga subscription {sub_id} for user {user_id}")
            return sub_id

        # Создаём новую
        return await self.create_yoga_subscription(
            user_id, product, expires_at, last_payment_id, channel_id
        )

    async def is_first_yoga_subscription(self, user_id: int) -> bool:
        """
        Проверить, первая ли это йога-подписка пользователя.

        Args:
            user_id: Internal user ID

        Returns:
            True если у пользователя ещё не было йога-подписок
        """
        row = await self.fetchrow(
            "SELECT 1 FROM subscriptions WHERE user_id=$1 AND product LIKE 'yoga_%' LIMIT 1",
            user_id
        )
        return row is None

    async def expire_subscriptions_due(self) -> List[dict]:
        """
        Получить список подписок, которые истекли.

        Returns:
            List of dicts с данными истекших подписок
        """
        rows = await self.fetch(
            """
            SELECT s.id, s.user_id, u.tg_user_id, s.product
            FROM subscriptions s
            JOIN users u ON u.id = s.user_id
            WHERE s.status = $1 AND s.expires_at <= NOW()
            """,
            SubscriptionStatus.ACTIVE
        )
        return [dict(r) for r in rows]

    async def get_expired_yoga_subscriptions(self, now: datetime) -> List[asyncpg.Record]:
        """
        Получить йога-подписки, истекшие к указанной дате.

        Args:
            now: Дата для сравнения

        Returns:
            List of records с данными подписок
        """
        return await self.fetch(
            """
            SELECT s.id, s.channel_id, u.tg_user_id
            FROM subscriptions s
            JOIN users u ON u.id = s.user_id
            WHERE s.product LIKE 'yoga_%'
              AND s.expires_at <= $1
              AND s.status = $2
              AND s.channel_id IS NOT NULL
            """,
            now,
            SubscriptionStatus.ACTIVE
        )

    async def mark_subscription_expired(self, sub_id: int) -> None:
        """
        Пометить подписку как истекшую.

        Args:
            sub_id: Subscription ID
        """
        await self.execute(
            "UPDATE subscriptions SET status=$2 WHERE id=$1",
            sub_id,
            SubscriptionStatus.EXPIRED
        )
        logger.info(f"Subscription {sub_id} marked as expired")

    # ==================== Channel Access ====================

    async def log_channel_access(
            self,
            user_id: int,
            channel_key: str,
            invite_link: Optional[str]
    ) -> None:
        """
        Залогировать выдачу доступа к каналу.

        Args:
            user_id: Internal user ID
            channel_key: Ключ канала
            invite_link: Invite link (опционально)
        """
        await self.execute(
            """
            INSERT INTO channel_access_log(user_id, channel_key, invite_link)
            VALUES($1, $2, $3)
            """,
            user_id, channel_key, invite_link
        )
        logger.info(f"Logged channel access for user {user_id}, channel: {channel_key}")

    async def log_channel_revoke(self, user_id: int, channel_key: str) -> None:
        """
        Залогировать отзыв доступа к каналу.

        Args:
            user_id: Internal user ID
            channel_key: Ключ канала
        """
        await self.execute(
            """
            UPDATE channel_access_log
            SET revoked_at = NOW()
            WHERE user_id = $1 AND channel_key = $2 AND revoked_at IS NULL
            """,
            user_id, channel_key
        )
        logger.info(f"Logged channel revoke for user {user_id}, channel: {channel_key}")

    # ==================== Yoga Feedback ====================

    async def get_subscriptions_expiring_between(
            self,
            start: datetime,
            end: datetime
    ) -> List[asyncpg.Record]:
        """
        Получить подписки на йогу, истекающие в заданном временном окне.

        Args:
            start: Начало временного окна
            end: Конец временного окна

        Returns:
            List of records с подписками
        """
        return await self.fetch(
            """
            SELECT s.id, s.user_id, s.product, s.expires_at, s.feedback_sent_at,
                   u.tg_user_id
            FROM subscriptions s
            JOIN users u ON u.id = s.user_id
            WHERE s.product LIKE 'yoga_%'
              AND s.status = $1
              AND s.expires_at BETWEEN $2 AND $3
            ORDER BY s.expires_at ASC
            """,
            SubscriptionStatus.ACTIVE,
            start,
            end
        )

    async def mark_feedback_sent(self, sub_id: int) -> None:
        """
        Пометить, что для подписки отправлен запрос на feedback.

        Args:
            sub_id: Subscription ID
        """
        await self.execute(
            "UPDATE subscriptions SET feedback_sent_at = NOW() WHERE id = $1",
            sub_id
        )
        logger.info(f"Marked feedback sent for subscription {sub_id}")

    async def get_subscription_feedback_status(self, sub_id: int) -> Optional[dict]:
        """
        Получить статус отправки feedback для подписки.

        Args:
            sub_id: Subscription ID

        Returns:
            Dict с полями feedback_sent_at или None
        """
        row = await self.fetchrow(
            "SELECT id, feedback_sent_at FROM subscriptions WHERE id = $1",
            sub_id
        )
        return dict(row) if row else None