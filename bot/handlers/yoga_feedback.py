# handlers/yoga_feedback.py
from __future__ import annotations

import logging
from html import escape
from typing import Optional

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from bot.keyboards.keyboards import yoga_renew_kb, payment_method_kb, yoga_change_plan_kb
from bot.states.yoga_feedback import YogaFeedback
from bot.keyboards.yoga_feedback_kb import (
    difficulty_kb,
    tempo_kb,
    feelings_kb,
    format_kb,
    freq_kb,
    types_kb,
)

logger = logging.getLogger(__name__)
router = Router()

# Константы
START_TEXT = (
    "Наш месяц практик подходит к завершению 🤍\n"
    "Спасибо, что были в этом пространстве 🧘‍♀️\n\n"
    "Ответьте, пожалуйста, на несколько вопросов 📝"
)

THANK_YOU_TEXT = (
    "Спасибо за вашу обратную связь 🤍\n\n"
    "Если вы хотите продолжить — буду рада видеть вас в следующем месяце.\n\n"
    "👉 Нажмите «Оплатить», чтобы продлить участие ✨"
)

# Маппинги для продуктов йоги (единый источник истины)
YOGA_PRODUCTS = {
    "yoga_4": {
        "title": "Йога 4 практики/мес",
        "price_attr": "yoga_4_rub",
    },
    "yoga_8": {
        "title": "Йога 8 практик/мес",
        "price_attr": "yoga_8_rub",
    },
    "yoga_ind": {
        "title": "Йога 1:1 10 практик/мес",
        "price_attr": "yoga_10ind_rub",
    },
    "yoga_10_individual": {  # альтернативное название для совместимости
        "title": "Йога 1:1 10 практик/мес",
        "price_attr": "yoga_10ind_rub",
    },
}


def _parse_callback_data(callback_data: str, separator: str = ":", max_split: int = 1) -> Optional[list[str]]:
    """Безопасно распарсить callback_data."""
    try:
        parts = callback_data.split(separator, max_split)
        if len(parts) == max_split + 1:
            return parts
    except Exception as e:
        logger.error(f"Failed to parse callback_data '{callback_data}': {e}")
    return None


def _get_product_info(product: str, cfg) -> Optional[dict]:
    """
    Получить информацию о продукте (цена и название).

    Returns:
        dict с ключами 'amount' и 'title' или None если продукт неизвестен
    """
    product_config = YOGA_PRODUCTS.get(product)
    if not product_config:
        logger.error(f"Unknown yoga product: {product}")
        return None

    try:
        price_attr = product_config["price_attr"]
        amount = int(getattr(cfg.prices, price_attr, 0))

        if amount <= 0:
            logger.error(f"Invalid price for product {product}: {amount}")
            return None

        return {
            "amount": amount,
            "title": product_config["title"],
        }
    except (AttributeError, ValueError, TypeError) as e:
        logger.error(f"Failed to get price for product {product}: {e}")
        return None


def _format_feedback_message(user, data: dict, last_answer: str) -> str:
    """Отформатировать сообщение с обратной связью для админов."""
    user_name = escape(user.full_name or "Без имени")
    user_tag = f"@{user.username}" if user.username else "—"
    user_id = user.id

    # Безопасно получаем ответы, заменяя None на "—"
    def safe_answer(key: str) -> str:
        value = data.get(key)
        if value is None:
            return "—"
        return escape(str(value))

    return (
        "🧘‍♀️ <b>Йога — обратная связь</b>\n\n"
        "👤 <b>От:</b>\n"
        f"• Имя: <b>{user_name}</b>\n"
        f"• Username: <b>{user_tag}</b>\n"
        f"• ID: <code>{user_id}</code>\n\n"
        "📋 <b>Ответы:</b>\n"
        f"1️⃣ <b>Сложность:</b> {safe_answer('yf_q1')}\n"
        f"2️⃣ <b>Темп:</b> {safe_answer('yf_q2')}\n"
        f"3️⃣ <b>После практик:</b> {safe_answer('yf_q3')}\n"
        f"4️⃣ <b>Формат:</b> {safe_answer('yf_q4')}\n"
        f"5️⃣ <b>Частота:</b> {safe_answer('yf_q5')}\n"
        f"6️⃣ <b>Типы практик:</b> {escape(last_answer)}\n"
    )


async def _notify_admins_feedback(bot, admin_ids: list[int], message_text: str) -> bool:
    """
    Отправить фидбек всем админам.

    Returns:
        True если хотя бы одному админу отправлено, False если всем не удалось
    """
    success_count = 0

    for admin_id in admin_ids:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=message_text,
                parse_mode="HTML",
            )
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to send feedback to admin {admin_id}: {e}")

    if success_count == 0:
        logger.error("Failed to send feedback to all admins")
        return False

    logger.info(f"Feedback sent to {success_count}/{len(admin_ids)} admins")
    return True


