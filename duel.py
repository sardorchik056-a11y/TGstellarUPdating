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
GEAR_CATALOG = {

    # ── ШЛЕМ ─────────────────────────────────────────────────
    "helmet-lvl1": {
        "slot": "helmet", "level": 1, "key": "helmet-lvl1",
        "name": "Helmet Lvl 1", "ru_name": "Железный Шлем",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5445284980978621387",
        "price": 5_000,
        "description": (
            "Грубо выкованный железный шлем без украшений. "
            "Прост в изготовлении, но надёжно прикрывает голову от первого удара. "
            "Идеальный выбор для тех, кто только встаёт на путь дуэлянта."
        ),
        "bonus": {"hp": 10, "phys_def": 3},
    },
    "helmet-lvl2": {
        "slot": "helmet", "level": 2, "key": "helmet-lvl2",
        "name": "Helmet Lvl 2", "ru_name": "Боевой Шлем",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5445284980978621387",
        "price": 15_000,
        "description": (
            "Усиленный шлем с рунической вставкой на лбу. "
            "Древние символы рассеивают слабые магические атаки, "
            "а закалённая сталь держит удары тяжёлого оружия. "
            "Стандартное снаряжение опытного бойца."
        ),
        "bonus": {"hp": 20, "phys_def": 6, "mag_def": 5},
    },
    "helmet-lvl3": {
        "slot": "helmet", "level": 3, "key": "helmet-lvl3",
        "name": "Helmet Lvl 3", "ru_name": "Шлем Гвардейца",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5445284980978621387",
        "price": 35_000,
        "description": (
            "Закалённый шлем королевской гвардии с забралом из мифрила. "
            "Повышает концентрацию в бою и значительно снижает усталость. "
            "Носившие его редко пропускали смертельные удары."
        ),
        "bonus": {"hp": 35, "phys_def": 10, "mag_def": 8, "stamina": 5},
    },
    "helmet-lvl4": {
        "slot": "helmet", "level": 4, "key": "helmet-lvl4",
        "name": "Helmet Lvl 4", "ru_name": "Шлем Стального Стража",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5445284980978621387",
        "price": 70_000,
        "description": (
            "Реликвийный шлем Стального Стража с рунической гравировкой по всей поверхности. "
            "Каждый символ — заклинание защиты, впитанное веками. "
            "Входящий урон частично поглощается магическим барьером."
        ),
        "bonus": {"hp": 50, "phys_def": 15, "mag_def": 12, "stamina": 10},
    },
    "helmet-lvl5": {
        "slot": "helmet", "level": 5, "key": "helmet-lvl5",
        "name": "Helmet Lvl 5", "ru_name": "Шлем Легенды",
        "slot_label": "Шлем", "emoji_char": "⛑️", "emoji_id": "5445284980978621387",
        "price": 150_000,
        "description": (
            "Артефакт эпохи Первых Воинов. Говорят, тот кто надевает его — "
            "слышит голоса павших героев, дающих силу и непоколебимость духа. "
            "Ни одна стрела, ни одно заклинание не может поколебать носителя этого шлема."
        ),
        "bonus": {"hp": 75, "phys_def": 22, "mag_def": 18, "stamina": 18},
    },

    # ── БРОНЯ ─────────────────────────────────────────────────
    "armor-lvl1": {
        "slot": "armor", "level": 1, "key": "armor-lvl1",
        "name": "Armor Lvl 1", "ru_name": "Кожаный Доспех",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5447644880824181073",
        "price": 6_000,
        "description": (
            "Доспех из дублёной кожи горного быка. Лёгкий и не сковывает движений — "
            "идеален для быстрых атак. Не выдержит удар тяжёлого меча, "
            "но защитит от скользящих ударов и стрел."
        ),
        "bonus": {"hp": 15, "phys_def": 5},
    },
    "armor-lvl2": {
        "slot": "armor", "level": 2, "key": "armor-lvl2",
        "name": "Armor Lvl 2", "ru_name": "Кольчужный Доспех",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5447644880824181073",
        "price": 18_000,
        "description": (
            "Тысячи закалённых колец, переплетённых вручную. "
            "Кольчуга хорошо поглощает рубящие и колющие удары, "
            "давая бойцу запас прочности в затяжных поединках. "
            "Классика среди опытных дуэлянтов."
        ),
        "bonus": {"hp": 30, "phys_def": 12, "stamina": 5},
    },
    "armor-lvl3": {
        "slot": "armor", "level": 3, "key": "armor-lvl3",
        "name": "Armor Lvl 3", "ru_name": "Пластинчатый Доспех",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5447644880824181073",
        "price": 40_000,
        "description": (
            "Боевые латы из стальных пластин с усиленными сочленениями. "
            "Распределяют силу удара по всей поверхности, сводя урон к минимуму. "
            "Тяжелее кольчуги, но даёт существенно лучшую защиту торса."
        ),
        "bonus": {"hp": 50, "phys_def": 20, "stamina": 8},
    },
    "armor-lvl4": {
        "slot": "armor", "level": 4, "key": "armor-lvl4",
        "name": "Armor Lvl 4", "ru_name": "Латы Воина Бездны",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5447644880824181073",
        "price": 80_000,
        "description": (
            "Прочнейшие латы, выкованные в жерле вулкана тёмными кузнецами Бездны. "
            "Металл пропитан магмой и заклят на стойкость. "
            "Поглощают часть урона в каждом бою, превращая его в регенерацию."
        ),
        "bonus": {"hp": 75, "phys_def": 30, "mag_def": 8, "stamina": 12},
    },
    "armor-lvl5": {
        "slot": "armor", "level": 5, "key": "armor-lvl5",
        "name": "Armor Lvl 5", "ru_name": "Латы Абсолюта",
        "slot_label": "Броня", "emoji_char": "🛡️", "emoji_id": "5447644880824181073",
        "price": 180_000,
        "description": (
            "Легендарный доспех, не знавший поражений за всю историю TGStellar. "
            "Выкован из металла упавшей звезды и закалён в крови древнего дракона. "
            "Максимальная физическая защита — ни одна атака не пройдёт сквозь него незамеченной."
        ),
        "bonus": {"hp": 110, "phys_def": 45, "mag_def": 15, "stamina": 20},
    },

    # ── ПЕРЧАТКИ ──────────────────────────────────────────────
    "gloves-lvl1": {
        "slot": "gloves", "level": 1, "key": "gloves-lvl1",
        "name": "Gloves Lvl 1", "ru_name": "Боевые Рукавицы",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5445284980978621387",
        "price": 4_000,
        "description": (
            "Простые кожаные рукавицы с наклёпками из железа на костяшках. "
            "Защищают кулаки и немного усиливают удар. "
            "Первый шаг к мощи твоих рук в дуэльном бою."
        ),
        "bonus": {"dmg": 4, "stamina": 2},
    },
    "gloves-lvl2": {
        "slot": "gloves", "level": 2, "key": "gloves-lvl2",
        "name": "Gloves Lvl 2", "ru_name": "Латные Рукавицы",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5445284980978621387",
        "price": 12_000,
        "description": (
            "Рукавицы с металлическими пластинами вдоль пальцев. "
            "Усиливают хват оружия и дают бонус к критическому удару. "
            "Любимое снаряжение арбитров дуэльных арен."
        ),
        "bonus": {"dmg": 8, "stamina": 5},
    },
    "gloves-lvl3": {
        "slot": "gloves", "level": 3, "key": "gloves-lvl3",
        "name": "Gloves Lvl 3", "ru_name": "Наручи Теневого Клинка",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5445284980978621387",
        "price": 28_000,
        "description": (
            "Боевые наручи с выдвижными шипами из чёрного железа. "
            "Ускоряют темп атаки и позволяют наносить удары, "
            "пробивающие стандартную броню. Оружие теневых воинов."
        ),
        "bonus": {"dmg": 14, "stamina": 8, "phys_def": 3},
    },
    "gloves-lvl4": {
        "slot": "gloves", "level": 4, "key": "gloves-lvl4",
        "name": "Gloves Lvl 4", "ru_name": "Наручи Убийцы",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5445284980978621387",
        "price": 55_000,
        "description": (
            "Зачарованные наручи элитных убийц гильдии Алой Тени. "
            "Вибрирующие руны в металле усиливают каждый удар магической энергией. "
            "Максимальный урон в сочетании с непревзойдённой скоростью атаки."
        ),
        "bonus": {"dmg": 20, "stamina": 12, "phys_def": 5},
    },
    "gloves-lvl5": {
        "slot": "gloves", "level": 5, "key": "gloves-lvl5",
        "name": "Gloves Lvl 5", "ru_name": "Длани Хаоса",
        "slot_label": "Перчатки", "emoji_char": "🥊", "emoji_id": "5445284980978621387",
        "price": 120_000,
        "description": (
            "Артефактные перчатки, пронизанные энергией первозданного хаоса. "
            "Каждый удар сотрясает реальность — противник ощущает не просто боль, "
            "но и разрушение своей воли к сопротивлению. "
            "Носить могут лишь те, кто укротил хаос внутри себя."
        ),
        "bonus": {"dmg": 30, "stamina": 18, "phys_def": 8, "regen": 3},
    },

    # ── ШТАНЫ ─────────────────────────────────────────────────
    "pants-lvl1": {
        "slot": "pants", "level": 1, "key": "pants-lvl1",
        "name": "Pants Lvl 1", "ru_name": "Боевые Штаны",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "5445284980978621387",
        "price": 4_500,
        "description": (
            "Прочные штаны из грубой холщовой ткани с кожаными вставками на бёдрах. "
            "Дают свободу движений и базовую защиту ног. "
            "Начало пути к полному боевому снаряжению."
        ),
        "bonus": {"hp": 8, "stamina": 5},
    },
    "pants-lvl2": {
        "slot": "pants", "level": 2, "key": "pants-lvl2",
        "name": "Pants Lvl 2", "ru_name": "Кольчужные Поножи",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "5445284980978621387",
        "price": 14_000,
        "description": (
            "Усиленные поножи с кольчужными вставками на бёдрах и голенях. "
            "Защищают от рубящих ударов в нижнюю часть тела. "
            "Особенно эффективны против быстрых ударов по ногам."
        ),
        "bonus": {"hp": 18, "stamina": 10, "phys_def": 4},
    },
    "pants-lvl3": {
        "slot": "pants", "level": 3, "key": "pants-lvl3",
        "name": "Pants Lvl 3", "ru_name": "Поножи Железного Рыцаря",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "5445284980978621387",
        "price": 30_000,
        "description": (
            "Тяжёлые боевые штаны с усиленными бёдрами и наколенниками из закалённой стали. "
            "Дают прибавку к выносливости и уклонению в долгих поединках. "
            "Стандарт тяжёлой пехоты Железного ордена."
        ),
        "bonus": {"hp": 30, "stamina": 16, "phys_def": 7},
    },
    "pants-lvl4": {
        "slot": "pants", "level": 4, "key": "pants-lvl4",
        "name": "Pants Lvl 4", "ru_name": "Зачарованные Поножи",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "5445284980978621387",
        "price": 60_000,
        "description": (
            "Латные поножи с вплавленными кристаллами выносливости. "
            "Магия кристаллов медленно восстанавливает силы бойца в ходе боя. "
            "Уклонение и стойкость выходят на профессиональный уровень."
        ),
        "bonus": {"hp": 45, "stamina": 22, "phys_def": 11, "regen": 3},
    },
    "pants-lvl5": {
        "slot": "pants", "level": 5, "key": "pants-lvl5",
        "name": "Pants Lvl 5", "ru_name": "Поножи Вечности",
        "slot_label": "Штаны", "emoji_char": "👖", "emoji_id": "5445284980978621387",
        "price": 130_000,
        "description": (
            "Реликвийные поножи, скованные в эпоху Великих Войн. "
            "Легенда гласит: ни один носитель этих поножей не упал в бою. "
            "Дают невероятную стойкость и восстановление — "
            "тело бойца будто отказывается сдаваться."
        ),
        "bonus": {"hp": 65, "stamina": 32, "phys_def": 16, "regen": 6},
    },

    # ── САПОГИ ────────────────────────────────────────────────
    "boots-lvl1": {
        "slot": "boots", "level": 1, "key": "boots-lvl1",
        "name": "Boots Lvl 1", "ru_name": "Походные Сапоги",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5445284980978621387",
        "price": 3_500,
        "description": (
            "Добротные кожаные сапоги, проверенные долгими походами. "
            "Мягкая подошва гасит шум шагов и даёт небольшую прибавку к скорости. "
            "Первый шаг к стремительности в бою."
        ),
        "bonus": {"dmg": 2, "regen": 3},
    },
    "boots-lvl2": {
        "slot": "boots", "level": 2, "key": "boots-lvl2",
        "name": "Boots Lvl 2", "ru_name": "Сапоги Следопыта",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5445284980978621387",
        "price": 11_000,
        "description": (
            "Лёгкие сапоги из кожи ночного пантеры. "
            "Позволяют двигаться практически бесшумно и увеличивают "
            "шанс нанести первый удар прежде чем противник успеет среагировать."
        ),
        "bonus": {"dmg": 5, "regen": 5, "stamina": 3},
    },
    "boots-lvl3": {
        "slot": "boots", "level": 3, "key": "boots-lvl3",
        "name": "Boots Lvl 3", "ru_name": "Сапоги Ветра Пустоши",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5445284980978621387",
        "price": 25_000,
        "description": (
            "Сапоги из кожи горного дракона, пропитанные эликсиром скорости ветра. "
            "Ноги бойца становятся лёгкими как перо — "
            "каждый шаг приносит восстановление сил и увеличивает скорость атаки."
        ),
        "bonus": {"dmg": 8, "regen": 8, "stamina": 6},
    },
    "boots-lvl4": {
        "slot": "boots", "level": 4, "key": "boots-lvl4",
        "name": "Boots Lvl 4", "ru_name": "Сапоги Призрака",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5445284980978621387",
        "price": 50_000,
        "description": (
            "Зачарованные сапоги элитных разведчиков, способные делать владельца "
            "почти невидимым в движении. Молниеносный первый удар "
            "и незаметное перемещение по арене дают огромное тактическое преимущество."
        ),
        "bonus": {"dmg": 12, "regen": 12, "stamina": 10, "phys_def": 4},
    },
    "boots-lvl5": {
        "slot": "boots", "level": 5, "key": "boots-lvl5",
        "name": "Boots Lvl 5", "ru_name": "Сапоги Грома",
        "slot_label": "Сапоги", "emoji_char": "👢", "emoji_id": "5445284980978621387",
        "price": 110_000,
        "description": (
            "Реликвийные сапоги Громового Бога. При каждом шаге слышен тихий раскат грома — "
            "знак того, что стихия сама несёт бойца вперёд. "
            "Максимальная скорость, восстановление и стойкость. "
            "Надевший их — неудержим."
        ),
        "bonus": {"dmg": 18, "regen": 18, "stamina": 16, "phys_def": 7},
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
#  БОЕВЫЕ НАВЫКИ
# ════════════════════════════════════════════════════════════

# Логика урона навыков:
#   Физ. навыки (взрыв, блок-маг) → снижаются phys_def противника
#   Маг. навыки (шар-маг, заморозка) → снижаются mag_def противника
#   Щит → защитный навык, не урон
#
# Формула физ. урона: base_dmg + atk_bonus - max(0, enemy_phys_def * 0.4)
# Формула маг. урона: base_mag + atk_bonus * 0.6 - max(0, enemy_mag_def * 0.5)

SKILLS = {
    "mag_ball": {
        "key": "mag_ball",
        "name": "Шар-маг",
        "emoji": "🔵",
        "type": "magic",          # урон от mag_def
        "cooldown": 15,           # секунды
        "base_dmg": (18, 28),     # диапазон базового маг.урона
        "description": "Концентрированный шар магической энергии. Пробивает магическую защиту.",
    },
    "mag_block": {
        "key": "mag_block",
        "name": "Блок-маг",
        "emoji": "🟣",
        "type": "magic",
        "cooldown": 20,
        "base_dmg": (25, 40),
        "description": "Мощный магический таран. Высокий урон, длинный кулдаун.",
    },
    "shield": {
        "key": "shield",
        "name": "Щит",
        "emoji": "🛡️",
        "type": "shield",          # защита
        "cooldown": 25,
        "shield_amount": (20, 35), # поглощает X урона
        "description": "Магический щит. Поглощает следующий входящий удар.",
    },
    "explosion": {
        "key": "explosion",
        "name": "Взрыв",
        "emoji": "💥",
        "type": "physical",        # урон от phys_def
        "cooldown": 18,
        "base_dmg": (22, 35),
        "description": "Взрыв физической силы. Снижается физической защитой.",
    },
    "freeze": {
        "key": "freeze",
        "name": "Заморозка",
        "emoji": "❄️",
        "type": "magic",
        "cooldown": 30,
        "base_dmg": (15, 22),
        "freeze_turns": 1,         # пропуск хода у врага
        "description": "Заморозка противника. Наносит маг. урон и лишает хода.",
    },
}

SKILLS_ORDER = ["mag_ball", "mag_block", "shield", "explosion", "freeze"]


def _calc_skill_damage(skill_key: str, attacker_stats: dict, defender_stats: dict) -> dict:
    """Вычислить урон от навыка с учётом характеристик обеих сторон."""
    sk = SKILLS[skill_key]
    result = {"type": sk["type"], "skill": skill_key}

    atk = attacker_stats.get("dmg", 15)

    if sk["type"] == "magic":
        base_min, base_max = sk["base_dmg"]
        base = random.randint(base_min, base_max)
        mag_bonus = atk * 0.6
        enemy_resist = max(0, defender_stats.get("mag_def", 10) * 0.5)
        dmg = max(1, int(base + mag_bonus - enemy_resist))
        result["dmg"] = dmg

    elif sk["type"] == "physical":
        base_min, base_max = sk["base_dmg"]
        base = random.randint(base_min, base_max)
        phys_bonus = atk
        enemy_resist = max(0, defender_stats.get("phys_def", 10) * 0.4)
        dmg = max(1, int(base + phys_bonus - enemy_resist))
        result["dmg"] = dmg

    elif sk["type"] == "shield":
        sh_min, sh_max = sk["shield_amount"]
        result["shield"] = random.randint(sh_min, sh_max)
        result["dmg"] = 0

    # Особый эффект заморозки
    if skill_key == "freeze":
        result["freeze"] = True

    return result


# ════════════════════════════════════════════════════════════
#  ПОИСК ПРОТИВНИКА / МАТЧМЕЙКИНГ
#  Хранение: user_data["duel_queue"] = timestamp попадания в очередь
#            активный бой: user_data["duel_battle"] = dict (состояние боя)
# ════════════════════════════════════════════════════════════

# in-memory очередь: uid -> (timestamp, user_data)
_match_queue: dict[int, tuple] = {}


def join_queue(uid: int, user_data: dict) -> dict | None:
    """Добавить игрока в очередь поиска.
    Если в очереди уже есть другой — создать бой и вернуть battle_state.
    Иначе вернуть None (ждём).
    """
    now = int(time.time())

    # Убираем устаревших (>120 сек) из очереди
    stale = [k for k, (ts, _) in _match_queue.items() if now - ts > 120]
    for k in stale:
        _match_queue.pop(k, None)

    # Ищем соперника
    for opponent_uid, (ts, opp_data) in list(_match_queue.items()):
        if opponent_uid == uid:
            continue
        # Нашли! Убираем соперника из очереди
        _match_queue.pop(opponent_uid, None)
        battle = _create_battle(uid, user_data, opponent_uid, opp_data)
        return battle

    # Никого нет — встаём в очередь
    _match_queue[uid] = (now, user_data)
    return None


def leave_queue(uid: int):
    """Покинуть очередь поиска."""
    _match_queue.pop(uid, None)


def in_queue(uid: int) -> bool:
    return uid in _match_queue


# ════════════════════════════════════════════════════════════
#  БОЙ
# ════════════════════════════════════════════════════════════

BASE_STATS = {
    "hp": 100, "dmg": 15, "regen": 5,
    "phys_def": 10, "mag_def": 10, "stamina": 20,
}


def _calc_stats(user_data: dict) -> dict:
    equipped = user_data.get("duel_equipped", {})
    stats    = dict(BASE_STATS)
    for item_key in equipped.values():
        item = GEAR_CATALOG.get(item_key)
        if not item:
            continue
        for stat, bonus in item["bonus"].items():
            stats[stat] = stats.get(stat, 0) + bonus
    return stats


def _create_battle(uid1: int, data1: dict, uid2: int, data2: dict) -> dict:
    """Создать состояние нового боя между двумя игроками."""
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
        "p1_shield": 0,     # активный щит
        "p2_shield": 0,
        "p1_frozen": False,  # пропускает ход
        "p2_frozen": False,
        # Перезарядка навыков: skill_key -> unix timestamp готовности
        "p1_cooldowns": {},
        "p2_cooldowns": {},
        "turn": uid1,       # чья очередь ходить (оба могут жать когда хотят)
        "started_at": now,
        "last_action": now,
        "log": [],           # лог действий
        "finished": False,
        "winner_uid": None,
    }
    return battle


def _get_player_prefix(battle: dict, uid: int) -> str:
    """Вернуть 'p1' или 'p2' для данного uid."""
    return "p1" if battle["p1_uid"] == uid else "p2"


def _get_enemy_prefix(battle: dict, uid: int) -> str:
    return "p2" if battle["p1_uid"] == uid else "p1"


def battle_use_skill(battle: dict, uid: int, skill_key: str) -> dict:
    """
    Применить навык в бою. Возвращает обновлённый battle + result dict.
    result: {"ok": bool, "msg": str, "dmg": int, "effect": str|None}
    """
    now = int(time.time())

    if battle.get("finished"):
        return battle, {"ok": False, "msg": "Бой уже завершён."}

    me  = _get_player_prefix(battle, uid)
    foe = _get_enemy_prefix(battle, uid)

    # Проверяем заморозку
    if battle.get(f"{me}_frozen"):
        battle[f"{me}_frozen"] = False
        return battle, {"ok": False, "msg": "❄️ Ты заморожен и пропускаешь ход!"}

    # Проверяем кулдаун
    cooldowns = battle.get(f"{me}_cooldowns", {})
    ready_at  = cooldowns.get(skill_key, 0)
    if now < ready_at:
        left = ready_at - now
        return battle, {"ok": False, "msg": f"⏳ Навык на перезарядке ещё {left}с."}

    sk = SKILLS.get(skill_key)
    if not sk:
        return battle, {"ok": False, "msg": "Неизвестный навык."}

    # Ставим кулдаун
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
        # Учитываем щит врага
        foe_shield = battle.get(f"{foe}_shield", 0)
        if foe_shield > 0:
            absorbed = min(foe_shield, raw_dmg)
            raw_dmg -= absorbed
            battle[f"{foe}_shield"] = foe_shield - absorbed
            effect_msg += f" (щит -{absorbed})"

        # Наносим урон
        battle[f"{foe}_hp"] = max(0, battle[f"{foe}_hp"] - raw_dmg)
        result["dmg"] = raw_dmg

        # Заморозка
        if result.get("freeze"):
            battle[f"{foe}_frozen"] = True
            effect_msg += " ❄️ заморозка!"

        log_entry = (
            f"{battle[f'{me}_name']}: {sk['emoji']} {sk['name']} "
            f"→ -{raw_dmg} HP{effect_msg}"
        )

    # Регенерация при каждом ходу
    regen = my_stats.get("regen", 0)
    if regen > 0:
        hp_max = battle[f"{me}_hp_max"]
        battle[f"{me}_hp"] = min(hp_max, battle[f"{me}_hp"] + regen)

    # Добавляем лог
    battle["log"].append(log_entry)
    if len(battle["log"]) > 6:
        battle["log"] = battle["log"][-6:]

    # Проверяем конец боя
    if battle["p1_hp"] <= 0 or battle["p2_hp"] <= 0:
        battle["finished"] = True
        if battle["p1_hp"] <= 0 and battle["p2_hp"] <= 0:
            battle["winner_uid"] = None  # ничья
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

    my_name  = battle[f"{me}_name"]
    foe_name = battle[f"{foe}_name"]
    my_hp    = battle[f"{me}_hp"]
    my_hp_max = battle[f"{me}_hp_max"]
    foe_hp   = battle[f"{foe}_hp"]
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

    # Лог последних действий
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


# ── Боевая клавиатура (навыки с кулдаунами) ─────────────────

def battle_keyboard(battle: dict, uid: int) -> InlineKeyboardMarkup:
    me  = _get_player_prefix(battle, uid)
    now = int(time.time())
    cooldowns = battle.get(f"{me}_cooldowns", {})

    builder = InlineKeyboardBuilder()

    if battle.get("finished"):
        builder.row(InlineKeyboardButton(
            text="🔄 Новый поиск", callback_data="duel_search"
        ))
        builder.row(InlineKeyboardButton(
            text="🏠 В меню дуэлей", callback_data="duel_main"
        ))
        return builder.as_markup()

    for skill_key in SKILLS_ORDER:
        sk = SKILLS[skill_key]
        ready_at = cooldowns.get(skill_key, 0)
        left = ready_at - now

        if left > 0:
            btn_text = f"{sk['emoji']} {sk['name']} ⏳{left}с"
        else:
            btn_text = f"{sk['emoji']} {sk['name']}"

        builder.row(InlineKeyboardButton(
            text=btn_text,
            callback_data=f"duel_skill:{skill_key}"
        ))

    builder.row(InlineKeyboardButton(
        text="🏳️ Сдаться", callback_data="duel_surrender"
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
        'В бою тебе доступны 5 боевых навыков:\n'
        '🔵 <b>Шар-маг</b> — маг. урон\n'
        '🟣 <b>Блок-маг</b> — мощный маг. удар\n'
        '🛡️ <b>Щит</b> — поглощает урон\n'
        '💥 <b>Взрыв</b> — физ. урон\n'
        '❄️ <b>Заморозка</b> — маг. урон + лишает хода</blockquote>'
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
#  ОРИГИНАЛЬНЫЕ ЭКРАНЫ (без изменений)
# ════════════════════════════════════════════════════════════

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

def duel_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=" Поиск противника", callback_data="duel_search",
        icon_custom_emoji_id=EMOJI_SEARCH,
    ))
    builder.row(InlineKeyboardButton(
        text=" Пригласить на поединок", callback_data="duel_invite",
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
        f'<blockquote>{"    ".join("") + chr(10).join(lines)}</blockquote>\n\n'
        '<i>Выбери слот для просмотра и покупки предметов</i>'
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
        emoji_s, ru, unit = STAT_META.get(stat, ("▫️", stat, ""))
        bonus_lines.append(f'  {emoji_s} <b>+{val}</b> {ru} <i>({unit})</i>')
    bonus_block = "\n".join(bonus_lines)

    stars = "⭐" * lvl + "☆" * (5 - lvl)

    return (
        f'{item["emoji_char"]} <b>{item["name"]}</b>\n'
        f'<i>{item["ru_name"]}</i>  {stars}\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>{item["description"]}</blockquote>\n\n'
        f'<b>Боевые бонусы:</b>\n{bonus_block}\n\n'
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


def duel_charstats_text(user_data: dict) -> str:
    s          = _calc_stats(user_data)
    equipped   = user_data.get("duel_equipped", {})
    gear_count = len(equipped)
    gear_line  = f"надето {gear_count}/5 предм." if gear_count else "снаряжение не надето"

    return (
        f'<tg-emoji emoji-id="{EMOJI_STATS_DUEL}">📊</tg-emoji> <b>ХАРАКТЕРИСТИКИ</b>\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        '<blockquote>'
        f'<tg-emoji emoji-id="{EMOJI_HP}">❤️</tg-emoji> <b>Здоровье</b> — <b>{s["hp"]}</b> HP\n\n'
        f'<tg-emoji emoji-id="{EMOJI_DMG}">⚔️</tg-emoji> <b>Урон</b> — <b>{s["dmg"]}</b> ATK\n\n'
        f'<tg-emoji emoji-id="{EMOJI_REGEN}">💚</tg-emoji> <b>Регенерация</b> — <b>{s["regen"]}</b> HP/ход\n\n'
        f'<tg-emoji emoji-id="{EMOJI_PHYS_DEF}">🛡️</tg-emoji> <b>Физ. защита</b> — <b>{s["phys_def"]}</b> DEF\n\n'
        f'<tg-emoji emoji-id="{EMOJI_MAG_DEF}">🔮</tg-emoji> <b>Маг. защита</b> — <b>{s["mag_def"]}</b> MDEF\n\n'
        f'<tg-emoji emoji-id="{EMOJI_STAMINA}">⚙️</tg-emoji> <b>Стойкость</b> — <b>{s["stamina"]}</b> STM'
        '</blockquote>\n\n'
        f'🎽 <i>Снаряжение: {gear_line}</i>'
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


# ── Экран навыков ────────────────────────────────────────────

def duel_skills_text() -> str:
    lines = []
    for sk_key in SKILLS_ORDER:
        sk = SKILLS[sk_key]
        if sk["type"] == "shield":
            val = f"поглощает {sk['shield_amount'][0]}–{sk['shield_amount'][1]} HP"
        else:
            val = f"урон {sk['base_dmg'][0]}–{sk['base_dmg'][1]}+ (зависит от ATK)"
        lines.append(
            f"{sk['emoji']} <b>{sk['name']}</b> [⏳{sk['cooldown']}с]\n"
            f"  <i>{val}</i>\n"
            f"  {sk['description']}"
        )
    block = "\n\n".join(lines)
    return (
        f'<tg-emoji emoji-id="{EMOJI_SKILLS}">✨</tg-emoji> <b>БОЕВЫЕ НАВЫКИ</b>\n'
        '━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<blockquote>{block}</blockquote>\n\n'
        '<i>Навыки доступны в бою. Каждый имеет время перезарядки.</i>'
    )

def duel_skills_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="Назад", callback_data="duel_main",
        icon_custom_emoji_id=EMOJI_BACK,
    ))
    return builder.as_markup()


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
