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

EMOJI_HP       = "5337080053119336309"
EMOJI_DMG      = "5337080053119336309"
EMOJI_REGEN    = "5438224604499819092"
EMOJI_PHYS_DEF = "5465154440287757794"
EMOJI_MAG_DEF  = "5321022334335724730"
EMOJI_STAMINA  = "5251281810729480172"

# ── Метки статов ────────────────────────────────────────────
STAT_META = {
    "hp":       ('<tg-emoji emoji-id="5337080053119336309">❤️</tg-emoji>', "Здоровье",    "HP"),
    "dmg":      ("⚔️", "Урон",        "ATK"),
    "regen":    ('<tg-emoji emoji-id="5438224604499819092">💚</tg-emoji>', "Регенерация", "HP/ход"),
    "phys_def": ('<tg-emoji emoji-id="5465154440287757794">🛡️</tg-emoji>', "Физ. защита", "DEF"),
    "mag_def":  ('<tg-emoji emoji-id="5321022334335724730">🔮</tg-emoji>', "Маг. защита", "MDEF"),
    "stamina":  ('<tg-emoji emoji-id="5251281810729480172">⚙️</tg-emoji>', "Стойкость",   "STM"),
}

# ── Каталог снаряжения: 5 слотов × 25 уровней ────────────────
# ВАЖНО: снаряжение даёт только HP, защиту, регенерацию, стойкость — НЕ урон!
GEAR_CATALOG = {

    # ── ШЛЕМ ────────────────────────────────────────
    "helmet-lvl1": {
        "slot": "helmet", "level": 1, "key": "helmet-lvl1",
        "name": "Helmet Lvl 1", "ru_name": "Железный Шлем",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 5_000,
        "description": "Грубо выкованный железный шлем. Надёжно прикрывает голову от первого удара.",
        "bonus": {"hp": 10, "phys_def": 3},
    },
    "helmet-lvl2": {
        "slot": "helmet", "level": 2, "key": "helmet-lvl2",
        "name": "Helmet Lvl 2", "ru_name": "Боевой Шлем",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 7_000,
        "description": "Усиленный шлем с рунической вставкой. Рассеивает слабые магические атаки.",
        "bonus": {"hp": 56, "phys_def": 14, "mag_def": 13},
    },
    "helmet-lvl3": {
        "slot": "helmet", "level": 3, "key": "helmet-lvl3",
        "name": "Helmet Lvl 3", "ru_name": "Шлем Гвардейца",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 9_000,
        "description": "Закалённый шлем королевской гвардии с забралом из мифрила.",
        "bonus": {"hp": 91, "phys_def": 22, "mag_def": 19, "stamina": 5},
    },
    "helmet-lvl4": {
        "slot": "helmet", "level": 4, "key": "helmet-lvl4",
        "name": "Helmet Lvl 4", "ru_name": "Шлем Стального Стража",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 13_000,
        "description": "Реликвийный шлем с рунической гравировкой. Входящий урон частично поглощается барьером.",
        "bonus": {"hp": 122, "phys_def": 29, "mag_def": 25, "stamina": 12},
    },
    "helmet-lvl5": {
        "slot": "helmet", "level": 5, "key": "helmet-lvl5",
        "name": "Helmet Lvl 5", "ru_name": "Шлем Легенды",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 18_000,
        "description": "Артефакт эпохи Первых Воинов. Ни одна стрела не может поколебать носителя.",
        "bonus": {"hp": 151, "phys_def": 36, "mag_def": 30, "stamina": 17},
    },
    "helmet-lvl6": {
        "slot": "helmet", "level": 6, "key": "helmet-lvl6",
        "name": "Helmet Lvl 6", "ru_name": "Шлем Ветерана",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 24_000,
        "description": "Шлем опытного воина, прошедшего сотни битв. Несёт следы многих поединков.",
        "bonus": {"hp": 178, "phys_def": 42, "mag_def": 35, "stamina": 21},
    },
    "helmet-lvl7": {
        "slot": "helmet", "level": 7, "key": "helmet-lvl7",
        "name": "Helmet Lvl 7", "ru_name": "Шлем Рыцаря",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 33_000,
        "description": "Латный шлем рыцаря с плюмажем из перьев феникса. Символ доблести.",
        "bonus": {"hp": 205, "phys_def": 48, "mag_def": 40, "stamina": 25},
    },
    "helmet-lvl8": {
        "slot": "helmet", "level": 8, "key": "helmet-lvl8",
        "name": "Helmet Lvl 8", "ru_name": "Шлем Паладина",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 46_000,
        "description": "Священный шлем паладина, освящённый в храме. Отражает тёмную магию.",
        "bonus": {"hp": 230, "phys_def": 54, "mag_def": 44, "stamina": 29},
    },
    "helmet-lvl9": {
        "slot": "helmet", "level": 9, "key": "helmet-lvl9",
        "name": "Helmet Lvl 9", "ru_name": "Шлем Воителя",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 65_000,
        "description": "Боевой шлем прославленного воителя. Видавший победы и поражения.",
        "bonus": {"hp": 255, "phys_def": 60, "mag_def": 49, "stamina": 33},
    },
    "helmet-lvl10": {
        "slot": "helmet", "level": 10, "key": "helmet-lvl10",
        "name": "Helmet Lvl 10", "ru_name": "Шлем Чемпиона",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 85_000,
        "description": "Шлем чемпиона арены. Украшен рунами побед над сильнейшими.",
        "bonus": {"hp": 279, "phys_def": 66, "mag_def": 53, "stamina": 37},
    },
    "helmet-lvl11": {
        "slot": "helmet", "level": 11, "key": "helmet-lvl11",
        "name": "Helmet Lvl 11", "ru_name": "Шлем Берсерка",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 120_000,
        "description": "Шлем берсерка с рогами ледяного быка. Дарует ярость в бою.",
        "bonus": {"hp": 303, "phys_def": 71, "mag_def": 57, "stamina": 40},
    },
    "helmet-lvl12": {
        "slot": "helmet", "level": 12, "key": "helmet-lvl12",
        "name": "Helmet Lvl 12", "ru_name": "Шлем Темпляра",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 165_000,
        "description": "Шлем ордена темпляров из освящённой стали. Непробиваем для нечисти.",
        "bonus": {"hp": 326, "phys_def": 76, "mag_def": 61, "stamina": 44},
    },
    "helmet-lvl13": {
        "slot": "helmet", "level": 13, "key": "helmet-lvl13",
        "name": "Helmet Lvl 13", "ru_name": "Шлем Стражника Бездны",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 225_000,
        "description": "Таинственный шлем из бездонных глубин. Поглощает тёмную энергию.",
        "bonus": {"hp": 349, "phys_def": 82, "mag_def": 65, "stamina": 47},
    },
    "helmet-lvl14": {
        "slot": "helmet", "level": 14, "key": "helmet-lvl14",
        "name": "Helmet Lvl 14", "ru_name": "Шлем Повелителя",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 300_000,
        "description": "Шлем Повелителя армий. Золотая инкрустация скрывает мощнейшие руны.",
        "bonus": {"hp": 371, "phys_def": 87, "mag_def": 69, "stamina": 51},
    },
    "helmet-lvl15": {
        "slot": "helmet", "level": 15, "key": "helmet-lvl15",
        "name": "Helmet Lvl 15", "ru_name": "Шлем Завоевателя",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 425_000,
        "description": "Шлем завоевателя миров. Слава его обладателя гремит по всем землям.",
        "bonus": {"hp": 393, "phys_def": 92, "mag_def": 73, "stamina": 54},
    },
    "helmet-lvl16": {
        "slot": "helmet", "level": 16, "key": "helmet-lvl16",
        "name": "Helmet Lvl 16", "ru_name": "Шлем Драконьей Гвардии",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 575_000,
        "description": "Шлем элитной гвардии дракона. Чешуя дракона вплавлена в металл.",
        "bonus": {"hp": 415, "phys_def": 97, "mag_def": 77, "stamina": 57},
    },
    "helmet-lvl17": {
        "slot": "helmet", "level": 17, "key": "helmet-lvl17",
        "name": "Helmet Lvl 17", "ru_name": "Шлем Арканиста",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 800_000,
        "description": "Шлем великого арканиста. Фокусирует магическую энергию вокруг головы.",
        "bonus": {"hp": 437, "phys_def": 102, "mag_def": 81, "stamina": 60},
    },
    "helmet-lvl18": {
        "slot": "helmet", "level": 18, "key": "helmet-lvl18",
        "name": "Helmet Lvl 18", "ru_name": "Шлем Вечного Воина",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 1_100_000,
        "description": "Шлем воина, пережившего тысячелетия. Прочнее любого современного металла.",
        "bonus": {"hp": 458, "phys_def": 107, "mag_def": 85, "stamina": 63},
    },
    "helmet-lvl19": {
        "slot": "helmet", "level": 19, "key": "helmet-lvl19",
        "name": "Helmet Lvl 19", "ru_name": "Шлем Короля",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 1_500_000,
        "description": "Шлем законного правителя. Никто не смеет поднять руку на его обладателя.",
        "bonus": {"hp": 479, "phys_def": 112, "mag_def": 88, "stamina": 66},
    },
    "helmet-lvl20": {
        "slot": "helmet", "level": 20, "key": "helmet-lvl20",
        "name": "Helmet Lvl 20", "ru_name": "Шлем Небес",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 2_100_000,
        "description": "Шлем небесного воителя. Ниспослан богами избранному герою.",
        "bonus": {"hp": 499, "phys_def": 117, "mag_def": 92, "stamina": 70},
    },
    "helmet-lvl21": {
        "slot": "helmet", "level": 21, "key": "helmet-lvl21",
        "name": "Helmet Lvl 21", "ru_name": "Шлем Титана",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 2_800_000,
        "description": "Шлем из кости Первородного Титана. Тяжелее горы, прочнее скалы.",
        "bonus": {"hp": 520, "phys_def": 121, "mag_def": 96, "stamina": 73},
    },
    "helmet-lvl22": {
        "slot": "helmet", "level": 22, "key": "helmet-lvl22",
        "name": "Helmet Lvl 22", "ru_name": "Шлем Астрального Стража",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 3_900_000,
        "description": "Астральный шлем, соткан из звёздного металла. Защищает даже душу.",
        "bonus": {"hp": 540, "phys_def": 126, "mag_def": 99, "stamina": 76},
    },
    "helmet-lvl23": {
        "slot": "helmet", "level": 23, "key": "helmet-lvl23",
        "name": "Helmet Lvl 23", "ru_name": "Шлем Первородного",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 5_250_000,
        "description": "Шлем Первородного Воина — до него никто не выжил в тысяче дуэлей.",
        "bonus": {"hp": 560, "phys_def": 131, "mag_def": 103, "stamina": 78},
    },
    "helmet-lvl24": {
        "slot": "helmet", "level": 24, "key": "helmet-lvl24",
        "name": "Helmet Lvl 24", "ru_name": "Шлем Богоборца",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 7_250_000,
        "description": "Шлем Богоборца. Даже боги дрогнули перед его обладателем.",
        "bonus": {"hp": 580, "phys_def": 135, "mag_def": 106, "stamina": 81},
    },
    "helmet-lvl25": {
        "slot": "helmet", "level": 25, "key": "helmet-lvl25",
        "name": "Helmet Lvl 25", "ru_name": "Шлем Абсолюта",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 10_000_000,
        "description": "Абсолютный артефакт. Вершина защиты, недостижимая смертными.",
        "bonus": {"hp": 600, "phys_def": 140, "mag_def": 110, "stamina": 84},
    },

    # ── БРОНЯ ────────────────────────────────────────
    "armor-lvl1": {
        "slot": "armor", "level": 1, "key": "armor-lvl1",
        "name": "Armor Lvl 1", "ru_name": "Кожаный Доспех",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 6_000,
        "description": "Доспех из дублёной кожи. Лёгкий, не сковывает движений.",
        "bonus": {"hp": 15, "phys_def": 5},
    },
    "armor-lvl2": {
        "slot": "armor", "level": 2, "key": "armor-lvl2",
        "name": "Armor Lvl 2", "ru_name": "Кольчужный Доспех",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 8_000,
        "description": "Тысячи закалённых колец. Хорошо поглощает рубящие удары.",
        "bonus": {"hp": 85, "phys_def": 19, "stamina": 5},
    },
    "armor-lvl3": {
        "slot": "armor", "level": 3, "key": "armor-lvl3",
        "name": "Armor Lvl 3", "ru_name": "Пластинчатый Доспех",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 11_000,
        "description": "Боевые латы из стальных пластин. Сводят урон к минимуму.",
        "bonus": {"hp": 136, "phys_def": 30, "stamina": 15},
    },
    "armor-lvl4": {
        "slot": "armor", "level": 4, "key": "armor-lvl4",
        "name": "Armor Lvl 4", "ru_name": "Латы Воина Бездны",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 16_000,
        "description": "Прочнейшие латы, выкованные в жерле вулкана тёмными кузнецами.",
        "bonus": {"hp": 183, "phys_def": 39, "stamina": 22, "mag_def": 8},
    },
    "armor-lvl5": {
        "slot": "armor", "level": 5, "key": "armor-lvl5",
        "name": "Armor Lvl 5", "ru_name": "Латы Абсолюта",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 21_000,
        "description": "Легендарный доспех. Выкован из металла упавшей звезды.",
        "bonus": {"hp": 226, "phys_def": 48, "stamina": 29, "mag_def": 16},
    },
    "armor-lvl6": {
        "slot": "armor", "level": 6, "key": "armor-lvl6",
        "name": "Armor Lvl 6", "ru_name": "Доспех Ветерана",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 29_000,
        "description": "Доспех ветерана, переживший сотни сражений. Каждая вмятина — история.",
        "bonus": {"hp": 267, "phys_def": 56, "stamina": 35, "mag_def": 23},
    },
    "armor-lvl7": {
        "slot": "armor", "level": 7, "key": "armor-lvl7",
        "name": "Armor Lvl 7", "ru_name": "Доспех Крепости",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 40_000,
        "description": "Монолитный доспех, прочный как крепостная стена.",
        "bonus": {"hp": 307, "phys_def": 64, "stamina": 41, "mag_def": 28},
    },
    "armor-lvl8": {
        "slot": "armor", "level": 8, "key": "armor-lvl8",
        "name": "Armor Lvl 8", "ru_name": "Латы Паладина",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 55_000,
        "description": "Освящённые латы паладина. Тёмная сила отступает перед ними.",
        "bonus": {"hp": 345, "phys_def": 72, "stamina": 46, "mag_def": 34},
    },
    "armor-lvl9": {
        "slot": "armor", "level": 9, "key": "armor-lvl9",
        "name": "Armor Lvl 9", "ru_name": "Броня Воителя",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 75_000,
        "description": "Тяжёлые боевые латы великого воителя.",
        "bonus": {"hp": 382, "phys_def": 80, "stamina": 52, "mag_def": 39},
    },
    "armor-lvl10": {
        "slot": "armor", "level": 10, "key": "armor-lvl10",
        "name": "Armor Lvl 10", "ru_name": "Доспех Чемпиона",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 105_000,
        "description": "Доспех чемпиона. Противники дрожат, видя его.",
        "bonus": {"hp": 419, "phys_def": 87, "stamina": 57, "mag_def": 43},
    },
    "armor-lvl11": {
        "slot": "armor", "level": 11, "key": "armor-lvl11",
        "name": "Armor Lvl 11", "ru_name": "Латы Берсерка",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 140_000,
        "description": "Безумные латы берсерка. Впитали кровь тысяч врагов.",
        "bonus": {"hp": 454, "phys_def": 94, "stamina": 62, "mag_def": 48},
    },
    "armor-lvl12": {
        "slot": "armor", "level": 12, "key": "armor-lvl12",
        "name": "Armor Lvl 12", "ru_name": "Доспех Темпляра",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 195_000,
        "description": "Священные доспехи темпляров. Прочнее любых известных материалов.",
        "bonus": {"hp": 489, "phys_def": 101, "stamina": 67, "mag_def": 52},
    },
    "armor-lvl13": {
        "slot": "armor", "level": 13, "key": "armor-lvl13",
        "name": "Armor Lvl 13", "ru_name": "Броня Тёмного Стража",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 275_000,
        "description": "Тёмная броня стражей бездны. Поглощает тёмные проклятия.",
        "bonus": {"hp": 523, "phys_def": 108, "stamina": 72, "mag_def": 57},
    },
    "armor-lvl14": {
        "slot": "armor", "level": 14, "key": "armor-lvl14",
        "name": "Armor Lvl 14", "ru_name": "Латы Повелителя",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 375_000,
        "description": "Золочёные латы Повелителя армий с магическим ядром.",
        "bonus": {"hp": 557, "phys_def": 115, "stamina": 77, "mag_def": 61},
    },
    "armor-lvl15": {
        "slot": "armor", "level": 15, "key": "armor-lvl15",
        "name": "Armor Lvl 15", "ru_name": "Доспех Завоевателя",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 500_000,
        "description": "Непробиваемые доспехи завоевателя. Выкованы из драконьей кости.",
        "bonus": {"hp": 590, "phys_def": 122, "stamina": 82, "mag_def": 65},
    },
    "armor-lvl16": {
        "slot": "armor", "level": 16, "key": "armor-lvl16",
        "name": "Armor Lvl 16", "ru_name": "Чешуйчатый Доспех Дракона",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 700_000,
        "description": "Чешуя Древнего Дракона — каждая пластина крепче стали.",
        "bonus": {"hp": 623, "phys_def": 129, "stamina": 86, "mag_def": 69},
    },
    "armor-lvl17": {
        "slot": "armor", "level": 17, "key": "armor-lvl17",
        "name": "Armor Lvl 17", "ru_name": "Аркановые Латы",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 950_000,
        "description": "Аркановые латы сотканы из застывшей магии. Меняют форму под удар.",
        "bonus": {"hp": 655, "phys_def": 135, "stamina": 91, "mag_def": 74},
    },
    "armor-lvl18": {
        "slot": "armor", "level": 18, "key": "armor-lvl18",
        "name": "Armor Lvl 18", "ru_name": "Броня Вечного Воина",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 1_300_000,
        "description": "Доспех, который не берут ни годы, ни оружие.",
        "bonus": {"hp": 687, "phys_def": 142, "stamina": 95, "mag_def": 78},
    },
    "armor-lvl19": {
        "slot": "armor", "level": 19, "key": "armor-lvl19",
        "name": "Armor Lvl 19", "ru_name": "Королевские Латы",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 1_800_000,
        "description": "Парадные королевские латы со спрятанными зачарованиями.",
        "bonus": {"hp": 718, "phys_def": 148, "stamina": 100, "mag_def": 81},
    },
    "armor-lvl20": {
        "slot": "armor", "level": 20, "key": "armor-lvl20",
        "name": "Armor Lvl 20", "ru_name": "Доспех Небес",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 2_500_000,
        "description": "Небесный доспех, откованный богами для избранного воина.",
        "bonus": {"hp": 749, "phys_def": 154, "stamina": 104, "mag_def": 85},
    },
    "armor-lvl21": {
        "slot": "armor", "level": 21, "key": "armor-lvl21",
        "name": "Armor Lvl 21", "ru_name": "Латы Титана",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 3_400_000,
        "description": "Кость первого Титана — вот из чего создан этот доспех.",
        "bonus": {"hp": 780, "phys_def": 161, "stamina": 109, "mag_def": 89},
    },
    "armor-lvl22": {
        "slot": "armor", "level": 22, "key": "armor-lvl22",
        "name": "Armor Lvl 22", "ru_name": "Астральная Броня",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 4_600_000,
        "description": "Астральные латы, закалённые в ткани самого пространства.",
        "bonus": {"hp": 810, "phys_def": 167, "stamina": 113, "mag_def": 93},
    },
    "armor-lvl23": {
        "slot": "armor", "level": 23, "key": "armor-lvl23",
        "name": "Armor Lvl 23", "ru_name": "Доспех Первородного",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 6_250_000,
        "description": "Броня Первородного: выдержала удар самой Смерти.",
        "bonus": {"hp": 840, "phys_def": 173, "stamina": 117, "mag_def": 97},
    },
    "armor-lvl24": {
        "slot": "armor", "level": 24, "key": "armor-lvl24",
        "name": "Armor Lvl 24", "ru_name": "Латы Богоборца",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 8_750_000,
        "description": "Доспех Богоборца. Ни один бог не пробил его.",
        "bonus": {"hp": 870, "phys_def": 179, "stamina": 122, "mag_def": 100},
    },
    "armor-lvl25": {
        "slot": "armor", "level": 25, "key": "armor-lvl25",
        "name": "Armor Lvl 25", "ru_name": "Доспех Абсолюта",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 12_000_000,
        "description": "Абсолютная броня. Конец и вершина любой защиты.",
        "bonus": {"hp": 900, "phys_def": 185, "stamina": 126, "mag_def": 104},
    },

    # ── ПЕРЧАТКИ ────────────────────────────────────────
    "gloves-lvl1": {
        "slot": "gloves", "level": 1, "key": "gloves-lvl1",
        "name": "Gloves Lvl 1", "ru_name": "Боевые Рукавицы",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 4_000,
        "description": "Кожаные рукавицы с наклёпками. Защищают кулаки.",
        "bonus": {"stamina": 5, "phys_def": 2},
    },
    "gloves-lvl2": {
        "slot": "gloves", "level": 2, "key": "gloves-lvl2",
        "name": "Gloves Lvl 2", "ru_name": "Латные Рукавицы",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 5_000,
        "description": "Рукавицы с металлическими пластинами. Усиливают хват оружия.",
        "bonus": {"stamina": 23, "phys_def": 10},
    },
    "gloves-lvl3": {
        "slot": "gloves", "level": 3, "key": "gloves-lvl3",
        "name": "Gloves Lvl 3", "ru_name": "Наручи Теневого Клинка",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 8_000,
        "description": "Боевые наручи с выдвижными шипами. Оружие теневых воинов.",
        "bonus": {"stamina": 36, "phys_def": 15, "mag_def": 3},
    },
    "gloves-lvl4": {
        "slot": "gloves", "level": 4, "key": "gloves-lvl4",
        "name": "Gloves Lvl 4", "ru_name": "Наручи Убийцы",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 10_000,
        "description": "Зачарованные наручи элитных убийц гильдии Алой Тени.",
        "bonus": {"stamina": 48, "phys_def": 21, "mag_def": 9},
    },
    "gloves-lvl5": {
        "slot": "gloves", "level": 5, "key": "gloves-lvl5",
        "name": "Gloves Lvl 5", "ru_name": "Длани Хаоса",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 14_000,
        "description": "Артефактные перчатки, пронизанные энергией первозданного хаоса.",
        "bonus": {"stamina": 59, "phys_def": 25, "mag_def": 14, "regen": 3},
    },
    "gloves-lvl6": {
        "slot": "gloves", "level": 6, "key": "gloves-lvl6",
        "name": "Gloves Lvl 6", "ru_name": "Наручи Ветерана",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 19_000,
        "description": "Потрёпанные наручи с историей. Каждый ремешок — знак победы.",
        "bonus": {"stamina": 69, "phys_def": 30, "mag_def": 18, "regen": 7},
    },
    "gloves-lvl7": {
        "slot": "gloves", "level": 7, "key": "gloves-lvl7",
        "name": "Gloves Lvl 7", "ru_name": "Рукавицы Чемпиона",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 27_000,
        "description": "Тяжёлые латные рукавицы чемпиона арены.",
        "bonus": {"stamina": 79, "phys_def": 34, "mag_def": 21, "regen": 9},
    },
    "gloves-lvl8": {
        "slot": "gloves", "level": 8, "key": "gloves-lvl8",
        "name": "Gloves Lvl 8", "ru_name": "Наручи Паладина",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 37_000,
        "description": "Освящённые наручи паладина. Отражают магические удары.",
        "bonus": {"stamina": 89, "phys_def": 39, "mag_def": 25, "regen": 12},
    },
    "gloves-lvl9": {
        "slot": "gloves", "level": 9, "key": "gloves-lvl9",
        "name": "Gloves Lvl 9", "ru_name": "Перчатки Воителя",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 50_000,
        "description": "Мощные рукавицы великого воителя. Хватка — как тиски.",
        "bonus": {"stamina": 98, "phys_def": 43, "mag_def": 28, "regen": 14},
    },
    "gloves-lvl10": {
        "slot": "gloves", "level": 10, "key": "gloves-lvl10",
        "name": "Gloves Lvl 10", "ru_name": "Наручи Победителя",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 70_000,
        "description": "Наручи победителя. Никто не выбил оружие из этих рук.",
        "bonus": {"stamina": 108, "phys_def": 47, "mag_def": 32, "regen": 16},
    },
    "gloves-lvl11": {
        "slot": "gloves", "level": 11, "key": "gloves-lvl11",
        "name": "Gloves Lvl 11", "ru_name": "Рукавицы Берсерка",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 95_000,
        "description": "Безумные рукавицы берсерка. Покрыты шипами и рунами ярости.",
        "bonus": {"stamina": 117, "phys_def": 51, "mag_def": 35, "regen": 19},
    },
    "gloves-lvl12": {
        "slot": "gloves", "level": 12, "key": "gloves-lvl12",
        "name": "Gloves Lvl 12", "ru_name": "Наручи Темпляра",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 130_000,
        "description": "Наручи темпляров. Выдерживают прямые удары двуручным мечом.",
        "bonus": {"stamina": 126, "phys_def": 55, "mag_def": 38, "regen": 21},
    },
    "gloves-lvl13": {
        "slot": "gloves", "level": 13, "key": "gloves-lvl13",
        "name": "Gloves Lvl 13", "ru_name": "Перчатки Тёмного Убийцы",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 180_000,
        "description": "Перчатки из тёмной кожи. Пропитаны ядом и тьмой.",
        "bonus": {"stamina": 134, "phys_def": 58, "mag_def": 41, "regen": 23},
    },
    "gloves-lvl14": {
        "slot": "gloves", "level": 14, "key": "gloves-lvl14",
        "name": "Gloves Lvl 14", "ru_name": "Наручи Повелителя",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 250_000,
        "description": "Золотые наручи Повелителя. Скрывают клинки под пластинами.",
        "bonus": {"stamina": 143, "phys_def": 62, "mag_def": 44, "regen": 24},
    },
    "gloves-lvl15": {
        "slot": "gloves", "level": 15, "key": "gloves-lvl15",
        "name": "Gloves Lvl 15", "ru_name": "Длани Завоевателя",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 325_000,
        "description": "Длани завоевателя сокрушали врата крепостей.",
        "bonus": {"stamina": 151, "phys_def": 66, "mag_def": 47, "regen": 26},
    },
    "gloves-lvl16": {
        "slot": "gloves", "level": 16, "key": "gloves-lvl16",
        "name": "Gloves Lvl 16", "ru_name": "Перчатки Дракона",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 450_000,
        "description": "Чешуя Дракона на перчатках даёт невероятную стойкость.",
        "bonus": {"stamina": 159, "phys_def": 69, "mag_def": 50, "regen": 28},
    },
    "gloves-lvl17": {
        "slot": "gloves", "level": 17, "key": "gloves-lvl17",
        "name": "Gloves Lvl 17", "ru_name": "Аркановые Рукавицы",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 625_000,
        "description": "Аркановые рукавицы превращают удар в магический импульс.",
        "bonus": {"stamina": 168, "phys_def": 73, "mag_def": 53, "regen": 30},
    },
    "gloves-lvl18": {
        "slot": "gloves", "level": 18, "key": "gloves-lvl18",
        "name": "Gloves Lvl 18", "ru_name": "Длани Вечного Воина",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 875_000,
        "description": "Перчатки, пережившие тысячелетия войн. Нестареющие.",
        "bonus": {"stamina": 176, "phys_def": 76, "mag_def": 56, "regen": 32},
    },
    "gloves-lvl19": {
        "slot": "gloves", "level": 19, "key": "gloves-lvl19",
        "name": "Gloves Lvl 19", "ru_name": "Рукавицы Короля",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 1_200_000,
        "description": "Парадные, но смертоносные рукавицы монарха.",
        "bonus": {"stamina": 184, "phys_def": 80, "mag_def": 59, "regen": 34},
    },
    "gloves-lvl20": {
        "slot": "gloves", "level": 20, "key": "gloves-lvl20",
        "name": "Gloves Lvl 20", "ru_name": "Наручи Небес",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 1_600_000,
        "description": "Небесные наручи избранного воина богов.",
        "bonus": {"stamina": 192, "phys_def": 83, "mag_def": 61, "regen": 35},
    },
    "gloves-lvl21": {
        "slot": "gloves", "level": 21, "key": "gloves-lvl21",
        "name": "Gloves Lvl 21", "ru_name": "Длани Титана",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 2_300_000,
        "description": "Кость Титана — даже прикосновение их разрушает.",
        "bonus": {"stamina": 199, "phys_def": 87, "mag_def": 64, "regen": 37},
    },
    "gloves-lvl22": {
        "slot": "gloves", "level": 22, "key": "gloves-lvl22",
        "name": "Gloves Lvl 22", "ru_name": "Астральные Рукавицы",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 3_100_000,
        "description": "Астральные рукавицы, сотканные из пространства и времени.",
        "bonus": {"stamina": 207, "phys_def": 90, "mag_def": 67, "regen": 39},
    },
    "gloves-lvl23": {
        "slot": "gloves", "level": 23, "key": "gloves-lvl23",
        "name": "Gloves Lvl 23", "ru_name": "Наручи Первородного",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 4_200_000,
        "description": "Длани Первородного: держали меч ещё до рождения мира.",
        "bonus": {"stamina": 215, "phys_def": 93, "mag_def": 70, "regen": 40},
    },
    "gloves-lvl24": {
        "slot": "gloves", "level": 24, "key": "gloves-lvl24",
        "name": "Gloves Lvl 24", "ru_name": "Длани Богоборца",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 5_750_000,
        "description": "Рукавицы Богоборца дробили божественные доспехи.",
        "bonus": {"stamina": 222, "phys_def": 97, "mag_def": 72, "regen": 42},
    },
    "gloves-lvl25": {
        "slot": "gloves", "level": 25, "key": "gloves-lvl25",
        "name": "Gloves Lvl 25", "ru_name": "Перчатки Абсолюта",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 8_000_000,
        "description": "Абсолютные перчатки. Стойкость без предела.",
        "bonus": {"stamina": 230, "phys_def": 100, "mag_def": 75, "regen": 44},
    },

    # ── ШТАНЫ ────────────────────────────────────────
    "pants-lvl1": {
        "slot": "pants", "level": 1, "key": "pants-lvl1",
        "name": "Pants Lvl 1", "ru_name": "Боевые Штаны",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 4_000,
        "description": "Прочные штаны с кожаными вставками. Дают свободу движений.",
        "bonus": {"hp": 8, "stamina": 5},
    },
    "pants-lvl2": {
        "slot": "pants", "level": 2, "key": "pants-lvl2",
        "name": "Pants Lvl 2", "ru_name": "Кольчужные Поножи",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 6_000,
        "description": "Усиленные поножи с кольчужными вставками на бёдрах.",
        "bonus": {"hp": 45, "stamina": 20, "phys_def": 4},
    },
    "pants-lvl3": {
        "slot": "pants", "level": 3, "key": "pants-lvl3",
        "name": "Pants Lvl 3", "ru_name": "Поножи Железного Рыцаря",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 8_000,
        "description": "Тяжёлые боевые штаны с наколенниками из закалённой стали.",
        "bonus": {"hp": 73, "stamina": 32, "phys_def": 13},
    },
    "pants-lvl4": {
        "slot": "pants", "level": 4, "key": "pants-lvl4",
        "name": "Pants Lvl 4", "ru_name": "Зачарованные Поножи",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 12_000,
        "description": "Латные поножи с кристаллами выносливости. Восстанавливают силы в бою.",
        "bonus": {"hp": 97, "stamina": 42, "phys_def": 19, "regen": 3},
    },
    "pants-lvl5": {
        "slot": "pants", "level": 5, "key": "pants-lvl5",
        "name": "Pants Lvl 5", "ru_name": "Поножи Вечности",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 16_000,
        "description": "Реликвийные поножи. Тело бойца отказывается сдаваться.",
        "bonus": {"hp": 121, "stamina": 52, "phys_def": 25, "regen": 8},
    },
    "pants-lvl6": {
        "slot": "pants", "level": 6, "key": "pants-lvl6",
        "name": "Pants Lvl 6", "ru_name": "Поножи Ветерана",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 22_000,
        "description": "Потёртые поножи с историей. Прошли сотни сражений.",
        "bonus": {"hp": 143, "stamina": 61, "phys_def": 30, "regen": 11},
    },
    "pants-lvl7": {
        "slot": "pants", "level": 7, "key": "pants-lvl7",
        "name": "Pants Lvl 7", "ru_name": "Штаны Чемпиона",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 30_000,
        "description": "Латные штаны чемпиона. Выдерживают удары двуручного оружия.",
        "bonus": {"hp": 164, "stamina": 69, "phys_def": 36, "regen": 15},
    },
    "pants-lvl8": {
        "slot": "pants", "level": 8, "key": "pants-lvl8",
        "name": "Pants Lvl 8", "ru_name": "Поножи Паладина",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 41_000,
        "description": "Освящённые поножи паладина. Ускоряют восстановление сил.",
        "bonus": {"hp": 184, "stamina": 78, "phys_def": 41, "regen": 18},
    },
    "pants-lvl9": {
        "slot": "pants", "level": 9, "key": "pants-lvl9",
        "name": "Pants Lvl 9", "ru_name": "Доспех Ног Воителя",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 55_000,
        "description": "Тяжёлые поножи воителя. Стабильность в любом бою.",
        "bonus": {"hp": 204, "stamina": 86, "phys_def": 45, "regen": 21},
    },
    "pants-lvl10": {
        "slot": "pants", "level": 10, "key": "pants-lvl10",
        "name": "Pants Lvl 10", "ru_name": "Поножи Победителя",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 80_000,
        "description": "Поножи победителя. Никакой удар не заставит упасть.",
        "bonus": {"hp": 223, "stamina": 94, "phys_def": 50, "regen": 23},
    },
    "pants-lvl11": {
        "slot": "pants", "level": 11, "key": "pants-lvl11",
        "name": "Pants Lvl 11", "ru_name": "Поножи Берсерка",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 105_000,
        "description": "Безумные штаны берсерка с рунами выносливости.",
        "bonus": {"hp": 242, "stamina": 102, "phys_def": 55, "regen": 26},
    },
    "pants-lvl12": {
        "slot": "pants", "level": 12, "key": "pants-lvl12",
        "name": "Pants Lvl 12", "ru_name": "Штаны Темпляра",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 145_000,
        "description": "Монолитные поножи темпляров. Прочнее стального блока.",
        "bonus": {"hp": 261, "stamina": 109, "phys_def": 59, "regen": 29},
    },
    "pants-lvl13": {
        "slot": "pants", "level": 13, "key": "pants-lvl13",
        "name": "Pants Lvl 13", "ru_name": "Поножи Тёмного Воина",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 200_000,
        "description": "Тёмные поножи убийцы. Лёгкие, но невероятно прочные.",
        "bonus": {"hp": 279, "stamina": 117, "phys_def": 63, "regen": 31},
    },
    "pants-lvl14": {
        "slot": "pants", "level": 14, "key": "pants-lvl14",
        "name": "Pants Lvl 14", "ru_name": "Поножи Повелителя",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 275_000,
        "description": "Золочёные поножи Повелителя с рунами регенерации.",
        "bonus": {"hp": 297, "stamina": 124, "phys_def": 68, "regen": 34},
    },
    "pants-lvl15": {
        "slot": "pants", "level": 15, "key": "pants-lvl15",
        "name": "Pants Lvl 15", "ru_name": "Доспех Ног Завоевателя",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 375_000,
        "description": "Поножи завоевателя. Прошли миллион шагов по полям сражений.",
        "bonus": {"hp": 315, "stamina": 132, "phys_def": 72, "regen": 36},
    },
    "pants-lvl16": {
        "slot": "pants", "level": 16, "key": "pants-lvl16",
        "name": "Pants Lvl 16", "ru_name": "Чешуйчатые Поножи Дракона",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 525_000,
        "description": "Чешуя Дракона защищает ноги лучше любой стали.",
        "bonus": {"hp": 332, "stamina": 139, "phys_def": 76, "regen": 39},
    },
    "pants-lvl17": {
        "slot": "pants", "level": 17, "key": "pants-lvl17",
        "name": "Pants Lvl 17", "ru_name": "Аркановые Поножи",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 725_000,
        "description": "Аркановые поножи хранят энергию каждого шага.",
        "bonus": {"hp": 349, "stamina": 146, "phys_def": 80, "regen": 41},
    },
    "pants-lvl18": {
        "slot": "pants", "level": 18, "key": "pants-lvl18",
        "name": "Pants Lvl 18", "ru_name": "Поножи Вечного Воина",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 975_000,
        "description": "Нестареющие поножи, переживавшие тысячелетия.",
        "bonus": {"hp": 366, "stamina": 153, "phys_def": 84, "regen": 43},
    },
    "pants-lvl19": {
        "slot": "pants", "level": 19, "key": "pants-lvl19",
        "name": "Pants Lvl 19", "ru_name": "Королевские Поножи",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 1_300_000,
        "description": "Парадные поножи монарха со скрытым зачарованием.",
        "bonus": {"hp": 383, "stamina": 160, "phys_def": 88, "regen": 46},
    },
    "pants-lvl20": {
        "slot": "pants", "level": 20, "key": "pants-lvl20",
        "name": "Pants Lvl 20", "ru_name": "Поножи Небес",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 1_800_000,
        "description": "Небесные поножи избранного. Ноги не устают никогда.",
        "bonus": {"hp": 400, "stamina": 167, "phys_def": 92, "regen": 48},
    },
    "pants-lvl21": {
        "slot": "pants", "level": 21, "key": "pants-lvl21",
        "name": "Pants Lvl 21", "ru_name": "Поножи Титана",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 2_500_000,
        "description": "Кость Первородного Титана — крепче любой горной породы.",
        "bonus": {"hp": 416, "stamina": 174, "phys_def": 96, "regen": 50},
    },
    "pants-lvl22": {
        "slot": "pants", "level": 22, "key": "pants-lvl22",
        "name": "Pants Lvl 22", "ru_name": "Астральные Поножи",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 3_500_000,
        "description": "Астральные поножи вне времени и пространства.",
        "bonus": {"hp": 432, "stamina": 180, "phys_def": 100, "regen": 52},
    },
    "pants-lvl23": {
        "slot": "pants", "level": 23, "key": "pants-lvl23",
        "name": "Pants Lvl 23", "ru_name": "Поножи Первородного",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 4_800_000,
        "description": "Поножи Первородного: выдержали всю мощь мироздания.",
        "bonus": {"hp": 448, "stamina": 187, "phys_def": 104, "regen": 54},
    },
    "pants-lvl24": {
        "slot": "pants", "level": 24, "key": "pants-lvl24",
        "name": "Pants Lvl 24", "ru_name": "Поножи Богоборца",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 6_500_000,
        "description": "Поножи Богоборца не знают усталости.",
        "bonus": {"hp": 464, "stamina": 193, "phys_def": 108, "regen": 57},
    },
    "pants-lvl25": {
        "slot": "pants", "level": 25, "key": "pants-lvl25",
        "name": "Pants Lvl 25", "ru_name": "Поножи Абсолюта",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 9_000_000,
        "description": "Абсолютные поножи. Совершенная выносливость.",
        "bonus": {"hp": 480, "stamina": 200, "phys_def": 111, "regen": 59},
    },

    # ── САПОГИ ────────────────────────────────────────
    "boots-lvl1": {
        "slot": "boots", "level": 1, "key": "boots-lvl1",
        "name": "Boots Lvl 1", "ru_name": "Походные Сапоги",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 4_000,
        "description": "Добротные кожаные сапоги. Мягкая подошва гасит шум шагов.",
        "bonus": {"regen": 3, "stamina": 3},
    },
    "boots-lvl2": {
        "slot": "boots", "level": 2, "key": "boots-lvl2",
        "name": "Boots Lvl 2", "ru_name": "Сапоги Следопыта",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 5_000,
        "description": "Лёгкие сапоги из кожи ночной пантеры. Почти бесшумны.",
        "bonus": {"regen": 14, "stamina": 16, "phys_def": 2},
    },
    "boots-lvl3": {
        "slot": "boots", "level": 3, "key": "boots-lvl3",
        "name": "Boots Lvl 3", "ru_name": "Сапоги Ветра Пустоши",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 7_000,
        "description": "Сапоги из кожи горного дракона, пропитанные эликсиром скорости.",
        "bonus": {"regen": 22, "stamina": 26, "phys_def": 8},
    },
    "boots-lvl4": {
        "slot": "boots", "level": 4, "key": "boots-lvl4",
        "name": "Boots Lvl 4", "ru_name": "Сапоги Призрака",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 9_000,
        "description": "Зачарованные сапоги разведчиков. Молниеносное перемещение.",
        "bonus": {"regen": 29, "stamina": 35, "phys_def": 13},
    },
    "boots-lvl5": {
        "slot": "boots", "level": 5, "key": "boots-lvl5",
        "name": "Boots Lvl 5", "ru_name": "Сапоги Грома",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 12_000,
        "description": "Реликвийные сапоги Громового Бога. Надевший их — неудержим.",
        "bonus": {"regen": 36, "stamina": 43, "phys_def": 17},
    },
    "boots-lvl6": {
        "slot": "boots", "level": 6, "key": "boots-lvl6",
        "name": "Boots Lvl 6", "ru_name": "Сапоги Ветерана",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 17_000,
        "description": "Потрёпанные сапоги с историей. Прошли тысячи лиг.",
        "bonus": {"regen": 42, "stamina": 51, "phys_def": 21},
    },
    "boots-lvl7": {
        "slot": "boots", "level": 7, "key": "boots-lvl7",
        "name": "Boots Lvl 7", "ru_name": "Сапоги Чемпиона",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 23_000,
        "description": "Прочные сапоги чемпиона. Держат позицию в любом бою.",
        "bonus": {"regen": 48, "stamina": 58, "phys_def": 24},
    },
    "boots-lvl8": {
        "slot": "boots", "level": 8, "key": "boots-lvl8",
        "name": "Boots Lvl 8", "ru_name": "Сапоги Паладина",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 32_000,
        "description": "Освящённые сапоги паладина. Восстанавливают силы на марше.",
        "bonus": {"regen": 54, "stamina": 65, "phys_def": 28},
    },
    "boots-lvl9": {
        "slot": "boots", "level": 9, "key": "boots-lvl9",
        "name": "Boots Lvl 9", "ru_name": "Сапоги Воителя",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 44_000,
        "description": "Тяжёлые сапоги воителя. Устойчивость как у скалы.",
        "bonus": {"regen": 60, "stamina": 72, "phys_def": 31},
    },
    "boots-lvl10": {
        "slot": "boots", "level": 10, "key": "boots-lvl10",
        "name": "Boots Lvl 10", "ru_name": "Сапоги Победителя",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 60_000,
        "description": "Сапоги победителя. Ни разу не сделали шаг назад.",
        "bonus": {"regen": 66, "stamina": 79, "phys_def": 34},
    },
    "boots-lvl11": {
        "slot": "boots", "level": 11, "key": "boots-lvl11",
        "name": "Boots Lvl 11", "ru_name": "Сапоги Берсерка",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 85_000,
        "description": "Безумные сапоги берсерка с рунами скорости и ярости.",
        "bonus": {"regen": 71, "stamina": 86, "phys_def": 38},
    },
    "boots-lvl12": {
        "slot": "boots", "level": 12, "key": "boots-lvl12",
        "name": "Boots Lvl 12", "ru_name": "Сапоги Темпляра",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 115_000,
        "description": "Монолитные сапоги темпляров. Не скользят даже на льду.",
        "bonus": {"regen": 76, "stamina": 92, "phys_def": 41},
    },
    "boots-lvl13": {
        "slot": "boots", "level": 13, "key": "boots-lvl13",
        "name": "Boots Lvl 13", "ru_name": "Сапоги Тёмного Следопыта",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 155_000,
        "description": "Тёмные сапоги убийцы. Беззвучны как ночь.",
        "bonus": {"regen": 82, "stamina": 99, "phys_def": 44},
    },
    "boots-lvl14": {
        "slot": "boots", "level": 14, "key": "boots-lvl14",
        "name": "Boots Lvl 14", "ru_name": "Сапоги Повелителя",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 225_000,
        "description": "Золочёные сапоги Повелителя с рунами восстановления.",
        "bonus": {"regen": 87, "stamina": 105, "phys_def": 47},
    },
    "boots-lvl15": {
        "slot": "boots", "level": 15, "key": "boots-lvl15",
        "name": "Boots Lvl 15", "ru_name": "Сапоги Завоевателя",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 300_000,
        "description": "Сапоги завоевателя. Прошли все земли этого мира.",
        "bonus": {"regen": 92, "stamina": 112, "phys_def": 50},
    },
    "boots-lvl16": {
        "slot": "boots", "level": 16, "key": "boots-lvl16",
        "name": "Boots Lvl 16", "ru_name": "Сапоги Дракона",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 400_000,
        "description": "Чешуя Дракона защищает стопы лучше любой кожи.",
        "bonus": {"regen": 97, "stamina": 118, "phys_def": 53},
    },
    "boots-lvl17": {
        "slot": "boots", "level": 17, "key": "boots-lvl17",
        "name": "Boots Lvl 17", "ru_name": "Арканические Сапоги",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 550_000,
        "description": "Арканические сапоги заряжаются от каждого шага.",
        "bonus": {"regen": 102, "stamina": 124, "phys_def": 56},
    },
    "boots-lvl18": {
        "slot": "boots", "level": 18, "key": "boots-lvl18",
        "name": "Boots Lvl 18", "ru_name": "Сапоги Вечного Воина",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 750_000,
        "description": "Нестареющие сапоги, переживавшие тысячелетия.",
        "bonus": {"regen": 107, "stamina": 130, "phys_def": 58},
    },
    "boots-lvl19": {
        "slot": "boots", "level": 19, "key": "boots-lvl19",
        "name": "Boots Lvl 19", "ru_name": "Королевские Сапоги",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 1_000_000,
        "description": "Парадные сапоги монарха со скрытым зачарованием скорости.",
        "bonus": {"regen": 112, "stamina": 136, "phys_def": 61},
    },
    "boots-lvl20": {
        "slot": "boots", "level": 20, "key": "boots-lvl20",
        "name": "Boots Lvl 20", "ru_name": "Сапоги Небес",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 1_400_000,
        "description": "Небесные сапоги избранного. Усталость им незнакома.",
        "bonus": {"regen": 117, "stamina": 142, "phys_def": 64},
    },
    "boots-lvl21": {
        "slot": "boots", "level": 21, "key": "boots-lvl21",
        "name": "Boots Lvl 21", "ru_name": "Сапоги Титана",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 2_000_000,
        "description": "Кость Первородного Титана — даже вес их сокрушителен.",
        "bonus": {"regen": 121, "stamina": 147, "phys_def": 67},
    },
    "boots-lvl22": {
        "slot": "boots", "level": 22, "key": "boots-lvl22",
        "name": "Boots Lvl 22", "ru_name": "Астральные Сапоги",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 2_700_000,
        "description": "Астральные сапоги, шагающие сквозь пространство.",
        "bonus": {"regen": 126, "stamina": 153, "phys_def": 69},
    },
    "boots-lvl23": {
        "slot": "boots", "level": 23, "key": "boots-lvl23",
        "name": "Boots Lvl 23", "ru_name": "Сапоги Первородного",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 3_700_000,
        "description": "Сапоги Первородного: ступали по мирозданию ещё до его рождения.",
        "bonus": {"regen": 131, "stamina": 159, "phys_def": 72},
    },
    "boots-lvl24": {
        "slot": "boots", "level": 24, "key": "boots-lvl24",
        "name": "Boots Lvl 24", "ru_name": "Сапоги Богоборца",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 5_000_000,
        "description": "Сапоги Богоборца несут следы битв с богами.",
        "bonus": {"regen": 135, "stamina": 164, "phys_def": 75},
    },
    "boots-lvl25": {
        "slot": "boots", "level": 25, "key": "boots-lvl25",
        "name": "Boots Lvl 25", "ru_name": "Сапоги Абсолюта",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 7_000_000,
        "description": "Абсолютные сапоги. Вершина скорости и регенерации.",
        "bonus": {"regen": 140, "stamina": 170, "phys_def": 77},
    },

}
GEAR_SLOTS_ORDER = ["helmet", "armor", "gloves", "pants", "boots"]

