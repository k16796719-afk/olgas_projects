from __future__ import annotations

import json
import logging
from typing import Union

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from bot.keyboards.keyboards import payment_wait_kb, payment_method_kb
from bot.states.states import LangFlow, YogaFlow, AstroFlow, MentorFlow
from bot.services.texts import payment_instructions, format_order_card
from bot.services.notify import notify_admins_with_proof
from bot.constants import (
    D_ENGLISH, D_CHINESE, D_YOGA, D_ASTRO, D_MENTOR,
    PAY_RUB_CARD, PAY_PIX, PAY_CRYPTO,
    C_RUB, C_BRL, C_USDT,
)

logger = logging.getLogger(__name__)
router = Router()

# Константы для валидации
ALLOWED_PAYMENT_METHODS = {PAY_RUB_CARD, PAY_PIX, PAY_CRYPTO}
ALLOWED_PREFIXES = {"lang", "yoga", "astro", "mentor"}

PAYMENT_METHOD_TITLES = {
    PAY_RUB_CARD: "RUB карта",
    PAY_PIX: "Pix",
    PAY_CRYPTO: "Крипта"
}

PAYMENT_METHOD_CURRENCIES = {
    PAY_RUB_CARD: C_RUB,
    PAY_PIX: C_BRL,
    PAY_CRYPTO: C_USDT
}

DIRECTION_TITLES = {
    D_ENGLISH: "Английский",
    D_CHINESE: "Китайский",
    D_YOGA: "Йога",
    D_ASTRO: "Астрология",
    D_MENTOR: "Менторство",
}

# Маппинг префиксов на состояния
PREFIX_TO_STATE = {
    "lang": LangFlow.wait_proof,
    "yoga": YogaFlow.wait_proof,
    "astro": AstroFlow.wait_proof,
    "mentor": MentorFlow.wait_proof,
}


def _method_title(method: str) -> str:
    """Получить читаемое название метода оплаты."""
    return PAYMENT_METHOD_TITLES.get(method, method)


def _currency_for_method(method: str) -> str:
    """Получить валюту для метода оплаты."""
    return PAYMENT_METHOD_CURRENCIES.get(method, C_USDT)


def _direction_title(direction: str) -> str:
    """Получить читаемое название направления."""
    return DIRECTION_TITLES.get(direction, direction)


async def _ensure_user(db, message_or_call: Union[Message, CallbackQuery]) -> int:
    """Создать или обновить пользователя в БД, вернуть его ID."""
    u = message_or_call.from_user
    try:
        return await db.upsert_user(u.id, u.username, u.first_name)
    except Exception as e:
        logger.error(f"Failed to upsert user {u.id}: {e}")
        raise


def _build_payload(direction: str, data: dict) -> dict:
    """Собрать payload для заказа в зависимости от направления."""
    if direction in (D_ENGLISH, D_CHINESE):
        return {
            "Цель": data.get("goal"),
            "Уровень": data.get("level"),
            "Частота": data.get("freq"),
            "Продукт": data.get("product_title"),
        }
    elif direction == D_YOGA:
        return {
            "Тариф": data.get("product_title"),
        }
    elif direction == D_ASTRO:
        return {
            "Сфера": data.get("sphere"),
            "Формат": data.get("product_title"),
        }
    elif direction == D_MENTOR:
        return {
            "План": data.get("product_title"),
        }
    return {}


def _parse_callback_data(callback_data: str, expected_parts: int) -> list[str] | None:
    """Безопасно распарсить callback_data, вернуть None если формат неверный."""
    try:
        parts = callback_data.split(":", expected_parts - 1)
        if len(parts) == expected_parts:
            return parts
    except Exception as e:
        logger.error(f"Failed to parse callback_data '{callback_data}': {e}")
    return None


def _safe_parse_json(json_str: str | dict, order_id: int = None) -> dict:
    """Безопасно распарсить JSON, вернуть пустой dict при ошибке."""
    if isinstance(json_str, dict):
        return json_str

    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Invalid JSON in order {order_id}: {e}")
        return {}


