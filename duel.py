# ============================================================
#  duel.py  —  Раздел Дуэлей TGStellar
# ============================================================

import random
import time
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from lang import t

# ── Эмодзи ──────────────────────────────────────────────────
EMOJI_BACK         = "5252272671669706296"
EMOJI_DUEL_MAIN    = "5424972470023104089"
EMOJI_SEARCH       = "5231012545799666522"
EMOJI_INVITE       = "5454014806950429357"
EMOJI_EQUIP        = "5454168390685965478"
EMOJI_SKILLS       = "5219714655802381430"
EMOJI_STATS_DUEL   = "5463277406435422003"
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

# ── Система титулов ──────────────────────────────────────────
# (wins, title_name, lang_key)  — первый диапазон где wins < порога
# title_name — канонический (RU) идентификатор, используется как ключ в TITLE_REWARDS
# и НЕ должен переводиться — для отображения игроку используй get_duel_title_display().
_TITLES = [
    (10,   "Слабак",             "weak"),
    (25,   "Тренирующийся",      "training"),
    (60,   "Сильный",            "strong"),
    (120,  "Герой",              "hero"),
    (200,  "Непобедимый",        "invincible"),
    (350,  "Бесподобный",        "incomparable"),
    (700,  "Приносящий гибель",  "death_bringer"),
    (None, "Вечный победитель",  "eternal_champion"),
]

# Награда за победу над игроком с данным титулом
TITLE_REWARDS: dict[str, int] = {
    "Слабак":              50_000,
    "Тренирующийся":      150_000,
    "Сильный":            350_000,
    "Герой":            1_000_000,
    "Непобедимый":      1_500_000,
    "Бесподобный":      2_500_000,
    "Приносящий гибель": 8_000_000,
    "Вечный победитель":15_000_000,
}

def get_duel_title(wins: int) -> str:
    """Возвращает канонический (RU) титул по количеству побед.

    Используется как внутренний ключ (например, в TITLE_REWARDS) —
    для показа игроку используй get_duel_title_display().
    """
    for threshold, name, _key in _TITLES:
        if threshold is None or wins < threshold:
            return name
    return "Вечный победитель"


def get_duel_title_display(wins: int, lang: str = "ru") -> str:
    """Возвращает титул для показа игроку на нужном языке."""
    for threshold, _name, key in _TITLES:
        if threshold is None or wins < threshold:
            return t(lang, f"duel_title_{key}")
    return t(lang, "duel_title_eternal_champion")

