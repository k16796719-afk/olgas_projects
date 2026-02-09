from __future__ import annotations

import logging
from html import escape
from typing import Optional

from aiogram import Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from bot.states.states import YogaFlow
from bot.keyboards.keyboards import yoga_plan_kb, payment_method_kb
from bot.constants import D_YOGA, YOGA_4, YOGA_8, YOGA_10IND

logger = logging.getLogger(__name__)
router = Router()

# Константы для продуктов йоги (единый источник истины)
YOGA_PRODUCTS = {
    YOGA_4: {
        "title": "Йога: 4 практики / месяц",
        "price_attr": "yoga_4_rub",
    },
    YOGA_8: {
        "title": "Йога: 8 практик / месяц",
        "price_attr": "yoga_8_rub",
    },
    YOGA_10IND: {
        "title": "Йога: 1-1 10 практик / месяц",
        "price_attr": "yoga_10ind_rub",
    },
}

# Ограничения
MAX_INTRO_TEXT_LENGTH = 4000  # Максимальная длина текста знакомства


def _parse_callback_data(callback_data: str, separator: str = ":", max_split: int = 1) -> Optional[list[str]]:
    """Безопасно распарсить callback_data."""
    try:
        parts = callback_data.split(separator, max_split)
        if len(parts) == max_split + 1:
            return parts
    except Exception as e:
        logger.error(f"Failed to parse callback_data '{callback_data}': {e}")
    return None


def _get_product_info(plan: str, cfg) -> Optional[dict]:
    """
    Получить информацию о продукте йоги.

    Args:
        plan: Код плана (YOGA_4, YOGA_8, YOGA_10IND)
        cfg: Конфигурация с ценами

    Returns:
        dict с ключами 'amount' и 'title' или None если план неизвестен
    """
    product_config = YOGA_PRODUCTS.get(plan)
    if not product_config:
        logger.error(f"Unknown yoga plan: {plan}")
        return None

    try:
        price_attr = product_config["price_attr"]
        amount = int(getattr(cfg.prices, price_attr, 0))

        if amount <= 0:
            logger.error(f"Invalid price for plan {plan}: {amount}")
            return None

        return {
            "amount": amount,
            "title": product_config["title"],
        }
    except (AttributeError, ValueError, TypeError) as e:
        logger.error(f"Failed to get price for plan {plan}: {e}")
        return None


async def _notify_admins_intro(
        bot,
        admin_ids: list[int],
        user_name: str,
        user_tag: str,
        user_id: int,
        plan: str,
        payment_id: int,
        intro_text: str
) -> bool:
    """
    Отправить текст знакомства всем админам.

    Returns:
        True если хотя бы одному админу отправлено, False если всем не удалось
    """
    # Формируем сообщение с HTML-escape
    text_to_admins = (
        "🧘‍♀️ <b>Йога: ответы на знакомство</b>\n"
        f"👤 <b>Пользователь:</b> {user_name}"
        f"{' (' + user_tag + ')' if user_tag else ''}\n"
        f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
        f"🧾 <b>Тариф:</b> {escape(str(plan))} занятий/мес\n"
        f"💳 <b>Payment ID:</b> <code>{payment_id}</code>\n\n"
        f"📝 <b>Ответ:</b>\n{escape(intro_text)}"
    )

    success_count = 0

    for admin_id in admin_ids:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=text_to_admins,
                parse_mode="HTML"
            )
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to send intro to admin {admin_id}: {e}")

    if success_count == 0:
        logger.error("Failed to send intro to all admins")
        return False

    logger.info(
        f"Intro from user {user_id} sent to {success_count}/{len(admin_ids)} admins"
    )
    return True


@router.callback_query(lambda c: c.data == "dir:yoga")
async def yoga_start(call: CallbackQuery, state: FSMContext, cfg):
    """Начать процесс выбора йога-подписки."""
    await state.clear()
    await state.update_data(direction=D_YOGA)
    await state.set_state(YogaFlow.plan)

    try:
        await call.message.edit_text(
            "Выбери абонемент йоги:",
            reply_markup=yoga_plan_kb(cfg)
        )
        await call.answer()
    except Exception as e:
        logger.error(f"Failed to edit message in yoga_start: {e}")
        # Пытаемся отправить новым сообщением
        try:
            await call.message.answer(
                "Выбери абонемент йоги:",
                reply_markup=yoga_plan_kb(cfg)
            )
            await call.answer()
        except Exception as e2:
            logger.error(f"Failed to send message in yoga_start: {e2}")
            await call.answer("Ошибка загрузки планов", show_alert=True)


