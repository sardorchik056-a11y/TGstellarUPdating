# ============================================================
#  duel.py  —  Раздел Дуэлей TGStellar
#  UI, тексты, клавиатуры.
#  Боевая логика подключается позже.
# ============================================================

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ── Эмодзи ──────────────────────────────────────────────────
EMOJI_BACK         = "5252272671669706296"
EMOJI_DUEL_MAIN    = "5424972470023104089"   # ⚔️
EMOJI_SEARCH       = "5440539497383087970"   # 🔎
EMOJI_INVITE       = "5332724926216428039"   # 👥
EMOJI_EQUIP        = "5445221832074483553"   # 🎒
EMOJI_SKILLS       = "5224607267797606837"   # 🔮
EMOJI_STATS_DUEL   = "5231200819986047254"   # 📊
EMOJI_SHOP         = "5447183459602669338"   # 🛒

EMOJI_HP           = "5262643974912355126"   # ❤️
EMOJI_DMG          = "5262643974912355126"   # ⚔️ урон
EMOJI_REGEN        = "5262643974912355126"   # 💚 восстановление
EMOJI_PHYS_DEF     = "5262643974912355126"   # 🛡️ физ защита
EMOJI_MAG_DEF      = "5262643974912355126"   # 🔮 маг защита
EMOJI_STAMINA      = "5262643974912355126"   # 🔩 стойкость


# ── Каталог снаряжения ───────────────────────────────────────
#  slot → { key, name, emoji_char, emoji_id, price, description }

GEAR_SLOTS = {
    "armor": {
        "key":         "armor",
        "name":        "Латы Воина Бездны",
        "slot_label":  "Броня",
        "emoji_char":  "🛡️",
        "emoji_id":    "5447644880824181073",
        "price":       25_000,
        "description": "Прочнейшие латы, выкованные в недрах тёмных кузниц.\nПоглощают часть урона в каждом бою.",
    },
    "helmet": {
        "key":         "helmet",
        "name":        "Шлем Стального Стража",
        "slot_label":  "Шлем",
        "emoji_char":  "⛑️",
        "emoji_id":    "5445284980978621387",
        "price":       40_000,
        "description": "Закалённый шлем с рунической гравировкой.\nПовышает концентрацию и снижает входящий урон.",
    },
    "gloves": {
        "key":         "gloves",
        "name":        "Наручи Теневого Клинка",
        "slot_label":  "Наручники",
        "emoji_char":  "🥊",
        "emoji_id":    "5445284980978621387",
        "price":       20_000,
        "description": "Боевые наручи с шипами из чёрного железа.\nУскоряют атаку и дают бонус к критическому удару.",
    },
    "pants": {
        "key":         "pants",
        "name":        "Поножи Железного Рыцаря",
        "slot_label":  "Штаны",
        "emoji_char":  "👖",
        "emoji_id":    "5445284980978621387",
        "price":       35_000,
        "description": "Тяжёлые боевые штаны с усиленными бёдрами.\nДают прибавку к выносливости и уклонению.",
    },
    "boots": {
        "key":         "boots",
        "name":        "Сапоги Ветра Пустоши",
        "slot_label":  "Сапоги",
        "emoji_char":  "👢",
        "emoji_id":    "5445284980978621387",
        "price":       15_000,
        "description": "Лёгкие сапоги из кожи горного дракона.\nУвеличивают скорость и шанс первого удара.",
    },
}

GEAR_ORDER = ["armor", "helmet", "gloves", "pants", "boots"]


def _fmt(amount: int) -> str:
    """Форматирует число: 25000 → 25 000."""
    return f"{amount:,}".replace(",", " ")


# ── Текст главного экрана ────────────────────────────────────

def duel_main_text() -> str:
    return (
        '<tg-emoji emoji-id="5424972470023104089">⚔️</tg-emoji> <b>ДУЭЛИ</b>\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        '<blockquote>'
        'Испытай себя в бою один на один.\n'
        'Собери снаряжение, прокачай навыки\n'
        'и докажи, кто сильнейший в TGStellar.'
        '</blockquote>'
    )


# ── Клавиатура главного экрана ───────────────────────────────

def duel_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=" Поиск противника",
            callback_data="duel_search",
            icon_custom_emoji_id=EMOJI_SEARCH,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=" Пригласить на поединок",
            callback_data="duel_invite",
            icon_custom_emoji_id=EMOJI_INVITE,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=" Экипировка",
            callback_data="duel_equip",
            icon_custom_emoji_id=EMOJI_EQUIP,
        ),
        InlineKeyboardButton(
            text=" Навыки",
            callback_data="duel_skills",
            icon_custom_emoji_id=EMOJI_SKILLS,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text=" Характеристики",
            callback_data="duel_charstats",
            icon_custom_emoji_id=EMOJI_STATS_DUEL,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data="back_to_menu",
            icon_custom_emoji_id=EMOJI_BACK,
        )
    )
    return builder.as_markup()