def slot_levels(slot: str) -> list:
    return [f"{slot}-lvl{i}" for i in range(1, 26)]

def slot_label(slot: str) -> str:
    return GEAR_CATALOG[f"{slot}-lvl1"]["slot_label"]

def slot_emoji(slot: str) -> str:
    return GEAR_CATALOG[f"{slot}-lvl1"]["emoji_char"]

def current_slot_item(slot: str, user_data: dict):
    equipped = user_data.get("duel_equipped", {})
    item_key = equipped.get(slot)
    return GEAR_CATALOG.get(item_key)

def owned_level(slot: str, user_data: dict) -> int:
    """Максимальный купленный уровень слота (для совместимости)."""
    owned = user_data.get("duel_owned_gear", [])
    max_lvl = 0
    for lvl in range(1, 26):
        if f"{slot}-lvl{lvl}" in owned:
            max_lvl = lvl
    return max_lvl

def owned_levels_set(slot: str, user_data: dict) -> set:
    """Конкретно купленные уровни слота — без автозаполнения ниже."""
    owned = user_data.get("duel_owned_gear", [])
    return {lvl for lvl in range(1, 26) if f"{slot}-lvl{lvl}" in owned}

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
        "name": "Искра Хаоса",
        "emoji": "🔵",
        "type": "magic",
        "cooldown": 15,
        "base_dmg": (18, 28),
        "description": "Сгусток хаотичной маг. энергии. Быстрый и доступный — твой первый шаг к победе.",
        "price": 0,
    },
    "explosion": {
        "key": "explosion",
        "name": "Удар",
        "emoji": "💥",
        "type": "physical",
        "cooldown": 18,
        "base_dmg": (22, 35),
        "description": "Удар с вложением всей физической мощи. Простой, надёжный, смертоносный.",
        "price": 0,
    },
    "shield": {
        "key": "shield",
        "name": "Барьер",
        "emoji": "🛡️",
        "type": "shield",
        "cooldown": 25,
        "shield_amount": (20, 35),
        "description": "Магический барьер, сотканный из чистой воли бойца. Поглощает следующий удар.",
        "price": 0,
    },

    # ── Покупаемые навыки ────────────────────────────────────
    "iron_fist": {
        "key": "iron_fist",
        "name": "Стальной Кулак",
        "emoji": "✊",
        "type": "physical",
        "cooldown": 14,
        "base_dmg": (24, 36),
        "description": "Удар голой рукой — но с такой силой, что броня крошится как глина.",
        "price": 9_000,
    },
    "mag_block": {
        "key": "mag_block",
        "name": "Таран",
        "emoji": "🟣",
        "type": "magic",
        "cooldown": 20,
        "base_dmg": (30, 48),
        "description": "Концентрированный пучок маг. силы, пробивающий защиту насквозь.",
        "price": 8_000,
    },
    "arcane_surge": {
        "key": "arcane_surge",
        "name": "Арканит",
        "emoji": "✨",
        "type": "magic",
        "cooldown": 18,
        "base_dmg": (26, 40),
        "description": "Выброс чистой аркановой энергии — быстро, метко, без промаха.",
        "price": 11_000,
    },
    "shadow_strike": {
        "key": "shadow_strike",
        "name": "Тьма",
        "emoji": "🌑",
        "type": "physical",
        "cooldown": 16,
        "base_dmg": (28, 42),
        "description": "Удар рождается в тени и настигает раньше, чем враг успевает моргнуть.",
        "price": 12_000,
    },
    "poison_dart": {
        "key": "poison_dart",
        "name": "Яд",
        "emoji": "🧪",
        "type": "magic",
        "cooldown": 20,
        "base_dmg": (20, 30),
        "description": "Игла, пропитанная редчайшим ядом. Проникает сквозь магическую защиту.",
        "price": 13_000,
    },
    "thunder": {
        "key": "thunder",
        "name": "Гром",
        "emoji": "⚡",
        "type": "magic",
        "cooldown": 22,
        "base_dmg": (35, 52),
        "description": "Молния бьёт из раскрытой ладони. Часть маг. защиты просто испаряется.",
        "price": 15_000,
    },
    "chain_lightning": {
        "key": "chain_lightning",
        "name": "Молния",
        "emoji": "🌩️",
        "type": "magic",
        "cooldown": 24,
        "base_dmg": (32, 48),
        "description": "Разряд прыгает по противнику снова и снова — стабильный и безжалостный.",
        "price": 16_000,
    },
    "blade_storm": {
        "key": "blade_storm",
        "name": "Вихрь",
        "emoji": "🌪️",
        "type": "physical",
        "cooldown": 26,
        "base_dmg": (38, 55),
        "description": "Сотни невидимых клинков обрушиваются на врага в вихре стали.",
        "price": 18_000,
    },
    "inferno": {
        "key": "inferno",
        "name": "Инферно",
        "emoji": "🔥",
        "type": "magic",
        "cooldown": 28,
        "base_dmg": (40, 60),
        "description": "Огонь из глубин преисподней — жжёт, не оставляя следов магической защиты.",
        "price": 20_000,
    },
    "war_cry": {
        "key": "war_cry",
        "name": "Боевой Клич",
        "emoji": "📣",
        "type": "physical",
        "cooldown": 30,
        "base_dmg": (42, 60),
        "description": "Боевой клич, от которого кровь стынет в жилах. Мощнейший физический выброс.",
        "price": 20_000,
    },
    "freeze": {
        "key": "freeze",
        "name": "Заморозка",
        "emoji": "❄️",
        "type": "magic",
        "cooldown": 30,
        "base_dmg": (15, 22),
        "freeze_turns": 1,
        "description": "Враг покрывается льдом и теряет ход. Урон невелик — зато время на твоей стороне.",
        "price": 10_000,
    },
    "earthquake": {
        "key": "earthquake",
        "name": "Землетряс",
        "emoji": "🌍",
        "type": "physical",
        "cooldown": 32,
        "base_dmg": (45, 65),
        "description": "Земля раскалывается под врагом. Сила удара — как горный обвал.",
        "price": 22_000,
    },
    "berserker": {
        "key": "berserker",
        "name": "Берсерк",
        "emoji": "🔴",
        "type": "physical",
        "cooldown": 35,
        "base_dmg": (55, 80),
        "description": "Разум выключается — остаётся только ярость. Один из самых разрушительных физ. ударов.",
        "price": 25_000,
    },
    "mega_shield": {
        "key": "mega_shield",
        "name": "Цитадель",
        "emoji": "🔰",
        "type": "shield",
        "cooldown": 40,
        "shield_amount": (50, 80),
        "description": "Колоссальный щит из сжатой магии. Способен поглотить удар любой силы.",
        "price": 28_000,
    },
    "soul_drain": {
        "key": "soul_drain",
        "name": "Дрейн",
        "emoji": "💜",
        "type": "magic",
        "cooldown": 45,
        "base_dmg": (50, 75),
        "drain_regen": 15,
        "description": "Вытягивает жизненную силу врага прямо в тебя. Часть урона возвращается как HP.",
        "price": 30_000,
    },
    "void_blast": {
        "key": "void_blast",
        "name": "Разлом",
        "emoji": "🌀",
        "type": "magic",
        "cooldown": 40,
        "base_dmg": (60, 90),
        "description": "Открывает брешь в ткани мироздания прямо под ногами врага. Боль неизбежна.",
        "price": 35_000,
    },
    "titan_slam": {
        "key": "titan_slam",
        "name": "Титан",
        "emoji": "⚒️",
        "type": "physical",
        "cooldown": 42,
        "base_dmg": (62, 88),
        "description": "Удар, от которого трескается камень под ногами. Мощь первородных существ.",
        "price": 40_000,
    },
    "meteor": {
        "key": "meteor",
        "name": "Метеор",
        "emoji": "☄️",
        "type": "magic",
        "cooldown": 50,
        "base_dmg": (70, 100),
        "description": "С небес обрушивается раскалённый камень. Враг не успевает даже вскрикнуть.",
        "price": 45_000,
    },
    "dark_nova": {
        "key": "dark_nova",
        "name": "Нова",
        "emoji": "🖤",
        "type": "magic",
        "cooldown": 55,
        "base_dmg": (80, 115),
        "description": "Взрыв тёмной материи поглощает всё вокруг. Один из разрушительнейших ударов.",
        "price": 60_000,
    },
    "divine_wrath": {
        "key": "divine_wrath",
        "name": "Кара",
        "emoji": "⚜️",
        "type": "magic",
        "cooldown": 60,
        "base_dmg": (90, 130),
        "description": "Священный огонь нисходит с небес. Абсолютное уничтожение — без исключений.",
        "price": 80_000,
    },

    # ── Новые навыки ─────────────────────────────────────────
    "bloodlust": {
        "key": "bloodlust",
        "name": "Кровопийца",
        "emoji": "🩸",
        "type": "physical",
        "cooldown": 28,
        "base_dmg": (44, 63),
        "drain_regen": 10,
        "description": "Атака, пропитанная животным инстинктом. Часть нанесённого урона возвращается как HP.",
        "price": 17_000,
    },
    "storm_eye": {
        "key": "storm_eye",
        "name": "Око Бури",
        "emoji": "🌊",
        "type": "magic",
        "cooldown": 33,
        "base_dmg": (48, 70),
        "description": "В центре шторма — абсолютная тишина. А потом — волна, сметающая всё.",
        "price": 26_000,
    },
    "obsidian_edge": {
        "key": "obsidian_edge",
        "name": "Обсидиан",
        "emoji": "🗡️",
        "type": "physical",
        "cooldown": 19,
        "base_dmg": (30, 45),
        "description": "Клинок из вулканического стекла — острее любой стали. Молниеносный и точный.",
        "price": 14_000,
    },
    "echo_blast": {
        "key": "echo_blast",
        "name": "Эхо",
        "emoji": "🔊",
        "type": "physical",
        "cooldown": 36,
        "base_dmg": (52, 74),
        "description": "Ударная волна, отражающаяся от каждой поверхности и бьющая снова и снова.",
        "price": 29_000,
    },
    "abyss_call": {
        "key": "abyss_call",
        "name": "Зов Бездны",
        "emoji": "🕳️",
        "type": "magic",
        "cooldown": 48,
        "base_dmg": (65, 95),
        "freeze_turns": 1,
        "description": "Из пустоты тянутся щупальца тьмы. Враг получает урон и теряет ход от ужаса.",
        "price": 50_000,
    },
    "runic_fortress": {
        "key": "runic_fortress",
        "name": "Руны",
        "emoji": "🏰",
        "type": "shield",
        "cooldown": 55,
        "shield_amount": (80, 120),
        "description": "Древние руны складываются в неприступную стену. Поглощает даже самые мощные удары.",
        "price": 55_000,
    },
    "solar_lance": {
        "key": "solar_lance",
        "name": "Солнцекопьё",
        "emoji": "☀️",
        "type": "magic",
        "cooldown": 38,
        "base_dmg": (57, 82),
        "description": "Луч солнечного света, сжатый до точки и выпущенный как копьё. Жжёт и слепит.",
        "price": 33_000,
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
        f'<tg-emoji emoji-id="5337080053119336309">❤️</tg-emoji> HP: <b>{stats["hp"]}</b>\n'
        f'<tg-emoji emoji-id="5465154440287757794">🛡️</tg-emoji> Физ. защита: <b>{stats["phys_def"]}</b>\n'
        f'<tg-emoji emoji-id="5321022334335724730">🔮</tg-emoji> Маг. защита: <b>{stats["mag_def"]}</b>\n'
        f'<tg-emoji emoji-id="5438224604499819092">💚</tg-emoji> Регенерация: <b>{stats["regen"]}</b> HP/ход\n'
        f'<tg-emoji emoji-id="5251281810729480172">⚙️</tg-emoji> Стойкость: <b>{stats["stamina"]}</b>\n\n'
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
            f'<tg-emoji emoji-id="5337080053119336309">❤️</tg-emoji> {my_bar}\n\n'
            f'👹 <b>{foe_name}</b>\n'
            f'<tg-emoji emoji-id="5337080053119336309">❤️</tg-emoji> {foe_bar}'
            f'</blockquote>'
            f'{log_block}'
        )

    return (
        f'⚔️ <b>БОЙ</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>'
        f'👤 <b>{my_name}</b>\n'
        f'<tg-emoji emoji-id="5337080053119336309">❤️</tg-emoji> {my_bar}'
        f'{shields}'
        f'{frozen_note}\n\n'
        f'👹 <b>{foe_name}</b>\n'
        f'<tg-emoji emoji-id="5337080053119336309">❤️</tg-emoji> {foe_bar}'
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
    """Возвращает навыки для страницы магазина (базовые + платные)."""
    all_keys = list(SKILLS.keys())
    start = page * SKILLS_SHOP_PAGE_SIZE
    return all_keys[start:start + SKILLS_SHOP_PAGE_SIZE], len(all_keys)


import random as _random

_DUEL_SHOP_QUOTES = [
    "✦ Великий воин побеждает не силой — а правильно потраченными монетами.\n\n— <i>Мудрец дуэльного рынка</i>",
    "✦ Враг тоже смотрел этот магазин. Вопрос в том, кто купил быстрее.\n\n— <i>Анонимный чемпион</i>",
    "✦ Зачем годами качать скилл в жизни, если можно купить его здесь за монеты?\n\n— <i>Философ арены</i>",
    "✦ Деньги — просто ресурс. Вкладывай в победы, а не в сожаления.\n\n— <i>Казначей боевой гильдии</i>",
    "✦ Побеждают не рождённые — а хорошо экипированные.\n\n— <i>Летопись турнира, том III</i>",
    "✦ Противник тоже думал сэкономить. Теперь он украшает таблицу проигравших.\n\n— <i>Свидетель дуэли №47</i>",
    "✦ Точность приходит с практикой. Практика приходит с хорошим навыком.\n\n— <i>Мастер клинка</i>",
    "✦ Магия не терпит скупости. Она терпит только тех, кто платит.\n\n— <i>Архивариус боевых искусств</i>",
    "✦ Заморозь врага раньше, чем он разморозит собственный кошелёк.\n\n— <i>Ледяной стратег</i>",
    "✦ Не важно как ты выглядишь перед боем. Важно — стоит ли противник после.\n\n— <i>Гладиатор без имени</i>",
    "✦ Тьма — лучший союзник. Особенно если за неё уже уплачено.\n\n— <i>Торговец теневых навыков</i>",
    "✦ Молния бьёт дважды в одного — если купить правильный навык.\n\n— <i>Громовой советник</i>",
    "✦ Сила воли — похвально. Сила навыка — эффективнее.\n\n— <i>Прагматик арены</i>",
    "✦ Каждый навык здесь прошёл боевые испытания. Ну, почти каждый.\n\n— <i>Главный тестировщик (уволен)</i>",
    "✦ Инвестируй в себя. Или хотя бы в свои боевые навыки.\n\n— <i>Финансовый консультант арены</i>",
]


def duel_skills_shop_text(user_data: dict, page: int = 0) -> str:
    items, total = _skill_page_items(page)
    total_pages = (total + SKILLS_SHOP_PAGE_SIZE - 1) // SKILLS_SHOP_PAGE_SIZE
    equipped_skills = get_equipped_skills(user_data)
    balance = user_data.get("balance", 0)
    eq_count = len(equipped_skills)
    quote = _random.choice(_DUEL_SHOP_QUOTES)
    return (
        f'<tg-emoji emoji-id="{EMOJI_SKILLS}">✨</tg-emoji> <b>МАГАЗИН НАВЫКОВ</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n'
        f'<i>Страница {page+1}/{total_pages} · ⚔️ в бою: {eq_count}/{MAX_EQUIPPED_SKILLS}</i>\n\n'
        f'<blockquote expandable>{quote}</blockquote>\n\n'
        f'💰 Баланс: <b>{_fmt(balance)}</b> монет\n'
        f'<i>Нажми навык — купи или экипируй в бой</i>'
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
            kw = dict(
                text=f"{sk['emoji']} {sk['name']}",
                callback_data=f"duel_skill_card:{sk_key}:{page}",
                style="success",
                icon_custom_emoji_id="5206607081334906820",
            )
        elif is_owned:
            kw = dict(
                text=f"{sk['emoji']} {sk['name']}",
                callback_data=f"duel_skill_card:{sk_key}:{page}",
                style="success",
            )
        elif balance >= sk["price"]:
            kw = dict(
                text=f"{sk['emoji']} {sk['name']} | {_fmt(sk['price'])}",
                callback_data=f"duel_skill_card:{sk_key}:{page}",
            )
        else:
            kw = dict(
                text=f"{sk['emoji']} {sk['name']} | {_fmt(sk['price'])}",
                callback_data=f"duel_skill_card:{sk_key}:{page}",
            )

        builder.row(InlineKeyboardButton(**kw))

    # Пагинация
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text="Назад",
            callback_data=f"duel_skills_shop_page:{page-1}",
            icon_custom_emoji_id="5255703720078879038",
        ))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(
            text="Вперёд",
            callback_data=f"duel_skills_shop_page:{page+1}",
            icon_custom_emoji_id="5253767677670862169",
        ))
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
        eid    = _SLOT_EMOJI_IDS.get(slot, "")
        char   = slot_emoji(slot)
        label  = slot_label(slot)
        eq_lvl = equipped_level(slot, user_data)
        ow_lvl = owned_level(slot, user_data)
        slot_tg = f'<tg-emoji emoji-id="{eid}">{char}</tg-emoji>'

        if eq_lvl:
            item   = current_slot_item(slot, user_data)
            status = f'<b>{item["name"]}</b> ✅'
        elif ow_lvl:
            status = f'<b>{slot}-lvl{ow_lvl}</b> 📦 <i>(не надето)</i>'
        else:
            status = '<i>пусто</i>'

        lines.append(f'{slot_tg} <b>{label}:</b> {status}')

    return (
        '<tg-emoji emoji-id="5445221832074483553">🎒</tg-emoji> <b>СНАРЯЖЕНИЕ</b>\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>{chr(10).join(lines)}</blockquote>\n\n'
        '<i>Снаряжение даёт HP и защиту — урон даётся навыками!</i>'
    )

