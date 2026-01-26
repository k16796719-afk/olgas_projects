from __future__ import annotations
from typing import Dict, Any


from typing import Dict, Any, Optional

from typing import Dict, Any, Optional

def format_order_card(
    direction_title: str,
    payload: Dict[str, Any],
    amount: int,
    currency: str,   # оставляем аргумент, но в выводе пока всегда RUB
    method: str,
    user_line: Optional[str] = None,
) -> str:
    def _humanize_lang(v):
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
        return MAP.get(v, v) if isinstance(v, str) else v

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
        return MAP.get(v, v) if isinstance(v, str) else v

    def _add_line(lines, icon: str, title: str, value: Any, humanize_fn=None):
        if value is None or value == "":
            return
        if humanize_fn:
            value = humanize_fn(value)
        lines.append(f"{icon} <b>{title}:</b> {value}")

    # определяем направление (лучше передавать отдельно, но раз уже в payload бывает)
    direction = payload.get("direction")  # например "astro" / "english" / "yoga"
    # если direction не кладёшь в payload — ок, тогда сфера/цель и т.д. всё равно обработается по наличию ключей

    lines: list[str] = []
    lines.append("🧾 <b>Карточка заказа</b>")
    if user_line:
        lines.append(f"👤 <b>Пользователь:</b> {user_line}")
    lines.append(f"📚 <b>Направление:</b> {direction_title}")
    lines.append("")

    # ======= АСТРОЛОГИЯ =======
    if direction == "astro" or "sphere" in payload:
        _add_line(lines, "🔮", "Сфера", payload.get("sphere"), humanize_fn=_humanize_astro_sphere)
        _add_line(lines, "✨", "Формат", payload.get("format"))
        # если у тебя есть ещё поля астрологии — добавляй сюда явно

    # ======= ЯЗЫКИ (EN / CN) =======
    elif direction in ("english", "chinese") or ("goal" in payload or "level" in payload or "freq" in payload):
        _add_line(lines, "🎯", "Цель", payload.get("goal"), humanize_fn=_humanize_lang)
        _add_line(lines, "📘", "Уровень", payload.get("level"), humanize_fn=_humanize_lang)
        _add_line(lines, "⏰", "Частота", payload.get("freq"), humanize_fn=_humanize_lang)
        _add_line(lines, "🧩", "Продукт", payload.get("product"))
        # если у тебя product хранится как trial/single/pack10, можно сделать отдельный humanize при желании

    # ======= ЙОГА =======
    elif direction == "yoga" or ("tariff" in payload or "plan" in payload):
        _add_line(lines, "🧘", "Тариф", payload.get("tariff") or payload.get("plan"))
        _add_line(lines, "✨", "Формат", payload.get("format"))

    # ======= ПРОЧЕЕ (fallback) =======
    else:
        # На случай если payload неожиданный: покажем только безопасные/понятные поля
        _add_line(lines, "✨", "Формат", payload.get("format"))
        _add_line(lines, "🧩", "Продукт", payload.get("product"))

    lines.append("")
    lines.append(f"💰 <b>Сумма:</b> {amount} RUB")
    lines.append(f"💳 <b>Способ оплаты:</b> {method}")
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
            "После оплаты *пришли сюда скриншот/чек*."
        )
    if method == "pix":
        return (
            "🇧🇷 *Оплата Pix*\n\n"
            f"Chave Pix: `{cfg.pay_pix_key}`\n"
            f"*{cfg.pay_pix_receiver_name}*\n\n"
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