# ── Каталог снаряжения: 5 слотов × 25 уровней ────────────────
# ВАЖНО: снаряжение даёт только HP, защиту, регенерацию, стойкость — НЕ урон!
GEAR_CATALOG = {

    # ── ШЛЕМ ────────────────────────────────────────
    "helmet-lvl1": {
        "slot": "helmet", "level": 1, "key": "helmet-lvl1",
        "name": "Helmet Lvl 1", "ru_name": "Железный Шлем",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 35_000,
        "description": "Грубо выкованный железный шлем. Надёжно прикрывает голову от первого удара.",
        "description_en": "A roughly forged iron helmet. Reliably shields the head from the first blow.",
        "bonus": {"hp": 80, "phys_def": 20},
    },
    "helmet-lvl2": {
        "slot": "helmet", "level": 2, "key": "helmet-lvl2",
        "name": "Helmet Lvl 2", "ru_name": "Боевой Шлем",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 65_000,
        "description": "Усиленный шлем с рунической вставкой. Рассеивает слабые магические атаки.",
        "description_en": "A reinforced helmet with a runic inlay. Disperses weak magical attacks.",
        "bonus": {"hp": 96, "phys_def": 24, "mag_def": 18, "stamina": 6},
    },
    "helmet-lvl3": {
        "slot": "helmet", "level": 3, "key": "helmet-lvl3",
        "name": "Helmet Lvl 3", "ru_name": "Шлем Гвардейца",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 120_000,
        "description": "Закалённый шлем королевской гвардии с забралом из мифрила.",
        "description_en": "A tempered royal guard helmet with a mithril visor.",
        "bonus": {"hp": 115, "phys_def": 29, "mag_def": 22, "stamina": 7},
    },
    "helmet-lvl4": {
        "slot": "helmet", "level": 4, "key": "helmet-lvl4",
        "name": "Helmet Lvl 4", "ru_name": "Шлем Стального Стража",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 220_000,
        "description": "Реликвийный шлем с рунической гравировкой. Входящий урон частично поглощается барьером.",
        "description_en": "A relic helmet with runic engravings. Incoming damage is partially absorbed by a barrier.",
        "bonus": {"hp": 137, "phys_def": 35, "mag_def": 26, "stamina": 9},
    },
    "helmet-lvl5": {
        "slot": "helmet", "level": 5, "key": "helmet-lvl5",
        "name": "Helmet Lvl 5", "ru_name": "Шлем Легенды",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 420_000,
        "description": "Артефакт эпохи Первых Воинов. Ни одна стрела не может поколебать носителя.",
        "description_en": "An artifact from the age of the First Warriors. No arrow can shake its wearer.",
        "bonus": {"hp": 164, "phys_def": 42, "mag_def": 32, "stamina": 11},
    },
    "helmet-lvl6": {
        "slot": "helmet", "level": 6, "key": "helmet-lvl6",
        "name": "Helmet Lvl 6", "ru_name": "Шлем Ветерана",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 770_000,
        "description": "Шлем опытного воина, прошедшего сотни битв. Несёт следы многих поединков.",
        "description_en": "The helmet of a seasoned warrior who survived hundreds of battles. Bears the marks of many duels.",
        "bonus": {"hp": 197, "phys_def": 51, "mag_def": 39, "stamina": 14},
    },
    "helmet-lvl7": {
        "slot": "helmet", "level": 7, "key": "helmet-lvl7",
        "name": "Helmet Lvl 7", "ru_name": "Шлем Рыцаря",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 1_400_000,
        "description": "Латный шлем рыцаря с плюмажем из перьев феникса. Символ доблести.",
        "description_en": "A knight's plate helmet crowned with a phoenix-feather plume. A symbol of valor.",
        "bonus": {"hp": 235, "phys_def": 62, "mag_def": 47, "stamina": 17},
    },
    "helmet-lvl8": {
        "slot": "helmet", "level": 8, "key": "helmet-lvl8",
        "name": "Helmet Lvl 8", "ru_name": "Шлем Паладина",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 2_700_000,
        "description": "Священный шлем паладина, освящённый в храме. Отражает тёмную магию.",
        "description_en": "A sacred paladin's helmet, blessed in a temple. Reflects dark magic.",
        "bonus": {"hp": 282, "phys_def": 74, "mag_def": 56, "stamina": 20},
    },
    "helmet-lvl9": {
        "slot": "helmet", "level": 9, "key": "helmet-lvl9",
        "name": "Helmet Lvl 9", "ru_name": "Шлем Воителя",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 5_000_000,
        "description": "Боевой шлем прославленного воителя. Видавший победы и поражения.",
        "description_en": "The battle helmet of a renowned warrior. It has seen both victory and defeat.",
        "bonus": {"hp": 337, "phys_def": 90, "mag_def": 68, "stamina": 25},
    },
    "helmet-lvl10": {
        "slot": "helmet", "level": 10, "key": "helmet-lvl10",
        "name": "Helmet Lvl 10", "ru_name": "Шлем Чемпиона",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 9_200_000,
        "description": "Шлем чемпиона арены. Украшен рунами побед над сильнейшими.",
        "description_en": "The arena champion's helmet. Adorned with runes marking victories over the mightiest foes.",
        "bonus": {"hp": 404, "phys_def": 108, "mag_def": 82, "stamina": 30},
    },
    "helmet-lvl11": {
        "slot": "helmet", "level": 11, "key": "helmet-lvl11",
        "name": "Helmet Lvl 11", "ru_name": "Шлем Берсерка",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 17_000_000,
        "description": "Шлем берсерка с рогами ледяного быка. Дарует ярость в бою.",
        "description_en": "A berserker's helmet crowned with frost-bull horns. Grants fury in battle.",
        "bonus": {"hp": 483, "phys_def": 130, "mag_def": 99, "stamina": 37},
    },
    "helmet-lvl12": {
        "slot": "helmet", "level": 12, "key": "helmet-lvl12",
        "name": "Helmet Lvl 12", "ru_name": "Шлем Темпляра",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 32_000_000,
        "description": "Шлем ордена темпляров из освящённой стали. Непробиваем для нечисти.",
        "description_en": "A Templar order helmet forged from consecrated steel. Impenetrable to unholy creatures.",
        "bonus": {"hp": 579, "phys_def": 157, "mag_def": 120, "stamina": 45},
    },
    "helmet-lvl13": {
        "slot": "helmet", "level": 13, "key": "helmet-lvl13",
        "name": "Helmet Lvl 13", "ru_name": "Шлем Стражника Бездны",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 59_000_000,
        "description": "Таинственный шлем из бездонных глубин. Поглощает тёмную энергию.",
        "description_en": "A mysterious helmet from the bottomless depths. Absorbs dark energy.",
        "bonus": {"hp": 693, "phys_def": 190, "mag_def": 145, "stamina": 55},
    },
    "helmet-lvl14": {
        "slot": "helmet", "level": 14, "key": "helmet-lvl14",
        "name": "Helmet Lvl 14", "ru_name": "Шлем Повелителя",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 110_000_000,
        "description": "Шлем Повелителя армий. Золотая инкрустация скрывает мощнейшие руны.",
        "description_en": "The Helmet of the Army's Overlord. Its gold inlay conceals the most powerful runes.",
        "bonus": {"hp": 829, "phys_def": 229, "mag_def": 175, "stamina": 67},
    },
    "helmet-lvl15": {
        "slot": "helmet", "level": 15, "key": "helmet-lvl15",
        "name": "Helmet Lvl 15", "ru_name": "Шлем Завоевателя",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 200_000_000,
        "description": "Шлем завоевателя миров. Слава его обладателя гремит по всем землям.",
        "description_en": "The helmet of a world conqueror. Its wearer's fame echoes across every land.",
        "bonus": {"hp": 993, "phys_def": 276, "mag_def": 211, "stamina": 82},
    },
    "helmet-lvl16": {
        "slot": "helmet", "level": 16, "key": "helmet-lvl16",
        "name": "Helmet Lvl 16", "ru_name": "Шлем Драконьей Гвардии",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 380_000_000,
        "description": "Шлем элитной гвардии дракона. Чешуя дракона вплавлена в металл.",
        "description_en": "The helmet of the elite dragon guard. Dragon scale is fused into the metal.",
        "bonus": {"hp": 1189, "phys_def": 333, "mag_def": 255, "stamina": 100},
    },
    "helmet-lvl17": {
        "slot": "helmet", "level": 17, "key": "helmet-lvl17",
        "name": "Helmet Lvl 17", "ru_name": "Шлем Арканиста",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 700_000_000,
        "description": "Шлем великого арканиста. Фокусирует магическую энергию вокруг головы.",
        "description_en": "The helmet of a great arcanist. Focuses magical energy around the head.",
        "bonus": {"hp": 1423, "phys_def": 402, "mag_def": 309, "stamina": 122},
    },
    "helmet-lvl18": {
        "slot": "helmet", "level": 18, "key": "helmet-lvl18",
        "name": "Helmet Lvl 18", "ru_name": "Шлем Вечного Воина",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 1_300_000_000,
        "description": "Шлем воина, пережившего тысячелетия. Прочнее любого современного металла.",
        "description_en": "The helmet of a warrior who has endured millennia. Stronger than any modern metal.",
        "bonus": {"hp": 1703, "phys_def": 484, "mag_def": 373, "stamina": 148},
    },
    "helmet-lvl19": {
        "slot": "helmet", "level": 19, "key": "helmet-lvl19",
        "name": "Helmet Lvl 19", "ru_name": "Шлем Короля",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 2_400_000_000,
        "description": "Шлем законного правителя. Никто не смеет поднять руку на его обладателя.",
        "description_en": "The helmet of a rightful ruler. No one dares raise a hand against its wearer.",
        "bonus": {"hp": 2039, "phys_def": 584, "mag_def": 450, "stamina": 181},
    },
    "helmet-lvl20": {
        "slot": "helmet", "level": 20, "key": "helmet-lvl20",
        "name": "Helmet Lvl 20", "ru_name": "Шлем Небес",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 4_500_000_000,
        "description": "Шлем небесного воителя. Ниспослан богами избранному герою.",
        "description_en": "The helmet of a celestial warrior. Bestowed by the gods upon a chosen hero.",
        "bonus": {"hp": 2441, "phys_def": 705, "mag_def": 544, "stamina": 221},
    },
    "helmet-lvl21": {
        "slot": "helmet", "level": 21, "key": "helmet-lvl21",
        "name": "Helmet Lvl 21", "ru_name": "Шлем Титана",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 8_400_000_000,
        "description": "Шлем из кости Первородного Титана. Тяжелее горы, прочнее скалы.",
        "description_en": "A helmet forged from the bone of the Primordial Titan. Heavier than a mountain, sturdier than stone.",
        "bonus": {"hp": 2922, "phys_def": 850, "mag_def": 657, "stamina": 270},
    },
    "helmet-lvl22": {
        "slot": "helmet", "level": 22, "key": "helmet-lvl22",
        "name": "Helmet Lvl 22", "ru_name": "Шлем Астрального Стража",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 16_000_000_000,
        "description": "Астральный шлем, соткан из звёздного металла. Защищает даже душу.",
        "description_en": "An astral helmet woven from starmetal. Protects even the soul.",
        "bonus": {"hp": 3498, "phys_def": 1026, "mag_def": 794, "stamina": 330},
    },
    "helmet-lvl23": {
        "slot": "helmet", "level": 23, "key": "helmet-lvl23",
        "name": "Helmet Lvl 23", "ru_name": "Шлем Первородного",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 29_000_000_000,
        "description": "Шлем Первородного Воина — до него никто не выжил в тысяче дуэлей.",
        "description_en": "The Helmet of the Primordial Warrior — no one before him survived a thousand duels.",
        "bonus": {"hp": 4187, "phys_def": 1237, "mag_def": 959, "stamina": 403},
    },
    "helmet-lvl24": {
        "slot": "helmet", "level": 24, "key": "helmet-lvl24",
        "name": "Helmet Lvl 24", "ru_name": "Шлем Богоборца",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 54_000_000_000,
        "description": "Шлем Богоборца. Даже боги дрогнули перед его обладателем.",
        "description_en": "The Helmet of the Godslayer. Even the gods faltered before its wearer.",
        "bonus": {"hp": 5012, "phys_def": 1492, "mag_def": 1159, "stamina": 491},
    },
    "helmet-lvl25": {
        "slot": "helmet", "level": 25, "key": "helmet-lvl25",
        "name": "Helmet Lvl 25", "ru_name": "Шлем Абсолюта",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5260546085251739109",
        "price": 100_000_000_000,
        "description": "Абсолютный артефакт. Вершина защиты, недостижимая смертными.",
        "description_en": "An absolute artifact. The pinnacle of defense, unattainable by mortals.",
        "bonus": {"hp": 6000, "phys_def": 1800, "mag_def": 1400, "stamina": 600},
    },

    # ── БРОНЯ ────────────────────────────────────────
    "armor-lvl1": {
        "slot": "armor", "level": 1, "key": "armor-lvl1",
        "name": "Armor Lvl 1", "ru_name": "Кожаный Доспех",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 40_000,
        "description": "Доспех из дублёной кожи. Лёгкий, не сковывает движений.",
        "description_en": "Armor made of tanned leather. Light and unrestrictive.",
        "bonus": {"hp": 120, "phys_def": 25},
    },
    "armor-lvl2": {
        "slot": "armor", "level": 2, "key": "armor-lvl2",
        "name": "Armor Lvl 2", "ru_name": "Кольчужный Доспех",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 74_000,
        "description": "Тысячи закалённых колец. Хорошо поглощает рубящие удары.",
        "description_en": "Thousands of tempered rings. Absorbs slashing blows well.",
        "bonus": {"hp": 143, "phys_def": 30, "stamina": 12, "mag_def": 10},
    },
    "armor-lvl3": {
        "slot": "armor", "level": 3, "key": "armor-lvl3",
        "name": "Armor Lvl 3", "ru_name": "Пластинчатый Доспех",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 140_000,
        "description": "Боевые латы из стальных пластин. Сводят урон к минимуму.",
        "description_en": "Battle plate made of steel plates. Minimizes incoming damage.",
        "bonus": {"hp": 170, "phys_def": 36, "stamina": 14, "mag_def": 12},
    },
    "armor-lvl4": {
        "slot": "armor", "level": 4, "key": "armor-lvl4",
        "name": "Armor Lvl 4", "ru_name": "Латы Воина Бездны",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 260_000,
        "description": "Прочнейшие латы, выкованные в жерле вулкана тёмными кузнецами.",
        "description_en": "The sturdiest plate armor, forged in a volcano's crater by dark blacksmiths.",
        "bonus": {"hp": 203, "phys_def": 44, "stamina": 17, "mag_def": 15},
    },
    "armor-lvl5": {
        "slot": "armor", "level": 5, "key": "armor-lvl5",
        "name": "Armor Lvl 5", "ru_name": "Латы Абсолюта",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 480_000,
        "description": "Легендарный доспех. Выкован из металла упавшей звезды.",
        "description_en": "A legendary suit of armor. Forged from the metal of a fallen star.",
        "bonus": {"hp": 242, "phys_def": 53, "stamina": 21, "mag_def": 18},
    },
    "armor-lvl6": {
        "slot": "armor", "level": 6, "key": "armor-lvl6",
        "name": "Armor Lvl 6", "ru_name": "Доспех Ветерана",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 890_000,
        "description": "Доспех ветерана, переживший сотни сражений. Каждая вмятина — история.",
        "description_en": "A veteran's armor that survived hundreds of battles. Every dent tells a story.",
        "bonus": {"hp": 288, "phys_def": 64, "stamina": 25, "mag_def": 22},
    },
    "armor-lvl7": {
        "slot": "armor", "level": 7, "key": "armor-lvl7",
        "name": "Armor Lvl 7", "ru_name": "Доспех Крепости",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 1_700_000,
        "description": "Монолитный доспех, прочный как крепостная стена.",
        "description_en": "Monolithic armor, as sturdy as a fortress wall.",
        "bonus": {"hp": 343, "phys_def": 77, "stamina": 30, "mag_def": 27},
    },
    "armor-lvl8": {
        "slot": "armor", "level": 8, "key": "armor-lvl8",
        "name": "Armor Lvl 8", "ru_name": "Латы Паладина",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 3_100_000,
        "description": "Освящённые латы паладина. Тёмная сила отступает перед ними.",
        "description_en": "The paladin's consecrated plate. Dark forces retreat before it.",
        "bonus": {"hp": 408, "phys_def": 92, "stamina": 36, "mag_def": 33},
    },
    "armor-lvl9": {
        "slot": "armor", "level": 9, "key": "armor-lvl9",
        "name": "Armor Lvl 9", "ru_name": "Броня Воителя",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 5_800_000,
        "description": "Тяжёлые боевые латы великого воителя.",
        "description_en": "The heavy battle plate of a great warrior.",
        "bonus": {"hp": 487, "phys_def": 111, "stamina": 43, "mag_def": 40},
    },
    "armor-lvl10": {
        "slot": "armor", "level": 10, "key": "armor-lvl10",
        "name": "Armor Lvl 10", "ru_name": "Доспех Чемпиона",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 11_000_000,
        "description": "Доспех чемпиона. Противники дрожат, видя его.",
        "description_en": "The champion's armor. Opponents tremble at the sight of it.",
        "bonus": {"hp": 580, "phys_def": 134, "stamina": 52, "mag_def": 49},
    },
    "armor-lvl11": {
        "slot": "armor", "level": 11, "key": "armor-lvl11",
        "name": "Armor Lvl 11", "ru_name": "Латы Берсерка",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 20_000_000,
        "description": "Безумные латы берсерка. Впитали кровь тысяч врагов.",
        "description_en": "The berserker's savage plate. Soaked in the blood of thousands of foes.",
        "bonus": {"hp": 690, "phys_def": 161, "stamina": 62, "mag_def": 60},
    },
    "armor-lvl12": {
        "slot": "armor", "level": 12, "key": "armor-lvl12",
        "name": "Armor Lvl 12", "ru_name": "Доспех Темпляра",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 37_000_000,
        "description": "Священные доспехи темпляров. Прочнее любых известных материалов.",
        "description_en": "The Templars' sacred armor. Sturdier than any known material.",
        "bonus": {"hp": 823, "phys_def": 195, "stamina": 75, "mag_def": 73},
    },
    "armor-lvl13": {
        "slot": "armor", "level": 13, "key": "armor-lvl13",
        "name": "Armor Lvl 13", "ru_name": "Броня Тёмного Стража",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 69_000_000,
        "description": "Тёмная броня стражей бездны. Поглощает тёмные проклятия.",
        "description_en": "The dark armor of the abyss guardians. Absorbs dark curses.",
        "bonus": {"hp": 980, "phys_def": 235, "stamina": 89, "mag_def": 89},
    },
    "armor-lvl14": {
        "slot": "armor", "level": 14, "key": "armor-lvl14",
        "name": "Armor Lvl 14", "ru_name": "Латы Повелителя",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 130_000_000,
        "description": "Золочёные латы Повелителя армий с магическим ядром.",
        "description_en": "The gilded plate of the Army's Overlord, fitted with a magical core.",
        "bonus": {"hp": 1167, "phys_def": 283, "stamina": 107, "mag_def": 109},
    },
    "armor-lvl15": {
        "slot": "armor", "level": 15, "key": "armor-lvl15",
        "name": "Armor Lvl 15", "ru_name": "Доспех Завоевателя",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 240_000_000,
        "description": "Непробиваемые доспехи завоевателя. Выкованы из драконьей кости.",
        "description_en": "The conqueror's impenetrable armor. Forged from dragon bone.",
        "bonus": {"hp": 1390, "phys_def": 341, "stamina": 129, "mag_def": 134},
    },
    "armor-lvl16": {
        "slot": "armor", "level": 16, "key": "armor-lvl16",
        "name": "Armor Lvl 16", "ru_name": "Чешуйчатый Доспех Дракона",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 450_000_000,
        "description": "Чешуя Древнего Дракона — каждая пластина крепче стали.",
        "description_en": "Scales of the Ancient Dragon — every plate stronger than steel.",
        "bonus": {"hp": 1656, "phys_def": 410, "stamina": 155, "mag_def": 164},
    },
    "armor-lvl17": {
        "slot": "armor", "level": 17, "key": "armor-lvl17",
        "name": "Armor Lvl 17", "ru_name": "Аркановые Латы",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 830_000_000,
        "description": "Аркановые латы сотканы из застывшей магии. Меняют форму под удар.",
        "description_en": "Arcane plate woven from frozen magic. Shifts shape to absorb blows.",
        "bonus": {"hp": 1973, "phys_def": 495, "stamina": 186, "mag_def": 200},
    },
    "armor-lvl18": {
        "slot": "armor", "level": 18, "key": "armor-lvl18",
        "name": "Armor Lvl 18", "ru_name": "Броня Вечного Воина",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 1_500_000_000,
        "description": "Доспех, который не берут ни годы, ни оружие.",
        "description_en": "Armor that neither years nor weapons can touch.",
        "bonus": {"hp": 2350, "phys_def": 596, "stamina": 223, "mag_def": 245},
    },
    "armor-lvl19": {
        "slot": "armor", "level": 19, "key": "armor-lvl19",
        "name": "Armor Lvl 19", "ru_name": "Королевские Латы",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 2_900_000_000,
        "description": "Парадные королевские латы со спрятанными зачарованиями.",
        "description_en": "Ceremonial royal plate with hidden enchantments.",
        "bonus": {"hp": 2800, "phys_def": 718, "stamina": 267, "mag_def": 299},
    },
    "armor-lvl20": {
        "slot": "armor", "level": 20, "key": "armor-lvl20",
        "name": "Armor Lvl 20", "ru_name": "Доспех Небес",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 5_400_000_000,
        "description": "Небесный доспех, откованный богами для избранного воина.",
        "description_en": "Celestial armor, forged by the gods for a chosen warrior.",
        "bonus": {"hp": 3335, "phys_def": 866, "stamina": 321, "mag_def": 366},
    },
    "armor-lvl21": {
        "slot": "armor", "level": 21, "key": "armor-lvl21",
        "name": "Armor Lvl 21", "ru_name": "Латы Титана",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 10_000_000_000,
        "description": "Кость первого Титана — вот из чего создан этот доспех.",
        "description_en": "The bone of the First Titan — that is what this armor is made of.",
        "bonus": {"hp": 3973, "phys_def": 1043, "stamina": 385, "mag_def": 447},
    },
    "armor-lvl22": {
        "slot": "armor", "level": 22, "key": "armor-lvl22",
        "name": "Armor Lvl 22", "ru_name": "Астральная Броня",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 19_000_000_000,
        "description": "Астральные латы, закалённые в ткани самого пространства.",
        "description_en": "Astral plate, tempered in the fabric of space itself.",
        "bonus": {"hp": 4733, "phys_def": 1257, "stamina": 463, "mag_def": 547},
    },
    "armor-lvl23": {
        "slot": "armor", "level": 23, "key": "armor-lvl23",
        "name": "Armor Lvl 23", "ru_name": "Доспех Первородного",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 35_000_000_000,
        "description": "Броня Первородного: выдержала удар самой Смерти.",
        "description_en": "The Primordial's armor: it withstood a blow from Death itself.",
        "bonus": {"hp": 5638, "phys_def": 1515, "stamina": 555, "mag_def": 669},
    },
    "armor-lvl24": {
        "slot": "armor", "level": 24, "key": "armor-lvl24",
        "name": "Armor Lvl 24", "ru_name": "Латы Богоборца",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 64_000_000_000,
        "description": "Доспех Богоборца. Ни один бог не пробил его.",
        "description_en": "The Godslayer's armor. No god has ever pierced it.",
        "bonus": {"hp": 6716, "phys_def": 1826, "stamina": 666, "mag_def": 818},
    },
    "armor-lvl25": {
        "slot": "armor", "level": 25, "key": "armor-lvl25",
        "name": "Armor Lvl 25", "ru_name": "Доспех Абсолюта",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5454168390685965478",
        "price": 120_000_000_000,
        "description": "Абсолютная броня. Конец и вершина любой защиты.",
        "description_en": "Absolute armor. The end and pinnacle of all defense.",
        "bonus": {"hp": 8000, "phys_def": 2200, "stamina": 800, "mag_def": 1000},
    },

    # ── ПЕРЧАТКИ ────────────────────────────────────────
    "gloves-lvl1": {
        "slot": "gloves", "level": 1, "key": "gloves-lvl1",
        "name": "Gloves Lvl 1", "ru_name": "Боевые Рукавицы",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 80_000,
        "description": "Кожаные рукавицы с наклёпками. Защищают кулаки.",
        "description_en": "Leather mitts studded with rivets. Protect the fists.",
        "bonus": {"hp": 60, "phys_def": 30},
    },
    "gloves-lvl2": {
        "slot": "gloves", "level": 2, "key": "gloves-lvl2",
        "name": "Gloves Lvl 2", "ru_name": "Латные Рукавицы",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 150_000,
        "description": "Рукавицы с металлическими пластинами. Усиливают хват оружия.",
        "description_en": "Mitts fitted with metal plates. Strengthen the grip on weapons.",
        "bonus": {"hp": 72, "phys_def": 36, "mag_def": 24, "stamina": 10, "regen": 6},
    },
    "gloves-lvl3": {
        "slot": "gloves", "level": 3, "key": "gloves-lvl3",
        "name": "Gloves Lvl 3", "ru_name": "Наручи Теневого Клинка",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 270_000,
        "description": "Боевые наручи с выдвижными шипами. Оружие теневых воинов.",
        "description_en": "Battle vambraces with retractable spikes. The weapon of shadow warriors.",
        "bonus": {"hp": 87, "phys_def": 44, "mag_def": 29, "stamina": 12, "regen": 7},
    },
    "gloves-lvl4": {
        "slot": "gloves", "level": 4, "key": "gloves-lvl4",
        "name": "Gloves Lvl 4", "ru_name": "Наручи Убийцы",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 490_000,
        "description": "Зачарованные наручи элитных убийц гильдии Алой Тени.",
        "description_en": "Enchanted vambraces of the elite assassins from the Crimson Shadow guild.",
        "bonus": {"hp": 104, "phys_def": 52, "mag_def": 35, "stamina": 14, "regen": 9},
    },
    "gloves-lvl5": {
        "slot": "gloves", "level": 5, "key": "gloves-lvl5",
        "name": "Gloves Lvl 5", "ru_name": "Длани Хаоса",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 900_000,
        "description": "Артефактные перчатки, пронизанные энергией первозданного хаоса.",
        "description_en": "Artifact gauntlets charged with the energy of primal chaos.",
        "bonus": {"hp": 125, "phys_def": 63, "mag_def": 42, "stamina": 17, "regen": 10},
    },
    "gloves-lvl6": {
        "slot": "gloves", "level": 6, "key": "gloves-lvl6",
        "name": "Gloves Lvl 6", "ru_name": "Наручи Ветерана",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 1_600_000,
        "description": "Потрёпанные наручи с историей. Каждый ремешок — знак победы.",
        "description_en": "Weathered vambraces with a history. Every strap marks a victory.",
        "bonus": {"hp": 151, "phys_def": 76, "mag_def": 51, "stamina": 20, "regen": 12},
    },
    "gloves-lvl7": {
        "slot": "gloves", "level": 7, "key": "gloves-lvl7",
        "name": "Gloves Lvl 7", "ru_name": "Рукавицы Чемпиона",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 3_000_000,
        "description": "Тяжёлые латные рукавицы чемпиона арены.",
        "description_en": "The heavy plate gauntlets of the arena champion.",
        "bonus": {"hp": 181, "phys_def": 92, "mag_def": 62, "stamina": 24, "regen": 15},
    },
    "gloves-lvl8": {
        "slot": "gloves", "level": 8, "key": "gloves-lvl8",
        "name": "Gloves Lvl 8", "ru_name": "Наручи Паладина",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 5_500_000,
        "description": "Освящённые наручи паладина. Отражают магические удары.",
        "description_en": "The paladin's blessed vambraces. Reflect magical strikes.",
        "bonus": {"hp": 218, "phys_def": 110, "mag_def": 74, "stamina": 29, "regen": 18},
    },
    "gloves-lvl9": {
        "slot": "gloves", "level": 9, "key": "gloves-lvl9",
        "name": "Gloves Lvl 9", "ru_name": "Перчатки Воителя",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 10_000_000,
        "description": "Мощные рукавицы великого воителя. Хватка — как тиски.",
        "description_en": "The powerful gauntlets of a great warrior. A grip like a vice.",
        "bonus": {"hp": 262, "phys_def": 133, "mag_def": 90, "stamina": 36, "regen": 22},
    },
    "gloves-lvl10": {
        "slot": "gloves", "level": 10, "key": "gloves-lvl10",
        "name": "Gloves Lvl 10", "ru_name": "Наручи Победителя",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 18_000_000,
        "description": "Наручи победителя. Никто не выбил оружие из этих рук.",
        "description_en": "The victor's vambraces. No one has ever knocked a weapon from these hands.",
        "bonus": {"hp": 315, "phys_def": 160, "mag_def": 108, "stamina": 43, "regen": 26},
    },
    "gloves-lvl11": {
        "slot": "gloves", "level": 11, "key": "gloves-lvl11",
        "name": "Gloves Lvl 11", "ru_name": "Рукавицы Берсерка",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 34_000_000,
        "description": "Безумные рукавицы берсерка. Покрыты шипами и рунами ярости.",
        "description_en": "The berserker's frenzied gauntlets. Covered in spikes and runes of rage.",
        "bonus": {"hp": 379, "phys_def": 193, "mag_def": 130, "stamina": 52, "regen": 31},
    },
    "gloves-lvl12": {
        "slot": "gloves", "level": 12, "key": "gloves-lvl12",
        "name": "Gloves Lvl 12", "ru_name": "Наручи Темпляра",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 62_000_000,
        "description": "Наручи темпляров. Выдерживают прямые удары двуручным мечом.",
        "description_en": "The Templars' vambraces. Withstand direct blows from a two-handed sword.",
        "bonus": {"hp": 456, "phys_def": 232, "mag_def": 157, "stamina": 62, "regen": 37},
    },
    "gloves-lvl13": {
        "slot": "gloves", "level": 13, "key": "gloves-lvl13",
        "name": "Gloves Lvl 13", "ru_name": "Перчатки Тёмного Убийцы",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 110_000_000,
        "description": "Перчатки из тёмной кожи. Пропитаны ядом и тьмой.",
        "description_en": "Gloves of dark leather. Steeped in poison and shadow.",
        "bonus": {"hp": 548, "phys_def": 279, "mag_def": 190, "stamina": 75, "regen": 45},
    },
    "gloves-lvl14": {
        "slot": "gloves", "level": 14, "key": "gloves-lvl14",
        "name": "Gloves Lvl 14", "ru_name": "Наручи Повелителя",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 210_000_000,
        "description": "Золотые наручи Повелителя. Скрывают клинки под пластинами.",
        "description_en": "The Overlord's golden vambraces. Conceal blades beneath their plates.",
        "bonus": {"hp": 659, "phys_def": 336, "mag_def": 229, "stamina": 90, "regen": 54},
    },
    "gloves-lvl15": {
        "slot": "gloves", "level": 15, "key": "gloves-lvl15",
        "name": "Gloves Lvl 15", "ru_name": "Длани Завоевателя",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 380_000_000,
        "description": "Длани завоевателя сокрушали врата крепостей.",
        "description_en": "The conqueror's hands shattered the gates of fortresses.",
        "bonus": {"hp": 792, "phys_def": 405, "mag_def": 276, "stamina": 109, "regen": 64},
    },
    "gloves-lvl16": {
        "slot": "gloves", "level": 16, "key": "gloves-lvl16",
        "name": "Gloves Lvl 16", "ru_name": "Перчатки Дракона",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 690_000_000,
        "description": "Чешуя Дракона на перчатках даёт невероятную стойкость.",
        "description_en": "Dragon scale set into the gloves grants incredible resilience.",
        "bonus": {"hp": 952, "phys_def": 488, "mag_def": 333, "stamina": 131, "regen": 77},
    },
    "gloves-lvl17": {
        "slot": "gloves", "level": 17, "key": "gloves-lvl17",
        "name": "Gloves Lvl 17", "ru_name": "Аркановые Рукавицы",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 1_300_000_000,
        "description": "Аркановые рукавицы превращают удар в магический импульс.",
        "description_en": "Arcane gauntlets turn every strike into a magical pulse.",
        "bonus": {"hp": 1145, "phys_def": 588, "mag_def": 402, "stamina": 158, "regen": 93},
    },
    "gloves-lvl18": {
        "slot": "gloves", "level": 18, "key": "gloves-lvl18",
        "name": "Gloves Lvl 18", "ru_name": "Длани Вечного Воина",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 2_300_000_000,
        "description": "Перчатки, пережившие тысячелетия войн. Нестареющие.",
        "description_en": "Gloves that survived millennia of war. They never age.",
        "bonus": {"hp": 1376, "phys_def": 708, "mag_def": 484, "stamina": 190, "regen": 111},
    },
    "gloves-lvl19": {
        "slot": "gloves", "level": 19, "key": "gloves-lvl19",
        "name": "Gloves Lvl 19", "ru_name": "Рукавицы Короля",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 4_300_000_000,
        "description": "Парадные, но смертоносные рукавицы монарха.",
        "description_en": "The monarch's ceremonial yet deadly gauntlets.",
        "bonus": {"hp": 1655, "phys_def": 852, "mag_def": 584, "stamina": 229, "regen": 134},
    },
    "gloves-lvl20": {
        "slot": "gloves", "level": 20, "key": "gloves-lvl20",
        "name": "Gloves Lvl 20", "ru_name": "Наручи Небес",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 7_800_000_000,
        "description": "Небесные наручи избранного воина богов.",
        "description_en": "The celestial vambraces of the gods' chosen warrior.",
        "bonus": {"hp": 1990, "phys_def": 1026, "mag_def": 705, "stamina": 276, "regen": 161},
    },
    "gloves-lvl21": {
        "slot": "gloves", "level": 21, "key": "gloves-lvl21",
        "name": "Gloves Lvl 21", "ru_name": "Длани Титана",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 14_000_000_000,
        "description": "Кость Титана — даже прикосновение их разрушает.",
        "description_en": "Titan bone — even their touch brings ruin.",
        "bonus": {"hp": 2392, "phys_def": 1236, "mag_def": 850, "stamina": 332, "regen": 193},
    },
    "gloves-lvl22": {
        "slot": "gloves", "level": 22, "key": "gloves-lvl22",
        "name": "Gloves Lvl 22", "ru_name": "Астральные Рукавицы",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 26_000_000_000,
        "description": "Астральные рукавицы, сотканные из пространства и времени.",
        "description_en": "Astral gauntlets woven from space and time.",
        "bonus": {"hp": 2877, "phys_def": 1488, "mag_def": 1026, "stamina": 400, "regen": 231},
    },
    "gloves-lvl23": {
        "slot": "gloves", "level": 23, "key": "gloves-lvl23",
        "name": "Gloves Lvl 23", "ru_name": "Наручи Первородного",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 48_000_000_000,
        "description": "Длани Первородного: держали меч ещё до рождения мира.",
        "description_en": "The Primordial's hands: they held a sword before the world was born.",
        "bonus": {"hp": 3459, "phys_def": 1793, "mag_def": 1237, "stamina": 482, "regen": 278},
    },
    "gloves-lvl24": {
        "slot": "gloves", "level": 24, "key": "gloves-lvl24",
        "name": "Gloves Lvl 24", "ru_name": "Длани Богоборца",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 87_000_000_000,
        "description": "Рукавицы Богоборца дробили божественные доспехи.",
        "description_en": "The Godslayer's gauntlets shattered divine armor.",
        "bonus": {"hp": 4158, "phys_def": 2159, "mag_def": 1492, "stamina": 581, "regen": 333},
    },
    "gloves-lvl25": {
        "slot": "gloves", "level": 25, "key": "gloves-lvl25",
        "name": "Gloves Lvl 25", "ru_name": "Перчатки Абсолюта",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5404591969735308062",
        "price": 160_000_000_000,
        "description": "Абсолютные перчатки. Стойкость без предела.",
        "description_en": "Absolute gauntlets. Resilience without limit.",
        "bonus": {"hp": 5000, "phys_def": 2600, "mag_def": 1800, "stamina": 700, "regen": 400},
    },

    # ── ШТАНЫ ────────────────────────────────────────
    "pants-lvl1": {
        "slot": "pants", "level": 1, "key": "pants-lvl1",
        "name": "Pants Lvl 1", "ru_name": "Боевые Штаны",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 50_000,
        "description": "Прочные штаны с кожаными вставками. Дают свободу движений.",
        "description_en": "Sturdy trousers with leather inserts. Allow full freedom of movement.",
        "bonus": {"hp": 100, "phys_def": 20},
    },
    "pants-lvl2": {
        "slot": "pants", "level": 2, "key": "pants-lvl2",
        "name": "Pants Lvl 2", "ru_name": "Кольчужные Поножи",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 93_000,
        "description": "Усиленные поножи с кольчужными вставками на бёдрах.",
        "description_en": "Reinforced greaves with chainmail inserts on the thighs.",
        "bonus": {"hp": 119, "stamina": 18, "phys_def": 24, "regen": 4},
    },
    "pants-lvl3": {
        "slot": "pants", "level": 3, "key": "pants-lvl3",
        "name": "Pants Lvl 3", "ru_name": "Поножи Железного Рыцаря",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 170_000,
        "description": "Тяжёлые боевые штаны с наколенниками из закалённой стали.",
        "description_en": "Heavy battle trousers with kneecaps forged from tempered steel.",
        "bonus": {"hp": 142, "stamina": 21, "phys_def": 29, "regen": 4},
    },
    "pants-lvl4": {
        "slot": "pants", "level": 4, "key": "pants-lvl4",
        "name": "Pants Lvl 4", "ru_name": "Зачарованные Поножи",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 320_000,
        "description": "Латные поножи с кристаллами выносливости. Восстанавливают силы в бою.",
        "description_en": "Plate greaves set with stamina crystals. Restore strength in battle.",
        "bonus": {"hp": 170, "stamina": 25, "phys_def": 35, "regen": 5},
    },
    "pants-lvl5": {
        "slot": "pants", "level": 5, "key": "pants-lvl5",
        "name": "Pants Lvl 5", "ru_name": "Поножи Вечности",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 590_000,
        "description": "Реликвийные поножи. Тело бойца отказывается сдаваться.",
        "description_en": "Relic greaves. The wearer's body refuses to give up.",
        "bonus": {"hp": 203, "stamina": 30, "phys_def": 42, "regen": 7},
    },
    "pants-lvl6": {
        "slot": "pants", "level": 6, "key": "pants-lvl6",
        "name": "Pants Lvl 6", "ru_name": "Поножи Ветерана",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 1_100_000,
        "description": "Потёртые поножи с историей. Прошли сотни сражений.",
        "description_en": "Weathered greaves with a history. They've survived hundreds of battles.",
        "bonus": {"hp": 242, "stamina": 36, "phys_def": 50, "regen": 8},
    },
    "pants-lvl7": {
        "slot": "pants", "level": 7, "key": "pants-lvl7",
        "name": "Pants Lvl 7", "ru_name": "Штаны Чемпиона",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 2_000_000,
        "description": "Латные штаны чемпиона. Выдерживают удары двуручного оружия.",
        "description_en": "Champion's plate leggings. They withstand blows from two-handed weapons.",
        "bonus": {"hp": 289, "stamina": 43, "phys_def": 60, "regen": 10},
    },
    "pants-lvl8": {
        "slot": "pants", "level": 8, "key": "pants-lvl8",
        "name": "Pants Lvl 8", "ru_name": "Поножи Паладина",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 3_700_000,
        "description": "Освящённые поножи паладина. Ускоряют восстановление сил.",
        "description_en": "Blessed paladin's greaves. They speed up stamina recovery.",
        "bonus": {"hp": 345, "stamina": 51, "phys_def": 72, "regen": 12},
    },
    "pants-lvl9": {
        "slot": "pants", "level": 9, "key": "pants-lvl9",
        "name": "Pants Lvl 9", "ru_name": "Доспех Ног Воителя",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 6_900_000,
        "description": "Тяжёлые поножи воителя. Стабильность в любом бою.",
        "description_en": "Heavy warlord's greaves. Stability in any fight.",
        "bonus": {"hp": 412, "stamina": 61, "phys_def": 86, "regen": 15},
    },
    "pants-lvl10": {
        "slot": "pants", "level": 10, "key": "pants-lvl10",
        "name": "Pants Lvl 10", "ru_name": "Поножи Победителя",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 13_000_000,
        "description": "Поножи победителя. Никакой удар не заставит упасть.",
        "description_en": "The victor's greaves. No blow can bring you to your knees.",
        "bonus": {"hp": 492, "stamina": 72, "phys_def": 103, "regen": 18},
    },
    "pants-lvl11": {
        "slot": "pants", "level": 11, "key": "pants-lvl11",
        "name": "Pants Lvl 11", "ru_name": "Поножи Берсерка",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 24_000_000,
        "description": "Безумные штаны берсерка с рунами выносливости.",
        "description_en": "Berserker's frenzied leggings inscribed with runes of endurance.",
        "bonus": {"hp": 587, "stamina": 86, "phys_def": 124, "regen": 22},
    },
    "pants-lvl12": {
        "slot": "pants", "level": 12, "key": "pants-lvl12",
        "name": "Pants Lvl 12", "ru_name": "Штаны Темпляра",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 44_000_000,
        "description": "Монолитные поножи темпляров. Прочнее стального блока.",
        "description_en": "Monolithic templar greaves. Sturdier than a steel block.",
        "bonus": {"hp": 701, "stamina": 103, "phys_def": 149, "regen": 27},
    },
    "pants-lvl13": {
        "slot": "pants", "level": 13, "key": "pants-lvl13",
        "name": "Pants Lvl 13", "ru_name": "Поножи Тёмного Воина",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 81_000_000,
        "description": "Тёмные поножи убийцы. Лёгкие, но невероятно прочные.",
        "description_en": "Dark assassin's greaves. Light, yet incredibly durable.",
        "bonus": {"hp": 837, "stamina": 122, "phys_def": 179, "regen": 32},
    },
    "pants-lvl14": {
        "slot": "pants", "level": 14, "key": "pants-lvl14",
        "name": "Pants Lvl 14", "ru_name": "Поножи Повелителя",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 150_000_000,
        "description": "Золочёные поножи Повелителя с рунами регенерации.",
        "description_en": "Gilded greaves of the Overlord, etched with runes of regeneration.",
        "bonus": {"hp": 999, "stamina": 146, "phys_def": 215, "regen": 40},
    },
    "pants-lvl15": {
        "slot": "pants", "level": 15, "key": "pants-lvl15",
        "name": "Pants Lvl 15", "ru_name": "Доспех Ног Завоевателя",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 280_000_000,
        "description": "Поножи завоевателя. Прошли миллион шагов по полям сражений.",
        "description_en": "The conqueror's greaves. They've marched a million steps across battlefields.",
        "bonus": {"hp": 1192, "stamina": 174, "phys_def": 258, "regen": 48},
    },
    "pants-lvl16": {
        "slot": "pants", "level": 16, "key": "pants-lvl16",
        "name": "Pants Lvl 16", "ru_name": "Чешуйчатые Поножи Дракона",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 510_000_000,
        "description": "Чешуя Дракона защищает ноги лучше любой стали.",
        "description_en": "Dragon scales guard the legs better than any steel.",
        "bonus": {"hp": 1423, "stamina": 207, "phys_def": 309, "regen": 59},
    },
    "pants-lvl17": {
        "slot": "pants", "level": 17, "key": "pants-lvl17",
        "name": "Pants Lvl 17", "ru_name": "Аркановые Поножи",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 950_000_000,
        "description": "Аркановые поножи хранят энергию каждого шага.",
        "description_en": "Arcane greaves that store energy with every step.",
        "bonus": {"hp": 1698, "stamina": 247, "phys_def": 371, "regen": 72},
    },
    "pants-lvl18": {
        "slot": "pants", "level": 18, "key": "pants-lvl18",
        "name": "Pants Lvl 18", "ru_name": "Поножи Вечного Воина",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 1_700_000_000,
        "description": "Нестареющие поножи, переживавшие тысячелетия.",
        "description_en": "Ageless greaves that have endured for millennia.",
        "bonus": {"hp": 2027, "stamina": 294, "phys_def": 446, "regen": 87},
    },
    "pants-lvl19": {
        "slot": "pants", "level": 19, "key": "pants-lvl19",
        "name": "Pants Lvl 19", "ru_name": "Королевские Поножи",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 3_200_000_000,
        "description": "Парадные поножи монарха со скрытым зачарованием.",
        "description_en": "The monarch's ceremonial greaves, hiding a subtle enchantment.",
        "bonus": {"hp": 2420, "stamina": 350, "phys_def": 535, "regen": 106},
    },
    "pants-lvl20": {
        "slot": "pants", "level": 20, "key": "pants-lvl20",
        "name": "Pants Lvl 20", "ru_name": "Поножи Небес",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 6_000_000_000,
        "description": "Небесные поножи избранного. Ноги не устают никогда.",
        "description_en": "Heavenly greaves of the chosen one. The legs never tire.",
        "bonus": {"hp": 2889, "stamina": 417, "phys_def": 642, "regen": 130},
    },
    "pants-lvl21": {
        "slot": "pants", "level": 21, "key": "pants-lvl21",
        "name": "Pants Lvl 21", "ru_name": "Поножи Титана",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 11_000_000_000,
        "description": "Кость Первородного Титана — крепче любой горной породы.",
        "description_en": "Bone of the Primordial Titan - tougher than any mountain rock.",
        "bonus": {"hp": 3448, "stamina": 497, "phys_def": 771, "regen": 158},
    },
    "pants-lvl22": {
        "slot": "pants", "level": 22, "key": "pants-lvl22",
        "name": "Pants Lvl 22", "ru_name": "Астральные Поножи",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 21_000_000_000,
        "description": "Астральные поножи вне времени и пространства.",
        "description_en": "Astral greaves that exist beyond time and space.",
        "bonus": {"hp": 4116, "stamina": 592, "phys_def": 925, "regen": 193},
    },
    "pants-lvl23": {
        "slot": "pants", "level": 23, "key": "pants-lvl23",
        "name": "Pants Lvl 23", "ru_name": "Поножи Первородного",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 38_000_000_000,
        "description": "Поножи Первородного: выдержали всю мощь мироздания.",
        "description_en": "Greaves of the Firstborn: they withstood the full force of creation.",
        "bonus": {"hp": 4913, "stamina": 705, "phys_def": 1111, "regen": 235},
    },
    "pants-lvl24": {
        "slot": "pants", "level": 24, "key": "pants-lvl24",
        "name": "Pants Lvl 24", "ru_name": "Поножи Богоборца",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 70_000_000_000,
        "description": "Поножи Богоборца не знают усталости.",
        "description_en": "The Godslayer's greaves know no fatigue.",
        "bonus": {"hp": 5864, "stamina": 839, "phys_def": 1333, "regen": 287},
    },
    "pants-lvl25": {
        "slot": "pants", "level": 25, "key": "pants-lvl25",
        "name": "Pants Lvl 25", "ru_name": "Поножи Абсолюта",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "4952249553173613188",
        "price": 130_000_000_000,
        "description": "Абсолютные поножи. Совершенная выносливость.",
        "description_en": "Absolute greaves. Perfect endurance.",
        "bonus": {"hp": 7000, "stamina": 1000, "phys_def": 1600, "regen": 350},
    },

    # ── САПОГИ ────────────────────────────────────────
    "boots-lvl1": {
        "slot": "boots", "level": 1, "key": "boots-lvl1",
        "name": "Boots Lvl 1", "ru_name": "Походные Сапоги",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 25_000,
        "description": "Добротные кожаные сапоги. Мягкая подошва гасит шум шагов.",
        "description_en": "Sturdy leather boots. A soft sole muffles the sound of footsteps.",
        "bonus": {"phys_def": 8},
    },
    "boots-lvl2": {
        "slot": "boots", "level": 2, "key": "boots-lvl2",
        "name": "Boots Lvl 2", "ru_name": "Сапоги Следопыта",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 47_000,
        "description": "Лёгкие сапоги из кожи ночной пантеры. Почти бесшумны.",
        "description_en": "Lightweight boots made from night panther hide. Nearly silent.",
        "bonus": {"regen": 4, "stamina": 12, "phys_def": 10},
    },
    "boots-lvl3": {
        "slot": "boots", "level": 3, "key": "boots-lvl3",
        "name": "Boots Lvl 3", "ru_name": "Сапоги Ветра Пустоши",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 87_000,
        "description": "Сапоги из кожи горного дракона, пропитанные эликсиром скорости.",
        "description_en": "Boots of mountain dragon hide, soaked in a speed elixir.",
        "bonus": {"regen": 5, "stamina": 15, "phys_def": 12},
    },
    "boots-lvl4": {
        "slot": "boots", "level": 4, "key": "boots-lvl4",
        "name": "Boots Lvl 4", "ru_name": "Сапоги Призрака",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 160_000,
        "description": "Зачарованные сапоги разведчиков. Молниеносное перемещение.",
        "description_en": "Enchanted scout boots. Lightning-fast movement.",
        "bonus": {"regen": 6, "stamina": 18, "phys_def": 14},
    },
    "boots-lvl5": {
        "slot": "boots", "level": 5, "key": "boots-lvl5",
        "name": "Boots Lvl 5", "ru_name": "Сапоги Грома",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 300_000,
        "description": "Реликвийные сапоги Громового Бога. Надевший их — неудержим.",
        "description_en": "Relic boots of the Thunder God. Whoever wears them is unstoppable.",
        "bonus": {"regen": 7, "stamina": 21, "phys_def": 17},
    },
    "boots-lvl6": {
        "slot": "boots", "level": 6, "key": "boots-lvl6",
        "name": "Boots Lvl 6", "ru_name": "Сапоги Ветерана",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 570_000,
        "description": "Потрёпанные сапоги с историей. Прошли тысячи лиг.",
        "description_en": "Worn boots with a history. They've marched thousands of leagues.",
        "bonus": {"regen": 9, "stamina": 26, "phys_def": 21},
    },
    "boots-lvl7": {
        "slot": "boots", "level": 7, "key": "boots-lvl7",
        "name": "Boots Lvl 7", "ru_name": "Сапоги Чемпиона",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 1_100_000,
        "description": "Прочные сапоги чемпиона. Держат позицию в любом бою.",
        "description_en": "Sturdy champion's boots. Hold their ground in any fight.",
        "bonus": {"regen": 11, "stamina": 31, "phys_def": 25},
    },
    "boots-lvl8": {
        "slot": "boots", "level": 8, "key": "boots-lvl8",
        "name": "Boots Lvl 8", "ru_name": "Сапоги Паладина",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 2_000_000,
        "description": "Освящённые сапоги паладина. Восстанавливают силы на марше.",
        "description_en": "Blessed paladin's boots. They restore strength on the march.",
        "bonus": {"regen": 13, "stamina": 37, "phys_def": 31},
    },
    "boots-lvl9": {
        "slot": "boots", "level": 9, "key": "boots-lvl9",
        "name": "Boots Lvl 9", "ru_name": "Сапоги Воителя",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 3_700_000,
        "description": "Тяжёлые сапоги воителя. Устойчивость как у скалы.",
        "description_en": "Heavy warlord's boots. Stability like solid rock.",
        "bonus": {"regen": 17, "stamina": 45, "phys_def": 37},
    },
    "boots-lvl10": {
        "slot": "boots", "level": 10, "key": "boots-lvl10",
        "name": "Boots Lvl 10", "ru_name": "Сапоги Победителя",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 6_900_000,
        "description": "Сапоги победителя. Ни разу не сделали шаг назад.",
        "description_en": "The victor's boots. Never once took a step back.",
        "bonus": {"regen": 20, "stamina": 54, "phys_def": 45},
    },
    "boots-lvl11": {
        "slot": "boots", "level": 11, "key": "boots-lvl11",
        "name": "Boots Lvl 11", "ru_name": "Сапоги Берсерка",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 13_000_000,
        "description": "Безумные сапоги берсерка с рунами скорости и ярости.",
        "description_en": "Berserker's frenzied boots inscribed with runes of speed and rage.",
        "bonus": {"regen": 25, "stamina": 65, "phys_def": 55},
    },
    "boots-lvl12": {
        "slot": "boots", "level": 12, "key": "boots-lvl12",
        "name": "Boots Lvl 12", "ru_name": "Сапоги Темпляра",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 24_000_000,
        "description": "Монолитные сапоги темпляров. Не скользят даже на льду.",
        "description_en": "Monolithic templar boots. They never slip, even on ice.",
        "bonus": {"regen": 31, "stamina": 79, "phys_def": 66},
    },
    "boots-lvl13": {
        "slot": "boots", "level": 13, "key": "boots-lvl13",
        "name": "Boots Lvl 13", "ru_name": "Сапоги Тёмного Следопыта",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 45_000_000,
        "description": "Тёмные сапоги убийцы. Беззвучны как ночь.",
        "description_en": "Dark tracker's boots. Silent as the night.",
        "bonus": {"regen": 39, "stamina": 95, "phys_def": 80},
    },
    "boots-lvl14": {
        "slot": "boots", "level": 14, "key": "boots-lvl14",
        "name": "Boots Lvl 14", "ru_name": "Сапоги Повелителя",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 83_000_000,
        "description": "Золочёные сапоги Повелителя с рунами восстановления.",
        "description_en": "Gilded boots of the Overlord, etched with runes of recovery.",
        "bonus": {"regen": 48, "stamina": 114, "phys_def": 97},
    },
    "boots-lvl15": {
        "slot": "boots", "level": 15, "key": "boots-lvl15",
        "name": "Boots Lvl 15", "ru_name": "Сапоги Завоевателя",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 160_000_000,
        "description": "Сапоги завоевателя. Прошли все земли этого мира.",
        "description_en": "The conqueror's boots. They've crossed every land in this world.",
        "bonus": {"regen": 59, "stamina": 138, "phys_def": 117},
    },
    "boots-lvl16": {
        "slot": "boots", "level": 16, "key": "boots-lvl16",
        "name": "Boots Lvl 16", "ru_name": "Сапоги Дракона",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 290_000_000,
        "description": "Чешуя Дракона защищает стопы лучше любой кожи.",
        "description_en": "Dragon scales protect the feet better than any leather.",
        "bonus": {"regen": 73, "stamina": 166, "phys_def": 142},
    },
    "boots-lvl17": {
        "slot": "boots", "level": 17, "key": "boots-lvl17",
        "name": "Boots Lvl 17", "ru_name": "Арканические Сапоги",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 540_000_000,
        "description": "Арканические сапоги заряжаются от каждого шага.",
        "description_en": "Arcane boots that charge with every step.",
        "bonus": {"regen": 91, "stamina": 201, "phys_def": 172},
    },
    "boots-lvl18": {
        "slot": "boots", "level": 18, "key": "boots-lvl18",
        "name": "Boots Lvl 18", "ru_name": "Сапоги Вечного Воина",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 1_000_000_000,
        "description": "Нестареющие сапоги, переживавшие тысячелетия.",
        "description_en": "Ageless boots that have endured for millennia.",
        "bonus": {"regen": 112, "stamina": 242, "phys_def": 209},
    },
    "boots-lvl19": {
        "slot": "boots", "level": 19, "key": "boots-lvl19",
        "name": "Boots Lvl 19", "ru_name": "Королевские Сапоги",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 1_900_000_000,
        "description": "Парадные сапоги монарха со скрытым зачарованием скорости.",
        "description_en": "The monarch's ceremonial boots, hiding a subtle speed enchantment.",
        "bonus": {"regen": 139, "stamina": 292, "phys_def": 253},
    },
    "boots-lvl20": {
        "slot": "boots", "level": 20, "key": "boots-lvl20",
        "name": "Boots Lvl 20", "ru_name": "Сапоги Небес",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 3_500_000_000,
        "description": "Небесные сапоги избранного. Усталость им незнакома.",
        "description_en": "Heavenly boots of the chosen one. Fatigue is unknown to them.",
        "bonus": {"regen": 172, "stamina": 352, "phys_def": 306},
    },
    "boots-lvl21": {
        "slot": "boots", "level": 21, "key": "boots-lvl21",
        "name": "Boots Lvl 21", "ru_name": "Сапоги Титана",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 6_600_000_000,
        "description": "Кость Первородного Титана — даже вес их сокрушителен.",
        "description_en": "Bone of the Primordial Titan - even their weight is crushing.",
        "bonus": {"regen": 213, "stamina": 425, "phys_def": 371},
    },
    "boots-lvl22": {
        "slot": "boots", "level": 22, "key": "boots-lvl22",
        "name": "Boots Lvl 22", "ru_name": "Астральные Сапоги",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 12_000_000_000,
        "description": "Астральные сапоги, шагающие сквозь пространство.",
        "description_en": "Astral boots that stride through space itself.",
        "bonus": {"regen": 264, "stamina": 513, "phys_def": 450},
    },
    "boots-lvl23": {
        "slot": "boots", "level": 23, "key": "boots-lvl23",
        "name": "Boots Lvl 23", "ru_name": "Сапоги Первородного",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 23_000_000_000,
        "description": "Сапоги Первородного: ступали по мирозданию ещё до его рождения.",
        "description_en": "Boots of the Firstborn: they walked the cosmos before it was born.",
        "bonus": {"regen": 326, "stamina": 619, "phys_def": 545},
    },
    "boots-lvl24": {
        "slot": "boots", "level": 24, "key": "boots-lvl24",
        "name": "Boots Lvl 24", "ru_name": "Сапоги Богоборца",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 43_000_000_000,
        "description": "Сапоги Богоборца несут следы битв с богами.",
        "description_en": "The Godslayer's boots bear the scars of battles against gods.",
        "bonus": {"regen": 404, "stamina": 746, "phys_def": 660},
    },
    "boots-lvl25": {
        "slot": "boots", "level": 25, "key": "boots-lvl25",
        "name": "Boots Lvl 25", "ru_name": "Сапоги Абсолюта",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5776192535890235363",
        "price": 80_000_000_000,
        "description": "Абсолютные сапоги. Вершина скорости и регенерации.",
        "description_en": "Absolute boots. The pinnacle of speed and regeneration.",
        "bonus": {"regen": 500, "stamina": 900, "phys_def": 800},
    },

}
GEAR_SLOTS_ORDER = ["helmet", "armor", "gloves", "pants", "boots"]