_SLOT_EMOJI_IDS = {
    "armor":  "5454168390685965478",
    "helmet": "5260546085251739109",
    "pants":  "4952249553173613188",
    "boots":  "5776192535890235363",
    "gloves": "5404591969735308062",
}

def duel_equip_keyboard(user_data: dict = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    row_buf = []
    for slot in GEAR_SLOTS_ORDER:
        is_owned = user_data and owned_level(slot, user_data) > 0
        kw = dict(
            text=f"{slot_label(slot)}",
            callback_data=f"duel_equip_slot:{slot}",
            icon_custom_emoji_id=_SLOT_EMOJI_IDS.get(slot),
        )
        if is_owned:
            kw["style"] = "success"
        row_buf.append(InlineKeyboardButton(**kw))
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


_SLOT_PAGE_SIZE = 5   # уровней на странице

def duel_equip_slot_text(slot: str, user_data: dict, page: int = 0) -> str:
    owned_lvls = owned_levels_set(slot, user_data)
    eq_lvl     = equipped_level(slot, user_data)
    emoji      = slot_emoji(slot)
    label      = slot_label(slot)

    total_pages = (25 + _SLOT_PAGE_SIZE - 1) // _SLOT_PAGE_SIZE
    page = max(0, min(page, total_pages - 1))
    lvl_start = page * _SLOT_PAGE_SIZE + 1
    lvl_end   = min(lvl_start + _SLOT_PAGE_SIZE - 1, 25)

    lines = []
    for lvl in range(lvl_start, lvl_end + 1):
        item = GEAR_CATALOG[f"{slot}-lvl{lvl}"]
        if lvl == eq_lvl:
            marker = "✅"
            state  = "<i>надето</i>"
        elif lvl in owned_lvls:
            marker = "📦"
            state  = "<i>в инвентаре</i>"
        else:
            marker = "🔒"
            state  = f"<i>{_fmt(item['price'])} монет</i>"
        lines.append(f"{marker} <b>[{item['name']}]</b> — {item['ru_name']} · {state}")

    block = "\n".join(lines)
    return (
        f'{emoji} <b>СНАРЯЖЕНИЕ — {label.upper()}</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n'
        f'<i>Страница {page + 1}/{total_pages} · уровни {lvl_start}–{lvl_end}</i>\n\n'
        f'<blockquote>{block}</blockquote>\n\n'
        '<i>Нажми на предмет, чтобы узнать подробности</i>'
    )

def duel_equip_slot_keyboard(slot: str, user_data: dict, page: int = 0) -> InlineKeyboardMarkup:
    owned_lvls = owned_levels_set(slot, user_data)
    eq_lvl     = equipped_level(slot, user_data)
    total_pages = (25 + _SLOT_PAGE_SIZE - 1) // _SLOT_PAGE_SIZE
    page = max(0, min(page, total_pages - 1))
    lvl_start = page * _SLOT_PAGE_SIZE + 1
    lvl_end   = min(lvl_start + _SLOT_PAGE_SIZE - 1, 25)
    builder = InlineKeyboardBuilder()

    for lvl in range(lvl_start, lvl_end + 1):
        item_key = f"{slot}-lvl{lvl}"
        item     = GEAR_CATALOG[item_key]
        if lvl == eq_lvl:
            btn_text = f"[{item['name']}]"
            builder.row(InlineKeyboardButton(
                text=btn_text,
                callback_data=f"duel_item_card:{item_key}:{page}",
                style="success",
                icon_custom_emoji_id="5206607081334906820",
            ))
        elif lvl in owned_lvls:
            btn_text = f"[{item['name']}]"
            builder.row(InlineKeyboardButton(
                text=btn_text,
                callback_data=f"duel_item_card:{item_key}:{page}",
                style="success",
            ))
        else:
            btn_text = f"{item['name']} | {_fmt(item['price'])}"
            builder.row(InlineKeyboardButton(
                text=btn_text,
                callback_data=f"duel_item_card:{item_key}:{page}",
            ))

    # Навигация по страницам
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text="Назад",
            callback_data=f"duel_slot_page:{slot}:{page - 1}",
            icon_custom_emoji_id="5255703720078879038",
        ))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(
            text="Вперёд",
            callback_data=f"duel_slot_page:{slot}:{page + 1}",
            icon_custom_emoji_id="5253767677670862169",
        ))
    if nav:
        builder.row(*nav)

    builder.row(InlineKeyboardButton(
        text="Назад", callback_data="duel_equip",
        icon_custom_emoji_id=EMOJI_BACK,
    ))
    return builder.as_markup()