@router.callback_query(lambda c: c.data.startswith("pay_m:"))
async def pick_payment_method(call: CallbackQuery, state: FSMContext, db, cfg):
    """Обработка выбора метода оплаты."""
    # Парсим callback_data
    parts = _parse_callback_data(call.data, 3)
    if not parts:
        await call.answer("Ошибка формата данных", show_alert=True)
        logger.warning(f"Invalid callback_data format: {call.data}")
        return

    _, prefix, method = parts

    logger.info(f"User {call.from_user.id} selected payment method: {method} (prefix: {prefix})")

    # Валидация метода
    if method not in ALLOWED_PAYMENT_METHODS:
        await call.answer("Неизвестный метод оплаты", show_alert=True)
        logger.warning(f"Unknown payment method: {method}")
        return

    # Валидация префикса
    if prefix not in ALLOWED_PREFIXES:
        await call.answer("Ошибка: неверный тип продукта", show_alert=True)
        logger.warning(f"Unknown prefix: {prefix}")
        return

    # Проверка существующих платежей
    try:
        if await db.pending_payment_exists_for_user(call.from_user.id):
            await call.answer(
                "У тебя уже есть неоплаченный/непроверенный платеж. Сначала заверши его.",
                show_alert=True
            )
            return
    except Exception as e:
        logger.error(f"Error checking pending payments for user {call.from_user.id}: {e}")
        await call.answer("Ошибка проверки платежей. Попробуй позже.", show_alert=True)
        return

    # Получаем или создаём пользователя
    try:
        uid = await _ensure_user(db, call)
    except Exception as e:
        await call.answer("Ошибка создания пользователя. Попробуй позже.", show_alert=True)
        return

    # Получаем данные из state
    data = await state.get_data()
    direction = data.get("direction")

    if not direction:
        await call.answer("Сессия устарела. Нажми /menu", show_alert=True)
        logger.warning(f"No direction in state for user {call.from_user.id}")
        return

    # Валидация суммы
    try:
        amount = int(data["amount"])
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except (ValueError, KeyError, TypeError) as e:
        await call.answer("Ошибка: некорректная сумма оплаты", show_alert=True)
        logger.error(f"Invalid amount in state for user {call.from_user.id}: {e}")
        return

    # Определяем валюту
    currency = _currency_for_method(method)

    # Собираем payload
    payload = _build_payload(direction, data)

    # Создаём заказ и платёж в БД
    try:
        order_id = await db.create_order(
            user_id=uid,
            direction=direction,
            payload=payload,
            status="awaiting_payment"
        )
        payment_id = await db.create_payment(
            order_id=order_id,
            method=method,
            currency=currency,
            amount=amount
        )

        logger.info(
            f"Created order {order_id} and payment {payment_id} "
            f"for user {call.from_user.id} (direction: {direction}, method: {method})"
        )
    except Exception as e:
        logger.error(f"Failed to create order/payment for user {call.from_user.id}: {e}")
        await call.answer(
            "Ошибка создания заказа. Попробуй позже или обратись к админам.",
            show_alert=True
        )
        return

    # Обновляем state
    await state.update_data(
        order_id=order_id,
        payment_id=payment_id,
        pay_method=method,
        pay_currency=currency
    )

    # Отправляем инструкции
    try:
        instr = payment_instructions(method=method, currency=currency, cfg=cfg)
        await call.message.edit_text(
            instr,
            reply_markup=payment_wait_kb(order_id),
            parse_mode="HTML",
        )
        await call.answer("Жду подтверждение оплаты (скрин/чек)")
    except Exception as e:
        logger.error(f"Failed to send payment instructions to user {call.from_user.id}: {e}")
        # Не возвращаем - платёж уже создан, пользователь может загрузить чек

    # Переводим в состояние ожидания чека
    try:
        new_state = PREFIX_TO_STATE.get(prefix)
        if new_state:
            await state.set_state(new_state)
        else:
            logger.error(f"No state mapping for prefix: {prefix}")
            await state.set_state(MentorFlow.wait_proof)  # fallback
    except Exception as e:
        logger.error(f"Failed to set state for user {call.from_user.id}: {e}")