def slot_levels(slot: str) -> list:
    return [f"{slot}-lvl{i}" for i in range(1, 26)]

def slot_label(slot: str, lang: str = "ru") -> str:
    return t(lang, f"duel_slot_{slot}")

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

_FMT_SUFFIXES = {
    "ru": [
        (1_000_000_000_000, "трлн"),
        (1_000_000_000,     "млрд"),
        (1_000_000,         "м"),
        (1_000,             "к"),
    ],
    "en": [
        (1_000_000_000_000, "T"),
        (1_000_000_000,     "B"),
        (1_000_000,         "M"),
        (1_000,             "K"),
    ],
}

def _fmt(n, lang: str = "ru") -> str:
    """Сокращает число как format_amount в database.py: 1500->1.5к/1.5K, 2.3м/2.3M, 1.5млрд/1.5B."""
    try:
        n = float(n)
    except (TypeError, ValueError):
        return str(n)
    sign = "-" if n < 0 else ""
    n = abs(n)
    if n < 1000:
        return f"{sign}{int(n)}" if n == int(n) else f"{sign}{n:.1f}"
    for threshold, suffix in _FMT_SUFFIXES.get(lang, _FMT_SUFFIXES["ru"]):
        if n >= threshold:
            value = int(n / threshold * 10) / 10
            if value == int(value):
                return f"{sign}{int(value)}{suffix}"
            return f"{sign}{value:.1f}{suffix}"
    return f"{sign}{int(n)}"


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
        "emoji_id": "5222108309795908493",
        "type": "magic",
        "cooldown": 8,
        "base_dmg": (18, 28),
        "description": "Сгусток хаотичной маг. энергии. Быстрый и доступный — твой первый шаг к победе.",
        "description_en": "A clump of chaotic magic energy. Fast and accessible - your first step to victory.",
        "price": 0,
    },
    "explosion": {
        "key": "explosion",
        "name": "Удар",
        "emoji": "💥",
        "emoji_id": "5231406626228948265",
        "type": "physical",
        "cooldown": 10,
        "base_dmg": (22, 35),
        "description": "Удар с вложением всей физической мощи. Простой, надёжный, смертоносный.",
        "description_en": "A strike backed by full physical force. Simple, reliable, deadly.",
        "price": 0,
    },
    "shield": {
        "key": "shield",
        "name": "Барьер",
        "emoji": "🛡️",
        "emoji_id": "5465154440287757794",
        "type": "shield",
        "cooldown": 25,
        "shield_amount": (20, 35),
        "description": "Магический барьер, сотканный из чистой воли бойца. Поглощает следующий удар.",
        "description_en": "A magic barrier woven from the fighter's pure will. Absorbs the next hit.",
        "price": 0,
    },

    # ── Покупаемые навыки ────────────────────────────────────
    "iron_fist": {
        "key": "iron_fist",
        "name": "Стальной Кулак",
        "emoji": "✊",
        "emoji_id": "5458465612839792700",
        "type": "physical",
        "cooldown": 8,
        "base_dmg": (25, 35),
        "description": "Удар голой рукой — но с такой силой, что броня крошится как глина.",
        "description_en": "A bare-handed punch - but with such force that armor crumbles like clay.",
        "price": 500_000,
    },
    "mag_block": {
        "key": "mag_block",
        "name": "Астральный Удар",
        "emoji": "🟣",
        "emoji_id": "5226893221191237996",
        "type": "magic",
        "cooldown": 9,
        "base_dmg": (29, 40),
        "description": "Концентрированный пучок маг. силы, пробивающий защиту насквозь.",
        "description_en": "A concentrated beam of magic energy that pierces straight through defense.",
        "price": 840_000,
    },
    "arcane_surge": {
        "key": "arcane_surge",
        "name": "Арканный Удар",
        "emoji": "✨",
        "emoji_id": "5337037846475720165",
        "type": "magic",
        "cooldown": 10,
        "base_dmg": (33, 46),
        "description": "Выброс чистой аркановой энергии — быстро, метко, без промаха.",
        "description_en": "A burst of pure arcane energy - fast, precise, never misses.",
        "price": 1_400_000,
    },
    "shadow_strike": {
        "key": "shadow_strike",
        "name": "Тьма",
        "emoji": "🌑",
        "emoji_id": "5335072469441078225",
        "type": "physical",
        "cooldown": 11,
        "base_dmg": (38, 53),
        "description": "Удар рождается в тени и настигает раньше, чем враг успевает моргнуть.",
        "description_en": "A strike born in shadow that lands before the enemy can blink.",
        "price": 2_400_000,
    },
    "poison_dart": {
        "key": "poison_dart",
        "name": "Яд",
        "emoji": "🧪",
        "emoji_id": "5899831875404304784",
        "type": "magic",
        "cooldown": 11,
        "base_dmg": (44, 61),
        "description": "Игла, пропитанная редчайшим ядом. Проникает сквозь магическую защиту.",
        "description_en": "A needle soaked in the rarest poison. Pierces right through magic defense.",
        "price": 4_000_000,
    },
    "thunder": {
        "key": "thunder",
        "name": "Гром",
        "emoji": "⚡",
        "emoji_id": "5307493878843059915",
        "type": "magic",
        "cooldown": 12,
        "base_dmg": (51, 70),
        "description": "Молния бьёт из раскрытой ладони. Часть маг. защиты просто испаряется.",
        "description_en": "Lightning strikes from an open palm. Part of the magic defense simply evaporates.",
        "price": 6_700_000,
    },
    "chain_lightning": {
        "key": "chain_lightning",
        "name": "Молния",
        "emoji": "🌩️",
        "emoji_id": "5438571934210082705",
        "type": "magic",
        "cooldown": 13,
        "base_dmg": (59, 80),
        "description": "Разряд прыгает по противнику снова и снова — стабильный и безжалостный.",
        "description_en": "A charge that keeps leaping across the enemy - steady and merciless.",
        "price": 11_000_000,
    },
    "blade_storm": {
        "key": "blade_storm",
        "name": "Вихрь",
        "emoji": "🌪️",
        "emoji_id": "5220181540222291016",
        "type": "physical",
        "cooldown": 14,
        "base_dmg": (67, 92),
        "description": "Сотни невидимых клинков обрушиваются на врага в вихре стали.",
        "description_en": "Hundreds of invisible blades crash down on the enemy in a whirlwind of steel.",
        "price": 19_000_000,
    },
    "inferno": {
        "key": "inferno",
        "name": "Инферно",
        "emoji": "🔥",
        "emoji_id": "5256047523620995497",
        "type": "magic",
        "cooldown": 15,
        "base_dmg": (78, 105),
        "description": "Огонь из глубин преисподней — жжёт, не оставляя следов магической защиты.",
        "description_en": "Fire from the depths of hell - it burns, leaving no trace of magic defense.",
        "price": 31_000_000,
    },
    "war_cry": {
        "key": "war_cry",
        "name": "Боевой Клич",
        "emoji": "📣",
        "emoji_id": "5462921117423384478",
        "type": "physical",
        "cooldown": 16,
        "base_dmg": (90, 121),
        "description": "Боевой клич, от которого кровь стынет в жилах. Мощнейший физический выброс.",
        "description_en": "A war cry that freezes the blood. The mightiest physical burst there is.",
        "price": 53_000_000,
    },
    "freeze": {
        "key": "freeze",
        "name": "Заморозка",
        "emoji": "❄️",
        "emoji_id": "5449449325434266744",
        "type": "magic",
        "cooldown": 16,
        "base_dmg": (103, 138),
        "freeze_turns": 1,
        "description": "Враг покрывается льдом и теряет ход. Урон невелик — зато время на твоей стороне.",
        "description_en": "The enemy is coated in ice and loses their turn. Damage is small - but time is on your side.",
        "price": 89_000_000,
    },
    "earthquake": {
        "key": "earthquake",
        "name": "Землетрясение",
        "emoji": "🌍",
        "emoji_id": "5361662921208254475",
        "type": "physical",
        "cooldown": 17,
        "base_dmg": (119, 159),
        "description": "Земля раскалывается под врагом. Сила удара — как горный обвал.",
        "description_en": "The ground splits open beneath the enemy. The force hits like a landslide.",
        "price": 150_000_000,
    },
    "berserker": {
        "key": "berserker",
        "name": "Берсерк",
        "emoji": "🔴",
        "emoji_id": "5463335865235288297",
        "type": "physical",
        "cooldown": 18,
        "base_dmg": (137, 182),
        "description": "Разум выключается — остаётся только ярость. Один из самых разрушительных физ. ударов.",
        "description_en": "The mind shuts off - only rage remains. One of the most devastating physical strikes.",
        "price": 250_000_000,
    },
    "mega_shield": {
        "key": "mega_shield",
        "name": "Щит Цитадели",
        "emoji": "🔰",
        "emoji_id": "5251203410396458957",
        "type": "shield",
        "cooldown": 40,
        "shield_amount": (350, 600),
        "description": "Колоссальный щит из сжатой магии. Способен поглотить удар любой силы.",
        "description_en": "A colossal shield of compressed magic. Able to absorb a blow of any strength.",
        "price": 420_000_000,
    },
    "soul_drain": {
        "key": "soul_drain",
        "name": "Жизнекрад",
        "emoji": "💜",
        "emoji_id": "5343545593807521643",
        "type": "magic",
        "cooldown": 20,
        "base_dmg": (158, 209),
        "drain_regen": 15,
        "description": "Вытягивает жизненную силу врага прямо в тебя. Часть урона возвращается как HP.",
        "description_en": "Draws the enemy's life force straight into you. Part of the damage returns as HP.",
        "price": 700_000_000,
    },
    "void_blast": {
        "key": "void_blast",
        "name": "Разрыв Бездны",
        "emoji": "🌀",
        "emoji_id": "5267114941378209946",
        "type": "magic",
        "cooldown": 21,
        "base_dmg": (182, 240),
        "description": "Открывает брешь в ткани мироздания прямо под ногами врага. Боль неизбежна.",
        "description_en": "Tears open a breach in the fabric of creation right under the enemy's feet. Pain is inevitable.",
        "price": 1_200_000_000,
    },
    "titan_slam": {
        "key": "titan_slam",
        "name": "Титан",
        "emoji": "⚒️",
        "emoji_id": "5235917510120861097",
        "type": "physical",
        "cooldown": 22,
        "base_dmg": (210, 275),
        "description": "Удар, от которого трескается камень под ногами. Мощь первородных существ.",
        "description_en": "A blow that cracks the stone underfoot. The might of primordial beings.",
        "price": 2_000_000_000,
    },
    "meteor": {
        "key": "meteor",
        "name": "Метеор",
        "emoji": "☄️",
        "emoji_id": "6001590126071779800",
        "type": "magic",
        "cooldown": 22,
        "base_dmg": (242, 316),
        "description": "С небес обрушивается раскалённый камень. Враг не успевает даже вскрикнуть.",
        "description_en": "A blazing rock crashes down from the sky. The enemy doesn't even have time to scream.",
        "price": 3_300_000_000,
    },
    "dark_nova": {
        "key": "dark_nova",
        "name": "Тёмный Взрыв",
        "emoji": "🖤",
        "emoji_id": "5204470073112146941",
        "type": "magic",
        "cooldown": 23,
        "base_dmg": (279, 363),
        "description": "Взрыв тёмной материи поглощает всё вокруг. Один из разрушительнейших ударов.",
        "description_en": "An explosion of dark matter swallows everything around it. One of the most devastating strikes.",
        "price": 5_600_000_000,
    },
    "divine_wrath": {
        "key": "divine_wrath",
        "name": "Небесная Кара",
        "emoji": "⚜️",
        "emoji_id": "6332360083116132292",
        "type": "magic",
        "cooldown": 24,
        "base_dmg": (321, 416),
        "description": "Священный огонь нисходит с небес. Абсолютное уничтожение — без исключений.",
        "description_en": "Sacred fire descends from the heavens. Absolute annihilation - no exceptions.",
        "price": 9_300_000_000,
    },

    # ── Новые навыки ─────────────────────────────────────────
    "bloodlust": {
        "key": "bloodlust",
        "name": "Жажда Крови",
        "emoji": "🩸",
        "emoji_id": "5269535069550162819",
        "type": "physical",
        "cooldown": 25,
        "base_dmg": (370, 477),
        "drain_regen": 10,
        "description": "Атака, пропитанная животным инстинктом. Часть нанесённого урона возвращается как HP.",
        "description_en": "An attack fueled by animal instinct. Part of the damage dealt returns as HP.",
        "price": 16_000_000_000,
    },
    "storm_eye": {
        "key": "storm_eye",
        "name": "Око Бури",
        "emoji": "🌊",
        "emoji_id": "5249454534073276043",
        "type": "magic",
        "cooldown": 26,
        "base_dmg": (427, 548),
        "description": "В центре шторма — абсолютная тишина. А потом — волна, сметающая всё.",
        "description_en": "At the center of the storm - absolute silence. Then a wave that sweeps away everything.",
        "price": 26_000_000_000,
    },
    "obsidian_edge": {
        "key": "obsidian_edge",
        "name": "Тёмный Клинок",
        "emoji": "🗡️",
        "emoji_id": "5449883370534238228",
        "type": "physical",
        "cooldown": 27,
        "base_dmg": (492, 628),
        "description": "Клинок из вулканического стекла — острее любой стали. Молниеносный и точный.",
        "description_en": "A blade of volcanic glass - sharper than any steel. Lightning-fast and precise.",
        "price": 44_000_000_000,
    },
    "echo_blast": {
        "key": "echo_blast",
        "name": "Ударная Волна",
        "emoji": "🔊",
        "emoji_id": "5818973781707722673",
        "type": "physical",
        "cooldown": 27,
        "base_dmg": (567, 721),
        "description": "Ударная волна, отражающаяся от каждой поверхности и бьющая снова и снова.",
        "description_en": "A shockwave that bounces off every surface, striking again and again.",
        "price": 74_000_000_000,
    },
    "abyss_call": {
        "key": "abyss_call",
        "name": "Зов Бездны",
        "emoji": "🕳️",
        "emoji_id": "5206523956537865948",
        "type": "magic",
        "cooldown": 28,
        "base_dmg": (653, 827),
        "freeze_turns": 1,
        "description": "Из пустоты тянутся щупальца тьмы. Враг получает урон и теряет ход от ужаса.",
        "description_en": "Tendrils of darkness reach out of the void. The enemy takes damage and loses their turn from terror.",
        "price": 120_000_000_000,
    },
    "runic_fortress": {
        "key": "runic_fortress",
        "name": "Рунический Щит",
        "emoji": "🏰",
        "emoji_id": "6111804548869787620",
        "type": "shield",
        "cooldown": 55,
        "shield_amount": (800, 1500),
        "description": "Древние руны складываются в неприступную стену. Поглощает даже самые мощные удары.",
        "description_en": "Ancient runes form an impregnable wall. Absorbs even the mightiest blows.",
        "price": 210_000_000_000,
    },
    "solar_lance": {
        "key": "solar_lance",
        "name": "Солнечное Копьё",
        "emoji": "☀️",
        "emoji_id": "5402477260982731644",
        "type": "magic",
        "cooldown": 30,
        "base_dmg": (753, 949),
        "description": "Луч солнечного света, сжатый до точки и выпущенный как копьё. Жжёт и слепит.",
        "description_en": "A beam of sunlight compressed to a point and launched like a spear. It burns and blinds.",
        "price": 350_000_000_000,
    },
}

