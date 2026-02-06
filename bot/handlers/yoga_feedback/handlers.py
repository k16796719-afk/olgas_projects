from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from .constants import SURVEY_INTRO_TEXT, FINAL_USER_TEXT, Q1, Q2, Q3, Q4, Q5, Q6
from .keyboards import kb_start_survey, kb_single_choice, kb_q6_multi, kb_renew
from .callbacks import YF
from .state import YogaSurvey

from .yoga_feedback_repo import YogaFeedbackRepo
from bot.handlers.payments import payment_method_kb
from bot.config import load_config

router = Router()


# ---------- helpers ----------

def _repo(query: CallbackQuery) -> YogaFeedbackRepo:
    db = query.bot["db"]
    return YogaFeedbackRepo(db)


def _q_text(n: int) -> str:
    return {
        1: "1️⃣ Насколько сложные были практики?",
        2: "2️⃣ Какой был темп йога-практик?",
        3: "3️⃣ Как вы себя обычно чувствовали после практик?",
        4: "4️⃣ Какой формат занятий вам больше подходит?",
        5: "5️⃣ Достаточно ли было практик для вас?\n"
           "Сколько бы вы хотели заниматься йогой в месяц?",
        6: "6️⃣ Каких практик вам бы хотелось видеть больше в новом месяце?",
    }[n]


async def _ask_q(message, n: int, state: FSMContext):
    if n == 1:
        await state.set_state(YogaSurvey.q1)
        await message.answer(_q_text(1), reply_markup=kb_single_choice(1, Q1).as_markup())
    elif n == 2:
        await state.set_state(YogaSurvey.q2)
        await message.answer(_q_text(2), reply_markup=kb_single_choice(2, Q2).as_markup())
    elif n == 3:
        await state.set_state(YogaSurvey.q3)
        await message.answer(_q_text(3), reply_markup=kb_single_choice(3, Q3).as_markup())
    elif n == 4:
        await state.set_state(YogaSurvey.q4)
        await message.answer(_q_text(4), reply_markup=kb_single_choice(4, Q4).as_markup())
    elif n == 5:
        await state.set_state(YogaSurvey.q5)
        await message.answer(_q_text(5), reply_markup=kb_single_choice(5, Q5).as_markup())
    elif n == 6:
        await state.set_state(YogaSurvey.q6)
        data = await state.get_data()
        selected = set(data.get("q6_selected", []))
        await message.answer(_q_text(6), reply_markup=kb_q6_multi(selected, Q6).as_markup())


async def _finish(
    bot,
    chat_id: int,
    state: FSMContext,
    yf_repo: YogaFeedbackRepo,
):
    data = await state.get_data()
    user_id = data["user_id"]
    subscription_id = data["subscription_id"]

    fb = await yf_repo.get(user_id, subscription_id)

    await bot.send_message(chat_id, FINAL_USER_TEXT, reply_markup=kb_renew().as_markup())

    cfg = load_config()

    def fmt(v):
        if not v:
            return "—"
        if isinstance(v, list):
            return ", ".join(v)
        return str(v)

    text = (
        "🧘‍♀️ Обратная связь по йоге\n\n"
        f"👤 user_id: {user_id}\n"
        f"📦 subscription_id: {subscription_id}\n\n"
        f"1️⃣ Сложность: {fmt(fb.get('q1_difficulty'))}\n"
        f"2️⃣ Темп: {fmt(fb.get('q2_pace'))}\n"
        f"3️⃣ После практик: {fmt(fb.get('q3_state'))}\n"
        f"4️⃣ Формат: {fmt(fb.get('q4_format'))}\n"
        f"5️⃣ Частота: {fmt(fb.get('q5_frequency'))}\n"
        f"6️⃣ Хотят больше: {fmt(fb.get('q6_preferences'))}\n"
    )

    for admin_id in cfg.admin_ids:
        await bot.send_message(admin_id, text)

    await state.clear()


# ---------- entry ----------

@router.message(F.text == "/feedback_test")
async def feedback_test(message: Message, state: FSMContext):
    test_sub_id = 999
    await message.answer(
        SURVEY_INTRO_TEXT,
        reply_markup=kb_start_survey(test_sub_id).as_markup(),
    )
    await state.update_data(user_id=message.from_user.id, subscription_id=test_sub_id)


# ---------- callbacks ----------

@router.callback_query(YF.filter(), F.action == "start")
async def cb_start(query: CallbackQuery, callback_data: YF, state: FSMContext):
    print("CB_START HIT:", callback_data)
    await query.answer()

    yf_repo = _repo(query)

    subscription_id = int(callback_data.v)
    user_id = query.from_user.id

    await state.update_data(
        user_id=user_id,
        subscription_id=subscription_id,
        q6_selected=[],
    )

    await yf_repo.upsert_blank(user_id, subscription_id)
    await _ask_q(query.message, 1, state)



@router.callback_query(YF.filter(), F.action == "skip")
async def cb_skip(query: CallbackQuery, callback_data: YF, state: FSMContext):
    await query.answer()
    next_q = callback_data.q + 1
    if next_q <= 6:
        await _ask_q(query.message, next_q, state)


@router.callback_query(YF.filter(), F.action == "a")
async def cb_answer_single(
    query: CallbackQuery,
    callback_data: YF,
    state: FSMContext,
    yf_repo: YogaFeedbackRepo,
):
    await query.answer()
    data = await state.get_data()

    field_map = {
        1: "q1_difficulty",
        2: "q2_pace",
        3: "q3_state",
        4: "q4_format",
        5: "q5_frequency",
    }

    field = field_map.get(callback_data.q)
    if not field:
        return

    await yf_repo.set_answer(
        data["user_id"],
        data["subscription_id"],
        field,
        callback_data.v,
    )

    next_q = callback_data.q + 1
    if next_q <= 6:
        await _ask_q(query.message, next_q, state)


@router.callback_query(YF.filter(), F.action == "toggle6")
async def cb_toggle_q6(
    query: CallbackQuery,
    callback_data: YF,
    state: FSMContext,
):
    await query.answer()
    data = await state.get_data()
    selected = set(data.get("q6_selected", []))

    if callback_data.v in selected:
        selected.remove(callback_data.v)
    else:
        selected.add(callback_data.v)

    await state.update_data(q6_selected=list(selected))
    await query.message.edit_reply_markup(
        reply_markup=kb_q6_multi(selected, Q6).as_markup()
    )


@router.callback_query(YF.filter(), F.action == "done6")
async def cb_done_q6(
    query: CallbackQuery,
    state: FSMContext,
    yf_repo: YogaFeedbackRepo,
):
    await query.answer()
    data = await state.get_data()

    await yf_repo.set_answer(
        data["user_id"],
        data["subscription_id"],
        "q6_preferences",
        data.get("q6_selected") or None,
    )

    await _finish(
        query.bot,
        query.message.chat.id,
        state,
        yf_repo,
    )


@router.callback_query(YF.filter(), F.action == "renew")
async def cb_renew(query: CallbackQuery):
    await query.answer()

    kb = payment_method_kb("yoga")
    reply_markup = kb.as_markup() if hasattr(kb, "as_markup") else kb

    await query.message.answer(
        "Для продления участия выберите способ оплаты:",
        reply_markup=reply_markup,
    )