# ── Экипировка: список слотов ────────────────────────────────

def duel_equip_text(user_data: dict) -> str:
    equipped = user_data.get("duel_equipped", {})   # slot → item_key | None
    lines = []
    for slot_key in GEAR_ORDER:
        g    = GEAR_SLOTS[slot_key]
        item = equipped.get(slot_key)
        if item:
            status = f'<b>{g["name"]}</b>'
        else:
            status = '<i>пусто</i>'
        lines.append(f'{g["emoji_char"]} <b>{g["slot_label"]}:</b> {status}')

    slots_block = "\n".join(lines)
    return (
        '<tg-emoji emoji-id="5445221832074483553">🎒</tg-emoji> <b>ЭКИПИРОВКА</b>\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>{slots_block}</blockquote>\n\n'
        'Выбери слот, чтобы купить или сменить предмет.'
    )


def duel_equip_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    # Два слота в ряд, последний — на всю ширину если нечётный
    row_buf = []
    for slot_key in GEAR_ORDER:
        g = GEAR_SLOTS[slot_key]
        row_buf.append(
            InlineKeyboardButton(
                text=f"{g['emoji_char']} {g['slot_label']}",
                callback_data=f"duel_equip_slot:{slot_key}",
            )
        )
        if len(row_buf) == 2:
            builder.row(*row_buf)
            row_buf = []
    if row_buf:
        builder.row(*row_buf)

    builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data="duel_main",
            icon_custom_emoji_id=EMOJI_BACK,
        )
    )
    return builder.as_markup()


# ── Экипировка: карточка конкретного слота ───────────────────

def duel_equip_slot_text(slot_key: str, user_data: dict) -> str:
    g        = GEAR_SLOTS[slot_key]
    equipped = user_data.get("duel_equipped", {})
    owned    = user_data.get("duel_owned_gear", [])
    balance  = user_data.get("balance", 0)

    is_owned    = slot_key in owned
    is_equipped = equipped.get(slot_key) == slot_key

    if is_equipped:
        status_line = '✅ <b>Надето</b>'
    elif is_owned:
        status_line = '📦 <b>Есть в инвентаре</b> (не надето)'
    else:
        status_line = f'💰 <b>Цена:</b> {_fmt(g["price"])} монет'

    return (
        f'{g["emoji_char"]} <b>{g["name"]}</b>\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>{g["description"]}\n\n'
        f'{status_line}</blockquote>'
    )


def duel_equip_slot_keyboard(slot_key: str, user_data: dict) -> InlineKeyboardMarkup:
    owned    = user_data.get("duel_owned_gear", [])
    equipped = user_data.get("duel_equipped", {})
    builder  = InlineKeyboardBuilder()

    is_owned    = slot_key in owned
    is_equipped = equipped.get(slot_key) == slot_key

    if is_equipped:
        # Снять
        builder.row(
            InlineKeyboardButton(
                text="❌ Снять",
                callback_data=f"duel_gear_unequip:{slot_key}",
            )
        )
    elif is_owned:
        # Надеть
        builder.row(
            InlineKeyboardButton(
                text="✅ Надеть",
                callback_data=f"duel_gear_equip:{slot_key}",
            )
        )
    else:
        # Купить и сразу надеть
        builder.row(
            InlineKeyboardButton(
                text=f"🛒 Купить — {_fmt(GEAR_SLOTS[slot_key]['price'])} монет",
                callback_data=f"duel_gear_buy_equip:{slot_key}",
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data="duel_equip",
            icon_custom_emoji_id=EMOJI_BACK,
        )
    )
    return builder.as_markup()


# ── Хелпер: купить и сразу надеть ───────────────────────────

