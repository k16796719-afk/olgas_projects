from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

from bot.config import load_config
from bot.db import Database
from bot.handlers import router as main_router
from bot.jobs import add_jobs

log = logging.getLogger(__name__)


async def main():
    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    cfg = load_config()

    # Always use HTML across the project to avoid Markdown/HTML mixing issues.
    bot = Bot(
        token=cfg.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=MemoryStorage())

    db = Database(cfg.database_url)
    await db.connect()

    # attach shared objects
    dp["cfg"] = cfg
    dp["db"] = db
    dp.include_router(main_router)

    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Запустить бота"),
            BotCommand(command="menu", description="Главное меню"),
        ]
    )

    scheduler = AsyncIOScheduler(timezone=cfg.tz)
    add_jobs(scheduler, bot=bot, db=db, cfg=cfg)
    scheduler.start()

    log.info("Bot started")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        log.info("Shutting down")
        await db.close()
        await bot.session.close()
