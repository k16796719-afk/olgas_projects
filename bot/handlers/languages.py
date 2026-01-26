from __future__ import annotations
from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.states import LangFlow
from bot.keyboards import lang_goal_kb, lang_level_kb, lang_freq_kb, lang_product_kb, payment_method_kb
from bot.constants import D_ENGLISH, D_CHINESE

router = Router()

def _dir_title(direction: str) -> str:
    return "Английский" if direction == D_ENGLISH else "Китайский"

@router.callback_query(lambda c: c.data in ("dir:english","dir:chinese"))
async def choose_language_dir(call: CallbackQuery, state: FSMContext):
    direction = call.data.split(":",1)[1]
    await state.clear()
    await state.update_data(direction=direction)
    await state.set_state(LangFlow.goal)
    await call.message.edit_text(f"Выбрано: *{_dir_title(direction)}*\n\nВыбери цель:", reply_markup=lang_goal_kb())
    await call.answer()

@router.callback_query(LangFlow.goal, lambda c: c.data.startswith("lg_goal:"))
async def lang_goal(call: CallbackQuery, state: FSMContext):
    goal = call.data.split(":",1)[1]
    await state.update_data(goal=goal)
    await state.set_state(LangFlow.level)
    await call.message.edit_text("Уровень:", reply_markup=lang_level_kb())
    await call.answer()

@router.callback_query(LangFlow.level, lambda c: c.data.startswith("lg_level:"))
async def lang_level(call: CallbackQuery, state: FSMContext):
    level = call.data.split(":",1)[1]
    await state.update_data(level=level)
    await state.set_state(LangFlow.freq)
    await call.message.edit_text("Частота занятий:", reply_markup=lang_freq_kb())
    await call.answer()

@router.callback_query(LangFlow.freq, lambda c: c.data.startswith("lg_freq:"))
async def lang_freq(call: CallbackQuery, state: FSMContext, cfg):
    freq = call.data.split(":",1)[1]
    await state.update_data(freq=freq)
    await state.set_state(LangFlow.product)
    data = await state.get_data()
    direction = data["direction"]
    await call.message.edit_text(
        "Выбери продукт:",
        reply_markup=lang_product_kb(cfg, direction)
    )
    await call.answer()

@router.callback_query(LangFlow.product, lambda c: c.data.startswith("lg_prod:"))
async def lang_product(call: CallbackQuery, state: FSMContext, cfg):
    prod = call.data.split(":",1)[1]
    data = await state.get_data()
    direction = data["direction"]
    # determine amount
    if prod == "trial":
        amount = cfg.prices.trial_rub if direction == D_ENGLISH else cfg.prices.trial_china_rub
        title = "Пробное 30 минут"
    elif prod == "single":
        amount = cfg.prices.en_lesson_rub if direction == D_ENGLISH else cfg.prices.china_lesson_rub
        title = "1 занятие"
    else:
        amount = cfg.prices.en_pack10_rub if direction == D_ENGLISH else cfg.prices.china_pack10_rub
        title = "Пакет 10 занятий"
    await state.update_data(product=prod, product_title=title, amount=amount)
    await state.set_state(LangFlow.payment)
    # prefix "lang" for payment callbacks
    await call.message.edit_text(
        f"Ок. *{title}*\nСумма: *{amount}* RUB\n\nВыбери метод оплаты:",
        reply_markup=payment_method_kb("lang")
    )
    await call.answer()