async def _send_start_question(target, state: FSMContext):
    """Отправить первый вопрос анкеты."""
    await target.answer(START_TEXT)
    await target.answer(
        text="1️⃣ Насколько сложные были практики?",
        reply_markup=difficulty_kb
    )
    await state.set_state(YogaFeedback.q1_difficulty)


@router.callback_query(lambda c: c.data == "yoga_feedback_start")
async def start_feedback_cb(call: CallbackQuery, state: FSMContext):
    """Начать анкету обратной связи (через callback)."""
    await _send_start_question(call.message, state)
    await call.answer()


from aiogram.filters import Command, StateFilter

@router.message(StateFilter("*"), Command("yoga_feedback_start"))
async def start_feedback(message: Message, state: FSMContext):
    await _send_start_question(message, state)


async def _process_step(
        call: CallbackQuery,
        state: FSMContext,
        next_state,
        text: str,
        kb
):
    """
    Обработать шаг анкеты: сохранить ответ, показать следующий вопрос.

    Args:
        call: CallbackQuery с ответом пользователя
        state: FSM контекст
        next_state: Следующее состояние FSM
        text: Текст следующего вопроса
        kb: Клавиатура для следующего вопроса
    """
    # Безопасно парсим callback_data
    parts = _parse_callback_data(call.data, ":", 1)
    if not parts or len(parts) != 2:
        await call.answer("Ошибка формата данных", show_alert=True)
        logger.warning(f"Invalid callback_data in feedback step: {call.data}")
        return

    question_key, answer_value = parts

    # Сохраняем ответ
    await state.update_data(**{question_key: answer_value})

    try:
        await call.message.edit_text(text, reply_markup=kb)
        await state.set_state(next_state)
        await call.answer()
    except Exception as e:
        logger.error(f"Failed to edit message in feedback step: {e}")
        await call.answer("Ошибка обновления", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("yf_q1"))
async def q1(call: CallbackQuery, state: FSMContext):
    """Обработать ответ на вопрос 1 (сложность)."""
    await _process_step(
        call, state,
        YogaFeedback.q2_tempo,
        "2️⃣ Какой был темп практик?",
        tempo_kb
    )


@router.callback_query(lambda c: c.data.startswith("yf_q2"))
async def q2(call: CallbackQuery, state: FSMContext):
    """Обработать ответ на вопрос 2 (темп)."""
    await _process_step(
        call, state,
        YogaFeedback.q3_feelings,
        "3️⃣ Как вы себя чувствовали после практик?",
        feelings_kb
    )


@router.callback_query(lambda c: c.data.startswith("yf_q3"))
async def q3(call: CallbackQuery, state: FSMContext):
    """Обработать ответ на вопрос 3 (ощущения)."""
    await _process_step(
        call, state,
        YogaFeedback.q4_format,
        "4️⃣ Какой формат вам ближе?",
        format_kb
    )


@router.callback_query(lambda c: c.data.startswith("yf_q4"))
async def q4(call: CallbackQuery, state: FSMContext):
    """Обработать ответ на вопрос 4 (формат)."""
    await _process_step(
        call, state,
        YogaFeedback.q5_frequency,
        "5️⃣ Сколько практик в месяц вам комфортно?",
        freq_kb
    )


@router.callback_query(lambda c: c.data.startswith("yf_q5"))
async def q5(call: CallbackQuery, state: FSMContext):
    """Обработать ответ на вопрос 5 (частота)."""
    await _process_step(
        call, state,
        YogaFeedback.q6_types,
        "6️⃣ Каких практик хотелось бы больше?",
        types_kb
    )


@router.callback_query(lambda c: c.data.startswith("yf_q6"))
async def finish(call: CallbackQuery, state: FSMContext, bot, cfg):
    """Завершить анкету, отправить результаты админам."""
    # Парсим последний ответ
    parts = _parse_callback_data(call.data, ":", 1)
    if not parts or len(parts) != 2:
        await call.answer("Ошибка формата данных", show_alert=True)
        logger.warning(f"Invalid callback_data in finish: {call.data}")
        return

    last_answer = parts[1]

    # Получаем все ответы из state
    data = await state.get_data()

    # Формируем сообщение для админов
    message_text = _format_feedback_message(call.from_user, data, last_answer)

    # Отправляем админам
    admins_notified = await _notify_admins_feedback(bot, cfg.admin_ids, message_text)

    # Показываем благодарность и предложение продлить
    try:
        await call.message.edit_text(
            THANK_YOU_TEXT,
            reply_markup=yoga_renew_kb()
        )
    except Exception as e:
        logger.error(f"Failed to show thank you message: {e}")
        # Пытаемся отправить новым сообщением
        try:
            await call.message.answer(THANK_YOU_TEXT, reply_markup=yoga_renew_kb())
        except Exception as e2:
            logger.error(f"Failed to send thank you message: {e2}")

    # Очищаем state
    await state.clear()

    # Логируем завершение
    logger.info(
        f"User {call.from_user.id} completed yoga feedback. "
        f"Admins notified: {admins_notified}"
    )

    await call.answer()


