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
        [InlineKeyboardButton(text="🌍 Жизнь за границей", callback_data="lg_goal:abroad")],
        [InlineKeyboardButton(text="📝 Школа", callback_data="lg_goal:school")],
        [InlineKeyboardButton(text="✈️ Путешествия", callback_data="lg_goal:travel")],
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

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# проверь, что эти константы у тебя совпадают
D_ENGLISH = "english"
D_CHINESE = "chinese"

def lang_product_kb(cfg, direction: str) -> InlineKeyboardMarkup:
    p = cfg.prices

    if direction == D_ENGLISH:
        trial = p.trial_rub
        single = p.en_lesson_rub
        pack10 = p.en_pack10_rub
        flag = "🇺🇸"
    else:  # китайский
        trial = p.trial_china_rub
        single = p.china_lesson_rub
        pack10 = p.china_pack10_rub
        flag = "🇨🇳"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{flag} Пробное 30 мин - {trial}₽", callback_data="lg_prod:trial")],
        [InlineKeyboardButton(text=f"{flag} 1 занятие - {single}₽", callback_data="lg_prod:single")],
        [InlineKeyboardButton(text=f"{flag} 10 занятий (пакет) - {pack10}₽", callback_data="lg_prod:pack10")],
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu")],
    ])


def yoga_plan_kb(cfg) -> InlineKeyboardMarkup:
    p = cfg.prices

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"4 практики /месяц - {p.yoga_4_rub}₽", callback_data="y_plan:yoga_4")],
        [InlineKeyboardButton(text=f"8 практик /месяц - {p.yoga_8_rub}₽", callback_data="y_plan:yoga_8")],
        [InlineKeyboardButton(text=f"1-1 10 практик /месяц - {p.yoga_10ind_rub}₽", callback_data="y_plan:yoga_10_individual")],
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu")],
    ])

def astrology_spheres_kb() -> InlineKeyboardMarkup:
    spheres = [
        ("Я и моя личность", "self"),
        ("Деньги, мои ресурсы", "money"),
        ("Учеба", "edu"),
        ("Семья, корни", "family"),
        ("Творчество ", "kids"),
        ("Здоровье", "health"),

        ("Партнерство", "sex"),
        ("Кризисы", "crisis"),
        ("Путешествия", "travel"),
        ("Карьера", "career"),
        ("Сообщества - друзья", "friends"),
        ("Подсознание и духовность", "spirit"),
    ]
    rows = []
    for i in range(0, len(spheres), 2):
        row = [InlineKeyboardButton(text=spheres[i][0], callback_data=f"as_sphere:{spheres[i][1]}")]
        if i+1 < len(spheres):
            row.append(InlineKeyboardButton(text=spheres[i+1][0], callback_data=f"as_sphere:{spheres[i+1][1]}"))
        rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def astrology_format_kb(cfg) -> InlineKeyboardMarkup:
    p = cfg.prices
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Разбор 1 сферы - {p.astro_1_rub}₽", callback_data="as_fmt:one")],
        [InlineKeyboardButton(text=f"Натальная карта полностью - {p.astro_full_rub}₽", callback_data="as_fmt:full")],
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu")],
    ])

def mentoring_kb(cfg) -> InlineKeyboardMarkup:
    p = cfg.prices
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"1 неделя - {p.mentor_week_rub}₽", callback_data="m_plan:week")],
        [InlineKeyboardButton(text=f"1 месяц - {p.mentor_month_rub}₽", callback_data="m_plan:month")],
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

def payment_wait_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔁 Изменить способ оплаты", callback_data=f"pay_change:{order_id}")],
        [InlineKeyboardButton(text="❌ Отменить заказ", callback_data=f"order_cancel:{order_id}")],
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu")],
    ])


def yoga_renew_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить (продлить)", callback_data="yoga_renew:pay")],
        [InlineKeyboardButton(text="🔁 Сменить тариф", callback_data="yoga_renew:change")],
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu")],
    ])

def yoga_change_plan_kb(cfg) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🧘 4 практики — {cfg.prices.yoga_4_rub} RUB", callback_data="yoga_renew_pick:yoga_4")],
        [InlineKeyboardButton(text=f"🧘‍♀️ 8 практик — {cfg.prices.yoga_8_rub} RUB", callback_data="yoga_renew_pick:yoga_8")],
        [InlineKeyboardButton(text=f"🧘‍ 1-1 10 практик /месяц - {cfg.prices.yoga_10ind_rub}₽", callback_data="yoga_renew_pick:yoga_10_individual")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="yoga_renew:back")],
    ])