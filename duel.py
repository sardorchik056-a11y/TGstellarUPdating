# ============================================================
#  duel.py  —  Раздел Дуэлей TGStellar
# ============================================================

import random
import time
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ── Эмодзи ──────────────────────────────────────────────────
EMOJI_BACK         = "5252272671669706296"
EMOJI_DUEL_MAIN    = "5424972470023104089"
EMOJI_SEARCH       = "5440539497383087970"
EMOJI_INVITE       = "5332724926216428039"
EMOJI_EQUIP        = "5445221832074483553"
EMOJI_SKILLS       = "5224607267797606837"
EMOJI_STATS_DUEL   = "5231200819986047254"
EMOJI_SHOP         = "5447183459602669338"

EMOJI_HP       = "5262643974912355126"
EMOJI_DMG      = "5262643974912355126"
EMOJI_REGEN    = "5262643974912355126"
EMOJI_PHYS_DEF = "5262643974912355126"
EMOJI_MAG_DEF  = "5262643974912355126"
EMOJI_STAMINA  = "5262643974912355126"

# ── Метки статов ────────────────────────────────────────────
STAT_META = {
    "hp":       ("❤️", "Здоровье",    "HP"),
    "dmg":      ("⚔️", "Урон",        "ATK"),
    "regen":    ("💚", "Регенерация", "HP/ход"),
    "phys_def": ("🛡️", "Физ. защита", "DEF"),
    "mag_def":  ("🔮", "Маг. защита", "MDEF"),
    "stamina":  ("⚙️", "Стойкость",   "STM"),
}

# ── Каталог снаряжения: 5 слотов × 5 уровней ────────────────
# ВАЖНО: снаряжение даёт только HP, защиту, регенерацию, стойкость — НЕ урон!
GEAR_CATALOG = {

    # ── ШЛЕМ ─────────────────────────────────────────────────
    "helmet-lvl1": {
        "slot": "helmet", "level": 1, "key": "helmet-lvl1",
        "name": "Helmet Lvl 1", "ru_name": "Железный Шлем",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5445284980978621387",
        "price": 5_000,
        "description": (
            "Грубо выкованный железный шлем без украшений. "
            "Прост в изготовлении, но надёжно прикрывает голову от первого удара."
        ),
        "bonus": {"hp": 10, "phys_def": 3},
    },
    "helmet-lvl2": {
        "slot": "helmet", "level": 2, "key": "helmet-lvl2",
        "name": "Helmet Lvl 2", "ru_name": "Боевой Шлем",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5445284980978621387",
        "price": 15_000,
        "description": "Усиленный шлем с рунической вставкой. Рассеивает слабые магические атаки.",
        "bonus": {"hp": 20, "phys_def": 6, "mag_def": 5},
    },
    "helmet-lvl3": {
        "slot": "helmet", "level": 3, "key": "helmet-lvl3",
        "name": "Helmet Lvl 3", "ru_name": "Шлем Гвардейца",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5445284980978621387",
        "price": 35_000,
        "description": "Закалённый шлем королевской гвардии с забралом из мифрила.",
        "bonus": {"hp": 35, "phys_def": 10, "mag_def": 8, "stamina": 5},
    },
    "helmet-lvl4": {
        "slot": "helmet", "level": 4, "key": "helmet-lvl4",
        "name": "Helmet Lvl 4", "ru_name": "Шлем Стального Стража",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5445284980978621387",
        "price": 70_000,
        "description": "Реликвийный шлем с рунической гравировкой. Входящий урон частично поглощается барьером.",
        "bonus": {"hp": 50, "phys_def": 15, "mag_def": 12, "stamina": 10},
    },
    "helmet-lvl5": {
        "slot": "helmet", "level": 5, "key": "helmet-lvl5",
        "name": "Helmet Lvl 5", "ru_name": "Шлем Легенды",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5445284980978621387",
        "price": 150_000,
        "description": "Артефакт эпохи Первых Воинов. Ни одна стрела не может поколебать носителя.",
        "bonus": {"hp": 75, "phys_def": 22, "mag_def": 18, "stamina": 18},
    },

    # ── БРОНЯ ─────────────────────────────────────────────────
    "armor-lvl1": {
        "slot": "armor", "level": 1, "key": "armor-lvl1",
        "name": "Armor Lvl 1", "ru_name": "Кожаный Доспех",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5447644880824181073",
        "price": 6_000,
        "description": "Доспех из дублёной кожи. Лёгкий, не сковывает движений.",
        "bonus": {"hp": 15, "phys_def": 5},
    },
    "armor-lvl2": {
        "slot": "armor", "level": 2, "key": "armor-lvl2",
        "name": "Armor Lvl 2", "ru_name": "Кольчужный Доспех",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5447644880824181073",
        "price": 18_000,
        "description": "Тысячи закалённых колец. Хорошо поглощает рубящие удары.",
        "bonus": {"hp": 30, "phys_def": 12, "stamina": 5},
    },
    "armor-lvl3": {
        "slot": "armor", "level": 3, "key": "armor-lvl3",
        "name": "Armor Lvl 3", "ru_name": "Пластинчатый Доспех",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5447644880824181073",
        "price": 40_000,
        "description": "Боевые латы из стальных пластин. Сводят урон к минимуму.",
        "bonus": {"hp": 50, "phys_def": 20, "stamina": 8},
    },
    "armor-lvl4": {
        "slot": "armor", "level": 4, "key": "armor-lvl4",
        "name": "Armor Lvl 4", "ru_name": "Латы Воина Бездны",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5447644880824181073",
        "price": 80_000,
        "description": "Прочнейшие латы, выкованные в жерле вулкана тёмными кузнецами.",
        "bonus": {"hp": 75, "phys_def": 30, "mag_def": 8, "stamina": 12},
    },
    "armor-lvl5": {
        "slot": "armor", "level": 5, "key": "armor-lvl5",
        "name": "Armor Lvl 5", "ru_name": "Латы Абсолюта",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5447644880824181073",
        "price": 180_000,
        "description": "Легендарный доспех. Выкован из металла упавшей звезды.",
        "bonus": {"hp": 110, "phys_def": 45, "mag_def": 15, "stamina": 20},
    },

    # ── ПЕРЧАТКИ ──────────────────────────────────────────────
    "gloves-lvl1": {
        "slot": "gloves", "level": 1, "key": "gloves-lvl1",
        "name": "Gloves Lvl 1", "ru_name": "Боевые Рукавицы",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5445284980978621387",
        "price": 4_000,
        "description": "Кожаные рукавицы с наклёпками. Защищают кулаки.",
        "bonus": {"stamina": 5, "phys_def": 2},
    },
    "gloves-lvl2": {
        "slot": "gloves", "level": 2, "key": "gloves-lvl2",
        "name": "Gloves Lvl 2", "ru_name": "Латные Рукавицы",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5445284980978621387",
        "price": 12_000,
        "description": "Рукавицы с металлическими пластинами. Усиливают хват оружия.",
        "bonus": {"stamina": 8, "phys_def": 5},
    },
    "gloves-lvl3": {
        "slot": "gloves", "level": 3, "key": "gloves-lvl3",
        "name": "Gloves Lvl 3", "ru_name": "Наручи Теневого Клинка",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5445284980978621387",
        "price": 28_000,
        "description": "Боевые наручи с выдвижными шипами. Оружие теневых воинов.",
        "bonus": {"stamina": 12, "phys_def": 6, "mag_def": 3},
    },
    "gloves-lvl4": {
        "slot": "gloves", "level": 4, "key": "gloves-lvl4",
        "name": "Gloves Lvl 4", "ru_name": "Наручи Убийцы",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5445284980978621387",
        "price": 55_000,
        "description": "Зачарованные наручи элитных убийц гильдии Алой Тени.",
        "bonus": {"stamina": 16, "phys_def": 10, "mag_def": 5},
    },
    "gloves-lvl5": {
        "slot": "gloves", "level": 5, "key": "gloves-lvl5",
        "name": "Gloves Lvl 5", "ru_name": "Длани Хаоса",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5445284980978621387",
        "price": 120_000,
        "description": "Артефактные перчатки, пронизанные энергией первозданного хаоса.",
        "bonus": {"stamina": 22, "phys_def": 14, "mag_def": 8, "regen": 3},
    },

    # ── ШТАНЫ ─────────────────────────────────────────────────
    "pants-lvl1": {
        "slot": "pants", "level": 1, "key": "pants-lvl1",
        "name": "Pants Lvl 1", "ru_name": "Боевые Штаны",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "5445284980978621387",
        "price": 4_500,
        "description": "Прочные штаны с кожаными вставками. Дают свободу движений.",
        "bonus": {"hp": 8, "stamina": 5},
    },
    "pants-lvl2": {
        "slot": "pants", "level": 2, "key": "pants-lvl2",
        "name": "Pants Lvl 2", "ru_name": "Кольчужные Поножи",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "5445284980978621387",
        "price": 14_000,
        "description": "Усиленные поножи с кольчужными вставками на бёдрах.",
        "bonus": {"hp": 18, "stamina": 10, "phys_def": 4},
    },
    "pants-lvl3": {
        "slot": "pants", "level": 3, "key": "pants-lvl3",
        "name": "Pants Lvl 3", "ru_name": "Поножи Железного Рыцаря",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "5445284980978621387",
        "price": 30_000,
        "description": "Тяжёлые боевые штаны с наколенниками из закалённой стали.",
        "bonus": {"hp": 30, "stamina": 16, "phys_def": 7},
    },
    "pants-lvl4": {
        "slot": "pants", "level": 4, "key": "pants-lvl4",
        "name": "Pants Lvl 4", "ru_name": "Зачарованные Поножи",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "5445284980978621387",
        "price": 60_000,
        "description": "Латные поножи с кристаллами выносливости. Восстанавливают силы в бою.",
        "bonus": {"hp": 45, "stamina": 22, "phys_def": 11, "regen": 3},
    },
    "pants-lvl5": {
        "slot": "pants", "level": 5, "key": "pants-lvl5",
        "name": "Pants Lvl 5", "ru_name": "Поножи Вечности",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "5445284980978621387",
        "price": 130_000,
        "description": "Реликвийные поножи. Тело бойца отказывается сдаваться.",
        "bonus": {"hp": 65, "stamina": 32, "phys_def": 16, "regen": 6},
    },

    # ── САПОГИ ────────────────────────────────────────────────
    "boots-lvl1": {
        "slot": "boots", "level": 1, "key": "boots-lvl1",
        "name": "Boots Lvl 1", "ru_name": "Походные Сапоги",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5445284980978621387",
        "price": 3_500,
        "description": "Добротные кожаные сапоги. Мягкая подошва гасит шум шагов.",
        "bonus": {"regen": 3, "stamina": 3},
    },
    "boots-lvl2": {
        "slot": "boots", "level": 2, "key": "boots-lvl2",
        "name": "Boots Lvl 2", "ru_name": "Сапоги Следопыта",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5445284980978621387",
        "price": 11_000,
        "description": "Лёгкие сапоги из кожи ночной пантеры. Почти бесшумны.",
        "bonus": {"regen": 5, "stamina": 6, "phys_def": 2},
    },
    "boots-lvl3": {
        "slot": "boots", "level": 3, "key": "boots-lvl3",
        "name": "Boots Lvl 3", "ru_name": "Сапоги Ветра Пустоши",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5445284980978621387",
        "price": 25_000,
        "description": "Сапоги из кожи горного дракона, пропитанные эликсиром скорости.",
        "bonus": {"regen": 8, "stamina": 10, "phys_def": 4},
    },
    "boots-lvl4": {
        "slot": "boots", "level": 4, "key": "boots-lvl4",
        "name": "Boots Lvl 4", "ru_name": "Сапоги Призрака",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5445284980978621387",
        "price": 50_000,
        "description": "Зачарованные сапоги разведчиков. Молниеносное перемещение.",
        "bonus": {"regen": 12, "stamina": 14, "phys_def": 6},
    },
    "boots-lvl5": {
        "slot": "boots", "level": 5, "key": "boots-lvl5",
        "name": "Boots Lvl 5", "ru_name": "Сапоги Грома",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5445284980978621387",
        "price": 110_000,
        "description": "Реликвийные сапоги Громового Бога. Надевший их — неудержим.",
        "bonus": {"regen": 18, "stamina": 20, "phys_def": 8},
    },
}