def apply_gear_purchase(slot_key: str, user_data: dict) -> dict:
    """
    Вызывается после успешного списания монет.
    Добавляет предмет в инвентарь и сразу надевает его.
    Возвращает обновлённый user_data (изменяет и на месте).

    Пример использования в хендлере duel_gear_buy_equip:{slot_key}:

        slot_key = callback.data.split(":")[1]
        g = GEAR_SLOTS[slot_key]
        if user_data["balance"] < g["price"]:
            # недостаточно монет
            ...
        else:
            deduct_balance(user_id, g["price"])
            apply_gear_purchase(slot_key, user_data)
            save_user_data(user_id, user_data)
            # показать обновлённую карточку слота
            await callback.message.edit_text(
                duel_equip_slot_text(slot_key, user_data),
                reply_markup=duel_equip_slot_keyboard(slot_key, user_data),
            )
    """
    owned    = user_data.setdefault("duel_owned_gear", [])
    equipped = user_data.setdefault("duel_equipped", {})

    if slot_key not in owned:
        owned.append(slot_key)

    equipped[slot_key] = slot_key   # надеваем сразу
    return user_data


# ── Характеристики ───────────────────────────────────────────

# Базовые значения (без снаряжения)
BASE_STATS = {
    "hp":       100,
    "dmg":      15,
    "regen":    5,
    "phys_def": 10,
    "mag_def":  10,
    "stamina":  20,
}

# Бонусы от каждого предмета снаряжения
GEAR_STAT_BONUS = {
    "armor":   {"hp": 40,  "phys_def": 20},
    "helmet":  {"hp": 25,  "mag_def": 15,  "stamina": 10},
    "gloves":  {"dmg": 10, "stamina": 5},
    "pants":   {"hp": 20,  "stamina": 15,  "phys_def": 5},
    "boots":   {"dmg": 5,  "regen": 5},
}


def _calc_stats(user_data: dict) -> dict:
    """Считает итоговые характеристики с учётом надетого снаряжения."""
    equipped = user_data.get("duel_equipped", {})
    stats    = dict(BASE_STATS)
    for slot_key in equipped.values():
        for stat, bonus in GEAR_STAT_BONUS.get(slot_key, {}).items():
            stats[stat] = stats.get(stat, 0) + bonus
    return stats


def duel_charstats_text(user_data: dict) -> str:
    s        = _calc_stats(user_data)
    equipped = user_data.get("duel_equipped", {})
    gear_count = len(equipped)

    gear_line = (
        f"надето {gear_count}/5 предм."
        if gear_count else "снаряжение не надето"
    )

    return (
        f'<tg-emoji emoji-id="{EMOJI_STATS_DUEL}">📊</tg-emoji> '
        f'<b>ХАРАКТЕРИСТИКИ</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>'
        f'<tg-emoji emoji-id="{EMOJI_HP}">❤️</tg-emoji> '
        f'<b>Очки здоровья</b> — <b>{s["hp"]}</b> HP\n\n'
        f'<tg-emoji emoji-id="{EMOJI_DMG}">⚔️</tg-emoji> '
        f'<b>Средний урон</b> — <b>{s["dmg"]}</b> ATK\n\n'
        f'<tg-emoji emoji-id="{EMOJI_REGEN}">💚</tg-emoji> '
        f'<b>Восстановление</b> — <b>{s["regen"]}</b> HP/ход\n\n'
        f'<tg-emoji emoji-id="{EMOJI_PHYS_DEF}">🛡️</tg-emoji> '
        f'<b>Физ. защита</b> — <b>{s["phys_def"]}</b> DEF\n\n'
        f'<tg-emoji emoji-id="{EMOJI_MAG_DEF}">🔮</tg-emoji> '
        f'<b>Маг. защита</b> — <b>{s["mag_def"]}</b> MDEF\n\n'
        f'<tg-emoji emoji-id="{EMOJI_STAMINA}">⚙️</tg-emoji> '
        f'<b>Стойкость</b> — <b>{s["stamina"]}</b> STM'
        f'</blockquote>\n\n'
        f'🎽 <i>Снаряжение: {gear_line}</i>'
    )


def duel_charstats_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Экипировка",
            callback_data="duel_equip",
            icon_custom_emoji_id=EMOJI_EQUIP,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data="duel_main",
            icon_custom_emoji_id=EMOJI_BACK,
        )
    )
    return builder.as_markup()


# ── Заглушки прочих подразделов ──────────────────────────────

def duel_soon_text(section: str) -> str:
    labels = {
        "search": "Поиск противника",
        "invite": "Пригласить на поединок",
        "skills": "Навыки",
    }
    name = labels.get(section, section)
    return (
        f'<tg-emoji emoji-id="{EMOJI_DUEL_MAIN}">⚔️</tg-emoji> <b>{name}</b>\n\n'
        '<blockquote>🚧 Раздел в разработке.\nСкоро будет доступен!</blockquote>'
    )


def duel_back_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data="duel_main",
            icon_custom_emoji_id=EMOJI_BACK,
        )
    )
    return builder.as_markup()
