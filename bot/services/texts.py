from __future__ import annotations
from typing import Dict, Any


def format_order_card(direction_title: str, payload: Dict[str, Any], amount: int, currency: str, method: str, user_line: str | None = None) -> str:
    def _humanize_value(v):
        MAP = {
            "abroad": "Жизнь за границей",
            "school": "Школа",
            "travel": "Путешествия",
            "other": "Другое",

            "basic": "Базовый уровень",
            "mid": "Средний уровень",
            "practice": "Говорю, нужна практика",

            "1_2": "1–2 раза в неделю",
            "3_5": "3–5 раз в неделю",
        }
        if isinstance(v, str):
            return MAP.get(v, v)
        return v

    lines = [
        "🧾 *Карточка заказа*",
    ]
    if user_line:
        lines.append(f"Пользователь: *{user_line}*")
    lines.append(f"Направление: *{direction_title}*")

    for k, v in payload.items():
        lines.append(f"{k}: *{_humanize_value(v)}*")
    lines += [
        "",
        f"Сумма: *{amount}* {currency}",
        f"Метод оплаты: *{method}*",
        "",
        "Пользователь отправил подтверждение оплаты (скрин/чек).",
    ]
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