async def _handle_proof_photo(message: Message, state: FSMContext, db, cfg, bot):
    """Общая логика обработки фото-чека от пользователя."""
    data = await state.get_data()
    payment_id = data.get("payment_id")
    order_id = data.get("order_id")

    if not payment_id or not order_id:
        await message.answer("Что-то сломалось в состоянии. Нажми /menu и начни заново.")
        logger.error(f"Missing payment_id or order_id in state for user {message.from_user.id}")
        return

    u = message.from_user
    user_line = f"{u.full_name}"
    if u.username:
        user_line += f" (@{u.username})"
    user_line += f" | id: {u.id}"

    # Получаем file_id фото в наилучшем качестве
    file_id = message.photo[-1].file_id

    # Сохраняем proof в БД
    try:
        await db.update_payment_proof(payment_id, file_id)
        logger.info(f"Updated payment {payment_id} with proof for user {u.id}")
    except Exception as e:
        logger.error(f"Failed to update payment proof {payment_id}: {e}")
        await message.answer(
            "Ошибка сохранения чека. Попробуй ещё раз или обратись к админам."
        )
        return

    # Получаем данные заказа и платежа
    try:
        order = await db.get_order(order_id)
        pay = await db.get_payment(payment_id)

        if not order or not pay:
            raise ValueError("Order or payment not found")

        direction = order["direction"]
        payload = _safe_parse_json(order["payload_json"], order_id)

    except Exception as e:
        logger.error(f"Failed to get order/payment data for notification: {e}")
        await message.answer(
            "Чек сохранён, но возникла ошибка при отправке админам. "
            "Они увидят платёж в системе."
        )
        return

    # Формируем карточку заказа
    try:
        card = format_order_card(
            direction_title=_direction_title(direction),
            payload=payload,
            amount=pay["amount"],
            currency=pay["currency"],
            method=_method_title(pay["method"]),
            user_line=user_line,
        )
    except Exception as e:
        logger.error(f"Failed to format order card for payment {payment_id}: {e}")
        card = (
            f"Новый платёж #{payment_id}\n"
            f"Пользователь: {user_line}\n"
            f"Направление: {_direction_title(direction)}\n"
            f"Сумма: {pay['amount']} {pay['currency']}\n"
            f"Метод: {_method_title(pay['method'])}"
        )

    # Уведомляем админов
    try:
        await notify_admins_with_proof(bot, cfg.admin_ids, card, file_id, payment_id)
        logger.info(f"Notified admins about payment {payment_id}")
    except Exception as e:
        logger.error(f"Failed to notify admins about payment {payment_id}: {e}")
        await message.answer(
            "Чек принят, но не удалось уведомить админов автоматически. "
            "Свяжись с ними напрямую, если прошло много времени."
        )
        return

    await message.answer(
        "Принято. Я отправил чек админам на проверку. "
        "Обычно это быстро (если люди бодрствуют)."
    )


# Единый хендлер для всех состояний wait_proof
@router.message(
    StateFilter(
        LangFlow.wait_proof,
        YogaFlow.wait_proof,
        AstroFlow.wait_proof,
        MentorFlow.wait_proof
    ),
    F.photo
)
async def receive_proof_photo(message: Message, state: FSMContext, db, cfg, bot):
    """Обработка фото-чека от пользователя (для всех направлений)."""
    await _handle_proof_photo(message, state, db, cfg, bot)