SKILLS_ORDER_BASE = ["mag_ball", "explosion", "shield"]
SKILLS_ORDER = list(SKILLS.keys())


def _skill_emoji(sk: dict) -> str:
    """Возвращает <tg-emoji> если есть emoji_id, иначе обычный emoji."""
    eid = sk.get("emoji_id")
    if eid:
        return f'<tg-emoji emoji-id="{eid}">{sk["emoji"]}</tg-emoji>'
    return sk["emoji"]

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
    """Возвращает список навыков, экипированных в бой (макс. 5).

    Базовые (бесплатные) навыки экипированы по умолчанию у всех —
    но их, как и остальные, можно снять/поменять.
    """
    owned = get_owned_skills(user_data)
    if "duel_equipped_skills" not in user_data:
        # Первое обращение — по умолчанию надеты базовые навыки
        base_keys = [k for k, v in SKILLS.items() if v["price"] == 0]
        user_data["duel_equipped_skills"] = [k for k in base_keys if k in owned]
    stored = user_data.get("duel_equipped_skills", [])
    return [k for k in stored if k in owned]


def equip_skill(skill_key: str, user_data: dict) -> tuple:
    """Экипировать навык в бой. Возвращает (ok, msg)."""
    owned = get_owned_skills(user_data)
    if skill_key not in owned:
        return False, "❌ Навык не куплен!"
    equipped = get_equipped_skills(user_data)  # инициализирует список базовыми при первом входе
    if skill_key in equipped:
        return False, "❌ Навык уже экипирован!"
    if len(equipped) >= MAX_EQUIPPED_SKILLS:
        return False, f"❌ Максимум {MAX_EQUIPPED_SKILLS} навыков в бою!"
    stored = user_data.setdefault("duel_equipped_skills", [])
    stored.append(skill_key)
    return True, "✅ Навык экипирован!"


