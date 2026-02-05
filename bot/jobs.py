from __future__ import annotations

import logging
from datetime import datetime, date

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.constants import YOGA_4, YOGA_8, YOGA_10IND
from bot.handlers.yoga_feedback.constants import SURVEY_INTRO_TEXT
from bot.handlers.yoga_feedback.keyboards import kb_start_survey
from bot.services.access import kick_user

log = logging.getLogger(__name__)


async def send_yoga_feedback_surveys(*, bot: Bot, db, cfg) -> None:
    """Send feedback survey 1 day before subscription expiry.

    Expects:
      - db.pool: asyncpg.Pool (or compatible acquire/execute/fetch interface)
      - subscriptions table has: id, tg_user_id, status, expires_at, feedback_sent_at
    """
    pool = getattr(db, "pool", None)
    if pool is None:
        log.error("db.pool not found; cannot run send_yoga_feedback_surveys")
        return

    today: date = datetime.utcnow().date()

    sql_select = """
    SELECT id, tg_user_id
    FROM subscriptions
    WHERE status = 'active'
      AND expires_at IS NOT NULL
      AND (expires_at::date = ($1::date + INTERVAL '1 day')::date)
      AND feedback_sent_at IS NULL
    """

    sql_mark = """
    UPDATE subscriptions
    SET feedback_sent_at = now()
    WHERE id = $1
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql_select, today)

        for row in rows:
            sub_id = int(row["id"])
            tg_user_id = int(row["tg_user_id"])

            try:
                await bot.send_message(
                    tg_user_id,
                    SURVEY_INTRO_TEXT,
                    reply_markup=kb_start_survey(sub_id).as_markup(),
                )
                await conn.execute(sql_mark, sub_id)
            except Exception:
                log.exception("Failed to send feedback survey (tg_user_id=%s, sub_id=%s)", tg_user_id, sub_id)


def add_jobs(scheduler: AsyncIOScheduler, *, bot: Bot, db, cfg) -> None:
    async def sweep_expired_yoga() -> None:
        due = await db.expire_subscriptions_due()
        if not due:
            return

        for sub in due:
            tg_user_id = int(sub["tg_user_id"])
            product = sub["product"]

            # remove from yoga channel depending on product
            if product == YOGA_4:
                await kick_user(bot, cfg.yoga_channel_4_id, tg_user_id)
                await db.log_channel_revoke(sub["user_id"], "yoga_4")
            elif product == YOGA_8:
                await kick_user(bot, cfg.yoga_channel_8_id, tg_user_id)
                await db.log_channel_revoke(sub["user_id"], "yoga_8")
            elif product == YOGA_10IND:
                # индивидуальный формат: групповой канал может не использоваться
                await db.log_channel_revoke(sub["user_id"], "yoga_individual")

            await db.mark_subscription_expired(int(sub["id"]))

            try:
                await bot.send_message(tg_user_id, "⏳ Доступ к йоге закончился. Нажми /menu чтобы продлить.")
            except Exception:
                log.exception("Failed to notify user about expired yoga access (tg_user_id=%s)", tg_user_id)

    scheduler.add_job(
        sweep_expired_yoga,
        trigger="cron",
        hour=cfg.sweeper_hour,
        minute=cfg.sweeper_minute,
        id="yoga_sweeper",
        replace_existing=True,
    )

    scheduler.add_job(
        send_yoga_feedback_surveys,
        trigger="cron",
        hour=10,
        minute=0,
        kwargs={"bot": bot, "db": db, "cfg": cfg},
        id="yoga_feedback_surveys",
        replace_existing=True,
    )
