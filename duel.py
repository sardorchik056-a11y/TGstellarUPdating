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

EMOJI_HP           = "5262643974912355126"
EMOJI_DMG          = "5262643974912355126"
EMOJI_REGEN        = "5262643974912355126"
EMOJI_PHYS_DEF     = "5262643974912355126"
EMOJI_MAG_DEF      = "5262643974912355126"
EMOJI_STAMINA      = "5262643974912355126"


# ── Каталог снаряжения: 5 слотов × 5 уровней ────────────────
#
#  Ключ предмета: "{slot}-lvl{n}"  (например "helmet-lvl3")
#  user_data["duel_equipped"]   = { slot_key: "helmet-lvl2", ... }
#  user_data["duel_owned_gear"] = ["helmet-lvl1", "helmet-lvl2", ...]

GEAR_CATALOG = {

    # ── ШЛЕМ ─────────────────────────────────────────────────
    "helmet-lvl1": {
        "slot":        "helmet",
        "level":       1,
        "key":         "helmet-lvl1",
        "name":        "Helmet Lvl 1",
        "ru_name":     "Боевой Шлем I",
        "slot_label":  "Шлем",
        "emoji_char":  "⛑️",
        "emoji_id":    "5445284980978621387",
        "price":       5_000,
        "description": "Простой железный шлем. Базовая защита головы.",
        "bonus":       {"hp": 10, "phys_def": 3},
    },
    "helmet-lvl2": {
        "slot":        "helmet",
        "level":       2,
        "key":         "helmet-lvl2",
        "name":        "Helmet Lvl 2",
        "ru_name":     "Боевой Шлем II",
        "slot_label":  "Шлем",
        "emoji_char":  "⛑️",
        "emoji_id":    "5445284980978621387",
        "price":       15_000,
        "description": "Усиленный шлем с рунической вставкой. Защищает от магии.",
        "bonus":       {"hp": 20, "phys_def": 6, "mag_def": 5},
    },
    "helmet-lvl3": {
        "slot":        "helmet",
        "level":       3,
        "key":         "helmet-lvl3",
        "name":        "Helmet Lvl 3",
        "ru_name":     "Боевой Шлем III",
        "slot_label":  "Шлем",
        "emoji_char":  "⛑️",
        "emoji_id":    "5445284980978621387",
        "price":       35_000,
        "description": "Закалённый шлем гвардейца. Значительно повышает выносливость.",
        "bonus":       {"hp": 35, "phys_def": 10, "mag_def": 8, "stamina": 5},
    },
    "helmet-lvl4": {
        "slot":        "helmet",
        "level":       4,
        "key":         "helmet-lvl4",
        "name":        "Helmet Lvl 4",
        "ru_name":     "Боевой Шлем IV",
        "slot_label":  "Шлем",
        "emoji_char":  "⛑️",
        "emoji_id":    "5445284980978621387",
        "price":       70_000,
        "description": "Шлем Стального Стража с рунической гравировкой. Снижает входящий урон.",
        "bonus":       {"hp": 50, "phys_def": 15, "mag_def": 12, "stamina": 10},
    },
    "helmet-lvl5": {
        "slot":        "helmet",
        "level":       5,
        "key":         "helmet-lvl5",
        "name":        "Helmet Lvl 5",
        "ru_name":     "Шлем Легенды",
        "slot_label":  "Шлем",
        "emoji_char":  "⛑️",
        "emoji_id":    "5445284980978621387",
        "price":       150_000,
        "description": "Реликвия древних воинов. Дарует непоколебимую концентрацию в бою.",
        "bonus":       {"hp": 75, "phys_def": 22, "mag_def": 18, "stamina": 18},
    },

    # ── БРОНЯ ─────────────────────────────────────────────────
    "armor-lvl1": {
        "slot":        "armor",
        "level":       1,
        "key":         "armor-lvl1",
        "name":        "Armor Lvl 1",
        "ru_name":     "Кожаный Доспех I",
        "slot_label":  "Броня",
        "emoji_char":  "🛡️",
        "emoji_id":    "5447644880824181073",
        "price":       6_000,
        "description": "Лёгкий кожаный доспех. Не сковывает движений.",
        "bonus":       {"hp": 15, "phys_def": 5},
    },
    "armor-lvl2": {
        "slot":        "armor",
        "level":       2,
        "key":         "armor-lvl2",
        "name":        "Armor Lvl 2",
        "ru_name":     "Кольчужный Доспех II",
        "slot_label":  "Броня",
        "emoji_char":  "🛡️",
        "emoji_id":    "5447644880824181073",
        "price":       18_000,
        "description": "Кольчуга из закалённых колец. Хорошо поглощает удары.",
        "bonus":       {"hp": 30, "phys_def": 12, "stamina": 5},
    },
    "armor-lvl3": {
        "slot":        "armor",
        "level":       3,
        "key":         "armor-lvl3",
        "name":        "Armor Lvl 3",
        "ru_name":     "Пластинчатый Доспех III",
        "slot_label":  "Броня",
        "emoji_char":  "🛡️",
        "emoji_id":    "5447644880824181073",
        "price":       40_000,
        "description": "Боевые латы с усиленными пластинами. Надёжная защита торса.",
        "bonus":       {"hp": 50, "phys_def": 20, "stamina": 8},
    },
    "armor-lvl4": {
        "slot":        "armor",
        "level":       4,
        "key":         "armor-lvl4",
        "name":        "Armor Lvl 4",
        "ru_name":     "Латы Воина Бездны IV",
        "slot_label":  "Броня",
        "emoji_char":  "🛡️",
        "emoji_id":    "5447644880824181073",
        "price":       80_000,
        "description": "Прочнейшие латы, выкованные в тёмных кузницах. Поглощают часть урона.",
        "bonus":       {"hp": 75, "phys_def": 30, "mag_def": 8, "stamina": 12},
    },
    "armor-lvl5": {
        "slot":        "armor",
        "level":       5,
        "key":         "armor-lvl5",
        "name":        "Armor Lvl 5",
        "ru_name":     "Латы Абсолюта",
        "slot_label":  "Броня",
        "emoji_char":  "🛡️",
        "emoji_id":    "5447644880824181073",
        "price":       180_000,
        "description": "Доспех, не знающий поражений. Максимальная физическая защита.",
        "bonus":       {"hp": 110, "phys_def": 45, "mag_def": 15, "stamina": 20},
    },

    # ── ПЕРЧАТКИ ──────────────────────────────────────────────
    "gloves-lvl1": {
        "slot":        "gloves",
        "level":       1,
        "key":         "gloves-lvl1",
        "name":        "Gloves Lvl 1",
        "ru_name":     "Боевые Рукавицы I",
        "slot_label":  "Перчатки",
        "emoji_char":  "🥊",
        "emoji_id":    "5445284980978621387",
        "price":       4_000,
        "description": "Простые кожаные рукавицы. Слегка усиливают удар.",
        "bonus":       {"dmg": 4, "stamina": 2},
    },
    "gloves-lvl2": {
        "slot":        "gloves",
        "level":       2,
        "key":         "gloves-lvl2",
        "name":        "Gloves Lvl 2",
        "ru_name":     "Боевые Рукавицы II",
        "slot_label":  "Перчатки",
        "emoji_char":  "🥊",
        "emoji_id":    "5445284980978621387",
        "price":       12_000,
        "description": "Рукавицы с металлическими вставками. Дают бонус к удару и крит.",
        "bonus":       {"dmg": 8, "stamina": 5},
    },
    "gloves-lvl3": {
        "slot":        "gloves",
        "level":       3,
        "key":         "gloves-lvl3",
        "name":        "Gloves Lvl 3",
        "ru_name":     "Наручи Теневого Клинка III",
        "slot_label":  "Перчатки",
        "emoji_char":  "🥊",
        "emoji_id":    "5445284980978621387",
        "price":       28_000,
        "description": "Боевые наручи с шипами из чёрного железа. Ускоряют атаку.",
        "bonus":       {"dmg": 14, "stamina": 8, "phys_def": 3},
    },
    "gloves-lvl4": {
        "slot":        "gloves",
        "level":       4,
        "key":         "gloves-lvl4",
        "name":        "Gloves Lvl 4",
        "ru_name":     "Наручи Теневого Клинка IV",
        "slot_label":  "Перчатки",
        "emoji_char":  "🥊",
        "emoji_id":    "5445284980978621387",
        "price":       55_000,
        "description": "Зачарованные наручи убийцы. Максимальный урон и скорость атаки.",
        "bonus":       {"dmg": 20, "stamina": 12, "phys_def": 5},
    },
    "gloves-lvl5": {
        "slot":        "gloves",
        "level":       5,
        "key":         "gloves-lvl5",
        "name":        "Gloves Lvl 5",
        "ru_name":     "Длани Хаоса",
        "slot_label":  "Перчатки",
        "emoji_char":  "🥊",
        "emoji_id":    "5445284980978621387",
        "price":       120_000,
        "description": "Перчатки, несущие разрушение. Каждый удар сотрясает мироздание.",
        "bonus":       {"dmg": 30, "stamina": 18, "phys_def": 8, "regen": 3},
    },

    # ── ШТАНЫ ─────────────────────────────────────────────────
    "pants-lvl1": {
        "slot":        "pants",
        "level":       1,
        "key":         "pants-lvl1",
        "name":        "Pants Lvl 1",
        "ru_name":     "Боевые Штаны I",
        "slot_label":  "Штаны",
        "emoji_char":  "👖",
        "emoji_id":    "5445284980978621387",
        "price":       4_500,
        "description": "Прочные штаны из грубой ткани. Базовая защита ног.",
        "bonus":       {"hp": 8, "stamina": 5},
    },
    "pants-lvl2": {
        "slot":        "pants",
        "level":       2,
        "key":         "pants-lvl2",
        "name":        "Pants Lvl 2",
        "ru_name":     "Боевые Штаны II",
        "slot_label":  "Штаны",
        "emoji_char":  "👖",
        "emoji_id":    "5445284980978621387",
        "price":       14_000,
        "description": "Кольчужные поножи. Защита бёдер от рубящих ударов.",
        "bonus":       {"hp": 18, "stamina": 10, "phys_def": 4},
    },
    "pants-lvl3": {
        "slot":        "pants",
        "level":       3,
        "key":         "pants-lvl3",
        "name":        "Pants Lvl 3",
        "ru_name":     "Поножи Железного Рыцаря III",
        "slot_label":  "Штаны",
        "emoji_char":  "👖",
        "emoji_id":    "5445284980978621387",
        "price":       30_000,
        "description": "Тяжёлые боевые штаны с усиленными бёдрами. Повышают выносливость.",
        "bonus":       {"hp": 30, "stamina": 16, "phys_def": 7},
    },
    "pants-lvl4": {
        "slot":        "pants",
        "level":       4,
        "key":         "pants-lvl4",
        "name":        "Pants Lvl 4",
        "ru_name":     "Поножи Железного Рыцаря IV",
        "slot_label":  "Штаны",
        "emoji_char":  "👖",
        "emoji_id":    "5445284980978621387",
        "price":       60_000,
        "description": "Зачарованные латные поножи. Уклонение и защита на высшем уровне.",
        "bonus":       {"hp": 45, "stamina": 22, "phys_def": 11, "regen": 3},
    },
    "pants-lvl5": {
        "slot":        "pants",
        "level":       5,
        "key":         "pants-lvl5",
        "name":        "Pants Lvl 5",
        "ru_name":     "Поножи Вечности",
        "slot_label":  "Штаны",
        "emoji_char":  "👖",
        "emoji_id":    "5445284980978621387",
        "price":       130_000,
        "description": "Реликвийные поножи. Дают невероятную стойкость в бою.",
        "bonus":       {"hp": 65, "stamina": 32, "phys_def": 16, "regen": 6},
    },

    # ── САПОГИ ────────────────────────────────────────────────
    "boots-lvl1": {
        "slot":        "boots",
        "level":       1,
        "key":         "boots-lvl1",
        "name":        "Boots Lvl 1",
        "ru_name":     "Походные Сапоги I",
        "slot_label":  "Сапоги",
        "emoji_char":  "👢",
        "emoji_id":    "5445284980978621387",
        "price":       3_500,
        "description": "Прочные походные сапоги. Дают небольшую прибавку к скорости.",
        "bonus":       {"dmg": 2, "regen": 3},
    },
    "boots-lvl2": {
        "slot":        "boots",
        "level":       2,
        "key":         "boots-lvl2",
        "name":        "Boots Lvl 2",
        "ru_name":     "Ботинки Следопыта II",
        "slot_label":  "Сапоги",
        "emoji_char":  "👢",
        "emoji_id":    "5445284980978621387",
        "price":       11_000,
        "description": "Лёгкие сапоги следопыта. Увеличивают шанс первого удара.",
        "bonus":       {"dmg": 5, "regen": 5, "stamina": 3},
    },
    "boots-lvl3": {
        "slot":        "boots",
        "level":       3,
        "key":         "boots-lvl3",
        "name":        "Boots Lvl 3",
        "ru_name":     "Сапоги Ветра Пустоши III",
        "slot_label":  "Сапоги",
        "emoji_char":  "👢",
        "emoji_id":    "5445284980978621387",
        "price":       25_000,
        "description": "Сапоги из кожи горного дракона. Скорость и регенерация.",
        "bonus":       {"dmg": 8, "regen": 8, "stamina": 6},
    },
    "boots-lvl4": {
        "slot":        "boots",
        "level":       4,
        "key":         "boots-lvl4",
        "name":        "Boots Lvl 4",
        "ru_name":     "Сапоги Ветра Пустоши IV",
        "slot_label":  "Сапоги",
        "emoji_char":  "👢",
        "emoji_id":    "5445284980978621387",
        "price":       50_000,
        "description": "Зачарованные сапоги призрака. Почти неслышимые шаги, молниеносный удар.",
        "bonus":       {"dmg": 12, "regen": 12, "stamina": 10, "phys_def": 4},
    },
    "boots-lvl5": {
        "slot":        "boots",
        "level":       5,
        "key":         "boots-lvl5",
        "name":        "Boots Lvl 5",
        "ru_name":     "Сапоги Грома",
        "slot_label":  "Сапоги",
        "emoji_char":  "👢",
        "emoji_id":    "5445284980978621387",
        "price":       110_000,
        "description": "Реликвийные сапоги. Ударная скорость и восстановление на максимуме.",
        "bonus":       {"dmg": 18, "regen": 18, "stamina": 16, "phys_def": 7},
    },
}

