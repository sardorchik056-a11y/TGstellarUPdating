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
EMOJI_SHOP         = "5447183459602669338"   # 🛒 (магазин/купить)


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
        # Купить (заглушка)
        builder.row(
            InlineKeyboardButton(
                text=f"🛒 Купить — {_fmt(GEAR_SLOTS[slot_key]['price'])} монет",
                callback_data=f"duel_gear_buy:{slot_key}",
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


# ── Заглушки прочих подразделов ──────────────────────────────

def duel_soon_text(section: str) -> str:
    labels = {
        "search":    "Поиск противника",
        "invite":    "Пригласить на поединок",
        "skills":    "Навыки",
        "charstats": "Характеристики",
    }
    name = labels.get(section, section)
    return (
        f'<tg-emoji emoji-id="5424972470023104089">⚔️</tg-emoji> <b>{name}</b>\n\n'
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
