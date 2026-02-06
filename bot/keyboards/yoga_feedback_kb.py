# keyboards/yoga_feedback_kb.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def kb(options: list[str], prefix: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=o, callback_data=f"{prefix}:{o}")]
            for o in options
        ]
    )

difficulty_kb = kb(
    ["Лёгкие", "Средние", "Сложные"], "yf_q1"
)

tempo_kb = kb(
    ["Медленный", "Комфортный", "Быстрый"], "yf_q2"
)

feelings_kb = kb(
    ["Расслабленно", "В балансе", "Заряженно"], "yf_q3"
)

format_kb = kb(
    ["Групповой", "Индивидуальный"], "yf_q4"
)

freq_kb = kb(
    ["4 раза в месяц", "8 раз в месяц", "10 практик 1-1"], "yf_q5"
)

types_kb = kb(
    [
        "🧘‍♀️ Мягкая йога и растяжка",
        "🔥 Силовая йога / тонус",
        "🌿 Расслабление и дыхание"
    ],
    "yf_q6"
)
