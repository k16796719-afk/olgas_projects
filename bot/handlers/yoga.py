from __future__ import annotations
from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.states import YogaFlow
from bot.keyboards import yoga_plan_kb, payment_method_kb
from bot.constants import D_YOGA, YOGA_4, YOGA_8, YOGA_10IND

router = Router()

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
        f"*{title}*\nСумма: *{amount}* RUB\n\nВыбери метод оплаты:",
        reply_markup=payment_method_kb("yoga")
    )
    await call.answer()
