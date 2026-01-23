from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from bot.states import LangFlow, YogaFlow, AstroFlow, MentorFlow
from bot.services.texts import payment_instructions, format_order_card
from bot.services.notify import notify_admins_with_proof
from bot.constants import (
    D_ENGLISH, D_CHINESE, D_YOGA, D_ASTRO, D_MENTOR,
    PAY_RUB_CARD, PAY_PIX, PAY_CRYPTO,
    C_RUB, C_BRL, C_USDT,
    YOGA_4, YOGA_8, YOGA_10IND
)

router = Router()

def _method_title(method: str) -> str:
    return {"rub_card":"RUB карта", "pix":"Pix", "crypto":"Крипта"}.get(method, method)

def _currency_for_method(method: str) -> str:
    if method == "rub_card":
        return C_RUB
    if method == "pix":
        return C_BRL  # by spec, Pix in Brazil
    return C_USDT

def _direction_title(direction: str) -> str:
    return {
        D_ENGLISH: "Английский",
        D_CHINESE: "Китайский",
        D_YOGA: "Йога",
        D_ASTRO: "Астрология",
        D_MENTOR: "Менторство",
    }.get(direction, direction)

async def _ensure_user(db, message_or_call) -> int:
    u = message_or_call.from_user
    return await db.upsert_user(u.id, u.username, u.first_name)

@router.callback_query(lambda c: c.data.startswith("pay_m:"))
async def pick_payment_method(call: CallbackQuery, state: FSMContext, db, cfg):
    # pay_m:<prefix>:<method>
    _, prefix, method = call.data.split(":", 2)
    if method not in ("rub_card", "pix", "crypto"):
        await call.answer("Неизвестный метод оплаты")
        return

    # block creating a new payment if user already has pending
    if await db.pending_payment_exists_for_user(call.from_user.id):
        await call.answer("У тебя уже есть неоплаченный/непроверенный платеж. Сначала заверши его.", show_alert=True)
        return

    uid = await _ensure_user(db, call)

    data = await state.get_data()
    direction = data.get("direction")
    if not direction:
        await call.answer("Сессия устарела. Нажми /menu")
        return

    amount = int(data["amount"])
    # currency is decided by provider:
    currency = _currency_for_method(method)

    # Build payload per direction (human-readable keys)
    payload = {}
    if direction in (D_ENGLISH, D_CHINESE):
        payload = {
            "Цель": data.get("goal"),
            "Уровень": data.get("level"),
            "Частота": data.get("freq"),
            "Продукт": data.get("product_title"),
        }
    elif direction == D_YOGA:
        payload = {
            "Тариф": data.get("product_title"),
        }
    elif direction == D_ASTRO:
        payload = {
            "Сфера": data.get("sphere"),
            "Формат": data.get("product_title"),
        }
    elif direction == D_MENTOR:
        payload = {
            "План": data.get("product_title"),
        }

    order_id = await db.create_order(user_id=uid, direction=direction, payload=payload, status="awaiting_payment")
    payment_id = await db.create_payment(order_id=order_id, method=method, currency=currency, amount=amount)

    await state.update_data(order_id=order_id, payment_id=payment_id, pay_method=method, pay_currency=currency)

    instr = payment_instructions(method=method, currency=currency, cfg=cfg)
    await call.message.edit_text(instr)
    await call.answer("Жду подтверждение оплаты (скрин/чек)")

    # move to wait_proof depending on flow
    if prefix == "lang":
        await state.set_state(LangFlow.wait_proof)
    elif prefix == "yoga":
        await state.set_state(YogaFlow.wait_proof)
    elif prefix == "astro":
        await state.set_state(AstroFlow.wait_proof)
    else:
        await state.set_state(MentorFlow.wait_proof)

# NOTE: aiogram v3 State objects do NOT support `|` (bitwise OR).
# Register separate handlers per state and reuse shared implementation.

async def _handle_proof_photo(message: Message, state: FSMContext, db, cfg, bot):
    data = await state.get_data()
    payment_id = data.get("payment_id")
    order_id = data.get("order_id")
    if not payment_id or not order_id:
        await message.answer("Что-то сломалось в состоянии. Нажми /menu и начни заново.")
        return

    u = message.from_user
    user_line = f"{u.full_name}"
    if u.username:
        user_line += f" (@{u.username})"
    user_line += f" | id: {u.id}"

    # highest resolution photo file_id
    file_id = message.photo[-1].file_id
    await db.update_payment_proof(payment_id, file_id)

    order = await db.get_order(order_id)
    direction = order["direction"]
    payload = order["payload_json"]
    if isinstance(payload, str):
        payload = json.loads(payload)
    pay = await db.get_payment(payment_id)


    card = format_order_card(
        direction_title=_direction_title(direction),
        payload=payload,
        amount=pay["amount"],
        currency=pay["currency"],
        method=_method_title(pay["method"]),
        user_line=user_line,
    )

    await notify_admins_with_proof(bot, cfg.admin_ids, card, file_id, payment_id)
    await message.answer("Принято. Я отправил чек админам на проверку. Обычно это быстро (если люди бодрствуют).")

@router.message(LangFlow.wait_proof, F.photo)
async def receive_proof_photo_lang(message: Message, state: FSMContext, db, cfg, bot):
    await _handle_proof_photo(message, state, db, cfg, bot)

@router.message(YogaFlow.wait_proof, F.photo)
async def receive_proof_photo_yoga(message: Message, state: FSMContext, db, cfg, bot):
    await _handle_proof_photo(message, state, db, cfg, bot)

@router.message(AstroFlow.wait_proof, F.photo)
async def receive_proof_photo_astro(message: Message, state: FSMContext, db, cfg, bot):
    await _handle_proof_photo(message, state, db, cfg, bot)

@router.message(MentorFlow.wait_proof, F.photo)
async def receive_proof_photo_mentor(message: Message, state: FSMContext, db, cfg, bot):
    await _handle_proof_photo(message, state, db, cfg, bot)
