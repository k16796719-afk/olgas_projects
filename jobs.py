from __future__ import annotations
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from bot.services.access import kick_user
from bot.constants import YOGA_4, YOGA_8, YOGA_10IND

def add_jobs(scheduler: AsyncIOScheduler, *, bot: Bot, db, cfg):
    async def sweep_expired_yoga():
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
            else:
                # individual: no group necessarily
                await db.log_channel_revoke(sub["user_id"], "yoga_individual")
            # also personal yoga channel if configured
            if cfg.yoga_personal_channel_id:
                await kick_user(bot, cfg.yoga_personal_channel_id, tg_user_id)
                await db.log_channel_revoke(sub["user_id"], "yoga_personal")
            await db.mark_subscription_expired(int(sub["id"]))
            try:
                await bot.send_message(tg_user_id, "⏳ Доступ к йоге закончился. Нажми /menu чтобы продлить.")
            except Exception:
                pass

    scheduler.add_job(
        sweep_expired_yoga,
        trigger="cron",
        hour=cfg.sweeper_hour,
        minute=cfg.sweeper_minute,
        id="yoga_sweeper",
        replace_existing=True,
    )