def unequip_skill(skill_key: str, user_data: dict) -> tuple:
    """Снять навык с экипировки. Возвращает (ok, msg)."""
    get_equipped_skills(user_data)  # инициализирует список базовыми при первом входе
    stored = user_data.setdefault("duel_equipped_skills", [])
    if skill_key not in stored:
        return False, "❌ Навык не экипирован!"
    stored.remove(skill_key)
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
        power_line = f'<tg-emoji emoji-id="5465154440287757794">✨</tg-emoji> <b>Поглощает:</b> {sk["shield_amount"][0]}–{sk["shield_amount"][1]} HP'
    else:
        power_line = f'<tg-emoji emoji-id="5454014806950429357">✨</tg-emoji> <b>Урон:</b> {sk["base_dmg"][0]}–{sk["base_dmg"][1]}'

    # Статус
    if is_equip:
        status_line = '✅ <b>Экипирован в бой</b>'
    elif is_owned:
        status_line = '📦 <b>Куплен</b> — не экипирован в бой'
    else:
        status_line = f'<tg-emoji emoji-id="5427168083074628963">✨</tg-emoji> <b>Цена: {_fmt(sk["price"])} <tg-emoji emoji-id="5199552030615558774">✨</tg-emoji></b>'
        if balance < sk["price"]:
            deficit = sk["price"] - balance
            status_line += f'\n⚠️ <i>Не хватает {_fmt(deficit)} монет</i>'

    # Слоты
    slot_info = f'{len(equipped)}/{MAX_EQUIPPED_SKILLS} навыков экипировано'

    return (
        f'{_skill_emoji(sk)} <b>{sk["name"]}</b>\n'
        f'<i>{type_label} · <tg-emoji emoji-id="5440621591387980068">✨</tg-emoji> Перезарядка: {sk["cooldown"]} сек.</i>\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote><b><i>{sk["description"]}</i></b></blockquote>\n\n'
        f'<b><tg-emoji emoji-id="5463277406435422003">✨</tg-emoji>Характеристики:</b>\n'
        f'{power_line}\n'
        f'<tg-emoji emoji-id="5440621591387980068">✨</tg-emoji> <b>Кулдаун:</b> {sk["cooldown"]} сек.\n\n'
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
            text="Снять из боя",
            callback_data=f"duel_skill_unequip:{skill_key}",
            style="danger",
        ))
    elif is_owned:
        if len(equipped) < MAX_EQUIPPED_SKILLS:
            builder.row(InlineKeyboardButton(
                text="Экипировать в бой",
                callback_data=f"duel_skill_equip:{skill_key}",
                style="primary",
            ))
        else:
            builder.row(InlineKeyboardButton(
                text=f"⚠️ Все {MAX_EQUIPPED_SKILLS} слотов заняты",
                callback_data="duel_skill_slots_full",
            ))
    else:
        if sk and balance >= sk["price"]:
            builder.row(InlineKeyboardButton(
                text=f"📖 Изучить — {_fmt(sk['price'])} монет",
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
    """Вычислить урон от навыка.

    Формула защиты: resist = min(0.65, def / (def + 300))
    Это процентное смягчение с кэпом 65% — защита никогда не делает урон
    близким к нулю, даже у самых прокачанных игроков.

    Бонус атаки: к base_dmg добавляется stamina * 0.5, чтобы урон
    масштабировался вместе с уровнем снаряжения и бои не становились
    вечными у равно прокачанных игроков.
    """
    _DEF_K   = 300    # кривизна кривой защиты (больше → защита слабее)
    _DEF_CAP = 0.65   # максимум 65% поглощения
    _STM_DMG = 0.5    # бонус урона за единицу стойкости

    sk = SKILLS[skill_key]
    result = {"type": sk["type"], "skill": skill_key}

    # Бонус атаки от стойкости атакующего
    stam_bonus = int(attacker_stats.get("stamina", 0) * _STM_DMG)

    if sk["type"] == "magic":
        base_min, base_max = sk["base_dmg"]
        base = random.randint(base_min, base_max) + stam_bonus
        def_val = max(0, defender_stats.get("mag_def", 10))
        resist  = min(_DEF_CAP, def_val / (def_val + _DEF_K))
        dmg = max(1, int(base * (1.0 - resist)))
        result["dmg"] = dmg

    elif sk["type"] == "physical":
        base_min, base_max = sk["base_dmg"]
        base = random.randint(base_min, base_max) + stam_bonus
        def_val = max(0, defender_stats.get("phys_def", 10))
        resist  = min(_DEF_CAP, def_val / (def_val + _DEF_K))
        dmg = max(1, int(base * (1.0 - resist)))
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

# ── Ограничение частоты вызовов одному и тому же игроку ─────
CHALLENGE_DAILY_LIMIT = 10          # макс. вызовов одному игроку за 24 часа
CHALLENGE_LIMIT_WINDOW = 86400      # окно в секундах (24 часа)
# (challenger_uid, target_uid) -> [timestamp, timestamp, ...]
_challenge_daily_log: dict[tuple[int, int], list[int]] = {}


def _clean_challenge_log(key: tuple[int, int]) -> list[int]:
    """Оставляет в логе только вызовы за последние 24 часа."""
    now = int(time.time())
    cutoff = now - CHALLENGE_LIMIT_WINDOW
    log = [ts for ts in _challenge_daily_log.get(key, []) if ts > cutoff]
    if log:
        _challenge_daily_log[key] = log
    else:
        _challenge_daily_log.pop(key, None)
    return log


def challenges_sent_today(challenger_uid: int, target_uid: int) -> int:
    """Сколько раз challenger уже вызывал target за последние 24 часа."""
    return len(_clean_challenge_log((challenger_uid, target_uid)))


def can_challenge_target(challenger_uid: int, target_uid: int) -> bool:
    """True, если дневной лимит вызовов (10/сутки) этому игроку ещё не исчерпан."""
    return challenges_sent_today(challenger_uid, target_uid) < CHALLENGE_DAILY_LIMIT


def seconds_until_challenge_slot(challenger_uid: int, target_uid: int) -> int:
    """Через сколько секунд освободится слот вызова (истечёт самый старый вызов из лога)."""
    log = _clean_challenge_log((challenger_uid, target_uid))
    if len(log) < CHALLENGE_DAILY_LIMIT:
        return 0
    oldest = min(log)
    return max(0, oldest + CHALLENGE_LIMIT_WINDOW - int(time.time()))


def create_challenge(challenger_uid: int, target_uid: int, target_name: str) -> bool:
    """
    Создаёт вызов на дуэль.
    Возвращает False, если превышен дневной лимит вызовов этому игроку
    (CHALLENGE_DAILY_LIMIT в сутки) — в этом случае вызов НЕ создаётся.
    """
    if not can_challenge_target(challenger_uid, target_uid):
        return False

    expires = int(time.time()) + 120  # 2 минуты
    _pending_challenges[challenger_uid] = {
        "target_uid": target_uid,
        "target_name": target_name,
        "expires_at": expires,
    }
    _incoming_challenge[target_uid] = challenger_uid

    key = (challenger_uid, target_uid)
    _challenge_daily_log.setdefault(key, []).append(int(time.time()))
    return True


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


def _calc_power(user_data: dict) -> int:
    """Суммарная «сила» игрока для матчмейкинга."""
    s = _calc_stats(user_data)
    return s["hp"] + s["phys_def"] * 3 + s["mag_def"] * 3 + s["stamina"] * 2


def join_queue(uid: int, user_data: dict) -> dict | None:
    now = int(time.time())
    stale = [k for k, (ts, _) in _match_queue.items() if now - ts > 120]
    for k in stale:
        _match_queue.pop(k, None)

    my_power = _calc_power(user_data)

    for opponent_uid, (ts, opp_data) in list(_match_queue.items()):
        if opponent_uid == uid:
            continue
        opp_power = _calc_power(opp_data)
        # Пропускаем если кто-то сильнее другого более чем на 25%
        stronger = max(my_power, opp_power)
        weaker   = min(my_power, opp_power)
        if weaker > 0 and (stronger / weaker) > 1.25:
            continue
        _match_queue.pop(opponent_uid, None)
        battle = _create_battle(uid, user_data, opponent_uid, opp_data)
        battle["p1_skills"] = get_equipped_skills(user_data) or SKILLS_ORDER_BASE
        battle["p2_skills"] = get_equipped_skills(opp_data) or SKILLS_ORDER_BASE
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

    sk_emoji = _skill_emoji(sk)
    if sk["type"] == "shield":
        sh = result["shield"]
        battle[f"{me}_shield"] = sh
        effect_msg = f"🛡️ Щит {sh} HP"
        log_entry = f"{battle[f'{me}_name']}: {sk_emoji} {sk['name']} → {effect_msg}"
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
            f"{battle[f'{me}_name']}: {sk_emoji} {sk['name']} "
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
        reward = battle.get("reward", 0)
        loser_title = battle.get("loser_title", "")
        if winner is None:
            result_line = "⚔️ <b>Ничья!</b>"
            reward_line = ""
        elif winner == uid:
            result_line = '<tg-emoji emoji-id="5413566144986503832">❤️</tg-emoji> <b>Ты победил!</b>'
            if reward:
                reward_line = f'\n\n<tg-emoji emoji-id="5397916757333654639">❤️</tg-emoji> <b>+{_fmt(reward)} <tg-emoji emoji-id="5199552030615558774">❤️</tg-emoji></b> <i>(титул врага: {loser_title})</i>'
            else:
                reward_line = ""
        else:
            result_line = "💀 <b>Ты проиграл!</b>"
            reward_line = ""
        return (
            f'⚔️ <b>БОЙ ЗАВЕРШЁН</b>\n'
            f'━━━━━━━━━━━━━━━━━━━━\n\n'
            f'{result_line}{reward_line}\n\n'
            f'<blockquote>'
            f'<tg-emoji emoji-id="5452085950022707790">❤️</tg-emoji> <b>{my_name}</b>\n'
            f'<tg-emoji emoji-id="5337080053119336309">❤️</tg-emoji> {my_bar}\n\n'
            f'<tg-emoji emoji-id="5206523956537865948">❤️</tg-emoji> <b>{foe_name}</b>\n'
            f'<tg-emoji emoji-id="5337080053119336309">❤️</tg-emoji> {foe_bar}'
            f'</blockquote>'
            f'{log_block}'
        )

    return (
        f'⚔️ <b>БОЙ</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>'
        f'<tg-emoji emoji-id="5452085950022707790">❤️</tg-emoji> <b>{my_name}</b>\n'
        f'<tg-emoji emoji-id="5337080053119336309">❤️</tg-emoji> {my_bar}'
        f'{shields}'
        f'{frozen_note}\n\n'
        f'<tg-emoji emoji-id="5206523956537865948">❤️</tg-emoji> <b>{foe_name}</b>\n'
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
        eid = sk.get("emoji_id")
        # Если есть кастомный эмодзи — убираем обычный из текста
        name_part = sk["name"] if eid else f"{sk['emoji']} {sk['name']}"
        btn_text = f"{name_part} ⏳{left}с" if left > 0 else name_part
        btn_kw = dict(text=btn_text, callback_data=f"duel_skill:{skill_key}")
        if eid:
            btn_kw["icon_custom_emoji_id"] = eid
        skill_buttons.append(InlineKeyboardButton(**btn_kw))

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


def duel_skills_shop_text(user_data: dict, page: int = 0, lang: str = "ru") -> str:
    items, total = _skill_page_items(page)
    total_pages = (total + SKILLS_SHOP_PAGE_SIZE - 1) // SKILLS_SHOP_PAGE_SIZE
    equipped_skills = get_equipped_skills(user_data)
    balance = user_data.get("balance", 0)
    eq_count = len(equipped_skills)
    quote = _random.choice(_DUEL_SHOP_QUOTES)
    return (
        f'<tg-emoji emoji-id="{EMOJI_SKILLS}">✨</tg-emoji> <b>{t(lang, "duel_shop_title")}</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n'
        f'<i>{t(lang, "duel_shop_page").format(page=page+1, total=total_pages, eq=eq_count, max=MAX_EQUIPPED_SKILLS)}</i>\n\n'
        f'<blockquote expandable><b><i>{quote}</i></b></blockquote>\n\n'
        f'<tg-emoji emoji-id="5278467510604160626">✨</tg-emoji> {t(lang, "duel_shop_balance").format(balance=_fmt(balance, lang))} <tg-emoji emoji-id="5199552030615558774">✨</tg-emoji>\n'
        f'<i>{t(lang, "duel_shop_footer")}</i>'
    )


def duel_skills_shop_keyboard(user_data: dict, page: int = 0, lang: str = "ru") -> InlineKeyboardMarkup:
    items, total = _skill_page_items(page)
    total_pages = (total + SKILLS_SHOP_PAGE_SIZE - 1) // SKILLS_SHOP_PAGE_SIZE
    owned_skills    = get_owned_skills(user_data)
    equipped_skills = get_equipped_skills(user_data)
    balance = user_data.get("balance", 0)
    builder = InlineKeyboardBuilder()

    for sk_key in items:
        sk       = SKILLS[sk_key]
        is_equip = sk_key in equipped_skills
        is_owned = sk_key in owned_skills
        eid      = sk.get("emoji_id")

        if is_equip:
            kw = dict(
                text=sk["name"],
                callback_data=f"duel_skill_card:{sk_key}:{page}",
                style="primary",
                icon_custom_emoji_id=eid or "5206607081334906820",
            )
        elif is_owned:
            kw = dict(
                text=sk["name"],
                callback_data=f"duel_skill_card:{sk_key}:{page}",
                style="success",
            )
            if eid:
                kw["icon_custom_emoji_id"] = eid
        elif balance >= sk["price"]:
            kw = dict(
                text=f"{sk['name']} | {_fmt(sk['price'])}",
                callback_data=f"duel_skill_card:{sk_key}:{page}",
            )
            if eid:
                kw["icon_custom_emoji_id"] = eid
        else:
            kw = dict(
                text=f"{sk['name']} | {_fmt(sk['price'])}",
                callback_data=f"duel_skill_card:{sk_key}:{page}",
            )
            if eid:
                kw["icon_custom_emoji_id"] = eid

        builder.row(InlineKeyboardButton(**kw))

    # Пагинация
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text=t(lang, "btn_back"),
            callback_data=f"duel_skills_shop_page:{page-1}",
            icon_custom_emoji_id="5255703720078879038",
        ))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(
            text=t(lang, "btn_forward"),
            callback_data=f"duel_skills_shop_page:{page+1}",
            icon_custom_emoji_id="5253767677670862169",
        ))
    if nav:
        builder.row(*nav)

    builder.row(InlineKeyboardButton(
        text=t(lang, "btn_back"), callback_data="duel_skills",
        icon_custom_emoji_id=EMOJI_BACK,
    ))
    return builder.as_markup()