def duel_item_card_text(item_key: str, user_data: dict) -> str:
    item   = GEAR_CATALOG[item_key]
    slot   = item["slot"]
    owned_lvls = owned_levels_set(slot, user_data)
    eq_lvl = equipped_level(slot, user_data)
    lvl    = item["level"]
    balance = user_data.get("balance", 0)

    if lvl == eq_lvl:
        status_line = '✅ <b>Надето прямо сейчас</b>'
    elif lvl in owned_lvls:
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

    if lvl <= 3:
        rarity = "⬜ Обычный"
    elif lvl <= 6:
        rarity = "🟩 Необычный"
    elif lvl <= 10:
        rarity = "🟦 Редкий"
    elif lvl <= 14:
        rarity = "🟪 Эпический"
    elif lvl <= 18:
        rarity = "🟧 Легендарный"
    elif lvl <= 21:
        rarity = "🟥 Мифический"
    elif lvl <= 23:
        rarity = "🔶 Древний"
    elif lvl <= 24:
        rarity = "💠 Реликвийный"
    else:
        rarity = "👑 Абсолютный"

    return (
        f'<tg-emoji emoji-id="{item["emoji_id"]}">{item["emoji_char"]}</tg-emoji> <b>{item["name"]}</b>\n'
        f'<i>{item["ru_name"]}</i>  {rarity}\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>{item["description"]}</blockquote>\n\n'
        f'<b>Боевые бонусы (защита и HP):</b>\n{bonus_block}\n\n'
        f'<i>💡 Урон в дуэли даётся навыками, а не снаряжением!</i>\n\n'
        f'{status_line}'
    )

