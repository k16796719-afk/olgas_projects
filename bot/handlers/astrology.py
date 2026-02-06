from __future__ import annotations
from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.states.states import AstroFlow
from bot.keyboards.keyboards import astrology_spheres_kb, astrology_format_kb, payment_method_kb
from bot.constants import D_ASTRO

router = Router()

@router.callback_query(lambda c: c.data == "dir:astrology")
async def astro_start(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.update_data(direction=D_ASTRO)
    await state.set_state(AstroFlow.sphere)
    await call.message.edit_text("Выбери сферу:", reply_markup=astrology_spheres_kb())
    await call.answer()

@router.callback_query(AstroFlow.sphere, lambda c: c.data.startswith("as_sphere:"))
async def astro_sphere(call: CallbackQuery, state: FSMContext, cfg):
    sphere = call.data.split(":",1)[1]
    await state.update_data(sphere=sphere)
    await state.set_state(AstroFlow.fmt)
    await call.message.edit_text("Выбери формат:", reply_markup=astrology_format_kb(cfg))
    await call.answer()

@router.callback_query(AstroFlow.fmt, lambda c: c.data.startswith("as_fmt:"))
async def astro_format(call: CallbackQuery, state: FSMContext, cfg):
    fmt = call.data.split(":",1)[1]
    if fmt == "one":
        amount = cfg.prices.astro_1_rub
        title = "Астрология: разбор 1 сферы"
    else:
        amount = cfg.prices.astro_full_rub
        title = "Астрология: натальная карта полностью"
    await state.update_data(astro_format=fmt, product_title=title, amount=amount)
    await state.set_state(AstroFlow.payment)
    await call.message.edit_text(
        f"*{title}*\nСумма: *{amount}* RUB\n\nВыбери метод оплаты:",
        reply_markup=payment_method_kb("astro")
    )
    await call.answer()