GEAR_SLOTS_ORDER = ["helmet", "armor", "gloves", "pants", "boots"]

def slot_levels(slot: str) -> list:
    return [f"{slot}-lvl{i}" for i in range(1, 6)]

def slot_label(slot: str) -> str:
    return GEAR_CATALOG[f"{slot}-lvl1"]["slot_label"]

def slot_emoji(slot: str) -> str:
    return GEAR_CATALOG[f"{slot}-lvl1"]["emoji_char"]

def current_slot_item(slot: str, user_data: dict):
    equipped = user_data.get("duel_equipped", {})
    item_key = equipped.get(slot)
    return GEAR_CATALOG.get(item_key)

def owned_level(slot: str, user_data: dict) -> int:
    owned = user_data.get("duel_owned_gear", [])
    max_lvl = 0
    for lvl in range(1, 6):
        if f"{slot}-lvl{lvl}" in owned:
            max_lvl = lvl
    return max_lvl

def equipped_level(slot: str, user_data: dict) -> int:
    item = current_slot_item(slot, user_data)
    return item["level"] if item else 0

def _fmt(amount: int) -> str:
    return f"{amount:,}".replace(",", " ")


# ════════════════════════════════════════════════════════════
#  БОЕВЫЕ НАВЫКИ — 22 навыка, покупаемые за монеты
#  Урон исходит ТОЛЬКО из навыков. Снаряжение урон НЕ даёт.
# ════════════════════════════════════════════════════════════

SKILLS = {
    # ── Базовые (бесплатные) ──────────────────────────────────
    "mag_ball": {
        "key": "mag_ball",
        "name": "Шар-маг",
        "emoji": "🔵",
        "type": "magic",
        "cooldown": 15,
        "base_dmg": (18, 28),
        "description": "Концентрированный шар магической энергии. Пробивает магическую защиту.",
        "price": 0,          # бесплатный — доступен всем
    },
    "explosion": {
        "key": "explosion",
        "name": "Взрыв",
        "emoji": "💥",
        "type": "physical",
        "cooldown": 18,
        "base_dmg": (22, 35),
        "description": "Взрыв физической силы. Снижается физической защитой.",
        "price": 0,
    },
    "shield": {
        "key": "shield",
        "name": "Щит",
        "emoji": "🛡️",
        "type": "shield",
        "cooldown": 25,
        "shield_amount": (20, 35),
        "description": "Магический щит. Поглощает следующий входящий удар.",
        "price": 0,
    },

    # ── Покупаемые навыки ────────────────────────────────────
    "mag_block": {
        "key": "mag_block",
        "name": "Блок-маг",
        "emoji": "🟣",
        "type": "magic",
        "cooldown": 20,
        "base_dmg": (30, 48),
        "description": "Мощный магический таран. Высокий урон, длинный кулдаун.",
        "price": 8_000,
    },
    "freeze": {
        "key": "freeze",
        "name": "Заморозка",
        "emoji": "❄️",
        "type": "magic",
        "cooldown": 30,
        "base_dmg": (15, 22),
        "freeze_turns": 1,
        "description": "Заморозка противника. Наносит маг. урон и лишает хода.",
        "price": 10_000,
    },
    "thunder": {
        "key": "thunder",
        "name": "Гром",
        "emoji": "⚡",
        "type": "magic",
        "cooldown": 22,
        "base_dmg": (35, 52),
        "description": "Удар молнией. Игнорирует часть магической защиты.",
        "price": 15_000,
    },
    "inferno": {
        "key": "inferno",
        "name": "Инферно",
        "emoji": "🔥",
        "type": "magic",
        "cooldown": 28,
        "base_dmg": (40, 60),
        "description": "Огненный шторм. Один из мощнейших магических ударов.",
        "price": 20_000,
    },
    "shadow_strike": {
        "key": "shadow_strike",
        "name": "Удар Тени",
        "emoji": "🌑",
        "type": "physical",
        "cooldown": 16,
        "base_dmg": (28, 42),
        "description": "Стремительный удар из тени. Снижается физической защитой.",
        "price": 12_000,
    },
    "berserker": {
        "key": "berserker",
        "name": "Берсерк",
        "emoji": "🔴",
        "type": "physical",
        "cooldown": 35,
        "base_dmg": (55, 80),
        "description": "Состояние боевого безумия. Колоссальный физический удар.",
        "price": 25_000,
    },
    "poison_dart": {
        "key": "poison_dart",
        "name": "Ядовитая Стрела",
        "emoji": "🧪",
        "type": "magic",
        "cooldown": 20,
        "base_dmg": (20, 30),
        "description": "Отравленная стрела. Наносит маг. урон и ослабляет врага.",
        "price": 13_000,
    },
    "earthquake": {
        "key": "earthquake",
        "name": "Землетрясение",
        "emoji": "🌍",
        "type": "physical",
        "cooldown": 32,
        "base_dmg": (45, 65),
        "description": "Раскалывает землю под ногами врага. Мощный физ. удар.",
        "price": 22_000,
    },
    "void_blast": {
        "key": "void_blast",
        "name": "Взрыв Пустоты",
        "emoji": "🌀",
        "type": "magic",
        "cooldown": 40,
        "base_dmg": (60, 90),
        "description": "Разрывает ткань реальности. Огромный урон, долгий кулдаун.",
        "price": 35_000,
    },
    "blade_storm": {
        "key": "blade_storm",
        "name": "Буря Клинков",
        "emoji": "🌪️",
        "type": "physical",
        "cooldown": 26,
        "base_dmg": (38, 55),
        "description": "Вихрь из тысячи лезвий. Рубящий физический удар.",
        "price": 18_000,
    },
    "soul_drain": {
        "key": "soul_drain",
        "name": "Похищение Души",
        "emoji": "💜",
        "type": "magic",
        "cooldown": 45,
        "base_dmg": (50, 75),
        "drain_regen": 15,   # восстанавливает HP атакующему
        "description": "Высасывает жизненную силу врага. Часть урона восстанавливает твоё HP.",
        "price": 30_000,
    },
    "meteor": {
        "key": "meteor",
        "name": "Метеор",
        "emoji": "☄️",
        "type": "magic",
        "cooldown": 50,
        "base_dmg": (70, 100),
        "description": "С небес падает огненный метеор. Сокрушительная мощь.",
        "price": 45_000,
    },
    "iron_fist": {
        "key": "iron_fist",
        "name": "Железный Кулак",
        "emoji": "✊",
        "type": "physical",
        "cooldown": 14,
        "base_dmg": (24, 36),
        "description": "Сокрушительный удар, пробивающий любую броню.",
        "price": 9_000,
    },
    "arcane_surge": {
        "key": "arcane_surge",
        "name": "Аркановый Всплеск",
        "emoji": "✨",
        "type": "magic",
        "cooldown": 18,
        "base_dmg": (26, 40),
        "description": "Выброс чистой маг. энергии. Быстрый и надёжный удар.",
        "price": 11_000,
    },
    "war_cry": {
        "key": "war_cry",
        "name": "Боевой Клич",
        "emoji": "📣",
        "type": "physical",
        "cooldown": 30,
        "base_dmg": (42, 60),
        "description": "Боевой клич, вселяющий ужас. Мощный физический удар.",
        "price": 20_000,
    },
    "dark_nova": {
        "key": "dark_nova",
        "name": "Тёмная Новa",
        "emoji": "🖤",
        "type": "magic",
        "cooldown": 55,
        "base_dmg": (80, 115),
        "description": "Взрыв тёмной материи. Разрушительная тёмная магия.",
        "price": 60_000,
    },
    "chain_lightning": {
        "key": "chain_lightning",
        "name": "Цепная Молния",
        "emoji": "🌩️",
        "type": "magic",
        "cooldown": 24,
        "base_dmg": (32, 48),
        "description": "Молния, скачущая от цели к цели. Стабильный маг. удар.",
        "price": 16_000,
    },
    "titan_slam": {
        "key": "titan_slam",
        "name": "Удар Титана",
        "emoji": "⚒️",
        "type": "physical",
        "cooldown": 42,
        "base_dmg": (62, 88),
        "description": "Удар с силой титана. Сотрясает врага до основания.",
        "price": 40_000,
    },
    "divine_wrath": {
        "key": "divine_wrath",
        "name": "Гнев Небес",
        "emoji": "⚜️",
        "type": "magic",
        "cooldown": 60,
        "base_dmg": (90, 130),
        "description": "Священный огонь небес. Абсолютное разрушение.",
        "price": 80_000,
    },
    "mega_shield": {
        "key": "mega_shield",
        "name": "Мега-Щит",
        "emoji": "🔰",
        "type": "shield",
        "cooldown": 40,
        "shield_amount": (50, 80),
        "description": "Огромный магический щит. Поглощает колоссальный урон.",
        "price": 28_000,
    },
}

