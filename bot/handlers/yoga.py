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

def _get_yoga_channel_id(cfg, plan) -> int | None:
    """Возвращает chat_id для публикации по тарифу йоги (4/8) или персональный (если задан)."""
    # plan может быть int (4/8) или строка
    try:
        p = int(plan)
    except Exception:
        s = str(plan or "")
        # грубый, но практичный парсер
        if "8" in s:
            p = 8
        elif "4" in s:
            p = 4
        else:
            p = None

    if p == 4:
        return int(cfg.yoga_channel_4_id)
    if p == 8:
        return int(cfg.yoga_channel_8_id)

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

    text_to_admins = (
        "🧘‍♀️ <b>Йога: ответы на знакомство</b>\n"
        f"👤 <b>Пользователь:</b> {user_line}\n"
        f"🧾 <b>Тариф:</b> {plan} занятий/мес\n"
        f"🧾 <b>Payment ID:</b> {payment_id}\n\n"
        f"📝 <b>Ответ:</b>\n{message.text}"
    )

    # отправляем всем админам
    for admin_id in cfg.admin_ids:
        try:
            await bot.send_message(admin_id, text_to_admins, parse_mode="HTML")
        except Exception:
            # не падаем из-за одного админа
            pass

    # Также публикуем знакомство в канале йоги
    channel_id = _get_yoga_channel_id(cfg, plan)
    print(channel_id)
    if channel_id:
        safe_user = html.escape(user_line)
        safe_plan = html.escape(str(plan)) if plan is not None else "?"
        safe_answer = html.escape(message.text)
        text_to_channel = (
            "🧘‍♀️ <b>А сейчас знакомимся!</b>\n"
            f"👤 <b>К нам присоединился </b> {safe_user}\n"
            f"📝 <b>О себе:</b>\n{safe_answer}"
        )
        try:
            await bot.send_message(int(channel_id), text_to_channel, parse_mode="HTML", disable_web_page_preview=True)
            print(f"Send to channel")
        except Exception as e:
            print(f"Send to channel failed - {e}")
            pass

    await message.answer("Спасибо! Я передала ваши ответы Ольге 🤍")
    await state.clear()