# Порядок слотов для отображения
GEAR_SLOTS_ORDER = ["helmet", "armor", "gloves", "pants", "boots"]

# Уровни для каждого слота по порядку
def slot_levels(slot: str) -> list[str]:
    """Возвращает список ключей предметов для слота, от lvl1 до lvl5."""
    return [f"{slot}-lvl{i}" for i in range(1, 6)]


def slot_label(slot: str) -> str:
    return GEAR_CATALOG[f"{slot}-lvl1"]["slot_label"]


def slot_emoji(slot: str) -> str:
    return GEAR_CATALOG[f"{slot}-lvl1"]["emoji_char"]


def current_slot_item(slot: str, user_data: dict) -> dict | None:
    """Возвращает dict предмета, надетого в слот, или None."""
    equipped = user_data.get("duel_equipped", {})
    item_key = equipped.get(slot)
    return GEAR_CATALOG.get(item_key)


def owned_level(slot: str, user_data: dict) -> int:
    """Возвращает максимальный купленный уровень для слота (0 = ничего нет)."""
    owned = user_data.get("duel_owned_gear", [])
    max_lvl = 0
    for lvl in range(1, 6):
        if f"{slot}-lvl{lvl}" in owned:
            max_lvl = lvl
    return max_lvl


def equipped_level(slot: str, user_data: dict) -> int:
    """Возвращает уровень надетого предмета (0 = не надето)."""
    item = current_slot_item(slot, user_data)
    return item["level"] if item else 0


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
            text=" Снаряжение",
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


