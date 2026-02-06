# handlers/yoga_feedback.py
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from bot.keyboards.keyboards import yoga_renew_kb, payment_method_kb
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

    text = (
        "🧘‍♀️ <b>Йога — обратная связь</b>\n\n"
        f"1. Сложность: {data.get('yf_q1')}\n"
        f"2. Темп: {data.get('yf_q2')}\n"
        f"3. После практик: {data.get('yf_q3')}\n"
        f"4. Формат: {data.get('yf_q4')}\n"
        f"5. Частота: {data.get('yf_q5')}\n"
        f"6. Типы: {call.data.split(':')[1]}"
    )

    for admin_id in cfg.admin_ids:
        await bot.send_message(admin_id, text, parse_mode="HTML")

    await call.message.edit_text(
        "Спасибо за вашу обратную связь 🤍\n\n"
        "Если вы хотите продолжить — буду рада видеть вас в следующем месяце.\n\n"
        "👉 Нажмите «Оплатить», чтобы продлить участие ✨", reply_markup=yoga_renew_kb())

    await state.clear()
    await call.answer()

@router.callback_query(lambda c: c.data == "yoga_renew")
async def yoga_renew(call: CallbackQuery, state: FSMContext):
    await state.update_data(direction="yoga")
    await call.message.answer(
        "Выберите способ оплаты:",
        reply_markup=payment_method_kb(prefix="yoga_renew")
    )
    await call.answer()
