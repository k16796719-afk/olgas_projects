from __future__ import annotations

import html
import logging

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.constants import (
    D_YOGA
)
from bot.services.access import create_invite_link

router = Router()

logger = logging.getLogger(__name__)


def _get_yoga_channel_id(cfg) -> int | None:
    """Достаём chat_id канала йоги из конфига (поддерживаем разные имена полей)."""
    for attr in ("yoga_channel_id", "yoga_channel", "yoga_channel_chat_id"):
        val = getattr(cfg, attr, None)
        if val:
            try:
                return int(val)
            except Exception:
                pass

    for container_name in ("channels", "chat_ids", "chats"):
        container = getattr(cfg, container_name, None)
        if container is None:
            continue
        for key in ("yoga", "yoga_channel", "yoga_intro"):
            val = None
            try:
                val = getattr(container, key, None)
            except Exception:
                val = None
            if (not val) and isinstance(container, dict):
                val = container.get(key)
            if val:
                try:
                    return int(val)
                except Exception:
                    pass
    return None


def _mention_user_html(tg_id: int, full_name: str) -> str:
    """Кликабельное упоминание пользователя."""
    safe_name = html.escape(full_name or "участник")
    return f'<a href="tg://user?id={int(tg_id)}">{safe_name}</a>'

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

    try:
        payment_id = int(call.data.split(":", 1)[1])
    except Exception:
        await call.answer("Некорректный платеж", show_alert=True)
        return

    pay = await db.get_payment(payment_id)
    if not pay:
        await call.answer("Платеж не найден", show_alert=True)
        return
    if pay["status"] == "paid":
        await call.answer("Уже подтверждено")
        return

    await db.approve_payment(payment_id, call.from_user.id)

    order = await db.get_order(pay["order_id"])
    if not order:
        await call.answer("Заказ не найден", show_alert=True)
        return

    direction = order.get("direction")
    payload = order.get("payload_json")

    # resolve user: orders.user_id -> users.tg_user_id
    row = await db.fetchrow(
        "SELECT u.id as user_id, u.tg_user_id FROM orders o JOIN users u ON u.id=o.user_id WHERE o.id=$1",
        order["id"],
    )
    if not row:
        await call.answer("Пользователь заказа не найден", show_alert=True)
        return

    user_db_id = int(row["user_id"])
    tg_user_id = int(row["tg_user_id"])

    # mark order paid
    await db.set_order_status(order["id"], "paid")

    import json
    import html
    from datetime import datetime, timedelta, timezone

    def _to_payload_dict(v):
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            try:
                vv = json.loads(v)
                if isinstance(vv, dict):
                    return vv
            except Exception:
                pass
        return {}

    def _extract_yoga_plan(v):
        """Return 4 or 8 if can detect, else None."""
        d = _to_payload_dict(v)
        for key in ("Тариф", "План", "Абонемент", "Yoga plan", "yoga_plan", "plan", "Продукт"):
            raw = d.get(key)
            if not raw:
                continue
            s = str(raw).lower()
            if "8" in s:
                return 8
            if "4" in s:
                return 4
        return None

    def _fmt_date(dt: datetime) -> str:
        return dt.astimezone(timezone.utc).strftime("%d.%m.%Y")

    async def _get_active_yoga_sub(uid: int):
        return await db.fetchrow(
            "SELECT id, product, expires_at FROM subscriptions "
            "WHERE user_id=$1 AND expires_at > NOW() "
            "ORDER BY expires_at DESC LIMIT 1",
            uid,
        )

    async def _upsert_yoga_sub(uid: int, product: str, expires_at: datetime, last_payment_id: int):
        sub = await _get_active_yoga_sub(uid)
        if sub:
            await db.execute(
                "UPDATE subscriptions SET product=$2, expires_at=$3, last_payment_id=$4 WHERE id=$1",
                int(sub["id"]),
                product,
                expires_at,
                last_payment_id,
            )
            return int(sub["id"])
        return await db.create_yoga_subscription(uid, product, expires_at, last_payment_id)

    async def _kick_from_channel(channel_id: int, tg_id: int):
        try:
            await bot.ban_chat_member(channel_id, tg_id)
            await bot.unban_chat_member(channel_id, tg_id)
        except Exception:
            pass

    WELCOME_YOGA_TEXT = (
        "Добро пожаловать 🤍\n\n"
        "💰 <b>Оплата прошла успешно</b> — вы в закрытой группе йога‑практик 🧘‍♀️\n\n"
        "🫶🏼 Здесь вас ждёт регулярная поддержка, мягкая работа с телом и состоянием, "
        "а главное — пространство для себя без спешки и давления.\n\n"
        "✅ Все анонсы практик, ссылки и важная информация будут появляться в группе."
    )

    if direction == "yoga":
        plan = _extract_yoga_plan(payload)
        if plan not in (4, 8):
            await bot.send_message(
                chat_id=tg_user_id,
                text=(
                    "✅ <b>Оплата подтверждена</b>\n\n"
                    "Спасибо! Мы получили подтверждение оплаты.\n\n"
                    "💬 В ближайшее время с вами свяжется <b>Ольга</b>.\n"
                    "Если вы долго не получаете ответа, вы можете написать ей напрямую:\n\n"
                    f"👉 <b>{cfg.olga_telegram}</b>"
                ),
                parse_mode="HTML",
            )
        else:
            new_product = f"yoga_{plan}"
            new_channel_id = cfg.yoga_channel_4_id if plan == 4 else cfg.yoga_channel_8_id

            cur_sub = await _get_active_yoga_sub(user_db_id)
            cur_product = cur_sub["product"] if cur_sub else None
            cur_expires = cur_sub["expires_at"] if cur_sub else None

            now_utc = datetime.now(timezone.utc)
            days = int(getattr(cfg, "yoga_subscription_days", 30))

            if isinstance(cur_expires, datetime) and cur_expires > now_utc:
                new_expires = cur_expires + timedelta(days=days)
                is_first_join = False
            else:
                new_expires = now_utc + timedelta(days=days)
                is_first_join = True

            await _upsert_yoga_sub(user_db_id, new_product, new_expires, payment_id)

            changing_plan = bool(cur_product) and cur_product != new_product

            if changing_plan:
                old_plan = 4 if "4" in str(cur_product) else 8 if "8" in str(cur_product) else None
                old_channel_id = cfg.yoga_channel_4_id if old_plan == 4 else cfg.yoga_channel_8_id if old_plan == 8 else None
                if old_channel_id:
                    await _kick_from_channel(old_channel_id, tg_user_id)

                invite = await bot.create_chat_invite_link(
                    chat_id=new_channel_id,
                    name=f"yoga{plan}:{tg_user_id}:{payment_id}",
                    member_limit=1,
                    expire_date=datetime.now(timezone.utc) + timedelta(days=2),
                )

                await bot.send_message(
                    chat_id=tg_user_id,
                    text=(
                        "✅ <b>Оплата подтверждена</b>\n\n"
                        f"🧘 Ваш новый тариф: <b>{plan} практик/мес</b>\n"
                        f"⏳ Доступ до: <b>{_fmt_date(new_expires)}</b>\n\n"
                        "Вот ссылка для входа в нужную группу:\n\n"
                        f"🔗 {invite.invite_link}\n\n"
                        f"Если ссылка не открывается — напишите Ольге {cfg.olga_telegram}."
                    ),
                    parse_mode="HTML",
                )

                await bot.send_message(tg_user_id, WELCOME_YOGA_TEXT, parse_mode="HTML")


                    # Публикуем в канале йоги: приветствие + просьба рассказать о себе в комментариях
                if new_channel_id:
                    try:
                        user_chat = await bot.get_chat(tg_user_id)
                        user_full_name = user_chat.full_name
                    except Exception:
                        user_full_name = str(tg_user_id)
                    user_mention = _mention_user_html(tg_user_id, user_full_name)
                    channel_text = (
                    "🧘‍♀️ <b>Новая(ый) участница(к) в йоге</b>\n"
                    f"👤 {user_mention}\n"
                    "Напиши в комментариях пару строк о себе: цель, опыт, ограничения (если есть)."
                    )
                    try:
                        await bot.send_message(int(new_channel_id), channel_text, parse_mode="HTML", disable_web_page_preview=True)
                    except Exception:
                        logger.info("notification to channel was not sent (change plan)")
                            # не ломаем подтверждение оплаты, если бот не может писать в канал
                        pass
            else:
                if is_first_join:
                    logger.info("first join")
                    invite = await bot.create_chat_invite_link(
                        chat_id=new_channel_id,
                        name=f"yoga{plan}:{tg_user_id}:{payment_id}",
                        member_limit=1,
                        expire_date=datetime.now(timezone.utc) + timedelta(days=2),
                    )
                    await bot.send_message(
                        chat_id=tg_user_id,
                        text=(
                            "✅ <b>Оплата подтверждена</b>\n\n"
                            f"🧘 Тариф: <b>{plan} практик/мес</b>\n"
                            f"⏳ Доступ до: <b>{_fmt_date(new_expires)}</b>\n\n"
                            "Вот ссылка для входа в закрытую группу:\n\n"
                            f"🔗 {invite.invite_link}\n\n"
                            f"Если ссылка не открывается — напишите Ольге {cfg.olga_telegram}."
                        ),
                        parse_mode="HTML",
                    )
                    await bot.send_message(tg_user_id, WELCOME_YOGA_TEXT, parse_mode="HTML")

                    # Публикуем в канале йоги: приветствие + просьба рассказать о себе в комментариях
                    logger.info(new_channel_id)
                    if new_channel_id:
                        try:
                            user_chat = await bot.get_chat(tg_user_id)
                            user_full_name = user_chat.full_name
                        except Exception:
                            user_full_name = str(tg_user_id)
                        user_mention = _mention_user_html(tg_user_id, user_full_name)
                        channel_text = (
                            "🧘‍♀️ <b>Новая(ый) участница(к) в йоге</b>\n"
                            f"👤 {user_mention}\n"
                            "Напиши в комментариях пару строк о себе: цель, опыт, ограничения (если есть)."
                        )
                        try:
                            await bot.send_message(int(new_channel_id), channel_text, parse_mode="HTML", disable_web_page_preview=True)
                            logger.info("Message to channel sent")
                        except Exception as e:
                            # не ломаем подтверждение оплаты, если бот не может писать в канал
                            logger.info(f"Message to channel was not sent: {e}")
                            pass
                else:
                    logger.info("not first join")

                    await bot.send_message(
                        chat_id=tg_user_id,
                        text=(
                            "✅ <b>Оплата подтверждена</b>\n\n"
                            f"Доступ в группу продлён до: <b>{_fmt_date(new_expires)}</b> 🤍\n\n"
                            "Если вы долго не получаете ответа, вы можете написать Ольге напрямую:\n"
                            f"👉 <b>{cfg.olga_telegram}</b>"
                        ),
                        parse_mode="HTML",
                    )
    else:
        await bot.send_message(
            chat_id=tg_user_id,
            text=(
                "✅ <b>Оплата подтверждена</b>\n\n"
                "Спасибо! Мы получили подтверждение оплаты.\n\n"
                "💬 В ближайшее время с вами свяжется <b>Ольга</b>.\n"
                "Если вы долго не получаете ответа, вы можете написать ей напрямую:\n\n"
                f"👉 <b>{cfg.olga_telegram}</b>"
            ),
            parse_mode="HTML",
        )

    await call.answer("✅ Подтверждено")

    try:
        chat = await bot.get_chat(tg_user_id)
        user_name = chat.full_name
        if chat.username:
            user_name += f" (@{chat.username})"
    except Exception:
        user_name = str(tg_user_id)

    safe_user_name = html.escape(user_name)

    for admin_id in getattr(cfg, "admin_ids", []):
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=(
                    "✅ <b>Оплата подтверждена</b>\n"
                    f"👤 Пользователь: <b>{safe_user_name}</b>\n"
                    f"🧾 Payment ID: <code>{payment_id}</code>"
                ),
                parse_mode="HTML",
            )
        except Exception:
            pass

    try:
        await call.message.delete()
    except Exception:
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

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
