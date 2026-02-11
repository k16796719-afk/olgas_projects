from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone, time

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.constants import YOGA_4, YOGA_8, YOGA_10IND
from bot.services.access import kick_user

logger = logging.getLogger(__name__)

# Бразильский часовой пояс (Рио-де-Жанейро)
# Важно: используем IANA timezone, чтобы не ловить сюрпризы, если когда-нибудь вернут DST.
if ZoneInfo:
    BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")
else:  # fallback
    BRAZIL_TZ = timezone(timedelta(hours=-3))


def add_jobs(scheduler: AsyncIOScheduler, *, bot: Bot, db, cfg) -> None:
    """Добавить все периодические задачи в scheduler."""

    async def sweep_expired_yoga() -> None:
        """
        Отозвать доступ к йога-каналам для истекших подписок.

        Выполняется ежедневно в указанное время.
        """
        try:
            due = await db.expire_subscriptions_due()
            if not due:
                logger.debug("No expired yoga subscriptions found")
                return

            logger.info(f"Processing {len(due)} expired yoga subscriptions")

            for sub in due:
                try:
                    tg_user_id = int(sub["tg_user_id"])
                    product = sub["product"]
                    user_id = sub["user_id"]
                    sub_id = int(sub["id"])

                    # Определяем канал и отзываем доступ
                    if product == YOGA_4:
                        await kick_user(bot, cfg.yoga_channel_4_id, tg_user_id)
                        await db.log_channel_revoke(user_id, "yoga_4")
                        logger.info(f"Revoked yoga_4 access for user {tg_user_id}")
                    elif product == YOGA_8:
                        await kick_user(bot, cfg.yoga_channel_8_id, tg_user_id)
                        await db.log_channel_revoke(user_id, "yoga_8")
                        logger.info(f"Revoked yoga_8 access for user {tg_user_id}")
                    elif product == YOGA_10IND:
                        # Индивидуальный формат может не использовать групповой канал
                        await db.log_channel_revoke(user_id, "yoga_individual")
                        logger.info(f"Logged revoke for yoga_individual user {tg_user_id}")

                    # Помечаем подписку как истекшую
                    await db.mark_subscription_expired(sub_id)

                    # Уведомляем пользователя
                    try:
                        await bot.send_message(
                            tg_user_id,
                            "⏳ Доступ к йоге закончился. Нажми /menu чтобы продлить."
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to notify user {tg_user_id} about expired yoga access: {e}"
                        )

                except Exception as e:
                    logger.error(f"Failed to process expired subscription {sub.get('id')}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to sweep expired yoga subscriptions: {e}")

    async def send_yoga_feedback_reminder() -> None:
        """
        Отправить опросник пользователям за день до окончания подписки.

        Выполняется ежедневно в 6:00 по бразильскому времени (UTC-3).
        """
        try:
            # Вычисляем окно "завтра" по местному времени (Бразилия/Рио)
            # Так уведомление придёт всем, у кого срок истекает завтра (по дате),
            # а не только тем, кто попадает в "24±1 час" от момента запуска джобы.
            now_local = datetime.now(BRAZIL_TZ)
            tomorrow_date = (now_local + timedelta(days=1)).date()

            start_local = datetime.combine(tomorrow_date, time.min, tzinfo=BRAZIL_TZ)
            end_local = start_local + timedelta(days=1)

            tomorrow_start = start_local.astimezone(timezone.utc)
            tomorrow_end = end_local.astimezone(timezone.utc)

            logger.debug(
                f"Checking for yoga subscriptions expiring between "
                f"{tomorrow_start} and {tomorrow_end}"
            )

            # Получаем подписки, истекающие завтра
            rows = await db.get_subscriptions_expiring_between(
                tomorrow_start,
                tomorrow_end
            )

            if not rows:
                logger.debug("No yoga subscriptions expiring tomorrow")
                return

            logger.info(f"Found {len(rows)} yoga subscriptions expiring tomorrow")

            for row in rows:
                try:
                    tg_user_id = int(row["tg_user_id"])
                    sub_id = int(row["id"])
                    product = row.get("product", "yoga")

                    # Проверяем, не отправляли ли уже опросник
                    if row.get("feedback_sent_at"):
                        logger.debug(
                            f"Feedback already sent for subscription {sub_id}, skipping"
                        )
                        continue

                    # Формируем сообщение с кнопкой для запуска опроса
                    message_text = (
                        "🧘‍♀️ Наш месяц практик подходит к завершению 🤍\n\n"
                        "Спасибо, что были в этом пространстве!\n\n"
                        "📋 Мы будем очень благодарны за обратную связь.\n"
                        "Это поможет сделать практики ещё лучше ✨\n\n"
                        "👇 Нажмите кнопку ниже, чтобы ответить на несколько вопросов"
                    )

                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text="📝 Оставить отзыв",
                            callback_data="yoga_feedback_start"
                        )]
                    ])

                    # Отправляем сообщение
                    await bot.send_message(
                        chat_id=tg_user_id,
                        text=message_text,
                        reply_markup=keyboard
                    )

                    # Помечаем, что опросник отправлен
                    await db.mark_feedback_sent(sub_id)

                    logger.info(
                        f"Sent feedback reminder to user {tg_user_id} "
                        f"for subscription {sub_id} ({product})"
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to send feedback reminder for subscription "
                        f"{row.get('id')}: {e}"
                    )
                    continue

        except Exception as e:
            logger.error(f"Failed to send yoga feedback reminders: {e}")

    # Добавляем задачу очистки истекших подписок
    # Выполняется в заданное время по конфигу
    scheduler.add_job(
        sweep_expired_yoga,
        trigger="cron",
        hour=cfg.sweeper_hour,
        minute=cfg.sweeper_minute,
        timezone="UTC",
        id="yoga_sweeper",
        replace_existing=True,
    )
    logger.info(
        f"Scheduled yoga_sweeper job at {cfg.sweeper_hour:02d}:{cfg.sweeper_minute:02d} UTC"
    )
    # Добавляем задачу отправки опросников
    # Выполняется в 06:00 по бразильскому времени (America/Sao_Paulo)
    scheduler.add_job(
        send_yoga_feedback_reminder,
        trigger="cron",
        hour=6,
        minute=0,
        timezone="America/Sao_Paulo",
        id="yoga_feedback_reminder",
        replace_existing=True,
    )
    logger.info("Scheduled yoga_feedback_reminder job at 06:00 America/Sao_Paulo")
