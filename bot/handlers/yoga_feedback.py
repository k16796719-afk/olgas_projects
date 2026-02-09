# handlers/yoga_feedback.py
from html import escape

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from bot.keyboards.keyboards import yoga_renew_kb, payment_method_kb, yoga_change_plan_kb
from bot.states.yoga_feedback import YogaFeedback
from bot.keyboards.yoga_feedback_kb import *

router = Router()

START_TEXT = (
    "Наш месяц практик подходит к завершению 🤍\n"
    "Спасибо, что были в этом пространстве 🧘‍♀️\n\n"
    "Ответьте, пожалуйста, на несколько вопросов 📝"
)

@router.callback_query(lambda c: c.data == "yoga_feedback_start")
async def start_feedback_cb(call: CallbackQuery, state: FSMContext):
    await call.message.answer(START_TEXT)
    await call.message.answer(
        text="1️⃣ Насколько сложные были практики?",
        reply_markup=difficulty_kb
    )
    await state.set_state(YogaFeedback.q1_difficulty)
    await call.answer()

@router.message(Command("yoga_feedback_start"))
async def start_feedback(message: Message, state: FSMContext):
    await message.answer(START_TEXT)
    await message.answer("1️⃣ Насколько сложные были практики?", reply_markup=difficulty_kb)
    await state.set_state(YogaFeedback.q1_difficulty)

async def step(call: CallbackQuery, state: FSMContext, next_state, text, kb):
    await state.update_data(**{call.data.split(":")[0]: call.data.split(":")[1]})
    await call.message.edit_text(text, reply_markup=kb)
    await state.set_state(next_state)
    await call.answer()

@router.callback_query(lambda c: c.data.startswith("yf_q1"))
async def q1(call: CallbackQuery, state: FSMContext):
    await step(call, state, YogaFeedback.q2_tempo, "2️⃣ Какой был темп практик?", tempo_kb)

@router.callback_query(lambda c: c.data.startswith("yf_q2"))
async def q2(call: CallbackQuery, state: FSMContext):
    await step(call, state, YogaFeedback.q3_feelings, "3️⃣ Как вы себя чувствовали после практик?", feelings_kb)

@router.callback_query(lambda c: c.data.startswith("yf_q3"))
async def q3(call: CallbackQuery, state: FSMContext):
    await step(call, state, YogaFeedback.q4_format, "4️⃣ Какой формат вам ближе?", format_kb)

@router.callback_query(lambda c: c.data.startswith("yf_q4"))
async def q4(call: CallbackQuery, state: FSMContext):
    await step(call, state, YogaFeedback.q5_frequency, "5️⃣ Сколько практик в месяц вам комфортно?", freq_kb)

@router.callback_query(lambda c: c.data.startswith("yf_q5"))
async def q5(call: CallbackQuery, state: FSMContext):
    await step(call, state, YogaFeedback.q6_types, "6️⃣ Каких практик хотелось бы больше?", types_kb)

@router.callback_query(lambda c: c.data.startswith("yf_q6"))
async def finish(call: CallbackQuery, state: FSMContext, bot, cfg):
    data = await state.get_data()

    u = call.from_user
    user_name = escape(u.full_name or "Без имени")
    user_tag = f"@{u.username}" if u.username else "—"
    user_id = u.id

    text = (
        "🧘‍♀️ <b>Йога — обратная связь</b>\n\n"
        "👤 <b>От:</b>\n"
        f"• Имя: <b>{user_name}</b>\n"
        f"• Username: <b>{user_tag}</b>\n"
        f"• ID: <code>{user_id}</code>\n\n"
        "📋 <b>Ответы:</b>\n"
        f"1️⃣ <b>Сложность:</b> {escape(str(data.get('yf_q1')))}\n"
        f"2️⃣ <b>Темп:</b> {escape(str(data.get('yf_q2')))}\n"
        f"3️⃣ <b>После практик:</b> {escape(str(data.get('yf_q3')))}\n"
        f"4️⃣ <b>Формат:</b> {escape(str(data.get('yf_q4')))}\n"
        f"5️⃣ <b>Частота:</b> {escape(str(data.get('yf_q5')))}\n"
        f"6️⃣ <b>Типы практик:</b> {escape(call.data.split(':')[1])}\n"
    )

    for admin_id in cfg.admin_ids:
        await bot.send_message(
            chat_id=admin_id,
            text=text,
            parse_mode="HTML",
        )

    await call.message.edit_text(
        "Спасибо за вашу обратную связь 🤍\n\n"
        "Если вы хотите продолжить — буду рада видеть вас в следующем месяце.\n\n"
        "👉 Нажмите «Оплатить», чтобы продлить участие ✨", reply_markup=yoga_renew_kb())

    await state.clear()
    await call.answer()


@router.callback_query(lambda c: c.data == "yoga_renew:pay")
async def yoga_renew_pay(call: CallbackQuery, state: FSMContext, db, cfg):
    uid = await db.get_user_id_by_tg(call.from_user.id)
    if not uid:
        await call.answer("Не нашёл пользователя. Нажми /start", show_alert=True)
        return

    sub = await db.get_active_yoga_subscription(uid)  # сделай функцию, см. ниже
    if not sub:
        await call.answer("У тебя нет активного доступа. Оформи новый заказ через меню.", show_alert=True)
        return

    product = sub["product"]  # ожидаем "yoga_4" или "yoga_8"
    price_map = {
        "yoga_4": cfg.prices.yoga_4_rub,
        "yoga_8": cfg.prices.yoga_8_rub,
        "yoga_ind": cfg.prices.yoga_10ind_rub,
    }
    amount = int(price_map.get(product, 0))
    if not amount:
        await call.answer("Не смог определить сумму. Напиши администратору.", show_alert=True)
        return

    title_map = {
        "yoga_4": "Йога 4 практики/мес",
        "yoga_8": "Йога 8 практик/мес",
        "yoga_ind": "Йога 1:1 10 практик/мес",
    }

    await state.update_data(
        direction="yoga",
        flow="renew_same",
        product=product,
        product_title=title_map.get(product, product),
        amount=amount,
    )

    await call.message.answer("Выбери способ оплаты 💳", reply_markup=payment_method_kb(prefix=product))
    await call.answer()


@router.callback_query(lambda c: c.data == "yoga_renew:change")
async def yoga_renew_change(call: CallbackQuery, state: FSMContext, cfg):
    await state.update_data(direction="yoga", flow="renew_change")
    await call.message.answer("Выбери новый тариф 👇", reply_markup=yoga_change_plan_kb(cfg))
    await call.answer()


@router.callback_query(lambda c: c.data.startswith("yoga_renew_pick:"))
async def yoga_renew_pick(call: CallbackQuery, state: FSMContext, cfg):
    _, product = call.data.split(":", 1)  # yoga_4 / yoga_8
    product = "yoga"

    price_map = {"yoga_4": cfg.prices.yoga_4_rub, "yoga_8": cfg.prices.yoga_8_rub, "yoga_10_individual": cfg.prices.yoga_10ind_rub}
    title_map = {"yoga_4": "Йога 4 практики/мес", "yoga_8": "Йога 8 практик/мес", "yoga_10_individual": "Йога 1:1 10 практик/мес"}

    amount = int(price_map[product])

    await state.update_data(
        direction="yoga",
        flow="renew_change",
        product=product,
        product_title=title_map[product],
        amount=amount,
    )

    await call.message.answer("Выбери способ оплаты 💳", reply_markup=payment_method_kb(prefix=product))
    await call.answer()
