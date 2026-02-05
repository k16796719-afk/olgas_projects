from __future__ import annotations

import html

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.constants import (
    D_YOGA
)
from bot.services.access import create_invite_link

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
async def admin_approve(call: CallbackQuery, db, cfg, bot, state: FSMContext):
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

    from datetime import datetime, timedelta
    import json

    def _extract_yoga_plan(payload) -> int | None:
        """
        Returns 4 or 8 if can detect, else None.
        """
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                return None
        if not isinstance(payload, dict):
            return None

        # try several possible keys
        for key in ("Тариф", "План", "Абонемент", "Yoga plan", "yoga_plan", "plan"):
            v = payload.get(key)
            if not v:
                continue
            s = str(v).lower()
            # detect 4 or 8
            if "8" in s:
                return 8
            if "4" in s:
                return 4
        return None

    payload = order["payload_json"]

    if direction == "yoga":

        WELCOME_YOGA_TEXT = (
            "Добро пожаловать 🤍\n\n"
            "💰 <b>Оплата прошла успешно</b> — вы в закрытой группе йога-практик 🧘‍♀️\n\n"
            "🫶🏼 Здесь вас ждёт регулярная поддержка, мягкая работа с телом и состоянием, "
            "а главное — пространство для себя без спешки и давления.\n\n"
            "✅ Все анонсы практик, ссылки и важная информация будут появляться в группе."
        )

        plan = _extract_yoga_plan(payload)
        channel_id = None
        if plan == 4:
            channel_id = cfg.yoga_channel_4_id
        elif plan == 8:
            channel_id = cfg.yoga_channel_8_id

        if channel_id:
            invite = await bot.create_chat_invite_link(
                chat_id=channel_id,
                name=f"yoga{plan}:{tg_user_id}:{payment_id}",
                member_limit=1,
                expire_date=datetime.utcnow() + timedelta(days=2),
            )

            access_expires_at = datetime.utcnow() + timedelta(days=30)

            is_first = await db.is_first_yoga_subscription(user_db_id)

            # создать подписку (yoga_4 / yoga_8)
            product = f"yoga_{plan}"
            await db.create_yoga_subscription(
                user_id=user_db_id,
                product=product,
                expires_at=access_expires_at,
                last_payment_id=payment_id,
                channel_id=int(channel_id),
            )

            await bot.send_message(
                chat_id=tg_user_id,
                text=(
                    "✅ <b>Оплата подтверждена</b>\n\n"
                    f"🧘 Ваш тариф: <b>{plan} занятий/мес</b>\n"
                    f"📅 Доступ активен до: <b>{access_expires_at:%d.%m.%Y}</b>\n\n"
                    "Вот ссылка для входа в закрытый канал:\n\n"
                    f"🔗 {invite.invite_link}\n\n"
                    f"Если ссылка не открывается — напишите Ольге {cfg.olga_telegram}."
                ),
                parse_mode="HTML",
            )

            # отправляем приветствие
            await bot.send_message(
                tg_user_id,
                WELCOME_YOGA_TEXT,
                parse_mode="HTML",
            )

            ONBOARDING_TEXT = (
                "Немного о формате 📝\n\n"
                "▫️ Практики проходят регулярно в этой группе\n"
                "▫️ Все записи сохраняются\n"
                "▫️ Можно заниматься в удобное время\n\n"
                "⏳ Доступ: <b>в течение 1 месяца</b>\n\n"
                "<b>Варианты участия:</b>\n"
                "▪️ 4 практики в месяц\n"
                "▪️ 8 практик в месяц\n"
                "▪️ Индивидуальный формат 1-1 (персональная работа, запрос под вас)\n\n"
                "Сегодня — знакомимся!\n"
                "Напишите, пожалуйста:\n"
                "1️⃣ Имя\n"
                "2️⃣ Из какого города/страны\n"
                "3️⃣ Как вы чувствуете своё тело сейчас? Занимались ли вы йогой раньше?"
            )

            if is_first:
                await bot.send_message(tg_user_id, ONBOARDING_TEXT, parse_mode="HTML")
                await state.update_data(yoga_intro_plan=plan, yoga_intro_payment_id=payment_id)
                await state.set_state("WAIT_YOGA_INTRO")


        else:
            # if we can't detect plan, don't crash
            await bot.send_message(
                chat_id=tg_user_id,
                text=(
                    "✅ <b>Оплата подтверждена</b>\n\n"
                    "Спасибо! Мы получили подтверждение оплаты.\n\n"
                    "💬 В ближайшее время с вами свяжется <b>Ольга</b>, "
                    "чтобы договориться о дальнейших шагах."
                    "Если вы долго не получаете ответа, вы можете написать ей напрямую:\n\n"
                    f"👉 <b>{cfg.olga_telegram}</b>\n\n"
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
                f"👉 <b>{cfg.olga_telegram}</b>\n\n"),
            parse_mode="HTML",
        )

    # покажем всплывашку
    await call.answer("✅ Подтверждено")

    # вместо edit_text/edit_caption -> отправляем новое админу
    chat = await bot.get_chat(tg_user_id)
    user_name = chat.full_name
    if chat.username:
        user_name += f" (@{chat.username})"
    safe_user_name = html.escape(user_name)

    await bot.send_message(
        chat_id=call.from_user.id,  # админ, который нажал
        text=(
            "✅ <b>Оплата подтверждена</b>\n"
            f"👤 Пользователь: <b>{safe_user_name}</b>\n"
            "📨 Пользователь уведомлён."
        ),
        parse_mode="HTML",
    )

    # опционально: попробуем убрать кнопки (если не получится — не падаем)
    try:
        await call.message.delete()
    except Exception as e:
        print("FAILED TO DELETE:", repr(e))
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
