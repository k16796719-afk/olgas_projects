from __future__ import annotations
import html
from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.types import Message


from bot.states.states import YogaFlow
from bot.keyboards.keyboards import yoga_plan_kb, payment_method_kb
from bot.constants import D_YOGA, YOGA_4, YOGA_8, YOGA_10IND

router = Router()


def _get_yoga_channel_id(cfg):
    """Пробуем достать chat_id канала йоги из cfg.
    Поддерживаем несколько возможных схем конфигурации, чтобы не ломаться при рефакторингах.
    """
    # 1) cfg.yoga_channel_id
    cid = getattr(cfg, "yoga_channel_id", None)
    if cid:
        return cid

    # 2) cfg.channels.yoga / cfg.channels.yoga_channel_id
    channels = getattr(cfg, "channels", None)
    if channels:
        cid = getattr(channels, "yoga", None) or getattr(channels, "yoga_channel_id", None)
        if cid:
            return cid

    # 3) cfg.chat_ids.yoga
    chat_ids = getattr(cfg, "chat_ids", None)
    if chat_ids:
        cid = getattr(chat_ids, "yoga", None) or getattr(chat_ids, "yoga_channel_id", None)
        if cid:
            return cid

    return None


@router.callback_query(lambda c: c.data == "dir:yoga")
async def yoga_start(call: CallbackQuery, state: FSMContext, cfg):
    await state.clear()
    await state.update_data(direction=D_YOGA)
    await state.set_state(YogaFlow.plan)
    await call.message.edit_text("Выбери абонемент йоги:", reply_markup=yoga_plan_kb(cfg))
    await call.answer()

@router.callback_query(YogaFlow.plan, lambda c: c.data.startswith("y_plan:"))
async def yoga_plan(call: CallbackQuery, state: FSMContext, cfg):
    plan = call.data.split(":",1)[1]
    if plan == YOGA_4:
        amount = cfg.prices.yoga_4_rub
        title = "Йога: 4 практики / месяц"
    elif plan == YOGA_8:
        amount = cfg.prices.yoga_8_rub
        title = "Йога: 8 практик / месяц"
    else:
        amount = cfg.prices.yoga_10ind_rub
        title = "Йога: 1-1 10 практик / месяц"
    await state.update_data(yoga_plan=plan, product_title=title, amount=amount)
    await state.set_state(YogaFlow.payment)
    await call.message.edit_text(
        f"{title}\nСумма: {amount} RUB\n\nВыбери метод оплаты:",
        reply_markup=payment_method_kb("yoga"),
        parse_mode="HTML"
    )
    await call.answer()

@router.message(lambda m: m.text is not None)
async def yoga_intro_catcher(message: Message, state: FSMContext, db, cfg, bot):
    if message.chat.type != "private":
        return

    if (await state.get_state()) != "WAIT_YOGA_INTRO":
        return

    data = await state.get_data()
    plan = data.get("yoga_intro_plan")
    payment_id = data.get("yoga_intro_payment_id")

    u = message.from_user
    user_line = u.full_name + (f" (@{u.username})" if u.username else "")

    safe_user_line = html.escape(user_line)
    safe_plan = html.escape(str(plan)) if plan is not None else "?"
    safe_payment_id = html.escape(str(payment_id)) if payment_id is not None else "?"
    safe_answer = html.escape(message.text)

    text_to_admins = (
        "🧘‍♀️ <b>Йога: ответы на знакомство</b>\n"
        f"👤 <b>Пользователь:</b> {safe_user_line}\n"
        f"🧾 <b>Тариф:</b> {safe_plan} занятий/мес\n"
        f"🧾 <b>Payment ID:</b> {safe_payment_id}\n\n"
        f"📝 <b>Ответ:</b>\n{safe_answer}"
    )

    # отправляем всем админам
    for admin_id in cfg.admin_ids:
        try:
            await bot.send_message(admin_id, text_to_admins, parse_mode="HTML")
        except Exception:
            # не падаем из-за одного админа
            pass

    # Публикуем краткое знакомство в канал (если настроен)
    channel_id = _get_yoga_channel_id(cfg)
    if channel_id:
        channel_text = (
            "🧘‍♀️ <b>К нам присоединился новый участник!</b>\n"
            f"👤 {safe_user_line}\n"
            f"📝 {safe_answer}"
        )
        try:
            await bot.send_message(int(channel_id), channel_text, parse_mode="HTML", disable_web_page_preview=True)
        except Exception:
            print("Нет прав на публикацию в канале")
            # не валим интро из-за прав/канала
            pass


    await message.answer("Спасибо! Я передала ваши ответы Ольге 🤍")
    await state.clear()