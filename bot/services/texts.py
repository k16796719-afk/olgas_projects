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

    def _humanize_astro_sphere(v):
        MAP = {
            "self": "Я и моя личность",
            "money": "Деньги, мои ресурсы",
            "edu": "Учёба",
            "family": "Семья, корни",
            "kids": "Творчество",
            "health": "Здоровье",

            "sex": "Партнёрство",
            "crisis": "Кризисы",
            "travel": "Путешествия",
            "career": "Карьера",
            "friends": "Сообщества и друзья",
            "spirit": "Подсознание и духовность",
        }

        if isinstance(v, str):
            return MAP.get(v, v)
        return v

    direction = payload.get("direction")

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
#        "Сфера": "🔮",
        "План": "🧠",
    }

    for k, v in payload.items():
        if k == "Сфера":
            continue
        icon = ICONS.get(k, "▫️")
        lines.append(f"<b>{icon} {k}: {_humanize(v)}</b>")

    sphere_key = payload.get("Сфера")  # <-- а не "sphere"
    if sphere_key:
        sphere = _humanize_astro_sphere(sphere_key)
        lines.append(f"🔮 <b>Сфера:</b> {sphere}")

    lines.append("")
    lines.append(f"💰 <b>Сумма: {amount} RUB </b>")
    lines.append(f"💳 <b>Способ оплаты: {method}</b>")
    lines.append("")
    lines.append("<b>📎 Пользователь отправил подтверждение оплаты (скрин/чек)</b>")

    return "\n".join(lines)

def payment_instructions(method: str, currency: str, cfg) -> str:
    if method == "rub_card":
        owner_line = ""
        if cfg.pay_rub_card_owner:
            owner_line = f"\n👤 <b>Владелец карты:</b> {cfg.pay_rub_card_owner}"
        return (
            "💳 *Оплата переводом на карту (RUB)*\n\n"
            f"{cfg.pay_rub_card_details}\n\n"
            f"{owner_line}\n\n"
            "После оплаты *пришли сюда скриншот/чек (только JPG)*."
        )
    if method == "pix":
        return (
            "🇧🇷 *Оплата Pix*\n\n"
            f"Chave Pix: `{cfg.pay_pix_key}`\n"
            f"*{cfg.pay_pix_receiver_name}*\n\n"
            "После оплаты *пришли сюда скриншот/чек (только JPG)*."
        )
    if method == "crypto":
        return (
            "🪙 *Оплата криптой*\n\n"
            f"Сеть: *{cfg.pay_crypto_network}*\n"
            f"Кошелек: `{cfg.pay_crypto_wallet}`\n\n"
            "После оплаты *пришли сюда скриншот/чек (только JPG)*."
        )
    return "Оплата: неизвестный метод."
