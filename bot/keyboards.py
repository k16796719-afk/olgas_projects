from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇸 Английский", callback_data="dir:english")],
        [InlineKeyboardButton(text="🇨🇳 Китайский", callback_data="dir:chinese")],
        [InlineKeyboardButton(text="🧘‍♀️ Йога", callback_data="dir:yoga")],
        [InlineKeyboardButton(text="✨ Астрология", callback_data="dir:astrology")],
        [InlineKeyboardButton(text="🧠 Менторство", callback_data="dir:mentoring")],
    ])

def back_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu")]
    ])

def lang_goal_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Жизнь за границей", callback_data="lg_goal:abroad")],
        [InlineKeyboardButton(text="Школа", callback_data="lg_goal:school")],
        [InlineKeyboardButton(text="Путешествия", callback_data="lg_goal:travel")],
        [InlineKeyboardButton(text="Другое", callback_data="lg_goal:other")],
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu")],
    ])

def lang_level_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Базовый уровень", callback_data="lg_level:basic")],
        [InlineKeyboardButton(text="Средний уровень", callback_data="lg_level:mid")],
        [InlineKeyboardButton(text="Говорю, нужна практика", callback_data="lg_level:practice")],
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu")],
    ])

def lang_freq_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1-2 раза в неделю", callback_data="lg_freq:1_2")],
        [InlineKeyboardButton(text="3-5 раз в неделю", callback_data="lg_freq:3_5")],
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu")],
    ])

def lang_product_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пробное 30 мин (1500₽)", callback_data="lg_prod:trial")],
        [InlineKeyboardButton(text="10 занятий (пакет)", callback_data="lg_prod:pack10")],
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu")],
    ])

def yoga_plan_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="4 практики / мес", callback_data="y_plan:yoga_4")],
        [InlineKeyboardButton(text="8 практик / мес", callback_data="y_plan:yoga_8")],
        [InlineKeyboardButton(text="Индивидуально 10 / мес", callback_data="y_plan:yoga_10_individual")],
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu")],
    ])

def astrology_spheres_kb() -> InlineKeyboardMarkup:
    spheres = [
        ("Саморазвитие", "self"),
        ("Предназначение", "purpose"),
        ("Карьера", "career"),
        ("Финансы", "money"),
        ("Дети", "kids"),
        ("Отношения", "relations"),
        ("Секс", "sex"),
        ("Любовь", "love"),
        ("Здоровье", "health"),
        ("Коммуникации", "comm"),
        ("Путешествия", "travel"),
        ("Образование", "edu"),
    ]
    rows = []
    for i in range(0, len(spheres), 2):
        row = [InlineKeyboardButton(text=spheres[i][0], callback_data=f"as_sphere:{spheres[i][1]}")]
        if i+1 < len(spheres):
            row.append(InlineKeyboardButton(text=spheres[i+1][0], callback_data=f"as_sphere:{spheres[i+1][1]}"))
        rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def astrology_format_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Разбор 1 сферы (1500₽)", callback_data="as_fmt:one")],
        [InlineKeyboardButton(text="Натальная карта полностью (18000₽)", callback_data="as_fmt:full")],
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu")],
    ])

def mentoring_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 неделя (25 000₽)", callback_data="m_plan:week")],
        [InlineKeyboardButton(text="1 месяц (100 000₽)", callback_data="m_plan:month")],
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu")],
    ])

def payment_method_kb(prefix: str) -> InlineKeyboardMarkup:
    # prefix should encode what we are paying for in state, but callback only chooses method
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Рубли (перевод на карту)", callback_data=f"pay_m:{prefix}:rub_card")],
        [InlineKeyboardButton(text="🇧🇷 Pix", callback_data=f"pay_m:{prefix}:pix")],
        [InlineKeyboardButton(text="🪙 Крипта", callback_data=f"pay_m:{prefix}:crypto")],
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu")],
    ])

def admin_approve_kb(payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"adm_ok:{payment_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_no:{payment_id}"),
        ]
    ])