@router.callback_query(lambda c: c.data == "yoga_renew:pay")
async def yoga_renew_pay(call: CallbackQuery, state: FSMContext, db, cfg):
    """Продлить подписку на тот же тариф."""
    # Получаем ID пользователя
    try:
        uid = await db.get_user_id_by_tg(call.from_user.id)
        if not uid:
            await call.answer("Не нашёл пользователя. Нажми /start", show_alert=True)
            logger.warning(f"User not found for tg_id {call.from_user.id}")
            return
    except Exception as e:
        logger.error(f"Failed to get user_id for tg_id {call.from_user.id}: {e}")
        await call.answer("Ошибка получения данных пользователя", show_alert=True)
        return

    # Получаем активную подписку
    try:
        sub = await db.get_active_yoga_subscription(uid)
        if not sub:
            await call.answer(
                "У тебя нет активного доступа. Оформи новый заказ через меню.",
                show_alert=True
            )
            logger.info(f"No active subscription for user {uid}")
            return
    except Exception as e:
        logger.error(f"Failed to get active subscription for user {uid}: {e}")
        await call.answer("Ошибка получения подписки", show_alert=True)
        return

    product = sub["product"]
    logger.info(f"User {uid} renewing subscription for product: {product}")

    # Получаем информацию о продукте
    product_info = _get_product_info(product, cfg)
    if not product_info:
        await call.answer(
            "Не смог определить сумму. Напиши администратору.",
            show_alert=True
        )
        return

    # Сохраняем данные в state
    await state.update_data(
        direction="yoga",
        flow="renew_same",
        product=product,
        product_title=product_info["title"],
        amount=product_info["amount"],
    )

    # Показываем выбор способа оплаты
    try:
        await call.message.answer(
            "Выбери способ оплаты 💳",
            reply_markup=payment_method_kb(prefix="yoga")
        )
        await call.answer()
    except Exception as e:
        logger.error(f"Failed to show payment methods to user {uid}: {e}")
        await call.answer("Ошибка показа методов оплаты", show_alert=True)


@router.callback_query(lambda c: c.data == "yoga_renew:change")
async def yoga_renew_change(call: CallbackQuery, state: FSMContext, cfg):
    """Начать процесс смены тарифа."""
    await state.update_data(direction="yoga", flow="renew_change")

    try:
        await call.message.answer(
            "Выбери новый тариф 👇",
            reply_markup=yoga_change_plan_kb(cfg)
        )
        await call.answer()
    except Exception as e:
        logger.error(f"Failed to show plan change options: {e}")
        await call.answer("Ошибка показа тарифов", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("yoga_renew_pick:"))
async def yoga_renew_pick(call: CallbackQuery, state: FSMContext, cfg):
    """Обработать выбор нового тарифа при смене подписки."""
    # Безопасно парсим product
    parts = _parse_callback_data(call.data, ":", 1)
    if not parts or len(parts) != 2:
        await call.answer("Ошибка формата данных", show_alert=True)
        logger.warning(f"Invalid callback_data in yoga_renew_pick: {call.data}")
        return

    product = parts[1]
    logger.info(f"User {call.from_user.id} picked new plan: {product}")

    # Получаем информацию о продукте
    product_info = _get_product_info(product, cfg)
    if not product_info:
        await call.answer(
            "Неизвестный тариф. Попробуй выбрать другой.",
            show_alert=True
        )
        return

    # Сохраняем данные в state
    await state.update_data(
        direction="yoga",
        flow="renew_change",
        product=product,
        product_title=product_info["title"],
        amount=product_info["amount"],
    )

    # Показываем выбор способа оплаты
    try:
        await call.message.answer(
            "Выбери способ оплаты 💳",
            reply_markup=payment_method_kb(prefix="yoga")
        )
        await call.answer()
    except Exception as e:
        logger.error(f"Failed to show payment methods: {e}")
        await call.answer("Ошибка показа методов оплаты", show_alert=True)