from __future__ import annotations

import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.constants import YOGA_4, YOGA_8, YOGA_10IND
from bot.services.access import kick_user

log = logging.getLogger(__name__)


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