def duel_item_card_keyboard(item_key: str, user_data: dict, page: int = 0) -> InlineKeyboardMarkup:
    item   = GEAR_CATALOG[item_key]
    slot   = item["slot"]
    owned_lvls = owned_levels_set(slot, user_data)
    eq_lvl = equipped_level(slot, user_data)
    lvl    = item["level"]
    balance = user_data.get("balance", 0)
    builder = InlineKeyboardBuilder()

    if lvl == eq_lvl:
        builder.row(InlineKeyboardButton(
            text="Снять",
            callback_data=f"duel_gear_unequip:{item_key}:{page}",
        ))
    elif lvl in owned_lvls:
        builder.row(InlineKeyboardButton(
            text="Надеть",
            callback_data=f"duel_gear_equip:{item_key}:{page}",
        ))
    else:
        if balance >= item["price"]:
            builder.row(InlineKeyboardButton(
                text=f"Купить — {_fmt(item['price'])} монет",
                callback_data=f"duel_gear_buy:{item_key}:{page}",
            ))
        else:
            builder.row(InlineKeyboardButton(
                text=f"Недостаточно монет",
                callback_data="duel_gear_nofunds",
            ))

    builder.row(InlineKeyboardButton(
        text="Назад", callback_data=f"duel_slot_page:{slot}:{page}",
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
    total_count = len(SKILLS)
    quote = _random.choice(_DUEL_SHOP_QUOTES)

    equip_block = ""
    if user_data:
        equipped = get_equipped_skills(user_data)
        if equipped:
            names = " / ".join(SKILLS[k]["emoji"] + " " + SKILLS[k]["name"] for k in equipped if k in SKILLS)
            equip_block = (
                f"\n\n<blockquote>⚔️ <b>В бою ({len(equipped)}/{MAX_EQUIPPED_SKILLS}):</b> {names}</blockquote>"
            )
        else:
            equip_block = (
                f"\n\n<blockquote>⚠️ <b>Ни один навык не экипирован!</b>\n"
                f"Зайди в магазин и экипируй до {MAX_EQUIPPED_SKILLS} навыков.</blockquote>"
            )

    return (
        f'<tg-emoji emoji-id="{EMOJI_SKILLS}">✨</tg-emoji> <b>БОЕВЫЕ НАВЫКИ</b>\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote expandable>{quote}</blockquote>\n\n'
        f'<blockquote>🛒 В магазине <b>{total_count} навыков</b> — базовые открыты сразу,\n'
        f'остальные покупаются за монеты.\n\n'
        f'💡 <i>Экипируй до {MAX_EQUIPPED_SKILLS} навыков — только они доступны в бою!</i></blockquote>'
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