# ════════════════════════════════════════════════════════════
#  ЭКРАН ПОИСКА
# ════════════════════════════════════════════════════════════

def duel_search_text(in_queue_flag: bool = False, lang: str = "ru") -> str:
    body = t(lang, "duel_search_wait") if in_queue_flag else t(lang, "duel_search_idle")
    return (
        f'<tg-emoji emoji-id="{EMOJI_SEARCH}">🔍</tg-emoji> <b>{t(lang, "duel_search_title")}</b>\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>{body}</blockquote>'
    )


def duel_search_keyboard(in_queue_flag: bool = False, lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if in_queue_flag:
        builder.row(InlineKeyboardButton(
            text=t(lang, "duel_btn_search_check"), callback_data="duel_search_check"
        ))
        builder.row(InlineKeyboardButton(
            text=t(lang, "duel_btn_search_cancel"), callback_data="duel_search_cancel"
        ))
    else:
        builder.row(InlineKeyboardButton(
            text=t(lang, "duel_btn_search_start"), callback_data="duel_search_start"
        ))
    builder.row(InlineKeyboardButton(
        text=t(lang, "btn_back"), callback_data="duel_main",
        icon_custom_emoji_id=EMOJI_BACK,
    ))
    return builder.as_markup()


# ════════════════════════════════════════════════════════════
#  ОРИГИНАЛЬНЫЕ ЭКРАНЫ
# ════════════════════════════════════════════════════════════

def duel_main_text(user_data: dict = None, lang: str = "ru") -> str:
    wins   = (user_data or {}).get("duel_wins", 0)
    losses = (user_data or {}).get("duel_losses", 0)
    title  = get_duel_title_display(wins, lang)
    return (
        f'<tg-emoji emoji-id="5424972470023104089">⚔️</tg-emoji> <b>{t(lang, "duel_main_title")}</b>\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        '<blockquote>'
        f'<tg-emoji emoji-id="5848400681416793625">⚔️</tg-emoji> {t(lang, "duel_main_title_line").format(title=title)}\n'
        f'<tg-emoji emoji-id="5413566144986503832">⚔️</tg-emoji> {t(lang, "duel_main_wl_line").format(wins=wins, losses=losses)}\n\n'
        f'<b><i>{t(lang, "duel_main_desc")}</i></b>\n\n'
        '</blockquote>'
    )

def duel_main_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=t(lang, "duel_btn_search"), callback_data="duel_search",
        icon_custom_emoji_id=EMOJI_SEARCH,
    ))
    builder.row(InlineKeyboardButton(
        text=t(lang, "duel_btn_challenge"), callback_data="duel_challenge_start",
        icon_custom_emoji_id=EMOJI_INVITE,
    ))
    builder.row(
        InlineKeyboardButton(text=t(lang, "duel_btn_equip"), callback_data="duel_equip",
                             icon_custom_emoji_id=EMOJI_EQUIP),
        InlineKeyboardButton(text=t(lang, "duel_btn_skills"), callback_data="duel_skills",
                             icon_custom_emoji_id=EMOJI_SKILLS),
    )
    builder.row(InlineKeyboardButton(
        text=t(lang, "duel_btn_charstats"), callback_data="duel_charstats",
        icon_custom_emoji_id=EMOJI_STATS_DUEL,
    ))
    builder.row(InlineKeyboardButton(
        text=t(lang, "btn_back"), callback_data="back_to_menu",
        icon_custom_emoji_id=EMOJI_BACK,
    ))
    return builder.as_markup()