# ── Снаряжение: список слотов ────────────────────────────────

def duel_equip_text(user_data: dict) -> str:
    lines = []
    for slot in GEAR_SLOTS_ORDER:
        emoji  = slot_emoji(slot)
        label  = slot_label(slot)
        eq_lvl = equipped_level(slot, user_data)
        ow_lvl = owned_level(slot, user_data)

        if eq_lvl:
            item   = current_slot_item(slot, user_data)
            status = f'<b>{item["name"]}</b> ✅'
        elif ow_lvl:
            status = f'<b>{slot}-lvl{ow_lvl}</b> 📦 <i>(не надето)</i>'
        else:
            status = '<i>пусто</i>'

        lines.append(f'{emoji} <b>{label}:</b> {status}')

    slots_block = "\n".join(lines)
    return (
        '<tg-emoji emoji-id="5445221832074483553">🎒</tg-emoji> <b>СНАРЯЖЕНИЕ</b>\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>{slots_block}</blockquote>\n\n'
        'Выбери слот, чтобы купить или улучшить предмет.'
    )


def duel_equip_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    row_buf = []
    for slot in GEAR_SLOTS_ORDER:
        row_buf.append(
            InlineKeyboardButton(
                text=f"{slot_emoji(slot)} {slot_label(slot)}",
                callback_data=f"duel_equip_slot:{slot}",
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


# ── Снаряжение: список уровней конкретного слота ─────────────

def duel_equip_slot_text(slot: str, user_data: dict) -> str:
    ow_lvl = owned_level(slot, user_data)
    eq_lvl = equipped_level(slot, user_data)
    emoji  = slot_emoji(slot)
    label  = slot_label(slot)

    lines = []
    for lvl in range(1, 6):
        item_key = f"{slot}-lvl{lvl}"
        item     = GEAR_CATALOG[item_key]
        price    = _fmt(item["price"])

        if lvl <= ow_lvl:
            if lvl == eq_lvl:
                prefix = f"✅ <b>[{item['name']}]</b>"
            else:
                prefix = f"📦 <b>[{item['name']}]</b>"
        else:
            prefix = f"🔒 [{item['name']}]"

        bonus_parts = []
        for stat, val in item["bonus"].items():
            bonus_parts.append(f"+{val} {stat.upper()}")
        bonus_str = ", ".join(bonus_parts)

        lines.append(
            f"{prefix}\n"
            f"   <i>{item['ru_name']}</i>\n"
            f"   {bonus_str}\n"
            f"   💰 {price} монет"
        )

    block = "\n\n".join(lines)
    return (
        f'{emoji} <b>СНАРЯЖЕНИЕ — {label.upper()}</b>\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>{block}</blockquote>\n\n'
        f'✅ надето  📦 есть (не надето)  🔒 не куплено'
    )


def duel_equip_slot_keyboard(slot: str, user_data: dict) -> InlineKeyboardMarkup:
    ow_lvl = owned_level(slot, user_data)
    eq_lvl = equipped_level(slot, user_data)
    builder = InlineKeyboardBuilder()

    for lvl in range(1, 6):
        item_key = f"{slot}-lvl{lvl}"
        item     = GEAR_CATALOG[item_key]
        price    = _fmt(item["price"])

        if lvl <= ow_lvl:
            if lvl == eq_lvl:
                # Уже надето — кнопка снять
                builder.row(
                    InlineKeyboardButton(
                        text=f"❌ Снять [{item['name']}]",
                        callback_data=f"duel_gear_unequip:{item_key}",
                    )
                )
            else:
                # Куплено, не надето — надеть
                builder.row(
                    InlineKeyboardButton(
                        text=f"✅ Надеть [{item['name']}]",
                        callback_data=f"duel_gear_equip:{item_key}",
                    )
                )
        else:
            # Не куплено
            if lvl == ow_lvl + 1:
                # Следующий уровень — доступен для покупки
                builder.row(
                    InlineKeyboardButton(
                        text=f"🛒 Купить [{item['name']}] — {price} монет",
                        callback_data=f"duel_gear_buy:{item_key}",
                    )
                )
            else:
                # Закрыт (нужно сначала купить предыдущий)
                builder.row(
                    InlineKeyboardButton(
                        text=f"🔒 [{item['name']}] — {price} монет",
                        callback_data=f"duel_gear_locked:{item_key}",
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


# ── Карточка конкретного предмета (по item_key) ──────────────

def duel_item_card_text(item_key: str, user_data: dict) -> str:
    item   = GEAR_CATALOG[item_key]
    slot   = item["slot"]
    ow_lvl = owned_level(slot, user_data)
    eq_lvl = equipped_level(slot, user_data)
    lvl    = item["level"]

    if lvl == eq_lvl:
        status = '✅ <b>Надето</b>'
    elif lvl <= ow_lvl:
        status = '📦 <b>Есть в инвентаре</b> (не надето)'
    else:
        if lvl == ow_lvl + 1:
            status = f'💰 <b>Цена:</b> {_fmt(item["price"])} монет'
        else:
            status = f'🔒 <b>Требуется {slot}-lvl{lvl-1}</b>'

    bonus_lines = "\n".join(f"  +{v} {k.upper()}" for k, v in item["bonus"].items())

    return (
        f'{item["emoji_char"]} <b>{item["name"]}</b>\n'
        f'<i>{item["ru_name"]}</i>\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>{item["description"]}\n\n'
        f'<b>Бонусы:</b>\n{bonus_lines}\n\n'
        f'{status}</blockquote>'
    )


# ── Хелпер: купить предмет ───────────────────────────────────

def apply_gear_purchase(item_key: str, user_data: dict) -> dict:
    """
    Вызывается после успешного списания монет.
    Добавляет предмет в инвентарь и сразу надевает его.

    Пример в хендлере duel_gear_buy:{item_key}:

        item_key = callback.data.split(":")[1]
        item = GEAR_CATALOG[item_key]
        slot = item["slot"]
        ow_lvl = owned_level(slot, user_data)

        # Проверка: только следующий уровень доступен
        if item["level"] != ow_lvl + 1:
            await callback.answer("Сначала купи предыдущий уровень!", show_alert=True)
            return

        if user_data["balance"] < item["price"]:
            await callback.answer("Недостаточно монет!", show_alert=True)
            return

        deduct_balance(user_id, item["price"])
        apply_gear_purchase(item_key, user_data)
        save_user_data(user_id, user_data)

        await callback.message.edit_text(
            duel_equip_slot_text(slot, user_data),
            reply_markup=duel_equip_slot_keyboard(slot, user_data),
        )
    """
    owned    = user_data.setdefault("duel_owned_gear", [])
    equipped = user_data.setdefault("duel_equipped", {})

    if item_key not in owned:
        owned.append(item_key)

    slot = GEAR_CATALOG[item_key]["slot"]
    equipped[slot] = item_key   # надеваем сразу
    return user_data


def apply_gear_equip(item_key: str, user_data: dict) -> dict:
    """Надевает предмет из инвентаря (без списания монет)."""
    slot = GEAR_CATALOG[item_key]["slot"]
    user_data.setdefault("duel_equipped", {})[slot] = item_key
    return user_data


def apply_gear_unequip(item_key: str, user_data: dict) -> dict:
    """Снимает предмет (слот становится пустым)."""
    slot     = GEAR_CATALOG[item_key]["slot"]
    equipped = user_data.setdefault("duel_equipped", {})
    if equipped.get(slot) == item_key:
        del equipped[slot]
    return user_data


# ── Характеристики ───────────────────────────────────────────

BASE_STATS = {
    "hp":       100,
    "dmg":      15,
    "regen":    5,
    "phys_def": 10,
    "mag_def":  10,
    "stamina":  20,
}


def _calc_stats(user_data: dict) -> dict:
    """Считает итоговые характеристики с учётом надетого снаряжения."""
    equipped = user_data.get("duel_equipped", {})
    stats    = dict(BASE_STATS)
    for item_key in equipped.values():
        item = GEAR_CATALOG.get(item_key)
        if not item:
            continue
        for stat, bonus in item["bonus"].items():
            stats[stat] = stats.get(stat, 0) + bonus
    return stats


def duel_charstats_text(user_data: dict) -> str:
    s          = _calc_stats(user_data)
    equipped   = user_data.get("duel_equipped", {})
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
            text="Снаряжение",
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
