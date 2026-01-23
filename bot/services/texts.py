from __future__ import annotations
from typing import Dict, Any


from typing import Dict, Any, Optional

def format_order_card(
    direction_title: str,
    payload: Dict[str, Any],
    amount: int,
    currency: str,
    method: str,
    user_line: Optional[str] = None,
) -> str:
    def _humanize(v):
        MAP = {
            # цели
            "abroad": "Жизнь за границей",
            "school": "Школа",
            "travel": "Путешествия",
            "other": "Другое",

            # уровни
            "basic": "Базовый уровень",
            "mid": "Средний уровень",
            "practice": "Говорю, нужна практика",

            # частота
            "1_2": "1–2 раза в неделю",
            "3_5": "3–5 раз в неделю",
        }
        if isinstance(v, str):
            return MAP.get(v, v)
        return v

    lines = []

    lines.append("🧾 <b>Карточка заказа</b>")
    if user_line:
        lines.append(f"👤 <b>Пользователь:</b> {user_line}")
    lines.append(f"📚 <b>Направление:</b> {direction_title}")
    lines.append("")

    # содержимое заказа
    ICONS = {
        "Цель": "🎯",
        "Уровень": "📘",
        "Частота": "⏰",
        "Продукт": "🧩",
        "Тариф": "🧘",
        "Формат": "✨",
        "Сфера": "🔮",
        "План": "🧠",
    }

    for k, v in payload.items():
        icon = ICONS.get(k, "▫️")
        lines.append(f"<b>{icon} *{k}:* {_humanize(v)}</b>")

    lines.append("")
    lines.append(f"💰 <b>*Сумма:* {amount} {currency}</b>")
    lines.append(f"💳 <b>*Способ оплаты:* {method}</b>")
    lines.append("")
    lines.append("<b>📎 Пользователь отправил подтверждение оплаты (скрин/чек)</b>")

    return "\n".join(lines)

def payment_instructions(method: str, currency: str, cfg) -> str:
    if method == "rub_card":
        return (
            "💳 *Оплата переводом на карту (RUB)*\n\n"
            f"{cfg.pay_rub_card_details}\n\n"
            "После оплаты *пришли сюда скриншот/чек*."
        )
    if method == "pix":
        return (
            "🇧🇷 *Оплата Pix*\n\n"
            f"Chave Pix: `{cfg.pay_pix_key}`\n"
            f"Recebedor: *{cfg.pay_pix_receiver_name}*\n\n"
            "После оплаты *пришли сюда скриншот/чек*."
        )
    if method == "crypto":
        return (
            "🪙 *Оплата криптой*\n\n"
            f"Сеть: *{cfg.pay_crypto_network}*\n"
            f"Кошелек: `{cfg.pay_crypto_wallet}`\n\n"
            "После оплаты *пришли сюда скриншот/чек*."
        )
    return "Оплата: неизвестный метод."