SKILLS_ORDER_BASE = ["mag_ball", "explosion", "shield"]
SKILLS_ORDER = list(SKILLS.keys())

# Максимум навыков в бою
MAX_EQUIPPED_SKILLS = 5


def get_owned_skills(user_data: dict) -> list:
    """Возвращает список ключей навыков, которыми владеет пользователь."""
    base = [k for k, v in SKILLS.items() if v["price"] == 0]
    owned = user_data.get("duel_owned_skills", [])
    result = []
    for k in base:
        if k not in result:
            result.append(k)
    for k in owned:
        if k not in result:
            result.append(k)
    return result


def get_equipped_skills(user_data: dict) -> list:
    """Возвращает список навыков, экипированных в бой (макс. 5)."""
    equipped = user_data.get("duel_equipped_skills", [])
    # Фильтруем: только те, которыми владеем
    owned = get_owned_skills(user_data)
    return [k for k in equipped if k in owned]


def equip_skill(skill_key: str, user_data: dict) -> tuple:
    """Экипировать навык в бой. Возвращает (ok, msg)."""
    owned = get_owned_skills(user_data)
    if skill_key not in owned:
        return False, "❌ Навык не куплен!"
    equipped = user_data.setdefault("duel_equipped_skills", [])
    if skill_key in equipped:
        return False, "❌ Навык уже экипирован!"
    if len(equipped) >= MAX_EQUIPPED_SKILLS:
        return False, f"❌ Максимум {MAX_EQUIPPED_SKILLS} навыков в бою!"
    equipped.append(skill_key)
    return True, "✅ Навык экипирован!"


def unequip_skill(skill_key: str, user_data: dict) -> tuple:
    """Снять навык с экипировки. Возвращает (ok, msg)."""
    equipped = user_data.setdefault("duel_equipped_skills", [])
    if skill_key not in equipped:
        return False, "❌ Навык не экипирован!"
    equipped.remove(skill_key)
    return True, "✅ Навык снят!"


# ── Карточка навыка (подробное окно, как у снаряжения) ────────────────────

def duel_skill_card_text(skill_key: str, user_data: dict) -> str:
    sk      = SKILLS.get(skill_key)
    if not sk:
        return "❌ Навык не найден."
    owned    = get_owned_skills(user_data)
    equipped = get_equipped_skills(user_data)
    balance  = user_data.get("balance", 0)
    is_owned = skill_key in owned
    is_equip = skill_key in equipped

    # Тип навыка
    type_labels = {"magic": "🔮 Магический", "physical": "⚔️ Физический", "shield": "🛡️ Защитный"}
    type_label  = type_labels.get(sk["type"], sk["type"])

    # Характеристики
    if sk["type"] == "shield":
        power_line = f'🛡️ <b>Поглощает:</b> {sk["shield_amount"][0]}–{sk["shield_amount"][1]} HP'
    else:
        power_line = f'⚔️ <b>Урон:</b> {sk["base_dmg"][0]}–{sk["base_dmg"][1]}'

    # Статус
    if is_equip:
        status_line = '✅ <b>Экипирован в бой</b>'
    elif is_owned:
        status_line = '📦 <b>Куплен</b> — не экипирован в бой'
    else:
        status_line = f'💰 <b>Цена: {_fmt(sk["price"])} монет</b>'
        if balance < sk["price"]:
            deficit = sk["price"] - balance
            status_line += f'\n⚠️ <i>Не хватает {_fmt(deficit)} монет</i>'

    # Слоты
    slot_info = f'{len(equipped)}/{MAX_EQUIPPED_SKILLS} навыков экипировано'

    return (
        f'{sk["emoji"]} <b>{sk["name"]}</b>\n'
        f'<i>{type_label} · ⏳ Перезарядка: {sk["cooldown"]} сек.</i>\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>{sk["description"]}</blockquote>\n\n'
        f'<b>Характеристики:</b>\n'
        f'{power_line}\n'
        f'⏳ <b>Кулдаун:</b> {sk["cooldown"]} сек.\n\n'
        f'<i>Слоты в бою: {slot_info}</i>\n\n'
        f'{status_line}'
    )


def duel_skill_card_keyboard(skill_key: str, user_data: dict, from_page: int = 0) -> InlineKeyboardMarkup:
    sk      = SKILLS.get(skill_key)
    owned   = get_owned_skills(user_data)
    equipped = get_equipped_skills(user_data)
    balance = user_data.get("balance", 0)
    is_owned = skill_key in owned
    is_equip = skill_key in equipped
    builder  = InlineKeyboardBuilder()

    if is_equip:
        builder.row(InlineKeyboardButton(
            text="❌ Снять из боя",
            callback_data=f"duel_skill_unequip:{skill_key}",
        ))
    elif is_owned:
        if len(equipped) < MAX_EQUIPPED_SKILLS:
            builder.row(InlineKeyboardButton(
                text="⚔️ Экипировать в бой",
                callback_data=f"duel_skill_equip:{skill_key}",
            ))
        else:
            builder.row(InlineKeyboardButton(
                text=f"⚠️ Все {MAX_EQUIPPED_SKILLS} слотов заняты",
                callback_data="duel_skill_slots_full",
            ))
    else:
        if sk and balance >= sk["price"]:
            builder.row(InlineKeyboardButton(
                text=f"🛒 Купить — {_fmt(sk['price'])} монет",
                callback_data=f"duel_skill_buy:{skill_key}",
            ))
        elif sk:
            builder.row(InlineKeyboardButton(
                text=f"💸 Недостаточно монет",
                callback_data="duel_skill_nofunds",
            ))

    builder.row(InlineKeyboardButton(
        text="Назад",
        callback_data=f"duel_skills_shop_page:{from_page}",
        icon_custom_emoji_id=EMOJI_BACK,
    ))
    return builder.as_markup()