@router.callback_query(YogaFlow.plan, lambda c: c.data.startswith("y_plan:"))
async def yoga_plan(call: CallbackQuery, state: FSMContext, cfg):
    """Обработать выбор плана йоги."""
    # Безопасно парсим callback_data
    parts = _parse_callback_data(call.data, ":", 1)
    if not parts or len(parts) != 2:
        await call.answer("Ошибка формата данных", show_alert=True)
        logger.warning(f"Invalid callback_data in yoga_plan: {call.data}")
        return

    plan = parts[1]
    logger.info(f"User {call.from_user.id} selected yoga plan: {plan}")

    # Получаем информацию о продукте
    product_info = _get_product_info(plan, cfg)
    if not product_info:
        await call.answer(
            "Неизвестный план. Попробуй выбрать другой.",
            show_alert=True
        )
        return

    amount = product_info["amount"]
    title = product_info["title"]

    # Сохраняем данные в state
    await state.update_data(
        yoga_plan=plan,
        product=plan,  # для совместимости с другими модулями
        product_title=title,
        amount=amount
    )
    await state.set_state(YogaFlow.payment)

    # Отправляем сообщение с выбором способа оплаты
    payment_text = (
        f"*{title}*\n"
        f"Сумма: *{amount}* RUB\n\n"
        f"Выбери метод оплаты:"
    )

    try:
        await call.message.edit_text(
            payment_text,
            reply_markup=payment_method_kb("yoga"),
            parse_mode="Markdown"
        )
        await call.answer()
    except Exception as e:
        logger.error(f"Failed to edit message in yoga_plan: {e}")
        # Пытаемся отправить новым сообщением
        try:
            await call.message.answer(
                payment_text,
                reply_markup=payment_method_kb("yoga"),
                parse_mode="Markdown"
            )
            await call.answer()
        except Exception as e2:
            logger.error(f"Failed to send message in yoga_plan: {e2}")
            await call.answer("Ошибка отображения", show_alert=True)


@router.message(
    StateFilter(YogaFlow.wait_intro),
    lambda m: m.text is not None and m.chat.type == "private"
)
async def yoga_intro_catcher(message: Message, state: FSMContext, db, cfg, bot):
    """
    Получить текст знакомства от пользователя и отправить админам.

    Этот хендлер срабатывает только в состоянии YogaFlow.wait_intro
    для приватных чатов с текстовыми сообщениями.
    """
    # Получаем данные из state
    data = await state.get_data()
    plan = data.get("yoga_intro_plan")
    payment_id = data.get("yoga_intro_payment_id")

    # Валидация данных
    if not plan or not payment_id:
        logger.warning(
            f"Missing plan or payment_id in state for user {message.from_user.id}"
        )
        await message.answer(
            "Произошла ошибка. Данные о заказе потеряны. "
            "Пожалуйста, обратись к администратору."
        )
        await state.clear()
        return

    # Получаем данные пользователя
    u = message.from_user
    user_name = escape(u.full_name or "Без имени")
    user_tag = f"@{u.username}" if u.username else ""
    user_id = u.id

    # Проверяем длину текста
    intro_text = message.text
    if len(intro_text) > MAX_INTRO_TEXT_LENGTH:
        logger.warning(
            f"User {user_id} sent intro text longer than {MAX_INTRO_TEXT_LENGTH} chars: "
            f"{len(intro_text)} chars"
        )
        intro_text = intro_text[:MAX_INTRO_TEXT_LENGTH] + "... (обрезано)"

    # Отправляем админам
    admins_notified = await _notify_admins_intro(
        bot=bot,
        admin_ids=cfg.admin_ids,
        user_name=user_name,
        user_tag=user_tag,
        user_id=user_id,
        plan=plan,
        payment_id=payment_id,
        intro_text=intro_text
    )

    if not admins_notified:
        logger.error(
            f"Failed to notify any admin about intro from user {user_id}, "
            f"payment {payment_id}"
        )
        await message.answer(
            "Спасибо! Я попытаюсь передать твои ответы Ольге, "
            "но возникла техническая проблема. "
            "Если долго не будет ответа — напиши администратору напрямую."
        )
    else:
        await message.answer("Спасибо! Я передала ваши ответы Ольге 🤍")

    # Логируем завершение
    logger.info(
        f"User {user_id} submitted yoga intro for plan {plan}, "
        f"payment {payment_id}. Admins notified: {admins_notified}"
    )

    # Очищаем state
    await state.clear()