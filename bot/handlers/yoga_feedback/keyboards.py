from __future__ import annotations
from aiogram.utils.keyboard import InlineKeyboardBuilder
from .callbacks import YF

def kb_start_survey(subscription_id: int) -> InlineKeyboardBuilder:
    b = InlineKeyboardBuilder()
    b.button(
        text="📝 Начать опрос",
        callback_data=YF(
            action="start",
            q=0,
            v=str(subscription_id)
        ).pack()
    )
    b.adjust(1)
    return b

def kb_single_choice(q: int, options: list[tuple[str, str]]) -> InlineKeyboardBuilder:
    b = InlineKeyboardBuilder()
    for text, v in options:
        b.button(text=f"▫️ {text}", callback_data=YF(action="a", q=q, v=v).pack())
    b.button(text="⏭ Пропустить", callback_data=YF(action="skip", q=q).pack())
    b.adjust(1)
    return b

def kb_q6_multi(selected: set[str], options: list[tuple[str, str]]) -> InlineKeyboardBuilder:
    b = InlineKeyboardBuilder()
    for text, v in options:
        mark = "✅ " if v in selected else ""
        b.button(text=f"{mark}{text}", callback_data=YF(action="toggle6", q=6, v=v).pack())
    b.button(text="Готово", callback_data=YF(action="done6", q=6).pack())
    b.button(text="⏭ Пропустить", callback_data=YF(action="skip", q=6).pack())
    b.adjust(1)
    return b

def kb_renew() -> InlineKeyboardBuilder:
    b = InlineKeyboardBuilder()
    b.button(text="💳 Продлить участие", callback_data=YF(action="renew").pack())
    b.adjust(1)
    return b