def _calc_skill_damage(skill_key: str, attacker_stats: dict, defender_stats: dict) -> dict:
    """Вычислить урон от навыка."""
    sk = SKILLS[skill_key]
    result = {"type": sk["type"], "skill": skill_key}

    if sk["type"] == "magic":
        base_min, base_max = sk["base_dmg"]
        base = random.randint(base_min, base_max)
        enemy_resist = max(0, defender_stats.get("mag_def", 10) * 0.5)
        dmg = max(1, int(base - enemy_resist))
        result["dmg"] = dmg

    elif sk["type"] == "physical":
        base_min, base_max = sk["base_dmg"]
        base = random.randint(base_min, base_max)
        enemy_resist = max(0, defender_stats.get("phys_def", 10) * 0.4)
        dmg = max(1, int(base - enemy_resist))
        result["dmg"] = dmg

    elif sk["type"] == "shield":
        sh_min, sh_max = sk["shield_amount"]
        result["shield"] = random.randint(sh_min, sh_max)
        result["dmg"] = 0

    if skill_key == "freeze":
        result["freeze"] = True

    if skill_key == "soul_drain":
        result["drain_regen"] = sk.get("drain_regen", 15)

    return result


# ════════════════════════════════════════════════════════════
#  СИСТЕМА HP ИГРОКА (восстановление после боя)
# ════════════════════════════════════════════════════════════
# Хранит текущий HP игрока вне боя: uid -> {"hp": int, "last_regen_at": int}
_player_hp: dict[int, dict] = {}

HP_REGEN_INTERVAL = 10   # секунд между тиками восстановления
HP_REGEN_AMOUNT   = 10   # HP за тик
HP_MAX_DEFAULT    = 100  # стандартный максимум HP (без снаряжения)


def get_player_hp(uid: int, user_data: dict) -> int:
    """Возвращает текущий HP игрока вне боя (с учётом регенерации)."""
    hp_max = _calc_stats(user_data)["hp"]
    entry  = _player_hp.get(uid)
    if entry is None:
        # Первый вызов — HP полное
        _player_hp[uid] = {"hp": hp_max, "last_regen_at": int(time.time())}
        return hp_max

    now     = int(time.time())
    elapsed = now - entry["last_regen_at"]
    ticks   = elapsed // HP_REGEN_INTERVAL
    if ticks > 0 and entry["hp"] < hp_max:
        entry["hp"] = min(hp_max, entry["hp"] + ticks * HP_REGEN_AMOUNT)
        entry["last_regen_at"] += ticks * HP_REGEN_INTERVAL
    return entry["hp"]


def set_player_hp(uid: int, hp: int, user_data: dict):
    """Устанавливает HP игрока после боя."""
    hp_max = _calc_stats(user_data)["hp"]
    _player_hp[uid] = {
        "hp": max(0, min(hp_max, hp)),
        "last_regen_at": int(time.time()),
    }


def is_player_ready(uid: int, user_data: dict) -> bool:
    """True если HP игрока >= 100 (можно идти в бой)."""
    return get_player_hp(uid, user_data) >= 100


def player_hp_regen_seconds(uid: int, user_data: dict) -> int:
    """Возвращает секунд до следующего тика регенерации."""
    hp_max = _calc_stats(user_data)["hp"]
    entry  = _player_hp.get(uid)
    if entry is None or entry["hp"] >= hp_max:
        return 0
    elapsed = int(time.time()) - entry["last_regen_at"]
    return max(0, HP_REGEN_INTERVAL - elapsed % HP_REGEN_INTERVAL)


# ════════════════════════════════════════════════════════════
#  СИСТЕМА ВЫЗОВА НА ДУЭЛЬ (Challenge)
# ════════════════════════════════════════════════════════════
# pending_challenges: uid_challenger -> {"target_uid": int, "target_name": str, "expires_at": int}
_pending_challenges: dict[int, dict] = {}
# Хранит uid того, кто бросил вызов: uid_target -> uid_challenger
_incoming_challenge: dict[int, int] = {}


def create_challenge(challenger_uid: int, target_uid: int, target_name: str):
    """Создаёт вызов на дуэль."""
    expires = int(time.time()) + 120  # 2 минуты
    _pending_challenges[challenger_uid] = {
        "target_uid": target_uid,
        "target_name": target_name,
        "expires_at": expires,
    }
    _incoming_challenge[target_uid] = challenger_uid


def get_incoming_challenge(uid: int) -> dict | None:
    """Возвращает данные входящего вызова или None."""
    challenger_uid = _incoming_challenge.get(uid)
    if challenger_uid is None:
        return None
    ch = _pending_challenges.get(challenger_uid)
    if ch is None or int(time.time()) > ch["expires_at"]:
        _incoming_challenge.pop(uid, None)
        _pending_challenges.pop(challenger_uid, None)
        return None
    ch = dict(ch)
    ch["challenger_uid"] = challenger_uid
    return ch


def cancel_challenge(challenger_uid: int):
    """Отменяет вызов."""
    ch = _pending_challenges.pop(challenger_uid, None)
    if ch:
        _incoming_challenge.pop(ch["target_uid"], None)


def accept_challenge(target_uid: int) -> dict | None:
    """
    Принимает вызов. Возвращает battle-dict или None если вызов устарел.
    Данные игроков надо передать снаружи через accept_challenge_with_data.
    """
    challenger_uid = _incoming_challenge.pop(target_uid, None)
    if challenger_uid is None:
        return None
    ch = _pending_challenges.pop(challenger_uid, None)
    if ch is None or int(time.time()) > ch["expires_at"]:
        return None
    return {"challenger_uid": challenger_uid}


def decline_challenge(target_uid: int) -> int | None:
    """Отклоняет вызов, возвращает uid вызывающего."""
    challenger_uid = _incoming_challenge.pop(target_uid, None)
    if challenger_uid:
        _pending_challenges.pop(challenger_uid, None)
    return challenger_uid


def start_challenge_battle(challenger_uid: int, challenger_data: dict,
                           target_uid: int, target_data: dict) -> dict:
    """Создаёт боевой state для вызова на дуэль."""
    battle = _create_battle(challenger_uid, challenger_data, target_uid, target_data)
    # Навыки обоих
    battle["p1_skills"] = get_equipped_skills(challenger_data) or get_owned_skills(challenger_data)
    battle["p2_skills"] = get_equipped_skills(target_data) or get_owned_skills(target_data)
    return battle


def challenge_invite_text(challenger_data: dict) -> str:
    """Текст уведомления о вызове для цели. Показывает хар-ки вызывающего."""
    stats  = _calc_stats(challenger_data)
    name   = challenger_data.get("first_name") or challenger_data.get("username") or "Игрок"
    lvl    = challenger_data.get("level", 1)
    skills = get_equipped_skills(challenger_data) or get_owned_skills(challenger_data)
    sk_names = ", ".join(SKILLS[k]["name"] for k in skills[:5] if k in SKILLS) or "нет"
    return (
        f'⚔️ <b>Вызов на дуэль!</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>'
        f'👤 <b>{name}</b> (уровень {lvl}) бросает тебе вызов!\n\n'
        f'📊 <b>Характеристики противника:</b>\n'
        f'❤️ HP: <b>{stats["hp"]}</b>\n'
        f'🛡️ Физ. защита: <b>{stats["phys_def"]}</b>\n'
        f'🔮 Маг. защита: <b>{stats["mag_def"]}</b>\n'
        f'💚 Регенерация: <b>{stats["regen"]}</b> HP/ход\n'
        f'⚙️ Стойкость: <b>{stats["stamina"]}</b>\n\n'
        f'⚔️ Навыки: <i>{sk_names}</i>\n\n'
        f'⏳ <i>Вызов действителен 2 минуты</i>'
        f'</blockquote>'
    )