@router.callback_query(lambda c: c.data.startswith("pay_change:"))
async def pay_change(call: CallbackQuery, state: FSMContext, db, cfg):
    """Изменение способа оплаты для существующего заказа."""
    parts = _parse_callback_data(call.data, 2)
    if not parts:
        await call.answer("Ошибка формата данных", show_alert=True)
        return

    try:
        order_id = int(parts[1])
    except (ValueError, IndexError) as e:
        await call.answer("Некорректный ID заказа", show_alert=True)
        logger.error(f"Invalid order_id in callback: {call.data}, error: {e}")
        return

    # Получаем заказ
    try:
        order = await db.get_order(order_id)
    except Exception as e:
        logger.error(f"Failed to get order {order_id}: {e}")
        await call.answer("Ошибка получения заказа", show_alert=True)
        return

    if not order or order["status"] == "paid":
        await call.answer("Этот заказ уже обработан", show_alert=True)
        return

    # Проверка прав доступа
    try:
        uid = await db.get_user_id_by_tg(call.from_user.id)
    except Exception as e:
        logger.error(f"Failed to get user_id for tg_id {call.from_user.id}: {e}")
        await call.answer("Ошибка проверки доступа", show_alert=True)
        return

    if int(order["user_id"]) != int(uid):
        await call.answer("Нет доступа", show_alert=True)
        logger.warning(
            f"User {call.from_user.id} tried to access order {order_id} "
            f"owned by user {order['user_id']}"
        )
        return

    # Отменяем текущие платежи
    try:
        await db.cancel_pending_payments_for_order(order_id)
        logger.info(f"Cancelled pending payments for order {order_id}")
    except Exception as e:
        logger.error(f"Failed to cancel payments for order {order_id}: {e}")
        await call.answer("Ошибка отмены платежей", show_alert=True)
        return

    # Определяем prefix на основе direction
    direction = order.get("direction", "")
    if direction in (D_ENGLISH, D_CHINESE):
        prefix = "lang"
    elif direction == D_YOGA:
        prefix = "yoga"
    elif direction == D_ASTRO:
        prefix = "astro"
    elif direction == D_MENTOR:
        prefix = "mentor"
    else:
        prefix = "order"  # fallback

    try:
        await call.message.edit_text(
            "Выберите другой способ оплаты:",
            reply_markup=payment_method_kb(prefix=prefix),
        )
        await call.answer()
    except Exception as e:
        logger.error(f"Failed to edit message for user {call.from_user.id}: {e}")
        await call.answer("Ошибка обновления сообщения", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("order_cancel:"))
async def order_cancel(call: CallbackQuery, state: FSMContext, db):
    """Отмена заказа пользователем."""
    parts = _parse_callback_data(call.data, 2)
    if not parts:
        await call.answer("Ошибка формата данных", show_alert=True)
        return

    try:
        order_id = int(parts[1])
    except (ValueError, IndexError) as e:
        await call.answer("Некорректный ID заказа", show_alert=True)
        logger.error(f"Invalid order_id in callback: {call.data}, error: {e}")
        return

    # Получаем заказ
    try:
        order = await db.get_order(order_id)
    except Exception as e:
        logger.error(f"Failed to get order {order_id}: {e}")
        await call.answer("Ошибка получения заказа", show_alert=True)
        return

    if not order or order["status"] == "paid":
        await call.answer("Этот заказ уже обработан", show_alert=True)
        return

    # Проверка прав доступа
    try:
        uid = await db.get_user_id_by_tg(call.from_user.id)
    except Exception as e:
        logger.error(f"Failed to get user_id for tg_id {call.from_user.id}: {e}")
        await call.answer("Ошибка проверки доступа", show_alert=True)
        return

    if int(order["user_id"]) != int(uid):
        await call.answer("Нет доступа", show_alert=True)
        logger.warning(
            f"User {call.from_user.id} tried to cancel order {order_id} "
            f"owned by user {order['user_id']}"
        )
        return

    # Отменяем платежи и заказ
    try:
        await db.cancel_pending_payments_for_order(order_id)
        await db.cancel_order(order_id)
        logger.info(f"User {call.from_user.id} cancelled order {order_id}")
    except Exception as e:
        logger.error(f"Failed to cancel order {order_id}: {e}")
        await call.answer("Ошибка отмены заказа", show_alert=True)
        return

    try:
        await call.message.edit_text(
            "❌ Заказ отменён.\n\nМожешь оформить заново и выбрать другой способ оплаты.",
            reply_markup=None,
        )
        await call.answer("Отменено")
    except Exception as e:
        logger.error(f"Failed to edit message for user {call.from_user.id}: {e}")
        await call.answer("Заказ отменён", show_alert=True)