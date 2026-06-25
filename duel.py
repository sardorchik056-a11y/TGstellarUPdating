# ============================================================
#  duel.py  —  Раздел Дуэлей TGStellar
# ============================================================

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


# ── Главный экран ────────────────────────────────────────────

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


# ── Экран: список слотов ─────────────────────────────────────

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


# ── Экран: список уровней слота ──────────────────────────────

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


# ── Экран: карточка предмета (отдельное окно) ────────────────

def duel_item_card_text(item_key: str, user_data: dict) -> str:
    item   = GEAR_CATALOG[item_key]
    slot   = item["slot"]
    ow_lvl = owned_level(slot, user_data)
    eq_lvl = equipped_level(slot, user_data)
    lvl    = item["level"]
    balance = user_data.get("balance", 0)

    # Статус предмета
    if lvl == eq_lvl:
        status_line = '✅ <b>Надето прямо сейчас</b>'
    elif lvl <= ow_lvl:
        status_line = '📦 <b>Есть в инвентаре</b> — не надето'
    else:
        status_line = f'💰 <b>Цена: {_fmt(item["price"])} монет</b>'
        if balance < item["price"]:
            deficit = item["price"] - balance
            status_line += f'\n⚠️ <i>Не хватает {_fmt(deficit)} монет</i>'

    # Бонусы
    bonus_lines = []
    for stat, val in item["bonus"].items():
        emoji_s, ru, unit = STAT_META.get(stat, ("▫️", stat, ""))
        bonus_lines.append(f'  {emoji_s} <b>+{val}</b> {ru} <i>({unit})</i>')
    bonus_block = "\n".join(bonus_lines)

    # Звёзды уровня
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


# ── Хелперы применения снаряжения ───────────────────────────

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


# ── Характеристики ───────────────────────────────────────────

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


# ── Заглушки ─────────────────────────────────────────────────

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