def challenge_invite_keyboard(challenger_uid: int) -> InlineKeyboardMarkup:
    """Кнопки Принять / Отказаться для цели вызова."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Принять",
            callback_data=f"duel_challenge_accept:{challenger_uid}",
        ),
        InlineKeyboardButton(
            text="❌ Отказаться",
            callback_data=f"duel_challenge_decline:{challenger_uid}",
        ),
    )
    return builder.as_markup()


# ════════════════════════════════════════════════════════════
#  ПОИСК ПРОТИВНИКА / МАТЧМЕЙКИНГ
# ════════════════════════════════════════════════════════════

_match_queue: dict[int, tuple] = {}


def join_queue(uid: int, user_data: dict) -> dict | None:
    now = int(time.time())
    stale = [k for k, (ts, _) in _match_queue.items() if now - ts > 120]
    for k in stale:
        _match_queue.pop(k, None)

    for opponent_uid, (ts, opp_data) in list(_match_queue.items()):
        if opponent_uid == uid:
            continue
        _match_queue.pop(opponent_uid, None)
        battle = _create_battle(uid, user_data, opponent_uid, opp_data)
        return battle

    _match_queue[uid] = (now, user_data)
    return None


def leave_queue(uid: int):
    _match_queue.pop(uid, None)


def in_queue(uid: int) -> bool:
    return uid in _match_queue


# ════════════════════════════════════════════════════════════
#  БОЙ
# ════════════════════════════════════════════════════════════

BASE_STATS = {
    "hp": 100, "dmg": 0, "regen": 5,
    "phys_def": 10, "mag_def": 10, "stamina": 20,
}


def _calc_stats(user_data: dict) -> dict:
    """
    Считаем статы персонажа.
    Снаряжение даёт hp, phys_def, mag_def, regen, stamina — НЕ dmg.
    Урон (dmg) снаряжение не даёт вообще.
    """
    equipped = user_data.get("duel_equipped", {})
    stats = dict(BASE_STATS)
    for item_key in equipped.values():
        item = GEAR_CATALOG.get(item_key)
        if not item:
            continue
        for stat, bonus in item["bonus"].items():
            if stat == "dmg":
                continue   # снаряжение НЕ добавляет урон
            stats[stat] = stats.get(stat, 0) + bonus
    return stats


def _create_battle(uid1: int, data1: dict, uid2: int, data2: dict) -> dict:
    stats1 = _calc_stats(data1)
    stats2 = _calc_stats(data2)

    name1 = data1.get("first_name") or data1.get("username") or f"Игрок {uid1}"
    name2 = data2.get("first_name") or data2.get("username") or f"Игрок {uid2}"

    now = int(time.time())
    battle = {
        "p1_uid": uid1,
        "p2_uid": uid2,
        "p1_name": name1,
        "p2_name": name2,
        "p1_hp": stats1["hp"],
        "p2_hp": stats2["hp"],
        "p1_hp_max": stats1["hp"],
        "p2_hp_max": stats2["hp"],
        "p1_stats": stats1,
        "p2_stats": stats2,
        "p1_shield": 0,
        "p2_shield": 0,
        "p1_frozen": False,
        "p2_frozen": False,
        "p1_cooldowns": {},
        "p2_cooldowns": {},
        "turn": uid1,
        "started_at": now,
        "last_action": now,
        "log": [],
        "finished": False,
        "winner_uid": None,
    }
    return battle


def _get_player_prefix(battle: dict, uid: int) -> str:
    return "p1" if battle["p1_uid"] == uid else "p2"


def _get_enemy_prefix(battle: dict, uid: int) -> str:
    return "p2" if battle["p1_uid"] == uid else "p1"


def battle_use_skill(battle: dict, uid: int, skill_key: str) -> tuple:
    now = int(time.time())

    if battle.get("finished"):
        return battle, {"ok": False, "msg": "Бой уже завершён."}

    me  = _get_player_prefix(battle, uid)
    foe = _get_enemy_prefix(battle, uid)

    if battle.get(f"{me}_frozen"):
        battle[f"{me}_frozen"] = False
        return battle, {"ok": False, "msg": "❄️ Ты заморожен и пропускаешь ход!"}

    cooldowns = battle.get(f"{me}_cooldowns", {})
    ready_at  = cooldowns.get(skill_key, 0)
    if now < ready_at:
        left = ready_at - now
        return battle, {"ok": False, "msg": f"⏳ Навык на перезарядке ещё {left}с."}

    sk = SKILLS.get(skill_key)
    if not sk:
        return battle, {"ok": False, "msg": "Неизвестный навык."}

    cooldowns[skill_key] = now + sk["cooldown"]
    battle[f"{me}_cooldowns"] = cooldowns

    my_stats  = battle[f"{me}_stats"]
    foe_stats = battle[f"{foe}_stats"]

    result = _calc_skill_damage(skill_key, my_stats, foe_stats)
    effect_msg = ""

    if sk["type"] == "shield":
        sh = result["shield"]
        battle[f"{me}_shield"] = sh
        effect_msg = f"🛡️ Щит {sh} HP"
        log_entry = f"{battle[f'{me}_name']}: {sk['emoji']} {sk['name']} → {effect_msg}"
    else:
        raw_dmg = result["dmg"]
        foe_shield = battle.get(f"{foe}_shield", 0)
        if foe_shield > 0:
            absorbed = min(foe_shield, raw_dmg)
            raw_dmg -= absorbed
            battle[f"{foe}_shield"] = foe_shield - absorbed
            effect_msg += f" (щит -{absorbed})"

        battle[f"{foe}_hp"] = max(0, battle[f"{foe}_hp"] - raw_dmg)
        result["dmg"] = raw_dmg

        if result.get("freeze"):
            battle[f"{foe}_frozen"] = True
            effect_msg += " ❄️ заморозка!"

        # Soul drain — восстановить HP атакующему
        if result.get("drain_regen"):
            drain = result["drain_regen"]
            hp_max = battle[f"{me}_hp_max"]
            battle[f"{me}_hp"] = min(hp_max, battle[f"{me}_hp"] + drain)
            effect_msg += f" 💜+{drain}HP"

        log_entry = (
            f"{battle[f'{me}_name']}: {sk['emoji']} {sk['name']} "
            f"→ -{raw_dmg} HP{effect_msg}"
        )

    # Регенерация
    regen = my_stats.get("regen", 0)
    if regen > 0:
        hp_max = battle[f"{me}_hp_max"]
        battle[f"{me}_hp"] = min(hp_max, battle[f"{me}_hp"] + regen)

    battle["log"].append(log_entry)
    if len(battle["log"]) > 6:
        battle["log"] = battle["log"][-6:]

    if battle["p1_hp"] <= 0 or battle["p2_hp"] <= 0:
        battle["finished"] = True
        if battle["p1_hp"] <= 0 and battle["p2_hp"] <= 0:
            battle["winner_uid"] = None
        elif battle["p1_hp"] <= 0:
            battle["winner_uid"] = battle["p2_uid"]
        else:
            battle["winner_uid"] = battle["p1_uid"]

    battle["last_action"] = now
    return battle, {"ok": True, "result": result, "log_entry": log_entry}


# ── HP-бар ───────────────────────────────────────────────────

def _hp_bar(hp: int, hp_max: int, length: int = 10) -> str:
    if hp_max <= 0:
        return "▓" * length
    ratio = max(0, min(1, hp / hp_max))
    filled = round(ratio * length)
    bar = "█" * filled + "░" * (length - filled)
    pct = int(ratio * 100)
    return f"[{bar}] {hp}/{hp_max} ({pct}%)"


# ── Боевой экран (текст) ─────────────────────────────────────

def battle_text(battle: dict, uid: int) -> str:
    me  = _get_player_prefix(battle, uid)
    foe = _get_enemy_prefix(battle, uid)

    my_name    = battle[f"{me}_name"]
    foe_name   = battle[f"{foe}_name"]
    my_hp      = battle[f"{me}_hp"]
    my_hp_max  = battle[f"{me}_hp_max"]
    foe_hp     = battle[f"{foe}_hp"]
    foe_hp_max = battle[f"{foe}_hp_max"]

    my_bar  = _hp_bar(my_hp, my_hp_max)
    foe_bar = _hp_bar(foe_hp, foe_hp_max)

    shields = ""
    if battle.get(f"{me}_shield", 0) > 0:
        shields += f"\n🛡️ Твой щит: <b>{battle[f'{me}_shield']} HP</b>"
    if battle.get(f"{foe}_shield", 0) > 0:
        shields += f"\n🛡️ Щит врага: <b>{battle[f'{foe}_shield']} HP</b>"

    frozen_note = ""
    if battle.get(f"{me}_frozen"):
        frozen_note = "\n❄️ <b>Ты заморожен! Следующий ход пропущен.</b>"
    if battle.get(f"{foe}_frozen"):
        frozen_note += f"\n❄️ <b>{foe_name} заморожен!</b>"

    log_lines = battle.get("log", [])
    log_block = ""
    if log_lines:
        log_block = "\n\n<blockquote>" + "\n".join(log_lines[-4:]) + "</blockquote>"

    if battle.get("finished"):
        winner = battle.get("winner_uid")
        if winner is None:
            result_line = "⚔️ <b>Ничья!</b>"
        elif winner == uid:
            result_line = "🏆 <b>Ты победил!</b>"
        else:
            result_line = "💀 <b>Ты проиграл!</b>"
        return (
            f'⚔️ <b>БОЙ ЗАВЕРШЁН</b>\n'
            f'━━━━━━━━━━━━━━━━━━━━\n\n'
            f'{result_line}\n\n'
            f'<blockquote>'
            f'👤 <b>{my_name}</b>\n'
            f'❤️ {my_bar}\n\n'
            f'👹 <b>{foe_name}</b>\n'
            f'❤️ {foe_bar}'
            f'</blockquote>'
            f'{log_block}'
        )

    return (
        f'⚔️ <b>БОЙ</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>'
        f'👤 <b>{my_name}</b>\n'
        f'❤️ {my_bar}'
        f'{shields}'
        f'{frozen_note}\n\n'
        f'👹 <b>{foe_name}</b>\n'
        f'❤️ {foe_bar}'
        f'</blockquote>'
        f'{log_block}\n\n'
        f'<i>Выбери навык для атаки:</i>'
    )


# ── Боевая клавиатура (навыки с кулдаунами, таймер обновляется) ──────────

def battle_keyboard(battle: dict, uid: int) -> InlineKeyboardMarkup:
    me  = _get_player_prefix(battle, uid)
    now = int(time.time())
    cooldowns = battle.get(f"{me}_cooldowns", {})

    # Экипированные навыки (макс. 5), записаны при старте боя
    p_skills = battle.get(f"{me}_skills") or SKILLS_ORDER_BASE

    builder = InlineKeyboardBuilder()

    if battle.get("finished"):
        builder.row(InlineKeyboardButton(
            text="🔄 Новый поиск", callback_data="duel_search"
        ))
        builder.row(InlineKeyboardButton(
            text="🏠 В меню дуэлей", callback_data="duel_main"
        ))
        return builder.as_markup()

    skill_buttons = []
    for skill_key in p_skills:
        sk = SKILLS.get(skill_key)
        if not sk:
            continue
        ready_at = cooldowns.get(skill_key, 0)
        left = ready_at - now
        if left > 0:
            btn_text = f"{sk['emoji']} {sk['name']} ⏳{left}с"
        else:
            btn_text = f"{sk['emoji']} {sk['name']}"
        skill_buttons.append(InlineKeyboardButton(
            text=btn_text,
            callback_data=f"duel_skill:{skill_key}"
        ))

    # Раскладка: по 2 в ряд
    for i in range(0, len(skill_buttons), 2):
        pair = skill_buttons[i:i+2]
        builder.row(*pair)

    builder.row(InlineKeyboardButton(
        text="🏳️ Сдаться", callback_data="duel_surrender"
    ))
    return builder.as_markup()


# ════════════════════════════════════════════════════════════
#  МАГАЗИН НАВЫКОВ
# ════════════════════════════════════════════════════════════

SKILLS_SHOP_PAGE_SIZE = 5   # навыков на страницу


def _skill_page_items(page: int) -> list:
    """Возвращает навыки для страницы магазина (только платные)."""
    paid = [k for k, v in SKILLS.items() if v["price"] > 0]
    start = page * SKILLS_SHOP_PAGE_SIZE
    return paid[start:start + SKILLS_SHOP_PAGE_SIZE], len(paid)


import random as _random

_DUEL_SHOP_QUOTES = [
    "⚔️ <i>Великий воин побеждает не силой, а кошельком.</i>",
    "💀 <i>Враг тоже читал этот магазин. Покупай быстрее.</i>",
    "🔥 <i>Зачем качать скилл в жизни, если можно купить в магазине?</i>",
    "😤 <i>Каждый навык здесь прошёл боевые испытания... на тестовом сервере.</i>",
    "🧠 <i>Умный воин выбирает навык с умом. Остальные берут всё подряд.</i>",
    "💸 <i>Деньги — это просто ресурс. Вкладывай в победы.</i>",
    "🏆 <i>Победители не рождаются — они просто лучше экипированы.</i>",
    "😂 <i>Противник тоже думал, что сэкономит. Теперь он в таблице проигравших.</i>",
    "⚡ <i>Молния бьёт дважды в одного — если купить правильный навык.</i>",
    "🧊 <i>Заморозь врага раньше, чем он разморозит кошелёк.</i>",
    "🌑 <i>Тьма — лучший союзник. Особенно если за неё заплачено.</i>",
    "😎 <i>Не важно как ты выглядишь в бою. Важно — остался ли противник стоять.</i>",
    "🔮 <i>Магия не терпит скупости. Магия терпит только оплату.</i>",
    "💪 <i>Сила воли — хорошо. Сила навыка — лучше.</i>",
    "🎯 <i>Точность приходит с практикой. А практика — с хорошим навыком.</i>",
]


def duel_skills_shop_text(user_data: dict, page: int = 0) -> str:
    items, total = _skill_page_items(page)
    total_pages = (total + SKILLS_SHOP_PAGE_SIZE - 1) // SKILLS_SHOP_PAGE_SIZE
    owned_skills    = get_owned_skills(user_data)
    equipped_skills = get_equipped_skills(user_data)
    balance = user_data.get("balance", 0)

    lines = []
    for sk_key in items:
        sk = SKILLS[sk_key]
        is_owned  = sk_key in owned_skills
        is_equip  = sk_key in equipped_skills

        if is_equip:
            marker    = "⚔️"
            price_str = "в бою"
        elif is_owned:
            marker    = "✅"
            price_str = "куплен"
        else:
            marker    = "🔒"
            price_str = f"{_fmt(sk['price'])} монет"

        if sk["type"] == "shield":
            val = f"щит {sk['shield_amount'][0]}–{sk['shield_amount'][1]} HP"
        else:
            val = f"урон {sk['base_dmg'][0]}–{sk['base_dmg'][1]}"

        lines.append(
            f"{marker} {sk['emoji']} <b>{sk['name']}</b> [{price_str}]"
        )

    block = "\n".join(lines)
    eq_count = len(equipped_skills)
    quote = _random.choice(_DUEL_SHOP_QUOTES)
    return (
        f'<tg-emoji emoji-id="{EMOJI_SKILLS}">✨</tg-emoji> <b>МАГАЗИН НАВЫКОВ</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>{block}</blockquote>\n\n'
        f'💰 Баланс: <b>{_fmt(balance)}</b> монет · Стр. {page+1}/{total_pages}\n'
        f'⚔️ Экипировано в бой: <b>{eq_count}/{MAX_EQUIPPED_SKILLS}</b>\n\n'
        f'{quote}'
    )


def duel_skills_shop_keyboard(user_data: dict, page: int = 0) -> InlineKeyboardMarkup:
    items, total = _skill_page_items(page)
    total_pages = (total + SKILLS_SHOP_PAGE_SIZE - 1) // SKILLS_SHOP_PAGE_SIZE
    owned_skills    = get_owned_skills(user_data)
    equipped_skills = get_equipped_skills(user_data)
    balance = user_data.get("balance", 0)
    builder = InlineKeyboardBuilder()

    for sk_key in items:
        sk      = SKILLS[sk_key]
        is_equip = sk_key in equipped_skills
        is_owned = sk_key in owned_skills

        if is_equip:
            prefix = "⚔️"
        elif is_owned:
            prefix = "✅"
        elif balance >= sk["price"]:
            prefix = "🛒"
        else:
            prefix = "💸"

        btn = InlineKeyboardButton(
            text=f"{prefix} {sk['emoji']} {sk['name']}",
            callback_data=f"duel_skill_card:{sk_key}:{page}",
        )
        builder.row(btn)

    # Пагинация
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"duel_skills_shop_page:{page-1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"duel_skills_shop_page:{page+1}"))
    if nav:
        builder.row(*nav)

    builder.row(InlineKeyboardButton(
        text="Назад", callback_data="duel_skills",
        icon_custom_emoji_id=EMOJI_BACK,
    ))
    return builder.as_markup()


# ════════════════════════════════════════════════════════════
#  ЭКРАН ПОИСКА
# ════════════════════════════════════════════════════════════

def duel_search_text(in_queue_flag: bool = False) -> str:
    if in_queue_flag:
        return (
            f'<tg-emoji emoji-id="{EMOJI_SEARCH}">🔍</tg-emoji> <b>ПОИСК ПРОТИВНИКА</b>\n'
            '━━━━━━━━━━━━━━━━━━━━\n\n'
            '<blockquote>⏳ <b>Ищем соперника...</b>\n\n'
            'Ожидай — как только найдётся противник,\n'
            'бой начнётся автоматически.\n\n'
            '<i>Нажми «Проверить» чтобы обновить статус.</i></blockquote>'
        )
    return (
        f'<tg-emoji emoji-id="{EMOJI_SEARCH}">🔍</tg-emoji> <b>ПОИСК ПРОТИВНИКА</b>\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        '<blockquote>Нажми <b>«Найти бой»</b> для поиска соперника.\n\n'
        'В бою тебе доступны твои навыки из магазина.\n'
        'Урон зависит <b>только от навыков</b> — прокачивай их!\n'
        '🔵 Маг. навыки снижаются магической защитой\n'
        '💥 Физ. навыки снижаются физической защитой\n'
        '🛡️ Щитовые навыки поглощают входящий урон</blockquote>'
    )


def duel_search_keyboard(in_queue_flag: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if in_queue_flag:
        builder.row(InlineKeyboardButton(
            text="🔄 Проверить", callback_data="duel_search_check"
        ))
        builder.row(InlineKeyboardButton(
            text="❌ Отменить поиск", callback_data="duel_search_cancel"
        ))
    else:
        builder.row(InlineKeyboardButton(
            text="⚔️ Найти бой", callback_data="duel_search_start"
        ))
    builder.row(InlineKeyboardButton(
        text="Назад", callback_data="duel_main",
        icon_custom_emoji_id=EMOJI_BACK,
    ))
    return builder.as_markup()


# ════════════════════════════════════════════════════════════
#  ОРИГИНАЛЬНЫЕ ЭКРАНЫ
# ════════════════════════════════════════════════════════════

def duel_main_text() -> str:
    return (
        '<tg-emoji emoji-id="5424972470023104089">⚔️</tg-emoji> <b>ДУЭЛИ</b>\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        '<blockquote>'
        'Испытай себя в бою один на один.\n'
        'Собери снаряжение для защиты, купи навыки для урона\n'
        'и докажи, кто сильнейший в TGStellar.\n\n'
        '⚔️ <b>Урон</b> — даётся навыками из магазина\n'
        '🛡️ <b>Защита</b> — даётся снаряжением'
        '</blockquote>'
    )

def duel_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=" Поиск противника", callback_data="duel_search",
        icon_custom_emoji_id=EMOJI_SEARCH,
    ))
    builder.row(InlineKeyboardButton(
        text=" Бросить вызов", callback_data="duel_challenge_start",
        icon_custom_emoji_id=EMOJI_INVITE,
    ))
    builder.row(
        InlineKeyboardButton(text=" Снаряжение", callback_data="duel_equip",
                             icon_custom_emoji_id=EMOJI_EQUIP),
        InlineKeyboardButton(text=" Навыки", callback_data="duel_skills",
                             icon_custom_emoji_id=EMOJI_SKILLS),
    )
    builder.row(InlineKeyboardButton(
        text=" Характеристики", callback_data="duel_charstats",
        icon_custom_emoji_id=EMOJI_STATS_DUEL,
    ))
    builder.row(InlineKeyboardButton(
        text="Назад", callback_data="back_to_menu",
        icon_custom_emoji_id=EMOJI_BACK,
    ))
    return builder.as_markup()


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

    return (
        '<tg-emoji emoji-id="5445221832074483553">🎒</tg-emoji> <b>СНАРЯЖЕНИЕ</b>\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>{chr(10).join(lines)}</blockquote>\n\n'
        '<i>Снаряжение даёт HP и защиту — урон даётся навыками!</i>'
    )

def duel_equip_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    row_buf = []
    for slot in GEAR_SLOTS_ORDER:
        row_buf.append(InlineKeyboardButton(
            text=f"{slot_emoji(slot)} {slot_label(slot)}",
            callback_data=f"duel_equip_slot:{slot}",
        ))
        if len(row_buf) == 2:
            builder.row(*row_buf)
            row_buf = []
    if row_buf:
        builder.row(*row_buf)
    builder.row(InlineKeyboardButton(
        text="Назад", callback_data="duel_main",
        icon_custom_emoji_id=EMOJI_BACK,
    ))
    return builder.as_markup()


def duel_equip_slot_text(slot: str, user_data: dict) -> str:
    ow_lvl = owned_level(slot, user_data)
    eq_lvl = equipped_level(slot, user_data)
    emoji  = slot_emoji(slot)
    label  = slot_label(slot)

    lines = []
    for lvl in range(1, 6):
        item = GEAR_CATALOG[f"{slot}-lvl{lvl}"]
        if lvl == eq_lvl:
            marker = "✅"
            state  = "<i>надето</i>"
        elif lvl <= ow_lvl:
            marker = "📦"
            state  = "<i>в инвентаре</i>"
        else:
            marker = "🔒"
            state  = f"<i>{_fmt(item['price'])} монет</i>"

        lines.append(f"{marker} <b>[{item['name']}]</b> — {item['ru_name']} · {state}")

    block = "\n".join(lines)
    return (
        f'{emoji} <b>СНАРЯЖЕНИЕ — {label.upper()}</b>\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>{block}</blockquote>\n\n'
        '<i>Нажми на предмет, чтобы узнать подробности</i>'
    )

def duel_equip_slot_keyboard(slot: str, user_data: dict) -> InlineKeyboardMarkup:
    ow_lvl = owned_level(slot, user_data)
    eq_lvl = equipped_level(slot, user_data)
    builder = InlineKeyboardBuilder()

    for lvl in range(1, 6):
        item_key = f"{slot}-lvl{lvl}"
        item     = GEAR_CATALOG[item_key]
        if lvl == eq_lvl:
            btn_text = f"✅ [{item['name']}]"
        elif lvl <= ow_lvl:
            btn_text = f"📦 [{item['name']}]"
        else:
            btn_text = f"🔒 [{item['name']}] — {_fmt(item['price'])} монет"

        builder.row(InlineKeyboardButton(
            text=btn_text,
            callback_data=f"duel_item_card:{item_key}",
        ))

    builder.row(InlineKeyboardButton(
        text="Назад", callback_data="duel_equip",
        icon_custom_emoji_id=EMOJI_BACK,
    ))
    return builder.as_markup()


def duel_item_card_text(item_key: str, user_data: dict) -> str:
    item   = GEAR_CATALOG[item_key]
    slot   = item["slot"]
    ow_lvl = owned_level(slot, user_data)
    eq_lvl = equipped_level(slot, user_data)
    lvl    = item["level"]
    balance = user_data.get("balance", 0)

    if lvl == eq_lvl:
        status_line = '✅ <b>Надето прямо сейчас</b>'
    elif lvl <= ow_lvl:
        status_line = '📦 <b>Есть в инвентаре</b> — не надето'
    else:
        status_line = f'💰 <b>Цена: {_fmt(item["price"])} монет</b>'
        if balance < item["price"]:
            deficit = item["price"] - balance
            status_line += f'\n⚠️ <i>Не хватает {_fmt(deficit)} монет</i>'

    bonus_lines = []
    for stat, val in item["bonus"].items():
        if stat == "dmg":
            continue
        emoji_s, ru, unit = STAT_META.get(stat, ("▫️", stat, ""))
        bonus_lines.append(f'  {emoji_s} <b>+{val}</b> {ru} <i>({unit})</i>')
    bonus_block = "\n".join(bonus_lines)

    stars = "⭐" * lvl + "☆" * (5 - lvl)

    return (
        f'{item["emoji_char"]} <b>{item["name"]}</b>\n'
        f'<i>{item["ru_name"]}</i>  {stars}\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>{item["description"]}</blockquote>\n\n'
        f'<b>Боевые бонусы (защита и HP):</b>\n{bonus_block}\n\n'
        f'<i>💡 Урон в дуэли даётся навыками, а не снаряжением!</i>\n\n'
        f'{status_line}'
    )

def duel_item_card_keyboard(item_key: str, user_data: dict) -> InlineKeyboardMarkup:
    item   = GEAR_CATALOG[item_key]
    slot   = item["slot"]
    ow_lvl = owned_level(slot, user_data)
    eq_lvl = equipped_level(slot, user_data)
    lvl    = item["level"]
    balance = user_data.get("balance", 0)
    builder = InlineKeyboardBuilder()

    if lvl == eq_lvl:
        builder.row(InlineKeyboardButton(
            text="❌ Снять",
            callback_data=f"duel_gear_unequip:{item_key}",
        ))
    elif lvl <= ow_lvl:
        builder.row(InlineKeyboardButton(
            text="✅ Надеть",
            callback_data=f"duel_gear_equip:{item_key}",
        ))
    else:
        if balance >= item["price"]:
            builder.row(InlineKeyboardButton(
                text=f"🛒 Купить — {_fmt(item['price'])} монет",
                callback_data=f"duel_gear_buy:{item_key}",
            ))
        else:
            builder.row(InlineKeyboardButton(
                text=f"💸 Недостаточно монет",
                callback_data="duel_gear_nofunds",
            ))

    builder.row(InlineKeyboardButton(
        text="Назад", callback_data=f"duel_equip_slot:{slot}",
        icon_custom_emoji_id=EMOJI_BACK,
    ))
    return builder.as_markup()


def apply_gear_purchase(item_key: str, user_data: dict) -> dict:
    owned    = user_data.setdefault("duel_owned_gear", [])
    equipped = user_data.setdefault("duel_equipped", {})
    if item_key not in owned:
        owned.append(item_key)
    slot = GEAR_CATALOG[item_key]["slot"]
    equipped[slot] = item_key
    return user_data

def apply_gear_equip(item_key: str, user_data: dict) -> dict:
    slot = GEAR_CATALOG[item_key]["slot"]
    user_data.setdefault("duel_equipped", {})[slot] = item_key
    return user_data

def apply_gear_unequip(item_key: str, user_data: dict) -> dict:
    slot     = GEAR_CATALOG[item_key]["slot"]
    equipped = user_data.setdefault("duel_equipped", {})
    if equipped.get(slot) == item_key:
        del equipped[slot]
    return user_data


def duel_charstats_text(user_data: dict, uid: int = None) -> str:
    s          = _calc_stats(user_data)
    equipped   = user_data.get("duel_equipped", {})
    gear_count = len(equipped)
    gear_line  = f"надето {gear_count}/5 предм." if gear_count else "снаряжение не надето"
    owned_sk   = get_owned_skills(user_data)
    sk_count   = len(owned_sk)

    # Текущий HP (если uid передан)
    if uid is not None:
        current_hp = get_player_hp(uid, user_data)
        hp_max     = s["hp"]
        hp_display = f"{current_hp}/{hp_max}"
        hp_regen_note = ""
        if current_hp < 100:
            secs = player_hp_regen_seconds(uid, user_data)
            hp_regen_note = (
                f'\n⚠️ <b>HP восстанавливается</b> (+{HP_REGEN_AMOUNT} каждые {HP_REGEN_INTERVAL} сек.)\n'
                f'Следующий тик через <b>{secs} сек.</b>\n'
                f'<i>Нельзя начать бой пока HP &lt; 100</i>\n'
            )
    else:
        hp_display    = str(s["hp"])
        hp_regen_note = ""

    return (
        f'<tg-emoji emoji-id="{EMOJI_STATS_DUEL}">📊</tg-emoji> <b>ХАРАКТЕРИСТИКИ</b>\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        '<blockquote>'
        f'<tg-emoji emoji-id="{EMOJI_HP}">❤️</tg-emoji> <b>Здоровье</b> — <b>{hp_display}</b> HP\n\n'
        f'<tg-emoji emoji-id="{EMOJI_REGEN}">💚</tg-emoji> <b>Регенерация</b> — <b>{s["regen"]}</b> HP/ход\n\n'
        f'<tg-emoji emoji-id="{EMOJI_PHYS_DEF}">🛡️</tg-emoji> <b>Физ. защита</b> — <b>{s["phys_def"]}</b> DEF\n\n'
        f'<tg-emoji emoji-id="{EMOJI_MAG_DEF}">🔮</tg-emoji> <b>Маг. защита</b> — <b>{s["mag_def"]}</b> MDEF\n\n'
        f'<tg-emoji emoji-id="{EMOJI_STAMINA}">⚙️</tg-emoji> <b>Стойкость</b> — <b>{s["stamina"]}</b> STM'
        '</blockquote>\n'
        f'{hp_regen_note}\n'
        f'🎽 <i>Снаряжение: {gear_line}</i>\n'
        f'⚔️ <i>Навыков куплено: {sk_count} шт.</i>\n\n'
        f'<i>💡 Урон в дуэли зависит от купленных навыков,\nа не от снаряжения!</i>'
    )

def duel_charstats_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="Снаряжение", callback_data="duel_equip",
        icon_custom_emoji_id=EMOJI_EQUIP,
    ))
    builder.row(InlineKeyboardButton(
        text="Назад", callback_data="duel_main",
        icon_custom_emoji_id=EMOJI_BACK,
    ))
    return builder.as_markup()


# ── Экран навыков (обзор + ссылка в магазин) ─────────────────

def duel_skills_text(user_data: dict = None) -> str:
    base_lines = []
    for sk_key in SKILLS_ORDER_BASE:
        sk = SKILLS[sk_key]
        base_lines.append(f"{sk['emoji']} <b>{sk['name']}</b> — <i>{sk['description']}</i>")
    base_block = "\n".join(base_lines)

    paid_count = len([k for k, v in SKILLS.items() if v["price"] > 0])

    # Экипированные навыки
    equip_block = ""
    if user_data:
        equipped = get_equipped_skills(user_data)
        if equipped:
            eq_lines = []
            for sk_key in equipped:
                sk = SKILLS.get(sk_key)
                if sk:
                    if sk["type"] == "shield":
                        val = f"щит {sk['shield_amount'][0]}–{sk['shield_amount'][1]} HP"
                    else:
                        val = f"урон {sk['base_dmg'][0]}–{sk['base_dmg'][1]}"
                    eq_lines.append(f"⚔️ {sk['emoji']} <b>{sk['name']}</b> · {val}")
            equip_block = (
                f"\n\n<blockquote><b>⚔️ Экипировано в бой ({len(equipped)}/{MAX_EQUIPPED_SKILLS}):</b>\n"
                + "\n".join(eq_lines)
                + "\n<i>Только эти навыки доступны в дуэли!</i></blockquote>"
            )
        else:
            equip_block = (
                f"\n\n<blockquote>⚠️ <b>Ни один навык не экипирован в бой!</b>\n"
                f"Перейди в магазин и экипируй до {MAX_EQUIPPED_SKILLS} навыков.</blockquote>"
            )

    return (
        f'<tg-emoji emoji-id="{EMOJI_SKILLS}">✨</tg-emoji> <b>БОЕВЫЕ НАВЫКИ</b>\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote><b>🆓 Базовые навыки (бесплатно):</b>\n\n{base_block}</blockquote>\n\n'
        f'<blockquote>🛒 <b>В магазине доступно ещё {paid_count} навыков</b>\n'
        f'от слабых ударов до разрушительных ультимейтов!\n\n'
        f'💡 <i>Экипируй до {MAX_EQUIPPED_SKILLS} навыков — именно они будут доступны в бою!</i></blockquote>'
        f'{equip_block}'
    )

def duel_skills_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="🛒 Магазин навыков", callback_data="duel_skills_shop",
    ))
    builder.row(InlineKeyboardButton(
        text="Назад", callback_data="duel_main",
        icon_custom_emoji_id=EMOJI_BACK,
    ))
    return builder.as_markup()


def duel_challenge_screen_text() -> str:
    return (
        f'<tg-emoji emoji-id="{EMOJI_INVITE}">⚔️</tg-emoji> <b>БРОСИТЬ ВЫЗОВ</b>\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        '<blockquote>'
        'Отправь <b>ID</b> или <b>@юзернейм</b> игрока которого хочешь вызвать на дуэль.\n\n'
        'Примеры:\n'
        '<code>123456789</code>\n'
        '<code>@username</code>\n\n'
        '⏳ <i>Вызов действует 2 минуты — если противник не ответит, он истечёт.</i>'
        '</blockquote>'
    )


def duel_challenge_screen_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="Назад", callback_data="duel_main",
        icon_custom_emoji_id=EMOJI_BACK,
    ))
    return builder.as_markup()


def duel_challenge_sent_text(target_name: str) -> str:
    return (
        f'⚔️ <b>Вызов отправлен!</b>\n\n'
        f'<blockquote>👤 <b>{target_name}</b> получил твой вызов.\n'
        f'⏳ Ожидай ответа — у него есть 2 минуты.</blockquote>'
    )


def duel_challenge_sent_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="❌ Отменить вызов", callback_data="duel_challenge_cancel",
    ))
    builder.row(InlineKeyboardButton(
        text="Назад", callback_data="duel_main",
        icon_custom_emoji_id=EMOJI_BACK,
    ))
    return builder.as_markup()


def duel_hp_status_text(uid: int, user_data: dict) -> str:
    """Текст статуса HP для отображения в поиске/вызове."""
    hp     = get_player_hp(uid, user_data)
    hp_max = _calc_stats(user_data)["hp"]
    if hp >= 100:
        return ""
    secs = player_hp_regen_seconds(uid, user_data)
    return (
        f'\n\n<blockquote>'
        f'⚠️ <b>Твоё HP: {hp}/{hp_max}</b>\n'
        f'Восстановление: +{HP_REGEN_AMOUNT} HP каждые {HP_REGEN_INTERVAL} сек.\n'
        f'Следующий тик через <b>{secs} сек.</b>\n'
        f'<i>Нельзя начать бой пока HP &lt; 100!</i>'
        f'</blockquote>'
    )



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
    builder.row(InlineKeyboardButton(
        text="Назад", callback_data="duel_main",
        icon_custom_emoji_id=EMOJI_BACK,
    ))
    return builder.as_markup()
