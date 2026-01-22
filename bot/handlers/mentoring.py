from __future__ import annotations
from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.states import MentorFlow
from bot.keyboards import mentoring_kb, payment_method_kb
from bot.constants import D_MENTOR

router = Router()

@router.callback_query(lambda c: c.data == "dir:mentoring")
async def mentor_start(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.update_data(direction=D_MENTOR)
    await state.set_state(MentorFlow.plan)
    await call.message.edit_text("Выбери план менторства:", reply_markup=mentoring_kb())
    await call.answer()

@router.callback_query(MentorFlow.plan, lambda c: c.data.startswith("m_plan:"))
async def mentor_plan(call: CallbackQuery, state: FSMContext, cfg):
    plan = call.data.split(":",1)[1]
    if plan == "week":
        amount = cfg.prices.mentor_week_rub
        title = "Менторство: 1 неделя"
    else:
        amount = cfg.prices.mentor_month_rub
        title = "Менторство: 1 месяц"
    await state.update_data(mentor_plan=plan, product_title=title, amount=amount)
    await state.set_state(MentorFlow.payment)
    await call.message.edit_text(
        f"*{title}*\nСумма: *{amount}* RUB\n\nВыбери метод оплаты:",
        reply_markup=payment_method_kb("mentor")
    )
    await call.answer()