def duel_equip_text(user_data: dict, lang: str = "ru") -> str:
    lines = []
    for slot in GEAR_SLOTS_ORDER:
        eid    = _SLOT_EMOJI_IDS.get(slot, "")
        char   = slot_emoji(slot)
        label  = slot_label(slot, lang)
        eq_lvl = equipped_level(slot, user_data)
        ow_lvl = owned_level(slot, user_data)
        slot_tg = f'<tg-emoji emoji-id="{eid}">{char}</tg-emoji>'

        if eq_lvl:
            item   = current_slot_item(slot, user_data)
            status = f'<b>{item["name"]}</b> ✅'
        elif ow_lvl:
            status = f'<b>{slot}-lvl{ow_lvl}</b> 📦 <i>{t(lang, "duel_equip_not_worn")}</i>'
        else:
            status = f'<i>{t(lang, "duel_equip_empty")}</i>'

        lines.append(f'{slot_tg} <b>{label}:</b> {status}')

    return (
        f'<tg-emoji emoji-id="5454168390685965478">🎒</tg-emoji> <b>{t(lang, "duel_equip_title")}</b>\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>{chr(10).join(lines)}</blockquote>\n\n'
        f'<i>{t(lang, "duel_equip_hint")}</i>'
    )

_SLOT_EMOJI_IDS = {
    "armor":  "5454168390685965478",
    "helmet": "5260546085251739109",
    "pants":  "4952249553173613188",
    "boots":  "5776192535890235363",
    "gloves": "5404591969735308062",
}

def duel_equip_keyboard(user_data: dict = None, lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    row_buf = []
    for slot in GEAR_SLOTS_ORDER:
        is_owned = user_data and owned_level(slot, user_data) > 0
        kw = dict(
            text=f"{slot_label(slot, lang)}",
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
        text=t(lang, "btn_back"), callback_data="duel_main",
        icon_custom_emoji_id=EMOJI_BACK,
    ))
    return builder.as_markup()


_SLOT_PAGE_SIZE = 5   # уровней на странице

def duel_equip_slot_text(slot: str, user_data: dict, page: int = 0, lang: str = "ru") -> str:
    owned_lvls = owned_levels_set(slot, user_data)
    eq_lvl     = equipped_level(slot, user_data)
    emoji      = slot_emoji(slot)
    label      = slot_label(slot, lang)

    total_pages = (25 + _SLOT_PAGE_SIZE - 1) // _SLOT_PAGE_SIZE
    page = max(0, min(page, total_pages - 1))
    lvl_start = page * _SLOT_PAGE_SIZE + 1
    lvl_end   = min(lvl_start + _SLOT_PAGE_SIZE - 1, 25)

    lines = []
    for lvl in range(lvl_start, lvl_end + 1):
        item = GEAR_CATALOG[f"{slot}-lvl{lvl}"]
        if lvl == eq_lvl:
            marker = "✅"
            state  = f'<i>{t(lang, "duel_state_worn")}</i>'
        elif lvl in owned_lvls:
            marker = "📦"
            state  = f'<i>{t(lang, "duel_state_in_inventory")}</i>'
        else:
            marker = "🔒"
            state  = f'<i>{_fmt(item["price"], lang)} {t(lang, "duel_coins_suffix")}</i>'
        lines.append(f"{marker} <b>[{item['name']}]</b> — {item['ru_name']} · {state}")

    block = "\n".join(lines)
    header = t(lang, "duel_equip_slot_header").format(label=label.upper())
    return (
        f'{emoji} <b>{header}</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━\n'
        f'<i>{t(lang, "duel_equip_slot_page").format(page=page + 1, total=total_pages, start=lvl_start, end=lvl_end)}</i>\n\n'
        f'<blockquote>{block}</blockquote>\n\n'
        f'<i>{t(lang, "duel_equip_slot_hint")}</i>'
    )

def duel_equip_slot_keyboard(slot: str, user_data: dict, page: int = 0, lang: str = "ru") -> InlineKeyboardMarkup:
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
            btn_text = f"{item['name']} | {_fmt(item['price'], lang)}"
            builder.row(InlineKeyboardButton(
                text=btn_text,
                callback_data=f"duel_item_card:{item_key}:{page}",
            ))

    # Навигация по страницам
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text=t(lang, "btn_back"),
            callback_data=f"duel_slot_page:{slot}:{page - 1}",
            icon_custom_emoji_id="5255703720078879038",
        ))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(
            text=t(lang, "btn_forward"),
            callback_data=f"duel_slot_page:{slot}:{page + 1}",
            icon_custom_emoji_id="5253767677670862169",
        ))
    if nav:
        builder.row(*nav)

    builder.row(InlineKeyboardButton(
        text=t(lang, "btn_back"), callback_data="duel_equip",
        icon_custom_emoji_id=EMOJI_BACK,
    ))
    return builder.as_markup()


