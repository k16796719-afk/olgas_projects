from __future__ import annotations
from datetime import datetime, timedelta, timezone

from aiogram import Router
from aiogram.types import CallbackQuery

from bot.constants import (
    D_ENGLISH, D_CHINESE, D_YOGA, D_ASTRO, D_MENTOR,
    YOGA_4, YOGA_8, YOGA_10IND
)
from bot.services.access import create_invite_link
from bot.keyboards import main_menu_kb

router = Router()

def _is_admin(user_id: int, cfg) -> bool:
    return user_id in cfg.admin_ids

async def _grant_access(bot, db, cfg, *, tg_user_id: int, user_db_id: int, direction: str, payload: dict):
    # Always grant personal channel for paid services (as per spec)
    links = []
    personal_link = await create_invite_link(bot, cfg.channel_personal_id, name=f"personal:{tg_user_id}")
    await db.log_channel_access(user_db_id, "personal", personal_link)
    links.append(("Личный канал", personal_link))

    if direction == D_YOGA:
        plan_title = payload.get("Тариф") or payload.get("Tariff") or ""
        # Determine yoga product from title if not stored as code
        # best effort mapping:
        if "4" in plan_title:
            yoga_chat = cfg.yoga_channel_4_id
            key = "yoga_4"
        elif "8" in plan_title:
            yoga_chat = cfg.yoga_channel_8_id
            key = "yoga_8"
        else:
            yoga_chat = None
            key = "yoga_individual"

        if cfg.yoga_personal_channel_id:
            yplink = await create_invite_link(bot, cfg.yoga_personal_channel_id, name=f"yoga_personal:{tg_user_id}")
            await db.log_channel_access(user_db_id, "yoga_personal", yplink)
            links.append(("Йога: личный", yplink))

        if yoga_chat:
            ylink = await create_invite_link(bot, yoga_chat, name=f"{key}:{tg_user_id}")
            await db.log_channel_access(user_db_id, key, ylink)
            links.append((f"Йога канал ({key})", ylink))

    return links

@router.callback_query(lambda c: c.data.startswith("adm_ok:"))
async def admin_approve(call: CallbackQuery, db, cfg, bot):
    if not _is_admin(call.from_user.id, cfg):
        await call.answer("Нет доступа", show_alert=True)
        return

    payment_id = int(call.data.split(":",1)[1])
    pay = await db.get_payment(payment_id)
    if not pay:
        await call.answer("Платеж не найден", show_alert=True)
        return
    if pay["status"] == "paid":
        await call.answer("Уже подтверждено")
        return

    await db.approve_payment(payment_id, call.from_user.id)

    order = await db.get_order(pay["order_id"])
    direction = order["direction"]
    payload = order["payload_json"]

    # resolve user
    # order.user_id -> users.tg_user_id
    row = await db.fetchrow(
        "SELECT u.id as user_id, u.tg_user_id FROM orders o JOIN users u ON u.id=o.user_id WHERE o.id=$1",
        order["id"]
    )
    user_db_id = int(row["user_id"])
    tg_user_id = int(row["tg_user_id"])

    # mark order paid
    await db.set_order_status(order["id"], "paid")

    # yoga subscription if needed
    if direction == D_YOGA:
        days = cfg.yoga_subscription_days
        expires_at = datetime.now(timezone.utc) + timedelta(days=days)
        plan_title = payload.get("Тариф","")
        if "4" in plan_title:
            product = "yoga_4"
        elif "8" in plan_title:
            product = "yoga_8"
        else:
            product = "yoga_10_individual"
        await db.create_yoga_subscription(user_db_id, product, expires_at, payment_id)

    links = await _grant_access(bot, db, cfg, tg_user_id=tg_user_id, user_db_id=user_db_id, direction=direction, payload=payload)

    msg = ["✅ Оплата подтверждена! Вот доступ:"]
    for title, link in links:
        msg.append(f"- {title}: {link}")
    msg.append("")
    if direction == D_YOGA:
        msg.append("⏳ Доступ к йоге на 1 месяц. Продление через /menu.")
    else:
        msg.append("Дальше работа идет в канале. Этот бот свою часть сделал (как и большинство людей, честно говоря).")

    try:
        await bot.send_message(tg_user_id, "\n".join(msg))
    except Exception:
        pass

    await call.message.edit_caption((call.message.caption or "") + "\n\n✅ Подтверждено админом.")
    await call.answer("Подтверждено")

@router.callback_query(lambda c: c.data.startswith("adm_no:"))
async def admin_reject(call: CallbackQuery, db, cfg, bot):
    if not _is_admin(call.from_user.id, cfg):
        await call.answer("Нет доступа", show_alert=True)
        return
    payment_id = int(call.data.split(":",1)[1])
    pay = await db.get_payment(payment_id)
    if not pay:
        await call.answer("Платеж не найден", show_alert=True)
        return
    if pay["status"] == "rejected":
        await call.answer("Уже отклонено")
        return

    await db.reject_payment(payment_id, call.from_user.id)

    row = await db.fetchrow(
        "SELECT u.tg_user_id FROM orders o JOIN users u ON u.id=o.user_id WHERE o.id=$1",
        pay["order_id"]
    )
    tg_user_id = int(row["tg_user_id"])
    try:
        await bot.send_message(tg_user_id, "❌ Платеж отклонен. Проверь чек/сумму и попробуй снова через /menu.")
    except Exception:
        pass

    await call.message.edit_caption((call.message.caption or "") + "\n\n❌ Отклонено админом.")
    await call.answer("Отклонено")