def duel_item_card_text(item_key: str, user_data: dict, lang: str = "ru") -> str:
    item   = GEAR_CATALOG[item_key]
    slot   = item["slot"]
    owned_lvls = owned_levels_set(slot, user_data)
    eq_lvl = equipped_level(slot, user_data)
    lvl    = item["level"]
    balance = user_data.get("balance", 0)

    if lvl == eq_lvl:
        status_line = t(lang, "duel_item_status_worn")
    elif lvl in owned_lvls:
        status_line = t(lang, "duel_item_status_inventory")
    else:
        status_line = t(lang, "duel_item_price_line").format(price=_fmt(item["price"], lang))
        if balance < item["price"]:
            deficit = item["price"] - balance
            status_line += "\n" + t(lang, "duel_item_deficit").format(deficit=_fmt(deficit, lang))

    bonus_lines = []
    for stat, val in item["bonus"].items():
        if stat == "dmg":
            continue
        emoji_s, _ru, unit = STAT_META.get(stat, ("▫️", stat, ""))
        stat_name = t(lang, f"duel_stats_{stat}")
        bonus_lines.append(f'  {emoji_s} <b>+{val}</b> {stat_name} <i>({unit})</i>')
    bonus_block = "\n".join(bonus_lines)

    if lvl <= 3:
        rarity = t(lang, "duel_rarity_common")
    elif lvl <= 6:
        rarity = t(lang, "duel_rarity_uncommon")
    elif lvl <= 10:
        rarity = t(lang, "duel_rarity_rare")
    elif lvl <= 14:
        rarity = t(lang, "duel_rarity_epic")
    elif lvl <= 18:
        rarity = t(lang, "duel_rarity_legendary")
    elif lvl <= 21:
        rarity = t(lang, "duel_rarity_mythic")
    elif lvl <= 23:
        rarity = t(lang, "duel_rarity_ancient")
    elif lvl <= 24:
        rarity = t(lang, "duel_rarity_relic")
    else:
        rarity = t(lang, "duel_rarity_absolute")

    return (
        f'<tg-emoji emoji-id="{item["emoji_id"]}">{item["emoji_char"]}</tg-emoji> <b>{item["name"]}</b>\n'
        f'<i>{item["ru_name"]}</i>  {rarity}\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>{item["description"]}</blockquote>\n\n'
        f'<b>{t(lang, "duel_item_bonus_title")}</b>\n{bonus_block}\n\n'
        f'<i>{t(lang, "duel_item_dmg_note")}</i>\n\n'
        f'{status_line}'
    )

def duel_item_card_keyboard(item_key: str, user_data: dict, page: int = 0, lang: str = "ru") -> InlineKeyboardMarkup:
    item   = GEAR_CATALOG[item_key]
    slot   = item["slot"]
    owned_lvls = owned_levels_set(slot, user_data)
    eq_lvl = equipped_level(slot, user_data)
    lvl    = item["level"]
    balance = user_data.get("balance", 0)
    builder = InlineKeyboardBuilder()

    if lvl == eq_lvl:
        builder.row(InlineKeyboardButton(
            text=t(lang, "duel_btn_unequip"),
            callback_data=f"duel_gear_unequip:{item_key}:{page}",
        ))
    elif lvl in owned_lvls:
        builder.row(InlineKeyboardButton(
            text=t(lang, "duel_btn_equip_item"),
            callback_data=f"duel_gear_equip:{item_key}:{page}",
        ))
    else:
        if balance >= item["price"]:
            builder.row(InlineKeyboardButton(
                text=t(lang, "duel_btn_buy_item").format(price=_fmt(item["price"], lang)),
                callback_data=f"duel_gear_buy:{item_key}:{page}",
            ))
        else:
            builder.row(InlineKeyboardButton(
                text=t(lang, "duel_btn_not_enough_coins"),
                callback_data="duel_gear_nofunds",
            ))

    builder.row(InlineKeyboardButton(
        text=t(lang, "btn_back"), callback_data=f"duel_slot_page:{slot}:{page}",
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


def duel_charstats_text(user_data: dict, uid: int = None, lang: str = "ru") -> str:
    s          = _calc_stats(user_data)
    equipped   = user_data.get("duel_equipped", {})
    gear_count = len(equipped)
    gear_line  = (t(lang, "duel_stats_gear_worn").format(count=gear_count) if gear_count
                  else t(lang, "duel_stats_gear_none"))
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
            hp_regen_note = "\n" + t(lang, "duel_stats_hp_regen_note").format(
                amount=HP_REGEN_AMOUNT, interval=HP_REGEN_INTERVAL, secs=secs
            ) + "\n"
    else:
        hp_display    = str(s["hp"])
        hp_regen_note = ""

    return (
        f'<tg-emoji emoji-id="{EMOJI_STATS_DUEL}">📊</tg-emoji> <b>{t(lang, "duel_stats_title")}</b>\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        '<blockquote>'
        f'<tg-emoji emoji-id="{EMOJI_HP}">❤️</tg-emoji> <b>{t(lang, "duel_stats_hp")}</b> — <b>{hp_display}</b> HP\n\n'
        f'<tg-emoji emoji-id="{EMOJI_REGEN}">💚</tg-emoji> <b>{t(lang, "duel_stats_regen")}</b> — <b>{s["regen"]}</b> {t(lang, "duel_stats_hp_per_turn")}\n\n'
        f'<tg-emoji emoji-id="{EMOJI_PHYS_DEF}">🛡️</tg-emoji> <b>{t(lang, "duel_stats_phys_def")}</b> — <b>{s["phys_def"]}</b> DEF\n\n'
        f'<tg-emoji emoji-id="{EMOJI_MAG_DEF}">🔮</tg-emoji> <b>{t(lang, "duel_stats_mag_def")}</b> — <b>{s["mag_def"]}</b> MDEF\n\n'
        f'<tg-emoji emoji-id="{EMOJI_STAMINA}">⚙️</tg-emoji> <b>{t(lang, "duel_stats_stamina")}</b> — <b>{s["stamina"]}</b> STM'
        '</blockquote>\n'
        f'{hp_regen_note}\n'
        f'{t(lang, "duel_stats_gear_line").format(gear=gear_line)}\n'
        f'{t(lang, "duel_stats_skills_line").format(count=sk_count)}\n\n'
        f'<i>{t(lang, "duel_stats_footer")}</i>'
    )

def duel_charstats_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=t(lang, "duel_btn_equip").strip(), callback_data="duel_equip",
        icon_custom_emoji_id=EMOJI_EQUIP,
    ))
    builder.row(InlineKeyboardButton(
        text=t(lang, "btn_back"), callback_data="duel_main",
        icon_custom_emoji_id=EMOJI_BACK,
    ))
    return builder.as_markup()


# ── Экран навыков (обзор + ссылка в магазин) ─────────────────

def duel_skills_text(user_data: dict = None, lang: str = "ru") -> str:
    quote = _random.choice(_DUEL_SHOP_QUOTES)

    # Формируем строки слотов экипировки (всегда 5 слотов)
    equipped = get_equipped_skills(user_data) if user_data else []
    empty_line = f'▫️ <i>{t(lang, "duel_skills_empty_slot")}</i>\n'
    slot_lines = ""
    for i in range(MAX_EQUIPPED_SKILLS):
        if i < len(equipped):
            k = equipped[i]
            if k in SKILLS:
                skill = SKILLS[k]
                slot_lines += f"{_skill_emoji(skill)} <b>{skill['name']}</b>\n"
            else:
                slot_lines += empty_line
        else:
            slot_lines += empty_line

    return (
        f'<tg-emoji emoji-id="{EMOJI_SKILLS}">✨</tg-emoji> <b>{t(lang, "duel_skills_title")}</b>\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote expandable><b><i>{quote}</i></b></blockquote>\n\n'
        f'<blockquote><b>{t(lang, "duel_skills_equipped_label")}</b>\n'
        f'{slot_lines}</blockquote>\n'
        f'<i><tg-emoji emoji-id="5334544901428229844">✨</tg-emoji> {t(lang, "duel_skills_hint").format(max=MAX_EQUIPPED_SKILLS)}</i>'
    )

def duel_skills_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=t(lang, "duel_btn_skills_shop"), callback_data="duel_skills_shop",
    ))
    builder.row(InlineKeyboardButton(
        text=t(lang, "btn_back"), callback_data="duel_main",
        icon_custom_emoji_id=EMOJI_BACK,
    ))
    return builder.as_markup()


def duel_challenge_screen_text(lang: str = "ru") -> str:
    return (
        f'<tg-emoji emoji-id="{EMOJI_INVITE}">⚔️</tg-emoji> <b>{t(lang, "duel_challenge_title")}</b>\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>{t(lang, "duel_challenge_body")}</blockquote>'
    )


def duel_challenge_screen_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=t(lang, "btn_back"), callback_data="duel_main",
        icon_custom_emoji_id=EMOJI_BACK,
    ))
    return builder.as_markup()


def duel_challenge_sent_text(target_name: str, lang: str = "ru") -> str:
    return (
        f'{t(lang, "duel_challenge_sent_title")}\n\n'
        f'<blockquote>{t(lang, "duel_challenge_sent_body").format(name=target_name)}</blockquote>'
    )


def duel_challenge_sent_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=t(lang, "duel_btn_challenge_cancel"), callback_data="duel_challenge_cancel",
    ))
    builder.row(InlineKeyboardButton(
        text=t(lang, "btn_back"), callback_data="duel_main",
        icon_custom_emoji_id=EMOJI_BACK,
    ))
    return builder.as_markup()


def duel_hp_status_text(uid: int, user_data: dict, lang: str = "ru") -> str:
    """Текст статуса HP для отображения в поиске/вызове."""
    hp     = get_player_hp(uid, user_data)
    hp_max = _calc_stats(user_data)["hp"]
    if hp >= 100:
        return ""
    secs = player_hp_regen_seconds(uid, user_data)
    body = t(lang, "duel_hp_status").format(
        hp=hp, hp_max=hp_max, amount=HP_REGEN_AMOUNT, interval=HP_REGEN_INTERVAL, secs=secs
    )
    return f'\n\n<blockquote>{body}</blockquote>'


def duel_soon_text(section: str, lang: str = "ru") -> str:
    labels = {
        "search": t(lang, "duel_soon_search"),
        "invite": t(lang, "duel_soon_invite"),
        "skills": t(lang, "duel_soon_skills"),
    }
    name = labels.get(section, section)
    return (
        f'<tg-emoji emoji-id="{EMOJI_DUEL_MAIN}">⚔️</tg-emoji> <b>{name}</b>\n\n'
        f'<blockquote>{t(lang, "duel_soon_body")}</blockquote>'
    )

def duel_back_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=t(lang, "btn_back"), callback_data="duel_main",
        icon_custom_emoji_id=EMOJI_BACK,
    ))
    return builder.as_markup()


# ════════════════════════════════════════════════════════════
#  БЫСТРЫЕ КОМАНДЫ ДУЭЛИ
#  Все алиасы работают со слешем и без, на RU и EN.
#  Логика вызова команд — здесь, в main.py только регистрация.
# ════════════════════════════════════════════════════════════

# Алиасы → целевой раздел
DUEL_CMD_MAIN   = frozenset(["дуэли", "дуель", "duel", "duels"])
DUEL_CMD_EQUIP  = frozenset(["дуэли-duel-екип", "снаряжение", "снар", "equip", "gear", "duel-equip"])
DUEL_CMD_SKILLS = frozenset(["нвык", "навыки", "skills", "skill", "умения"])
DUEL_CMD_STATS  = frozenset(["стата", "хк", "хар", "stats", "charstats", "характеристики"])
DUEL_CMD_INVITE = frozenset(["вз", "вызов", "challenge"])

def _normalize_cmd(text: str) -> str:
    """Убирает слеш, пробелы, переводит в нижний регистр."""
    return text.strip().lstrip("/").lower().split()[0]

def is_duel_main_cmd(text: str) -> bool:
    return _normalize_cmd(text) in DUEL_CMD_MAIN

def is_duel_equip_cmd(text: str) -> bool:
    return _normalize_cmd(text) in DUEL_CMD_EQUIP

def is_duel_skills_cmd(text: str) -> bool:
    return _normalize_cmd(text) in DUEL_CMD_SKILLS

def is_duel_stats_cmd(text: str) -> bool:
    return _normalize_cmd(text) in DUEL_CMD_STATS

def is_duel_invite_cmd(text: str) -> bool:
    return _normalize_cmd(text) in DUEL_CMD_INVITE

def is_any_duel_cmd(text: str) -> bool:
    return (is_duel_main_cmd(text) or is_duel_equip_cmd(text) or
            is_duel_skills_cmd(text) or is_duel_stats_cmd(text) or
            is_duel_invite_cmd(text))


# ── Тексты ошибок/помощи ────────────────────────────────────

def cmd_no_hp_text(hp_now: int, secs: int, lang: str = "ru") -> str:
    return t(lang, "duel_cmd_no_hp").format(hp=hp_now, secs=secs)

def cmd_already_in_battle_text(lang: str = "ru") -> str:
    return t(lang, "duel_cmd_already_in_battle")

def cmd_invite_usage_text(lang: str = "ru") -> str:
    return (
        f'<tg-emoji emoji-id="{EMOJI_INVITE}">⚔️</tg-emoji> <b>{t(lang, "duel_challenge_title")}</b>\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>{t(lang, "duel_cmd_invite_usage")}</blockquote>'
    )

def cmd_invite_self_text(lang: str = "ru") -> str:
    return t(lang, "duel_cmd_invite_self")

def cmd_invite_not_found_text(lang: str = "ru") -> str:
    return t(lang, "duel_cmd_invite_not_found")

def cmd_invite_in_battle_text(lang: str = "ru") -> str:
    return t(lang, "duel_cmd_invite_in_battle")

def cmd_invite_blocked_text(name: str, lang: str = "ru") -> str:
    return t(lang, "duel_cmd_invite_blocked").format(name=name)

def cmd_invite_limit_text(target_name: str, secs: int, limit: int = CHALLENGE_DAILY_LIMIT, lang: str = "ru") -> str:
    hours = secs // 3600
    mins  = (secs % 3600) // 60
    h_lbl = t(lang, "duel_hours_short")
    m_lbl = t(lang, "duel_mins_short")
    if hours > 0:
        wait = f'{hours} {h_lbl} {mins} {m_lbl}'
    else:
        wait = f'{mins} {m_lbl}'
    return t(lang, "duel_cmd_invite_limit").format(name=target_name, limit=limit, wait=wait)
