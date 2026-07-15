# ============================================================
#  green.py — «Мистический Сад» 🌺
#  Вся ЛОГИКА и ДАННЫЕ раздела: 220 цветков, посадка, рост во
#  времени, сбор урожая, ЭВОЛЮЦИЯ через СЛИЯНИЕ (3 цветка одного
#  тира — одинаковых ИЛИ разных — превращаются в случайный
#  цветок следующего тира), продажа, уникальные бонусы у КАЖДОГО
#  цветка, собственная мистическая валюта сада, тексты и
#  клавиатуры.
#
#  ХЕНДЛЕРЫ (команды/кнопки) сюда НЕ кладём — они в main.py,
#  ровно как это уже сделано с парой case.py <-> main.py.
#  Здесь используются готовые хелперы из database.py (сохранение
#  пользователя, формат чисел) — mainhelp.py не трогаем.
# ============================================================

import time
import random
import itertools

from database import format_amount

# ──────────────────────────────────────────────────────────────
#  МИСТИЧЕСКАЯ ВАЛЮТА САДА
# ──────────────────────────────────────────────────────────────
#  Сад больше не завязан на обычные монеты (data["balance"]) —
#  у него своя собственная валюта, которая копится ТОЛЬКО через
#  сад (урожай, продажа цветков) и тратится ТОЛЬКО в саду (семена,
#  ускорение роста, новые грядки).

ESSENCE_NAME  = "Мистическая Пыльца"
ESSENCE_SHORT = "Пыльца"
ESSENCE_ICON  = "✨"


def get_essence(data: dict) -> int:
    g = ensure_garden(data)
    return g.get("essence", 0)


def add_essence(data: dict, amount: int) -> int:
    g = ensure_garden(data)
    g["essence"] = g.get("essence", 0) + max(0, int(amount))
    return g["essence"]


def spend_essence(data: dict, amount: int) -> bool:
    g = ensure_garden(data)
    if g.get("essence", 0) < amount:
        return False
    g["essence"] -= amount
    return True


def fmt_essence(amount: int) -> str:
    return f"{format_amount(amount)} {ESSENCE_ICON}"


# ──────────────────────────────────────────────────────────────
#  ТИРЫ
# ──────────────────────────────────────────────────────────────

TIER_MIN = 1
TIER_MAX = 8

TIER_NAMES = {
    1: "Обычный",
    2: "Необычный",
    3: "Редкий",
    4: "Эпический",
    5: "Легендарный",
    6: "Мифический",
    7: "Божественный",
    8: "Изначальный",
}

TIER_ICON = {
    1: "🌱", 2: "🌿", 3: "🍀", 4: "🔮",
    5: "👑", 6: "🌌", 7: "✨", 8: "☠️",
}

# Время роста (сек) по тиру: от 5 минут до суток
GROW_SECONDS = {
    1: 5 * 60,
    2: 15 * 60,
    3: 30 * 60,
    4: 60 * 60,
    5: 3 * 60 * 60,
    6: 6 * 60 * 60,
    7: 12 * 60 * 60,
    8: 24 * 60 * 60,
}

# Стоимость семени тира 1 в мистической пыльце (единственный тир,
# который можно купить напрямую — остальные добываются только слиянием).
# ВАЖНО: подобрана так, чтобы базовый цикл "купить → вырастить → продать"
# НИКОГДА не уходил в минус, даже в худшем случае по RNG (см. HARVEST_REWARD
# ниже и SELL_PRICE[1]) — иначе новый игрок, ещё не дошедший до слияний,
# просто проедал бы стартовый запас пыльцы в ноль.
SEED_COST_TIER1 = 380

# Награда пыльцой за сбор урожая (диапазон) по тиру.
HARVEST_REWARD = {
    1: (450, 700),
    2: (500, 900),
    3: (1200, 2200),
    4: (3000, 5000),
    5: (7000, 12000),
    6: (18000, 30000),
    7: (45000, 75000),
    8: (120000, 200000),
}

# Опыт за сбор урожая по тиру
XP_REWARD = {
    1: 15, 2: 35, 3: 70, 4: 140,
    5: 280, 6: 500, 7: 900, 8: 1600,
}

# Цена продажи одного цветка из инвентаря (без слияния) по тиру, в пыльце
SELL_PRICE = {
    1: 150, 2: 400, 3: 900, 4: 2000,
    5: 4500, 6: 10000, 7: 22000, 8: 50000,
}

# Сколько цветков нужно для слияния (эволюции) — теперь можно мешать разные
MERGE_COUNT = 3
# Базовый шанс "прорыва" — слияние сразу перескакивает через тир
MERGE_SURGE_CHANCE = 0.08
# Небольшой доп.бонус к шансу прорыва, если в котле разные цветки
MERGE_MIX_SURGE_BONUS = 0.03

# Грядки: 4 на страницу, 3 страницы = 12 грядок максимум.
# Стартуют игроки всего с 1 открытой грядкой — остальные открывают сами
# за мистическую пыльцу по мере игры.
PLOT_BASE = 1
PLOT_MAX = 12
PLOTS_PER_PAGE = 4
PLOT_PAGES = 3

# Стартовый запас мистической пыльцы, который выдаётся новому саду один раз.
STARTING_ESSENCE = 1500

# Семена при посадке: тоже разбиваем на страницы — в тире 1 их 30 штук,
# а в инвентаре со временем может скопиться много разных редких семян.
SEEDS_PER_PAGE = 6

# Кастомный эмодзи для "закрытых" элементов интерфейса — недоступных
# грядок и неоткрытых видов в «Коллекции».
# ВАЖНО: по правилам Telegram Bot API icon_custom_emoji_id на кнопках
# показывается только у ботов, купивших доп. юзернейм на Fragment, либо
# в чатах, где у владельца бота есть Telegram Premium — в остальных
# случаях Telegram просто проигнорирует поле и покажет кнопку без иконки.
LOCKED_ICON_EMOJI_ID = "5296369303661067030"

# Кастомный эмодзи для кнопки "открыть новую грядку".
EXPAND_PLOT_ICON_EMOJI_ID = "5305699699204837855"

# Раздел «Коллекция»: сколько видов цветов на странице внутри тира.
COLLECTION_PER_PAGE = 8

# Разовая награда пыльцой за ПЕРВОЕ открытие каждого вида цветка в
# коллекции — считается ТОЛЬКО для видов, полученных СЛИЯНИЕМ (тир 2 и
# выше). Тир 1 сажается напрямую за пыльцу и виден целиком в меню посадки —
# «открывать» его не нужно, туда награда не даётся.
DISCOVERY_REWARD = {
    2: 700, 3: 1500, 4: 3500,
    5: 8000, 6: 18000, 7: 40000, 8: 100000,
}


def plot_expand_cost(next_count: int) -> int:
    """Стоимость открытия грядки №next_count, в мистической пыльце."""
    return int(4000 * (1.8 ** (next_count - PLOT_BASE - 1)))


def fertilizer_cost(remaining_seconds: int) -> int:
    """Стоимость ускорения роста в 2 РАЗА (не мгновенного завершения) —
    ровно половина цены полного мгновенного завершения (~0.45 пыльцы за
    секунду оставшегося времени), минимум 60. Ускорять можно несколько
    раз подряд, каждый раз вдвое сокращая остаток времени, а не сразу
    целиком."""
    remaining_seconds = max(0, int(remaining_seconds))
    full_instant_price = max(100, int(remaining_seconds * 0.9))
    return max(60, int(full_instant_price * 0.5))


# ──────────────────────────────────────────────────────────────
#  40 ИМЕННЫХ ("СИГНАТУРНЫХ") ЦВЕТКОВ — авторские, с уникальным лором
# ──────────────────────────────────────────────────────────────

FLOWERS_HANDCRAFTED = [
    # ---- Тир 1 · Обычный ----
    {"key": "sun_lotus",    "name": "Солнечный Лотос",     "tier": 1, "emoji": "🌼", "lore": "Раскрывается только на рассвете."},
    {"key": "amber_iris",   "name": "Янтарный Ирис",       "tier": 1, "emoji": "🌻", "lore": "Хранит тепло дня в лепестках."},
    {"key": "emerald_azalea","name": "Изумрудная Азалия",  "tier": 1, "emoji": "🌸", "lore": "Растёт даже на бесплодной земле."},
    {"key": "fire_azalea",  "name": "Огненная Азалия",     "tier": 1, "emoji": "🏵️", "lore": "Тёплая на ощупь в любую погоду."},
    {"key": "sky_lily",     "name": "Небесная Лилия",      "tier": 1, "emoji": "🌷", "lore": "Тянется к облакам сильнее, чем к земле."},

    # ---- Тир 2 · Необычный ----
    {"key": "amethyst_orchid","name": "Аметистовая Орхидея","tier": 2, "emoji": "💮", "lore": "Меняет оттенок в зависимости от настроения хозяина."},
    {"key": "crystal_camellia","name": "Кристальная Камелия","tier": 2, "emoji": "❄️", "lore": "Лепестки звенят на ветру, как стекло."},
    {"key": "twilight_violet","name": "Сумеречная Фиалка", "tier": 2, "emoji": "🌺", "lore": "Цветёт только между днём и ночью."},
    {"key": "silent_rose",  "name": "Безмолвная Роза",     "tier": 2, "emoji": "🥀", "lore": "Рядом с ней даже шёпот стихает."},
    {"key": "shadow_poppy", "name": "Теневой Мак",         "tier": 2, "emoji": "🖤", "lore": "Не отбрасывает собственной тени."},

    # ---- Тир 3 · Редкий ----
    {"key": "ghost_orchid", "name": "Призрачная Орхидея",  "tier": 3, "emoji": "👻", "lore": "Видна лишь тем, кто в неё верит."},
    {"key": "star_edelweiss","name": "Звёздный Эдельвейс", "tier": 3, "emoji": "⭐", "lore": "Семена этого цветка упали с ночного неба."},
    {"key": "crimson_narcissus","name": "Багровый Нарцисс","tier": 3, "emoji": "❤️", "lore": "Смотрится в собственное отражение целую вечность."},
    {"key": "oblivion_peony","name": "Пион Забвения",      "tier": 3, "emoji": "🌚", "lore": "Аромат стирает мелкие воспоминания."},
    {"key": "moon_blight",  "name": "Лунный Мор",          "tier": 3, "emoji": "🌑", "lore": "Расцветает только в новолуние."},

    # ---- Тир 4 · Эпический ----
    {"key": "damned_rose",  "name": "Роза Проклятых",      "tier": 4, "emoji": "🥀", "lore": "Шипы этой розы никогда не тупятся."},
    {"key": "void_aster",   "name": "Астра Пустоты",       "tier": 4, "emoji": "🕳️", "lore": "В центре бутона нет ничего — в буквальном смысле."},
    {"key": "hell_camellia","name": "Адская Камелия",      "tier": 4, "emoji": "🔥", "lore": "Тлеет, но никогда не сгорает дотла."},
    {"key": "abyss_bramble_rose","name": "Терновая Роза Бездны","tier": 4, "emoji": "🌹", "lore": "Корни уходят глубже, чем кто-либо копал."},
    {"key": "nightmare_flower","name": "Цветок Кошмаров",  "tier": 4, "emoji": "😈", "lore": "Снится тем, кто срывает его без разрешения."},

    # ---- Тир 5 · Легендарный ----
    {"key": "blood_lotus",  "name": "Кровавый Лотос",      "tier": 5, "emoji": "🩸", "lore": "Питается не водой, а старыми клятвами."},
    {"key": "abyss_lily",   "name": "Лилия Бездны",        "tier": 5, "emoji": "🖤", "lore": "Растёт там, где дно не видно."},
    {"key": "oblivion_flower","name": "Цветок Забвения",   "tier": 5, "emoji": "🌫️", "lore": "Стирает своё собственное имя из памяти сорвавшего."},
    {"key": "necroflower",  "name": "Некроцвет",           "tier": 5, "emoji": "💀", "lore": "Цветёт пышнее там, где давно никого нет."},
    {"key": "ash_magnolia", "name": "Пепельная Магнолия",  "tier": 5, "emoji": "🌫️", "lore": "Появляется на месте пожаров спустя годы."},

    # ---- Тир 6 · Мифический ----
    {"key": "devouring_orchid","name": "Архидея Поглощения","tier": 6, "emoji": "🐉", "lore": "Забирает силу у соседних растений."},
    {"key": "chaos_flower", "name": "Цветок Хаоса",        "tier": 6, "emoji": "🌀", "lore": "Каждый лепесток растёт в своём направлении времени."},
    {"key": "fate_orchid",  "name": "Архидея Судьбы",      "tier": 6, "emoji": "🔱", "lore": "Говорят, предсказывает, кто её сорвёт следующим."},
    {"key": "crown_of_dark","name": "Венец Тьмы",          "tier": 6, "emoji": "👑", "lore": "Носившие его короли исчезали без следа."},
    {"key": "thousand_souls_flower","name": "Цветок Тысячи Душ","tier": 6, "emoji": "🕯️", "lore": "В каждом лепестке — отголосок чужой жизни."},

    # ---- Тир 7 · Божественный ----
    {"key": "eternal_frost_lily","name": "Лилия Вечного Холода","tier": 7, "emoji": "🧊", "lore": "Не тает даже в самом жарком пламени."},
    {"key": "ancient_gods_flower","name": "Цветок Древних Богов","tier": 7, "emoji": "🏛️", "lore": "Рос ещё до первых храмов."},
    {"key": "ethereal_orchid","name": "Эфирная Орхидея",   "tier": 7, "emoji": "🌫️", "lore": "Наполовину существует в этом мире."},
    {"key": "forest_heart",  "name": "Сердце Леса",        "tier": 7, "emoji": "💚", "lore": "Бьётся раз в сутки — и весь лес слышит удар."},
    {"key": "ruin_flower",  "name": "Цветок Разрушения",   "tier": 7, "emoji": "☄️", "lore": "После цветения на земле остаётся выжженный круг."},

    # ---- Тир 8 · Изначальный ----
    {"key": "eternity_petal","name": "Лепесток Вечности",  "tier": 8, "emoji": "♾️", "lore": "Один-единственный лепесток, живущий вне времени."},
    {"key": "immortality_flower","name": "Цветок Бессмертия","tier": 8, "emoji": "🌟", "lore": "Не вянет никогда — просто перестаёт быть видимым."},
    {"key": "divine_orchid", "name": "Божественная Архидея","tier": 8, "emoji": "🕊️", "lore": "Последний цветок, выросший до рождения смертных."},
    {"key": "samsara_demon_flower","name": "Демонический Цветок Сансары","tier": 8, "emoji": "🔥", "lore": "Умирает и прорастает заново на месте своей гибели."},
    {"key": "ashen_phoenix_flower","name": "Цветок Пепельного Феникса","tier": 8, "emoji": "🐦‍🔥", "lore": "Каждую ночь сгорает, каждое утро расцветает вновь."},
]

# ──────────────────────────────────────────────────────────────
#  ГЕНЕРАЦИЯ ОСТАЛЬНЫХ 180 ЦВЕТКОВ (итого 220)
#  Каждый тир получает свою тематику (слова + эмодзи), из которой
#  комбинаторно собираются уникальные названия. У каждого цветка —
#  собственный, отличный от других, пассивный бонус.
# ──────────────────────────────────────────────────────────────

_TIER_THEMES = {
    1: {
        "adjectives": ["Росистый", "Пыльный", "Тихий", "Полевой", "Утренний", "Летний", "Дикий", "Ясный", "Мягкий", "Простой"],
        "nouns": ["Клевер", "Ромашка", "Гвоздика", "Вьюнок", "Мак", "Колокольчик", "Подсолнух", "Ландыш", "Пион", "Астра"],
        "emojis": ["🌼", "🌻", "🌸", "🏵️", "🌷", "🪷", "💐", "🌾"],
    },
    2: {
        "adjectives": ["Зеркальный", "Стеклянный", "Морозный", "Шёпчущий", "Сумрачный", "Жемчужный", "Туманный", "Певучий", "Бархатный", "Искристый"],
        "nouns": ["Ирис", "Гладиолус", "Хризантема", "Лилия", "Гортензия", "Азалия", "Камелия", "Орхидея", "Фиалка", "Тюльпан"],
        "emojis": ["💮", "❄️", "🌺", "🥀", "🖤", "🔔", "🌙", "🫧"],
    },
    3: {
        "adjectives": ["Призрачный", "Звёздный", "Полынный", "Забытый", "Костяной", "Пепельный", "Немой", "Хрустальный", "Мерцающий", "Блуждающий"],
        "nouns": ["Эдельвейс", "Нарцисс", "Пион", "Мак", "Орхидея", "Хризантема", "Ирис", "Лотос", "Тюльпан", "Астра"],
        "emojis": ["👻", "⭐", "❤️", "🌚", "🌑", "🕯️", "🩶", "🌫️"],
    },
    4: {
        "adjectives": ["Проклятый", "Терновый", "Адский", "Кровавый", "Демонический", "Обугленный", "Ядовитый", "Багровый", "Треснувший", "Клятвенный"],
        "nouns": ["Роза", "Астра", "Камелия", "Лилия", "Орхидея", "Гортензия", "Бутон", "Шип", "Венец", "Плющ"],
        "emojis": ["🥀", "🕳️", "🔥", "🌹", "😈", "⚔️", "🩸", "🖤"],
    },
    5: {
        "adjectives": ["Бездонный", "Кровавый", "Забытый", "Пепельный", "Могильный", "Теневой", "Скорбный", "Ледяной", "Тлеющий", "Утопший"],
        "nouns": ["Лотос", "Лилия", "Магнолия", "Цветок", "Орхидея", "Роза", "Венец", "Бутон", "Шип", "Корона"],
        "emojis": ["🩸", "🖤", "🌫️", "💀", "⚰️", "🕸️", "🩶", "🌪️"],
    },
    6: {
        "adjectives": ["Хаотичный", "Роковой", "Всепоглощающий", "Коронованный", "Вечный", "Изменчивый", "Пожирающий", "Многоликий", "Судьбоносный", "Безымянный"],
        "nouns": ["Орхидея", "Цветок", "Венец", "Корона", "Клинок", "Пламя", "Тень", "Печать", "Оракул", "Страж"],
        "emojis": ["🐉", "🌀", "🔱", "👑", "🕯️", "🔮", "🎭", "⚡"],
    },
    7: {
        "adjectives": ["Вечный", "Древний", "Эфирный", "Небесный", "Нетленный", "Священный", "Ледяной", "Пылающий", "Первородный", "Незримый"],
        "nouns": ["Лилия", "Цветок", "Орхидея", "Сердце", "Храм", "Алтарь", "Реликвия", "Слеза", "Корона", "Пламя"],
        "emojis": ["🧊", "🏛️", "🌫️", "💚", "☄️", "🕊️", "✨", "🌟"],
    },
    8: {
        "adjectives": ["Вечный", "Бессмертный", "Изначальный", "Божественный", "Демонический", "Пепельный", "Сансарический", "Абсолютный", "Нерождённый", "Всевидящий"],
        "nouns": ["Лепесток", "Цветок", "Орхидея", "Феникс", "Свет", "Исток", "Зов", "Оракул", "Трон", "Разлом"],
        "emojis": ["♾️", "🌟", "🕊️", "🔥", "🐦‍🔥", "☠️", "👁️", "💫"],
    },
}

_LORE_TEMPLATES = [
    "Говорят, этот цветок раскрывается лишь тогда, когда рядом никого нет.",
    "Его лепестки помнят каждое прикосновение садовника.",
    "Ни один травник так и не смог объяснить, откуда берётся его сила.",
    "Считается, что он растёт только там, где однажды случилось что-то важное.",
    "Аромат этого цветка чувствуют даже те, кто давно потерял обоняние.",
    "Легенда гласит, что он вырос из осколка чужой мечты.",
    "Никто не видел, как он увядает — будто у него нет конца.",
    "Его корни уходят глубже, чем кажется на первый взгляд.",
    "Он словно помнит времена, которых сад никогда не видел.",
    "Пчёлы облетают его стороной, а мотыльки — наоборот, тянутся к нему.",
    "Говорят, если загадать желание рядом с ним, оно услышит первым.",
    "Его лепестки холодные даже в самый жаркий полдень.",
    "Существует поверье, что он выбирает своего хозяина сам.",
    "Ботаники до сих пор спорят, стоит ли вообще называть его цветком.",
    "Он цветёт ровно один раз за сезон — и то не для всех.",
    "Некоторые уверяют, что слышали, как он шепчет по ночам.",
    "Его семена не тонут в воде и не горят в огне.",
    "Он будто бы знает, кто к нему подходит — друг или чужак.",
    "Садовники передают истории о нём из поколения в поколение.",
    "Иногда кажется, что он смотрит в ответ.",
    "Он растёт быстрее там, где недавно кто-то плакал.",
    "Его тень всегда чуть длиннее, чем должна быть.",
    "Он вянет от лжи и расцветает от честного слова.",
    "О нём не пишут в книгах — только передают из уст в уста.",
    "Он единственный, кто помнит, каким был сад до сада.",
]

_BONUS_TYPES = ["growth", "yield", "xp", "luck", "discount", "sell", "merge_saver", "jackpot"]

_BONUS_RANGE_BY_TIER = {
    1: (0.03, 0.06), 2: (0.05, 0.09), 3: (0.08, 0.13), 4: (0.12, 0.18),
    5: (0.16, 0.24), 6: (0.22, 0.32), 7: (0.30, 0.42), 8: (0.40, 0.55),
}

_BONUS_LABELS = {
    "growth":      ("⏱ <b>Ускорение роста</b>", lambda v: f"рост быстрее на <b>{v * 100:.1f}%</b>"),
    "yield":       ("✨ <b>Щедрый урожай</b>", lambda v: f"пыльцы за сбор больше на <b>{v * 100:.1f}%</b>"),
    "xp":          ("🧬 <b>Прилив опыта</b>", lambda v: f"опыта за сбор больше на <b>{v * 100:.1f}%</b>"),
    "luck":        ("🍀 <b>Счастливая эволюция</b>", lambda v: f"шанс прорыва при слиянии выше на <b>{v * 100:.1f}%</b>"),
    "discount":    ("💠 <b>Экономный рост</b>", lambda v: f"ускорение роста дешевле на <b>{v * 100:.1f}%</b>"),
    "sell":        ("💰 <b>Выгодная продажа</b>", lambda v: f"цена продажи выше на <b>{v * 100:.1f}%</b>"),
    "merge_saver": ("🔁 <b>Бережливое слияние</b>", lambda v: f"шанс не сгореть в котле при слиянии: <b>{v * 100:.1f}%</b>"),
    "jackpot":     ("🎰 <b>Джекпот сбора</b>", lambda v: f"шанс удвоить награду за сбор: <b>{v * 100:.1f}%</b>"),
}

# Эти бонусы мощнее прочих по своей природе (полностью удваивают/спасают
# результат), поэтому им даётся уменьшенный диапазон значений.
_BONUS_DAMPENED = {"luck": 0.4, "merge_saver": 0.3, "jackpot": 0.35}


def _make_bonus(tier: int, rng: random.Random) -> dict:
    btype = rng.choice(_BONUS_TYPES)
    lo, hi = _BONUS_RANGE_BY_TIER[tier]
    damp = _BONUS_DAMPENED.get(btype)
    if damp:
        lo, hi = lo * damp, hi * damp
    value = round(rng.uniform(lo, hi), 3)
    return {"type": btype, "value": value}


def _generate_extra_flowers() -> list:
    # Сколько сгенерировать сверх «сигнатурных» 5 на тир, чтобы в сумме
    # по всем 8 тирам получилось 220 цветков.
    generated_per_tier = {1: 25, 2: 24, 3: 23, 4: 23, 5: 22, 6: 21, 7: 21, 8: 21}
    rng = random.Random(20260714)  # фиксированный seed — набор цветков стабилен между запусками
    extra = []
    for tier in range(TIER_MIN, TIER_MAX + 1):
        theme = _TIER_THEMES[tier]
        combos = list(itertools.product(theme["adjectives"], theme["nouns"]))
        rng.shuffle(combos)
        existing_names = {f["name"] for f in FLOWERS_HANDCRAFTED if f["tier"] == tier}
        need = generated_per_tier[tier]
        picked, seen = [], set()
        for adj, noun in combos:
            name = f"{adj} {noun}"
            if name in existing_names or name in seen:
                continue
            seen.add(name)
            picked.append((adj, noun))
            if len(picked) >= need:
                break
        for i, (adj, noun) in enumerate(picked):
            name = f"{adj} {noun}"
            key = f"gen_t{tier}_{i:03d}"
            emoji = theme["emojis"][i % len(theme["emojis"])]
            lore = _LORE_TEMPLATES[(i + tier * 7) % len(_LORE_TEMPLATES)]
            bonus = _make_bonus(tier, rng)
            extra.append({"key": key, "name": name, "tier": tier, "emoji": emoji, "lore": lore, "bonus": bonus})
    return extra


def _build_all_flowers() -> list:
    generated = _generate_extra_flowers()
    all_flowers = [dict(f) for f in FLOWERS_HANDCRAFTED] + generated
    rng = random.Random(999331)
    for f in all_flowers:
        if "bonus" not in f:
            f["bonus"] = _make_bonus(f["tier"], rng)
    return all_flowers


FLOWERS = _build_all_flowers()
FLOWERS_BY_KEY = {f["key"]: f for f in FLOWERS}
FLOWERS_BY_TIER = {tier: [f for f in FLOWERS if f["tier"] == tier] for tier in range(TIER_MIN, TIER_MAX + 1)}

# Ключи всех цветков верхнего тира — нужны для бонуса "Полное цветение"
_TOP_TIER_KEYS = {f["key"] for f in FLOWERS_BY_TIER[TIER_MAX]}
GRAND_BLOOM_BONUS_ESSENCE = 1_000_000
GRAND_BLOOM_BONUS_XP      = 5_000


def flower_label(flower: dict) -> str:
    return f'{flower["emoji"]} {flower["name"]}'


def bonus_line(flower: dict) -> str:
    label, fmt = _BONUS_LABELS[flower["bonus"]["type"]]
    return f'{label} — <i>{fmt(flower["bonus"]["value"])}</i>'


def _now() -> int:
    return int(time.time())


def _fmt_time(seconds: int) -> str:
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}ч {m}м"
    if m:
        return f"{m}м {s}с"
    return f"{s}с"


def fmt_time_left(seconds: int) -> str:
    """Публичная обёртка над _fmt_time — для использования в хендлерах main.py."""
    return _fmt_time(seconds)


# ──────────────────────────────────────────────────────────────
#  СОСТОЯНИЕ САДА ПОЛЬЗОВАТЕЛЯ (хранится в data["garden"])
# ──────────────────────────────────────────────────────────────

def ensure_garden(data: dict) -> dict:
    """Гарантирует наличие и целостность структуры сада в data. Возвращает сам garden."""
    g = data.get("garden")
    if not isinstance(g, dict):
        g = {}

    g.setdefault("plot_count", PLOT_BASE)
    plots = g.setdefault("plots", [])
    while len(plots) < g["plot_count"]:
        plots.append(None)

    g.setdefault("essence", STARTING_ESSENCE)  # мистическая пыльца — валюта сада (стартовый дар — STARTING_ESSENCE)
    g.setdefault("inventory", {})       # flower_key -> количество собранных/полученных цветков
    g.setdefault("merge_cart", {"tier": None, "items": {}})  # текущий "котёл" слияния
    g.setdefault("stats", {
        "harvested": 0,
        "merges": 0,
        "surges": 0,
        "tier8_seen": [],   # ключи тир-8 цветков, которые хоть раз были получены
        "grand_bloom": False,
        "discovered": [],  # ключи ВСЕХ видов цветов, что игрок хоть раз получал — для «Коллекции»
    })
    g["stats"].setdefault("tier8_seen", [])
    g["stats"].setdefault("grand_bloom", False)
    g["stats"].setdefault("discovered", [])

    data["garden"] = g
    return g


def plot_state(plot: dict | None, now: int | None = None):
    """Возвращает (stage, progress, flower|None, seconds_left).
    stage: 'empty' | 'growing' | 'ready'.
    Учитывает персональный бонус цветка "⏱ Ускорение роста"."""
    if plot is None:
        return "empty", 0.0, None, 0

    now = now or _now()
    flower = FLOWERS_BY_KEY[plot["key"]]
    total = GROW_SECONDS[flower["tier"]]
    if flower["bonus"]["type"] == "growth":
        total = max(30, int(total * (1 - flower["bonus"]["value"])))
    elapsed = now - plot["planted_at"]
    left = max(0, total - elapsed)

    if elapsed >= total:
        return "ready", 1.0, flower, 0
    return "growing", min(1.0, elapsed / total), flower, left


def _progress_bar(progress: float, length: int = 12) -> str:
    """Полоса прогресса роста — сегментированная, другого стиля, чем раньше
    (тонкие блоки вместо квадратов-эмодзи)."""
    progress = max(0.0, min(1.0, progress))
    filled = int(round(progress * length))
    filled = max(0, min(length, filled))
    bar = "▰" * filled + "▱" * (length - filled)
    return f"[{bar}]"


# ──────────────────────────────────────────────────────────────
#  ДЕЙСТВИЯ
# ──────────────────────────────────────────────────────────────

def plant_flower(data: dict, plot_idx: int, flower_key: str) -> dict:
    g = ensure_garden(data)
    if not (0 <= plot_idx < g["plot_count"]):
        return {"ok": False, "reason": "bad_plot"}
    if g["plots"][plot_idx] is not None:
        return {"ok": False, "reason": "occupied"}

    flower = FLOWERS_BY_KEY.get(flower_key)
    if not flower:
        return {"ok": False, "reason": "unknown_flower"}

    if flower["tier"] == 1:
        cost = SEED_COST_TIER1
        if not spend_essence(data, cost):
            return {"ok": False, "reason": "no_essence", "cost": cost}
    else:
        have = g["inventory"].get(flower_key, 0)
        if have < 1:
            return {"ok": False, "reason": "no_seed"}
        g["inventory"][flower_key] = have - 1

    g["plots"][plot_idx] = {"key": flower_key, "planted_at": _now()}
    return {"ok": True, "flower": flower}


def _check_grand_bloom(data: dict, g: dict) -> bool:
    """Проверяет и выдаёт единоразовый бонус за то, что все 5 сигнатурных
    цветков тира «Изначальный» когда-либо были получены. Возвращает True,
    если бонус выдан только что."""
    if g["stats"]["grand_bloom"]:
        return False
    if _TOP_TIER_KEYS.issubset(set(g["stats"]["tier8_seen"])):
        g["stats"]["grand_bloom"] = True
        add_essence(data, GRAND_BLOOM_BONUS_ESSENCE)
        return True
    return False


def _register_flower_gain(g: dict, flower_key: str, count: int = 1):
    """Добавляет цветок в инвентарь — используется и при сборе урожая, и
    при слиянии. Отслеживание «Коллекции» сюда НЕ входит (см.
    _register_collection_discovery) — тир 1 сажается напрямую за пыльцу,
    все его виды и так видны в меню посадки, «открывать» их незачем."""
    g["inventory"][flower_key] = g["inventory"].get(flower_key, 0) + count
    flower = FLOWERS_BY_KEY[flower_key]
    if flower["tier"] == TIER_MAX and flower_key not in g["stats"]["tier8_seen"]:
        g["stats"]["tier8_seen"].append(flower_key)


def _register_collection_discovery(g: dict, flower_key: str) -> bool:
    """Отмечает вид как открытый в «Коллекции». Вызывается ТОЛЬКО для
    результатов слияния (тир 2+) — тир 1 в коллекции не участвует.
    Возвращает True при первом открытии данного вида."""
    if flower_key not in g["stats"]["discovered"]:
        g["stats"]["discovered"].append(flower_key)
        return True
    return False


def harvest_plot(data: dict, plot_idx: int) -> dict:
    g = ensure_garden(data)
    if not (0 <= plot_idx < g["plot_count"]):
        return {"ok": False, "reason": "bad_plot"}

    plot = g["plots"][plot_idx]
    if plot is None:
        return {"ok": False, "reason": "empty"}

    stage, _, flower, _ = plot_state(plot)
    if stage != "ready":
        return {"ok": False, "reason": "not_ready"}

    tier = flower["tier"]
    essence = random.randint(*HARVEST_REWARD[tier])
    xp = XP_REWARD[tier]

    bonus = flower["bonus"]
    jackpot = False
    if bonus["type"] == "yield":
        essence = int(essence * (1 + bonus["value"]))
    elif bonus["type"] == "xp":
        xp = int(xp * (1 + bonus["value"]))
    elif bonus["type"] == "jackpot" and random.random() < bonus["value"]:
        jackpot = True
        essence *= 2
        xp *= 2

    add_essence(data, essence)
    _register_flower_gain(g, flower["key"])
    g["stats"]["harvested"] += 1
    g["plots"][plot_idx] = None

    grand_bloom = _check_grand_bloom(data, g)

    return {"ok": True, "flower": flower, "essence": essence, "xp": xp,
            "jackpot": jackpot, "grand_bloom": grand_bloom}


def instant_grow(data: dict, plot_idx: int) -> dict:
    """Ускоряет рост цветка на грядке В 2 РАЗА за пыльцу — то есть сокращает
    оставшееся время ВДВОЕ, а не завершает выращивание мгновенно целиком.
    Стоит 50% от цены полного мгновенного завершения. Можно применять
    несколько раз подряд, каждый раз оплачивая новый (меньший) остаток —
    рост ускоряется постепенно, а не сразу."""
    g = ensure_garden(data)
    if not (0 <= plot_idx < g["plot_count"]):
        return {"ok": False, "reason": "bad_plot"}

    plot = g["plots"][plot_idx]
    if plot is None:
        return {"ok": False, "reason": "empty"}

    stage, _, flower, left = plot_state(plot)
    if stage == "ready":
        return {"ok": False, "reason": "already_ready"}

    cost = fertilizer_cost(left)
    if flower["bonus"]["type"] == "discount":
        cost = max(30, int(cost * (1 - flower["bonus"]["value"])))

    if not spend_essence(data, cost):
        return {"ok": False, "reason": "no_essence", "cost": cost}

    # Сокращаем оставшееся время вдвое, сдвигая момент посадки в прошлое —
    # минимум на 1 секунду, чтобы клик всегда давал заметный эффект.
    shift = max(1, left // 2)
    plot["planted_at"] -= shift

    _, _, _, new_left = plot_state(plot)
    return {"ok": True, "cost": cost, "flower": flower, "left": new_left}


# ── Слияние (эволюция) через "котёл": можно добавлять и одинаковые,
# и РАЗНЫЕ цветки — как только в котле набирается MERGE_COUNT штук
# одного тира, происходит автоматическое слияние в случайный цветок
# следующего тира. ──

def merge_cart_state(data: dict) -> dict:
    g = ensure_garden(data)
    return g["merge_cart"]


def merge_cart_clear(data: dict) -> dict:
    """Очищает котёл и ВОЗВРАЩАЕТ в инвентарь всё, что было в него
    зарезервировано (см. merge_cart_add) — иначе цветки, брошенные в
    котёл и не доведённые до слияния, просто пропадали бы."""
    g = ensure_garden(data)
    cart = g["merge_cart"]
    for key, cnt in cart["items"].items():
        g["inventory"][key] = g["inventory"].get(key, 0) + cnt
    g["merge_cart"] = {"tier": None, "items": {}}
    return {"ok": True}


def merge_cart_add(data: dict, flower_key: str) -> dict:
    """Добавляет цветок в котёл. ВАЖНО: цветок сразу СПИСЫВАЕТСЯ из
    инвентаря (резервируется), а не просто "помечается" — иначе между
    добавлением в котёл и самим слиянием тот же цветок можно было бы
    параллельно продать (garden_sell не знает про котёл): получить деньги
    за продажу и всё равно довести слияние до конца за счёт других
    цветков — инвентарь уходил в минус, а игрок получал дубликат ценности.
    При очистке котла (merge_cart_clear) зарезервированное возвращается
    обратно в инвентарь."""
    g = ensure_garden(data)
    flower = FLOWERS_BY_KEY.get(flower_key)
    if not flower:
        return {"ok": False, "reason": "unknown_flower"}
    if flower["tier"] >= TIER_MAX:
        return {"ok": False, "reason": "max_tier"}

    cart = g["merge_cart"]
    if cart["items"] and cart.get("tier") not in (None, flower["tier"]):
        return {"ok": False, "reason": "tier_mismatch", "tier": cart["tier"]}

    have = g["inventory"].get(flower_key, 0)
    if have < 1:
        return {"ok": False, "reason": "not_enough"}

    g["inventory"][flower_key] = have - 1
    cart["tier"] = flower["tier"]
    cart["items"][flower_key] = cart["items"].get(flower_key, 0) + 1

    if sum(cart["items"].values()) >= MERGE_COUNT:
        return _execute_merge(data, g)

    return {"ok": True, "done": False, "cart": dict(cart["items"]), "tier": flower["tier"],
            "need": MERGE_COUNT - sum(cart["items"].values())}


def _execute_merge(data: dict, g: dict) -> dict:
    """Цветки в котле уже списаны из инвентаря в момент merge_cart_add —
    здесь их заново вычитать НЕЛЬЗЯ (см. комментарий там же), иначе
    инвентарь снова уходит в минус. Единственное, что нужно сделать —
    вернуть в инвентарь тех, кого "спас" бонус merge_saver."""
    cart = g["merge_cart"]
    items = cart["items"]
    tier = cart["tier"]

    consumed = []
    saved_back = []
    luck_bonus = 0.0
    for key, cnt in items.items():
        f = FLOWERS_BY_KEY[key]
        if f["bonus"]["type"] == "merge_saver":
            saved = sum(1 for _ in range(cnt) if random.random() < f["bonus"]["value"])
            if saved:
                saved_back.append((f, saved))
                g["inventory"][key] = g["inventory"].get(key, 0) + saved
        consumed.append((f, cnt))
        if f["bonus"]["type"] == "luck":
            luck_bonus += f["bonus"]["value"] * cnt

    mixed = len(items) > 1
    surge_chance = MERGE_SURGE_CHANCE + luck_bonus + (MERGE_MIX_SURGE_BONUS if mixed else 0.0)
    surge = tier <= TIER_MAX - 2 and random.random() < surge_chance
    result_tier = min(TIER_MAX, tier + (2 if surge else 1))
    result = random.choice(FLOWERS_BY_TIER[result_tier])

    _register_flower_gain(g, result["key"])
    is_new = _register_collection_discovery(g, result["key"])
    discovery_reward = 0
    if is_new:
        discovery_reward = DISCOVERY_REWARD[result_tier]
        add_essence(data, discovery_reward)
    g["stats"]["merges"] += 1
    if surge:
        g["stats"]["surges"] += 1

    g["merge_cart"] = {"tier": None, "items": {}}
    grand_bloom = _check_grand_bloom(data, g)

    return {"ok": True, "done": True, "consumed": consumed, "result": result,
            "surge": surge, "mixed": mixed, "saved_back": saved_back, "grand_bloom": grand_bloom,
            "new_discovery": is_new, "discovery_reward": discovery_reward}


def sell_flower(data: dict, flower_key: str, count: int = 1) -> dict:
    g = ensure_garden(data)
    flower = FLOWERS_BY_KEY.get(flower_key)
    if not flower:
        return {"ok": False, "reason": "unknown_flower"}

    have = g["inventory"].get(flower_key, 0)
    if count <= 0 or have < count:
        return {"ok": False, "reason": "not_enough"}

    price = SELL_PRICE[flower["tier"]] * count
    if flower["bonus"]["type"] == "sell":
        price = int(price * (1 + flower["bonus"]["value"]))
    g["inventory"][flower_key] = have - count
    add_essence(data, price)
    return {"ok": True, "essence": price, "count": count, "flower": flower}


def expand_garden(data: dict) -> dict:
    """Открывает следующую по порядку грядку — за мистическую пыльцу."""
    g = ensure_garden(data)
    if g["plot_count"] >= PLOT_MAX:
        return {"ok": False, "reason": "max_plots"}

    cost = plot_expand_cost(g["plot_count"] + 1)
    if not spend_essence(data, cost):
        return {"ok": False, "reason": "no_essence", "cost": cost}

    g["plot_count"] += 1
    g["plots"].append(None)
    return {"ok": True, "plot_count": g["plot_count"], "cost": cost}


# ──────────────────────────────────────────────────────────────
#  ТЕКСТЫ / КЛАВИАТУРЫ
#  (используются напрямую в хендлерах main.py, как case_status_text
#  и case_keyboard используются из case.py)
# ──────────────────────────────────────────────────────────────

def garden_text(data: dict, page: int = 0) -> str:
    g = ensure_garden(data)
    lines = [
        '🌺 <b>МИСТИЧЕСКИЙ САД</b>',
        f'<blockquote><i>Выращивай цветки, собирай урожай и сливай в котле по '
        f'{MERGE_COUNT} шт. — одинаковых или даже разных — чтобы получить более '
        f'редкий цветок: от {TIER_ICON[1]} обычного до {TIER_ICON[8]} изначального. '
        f'Всего в саду <b>{len(FLOWERS)}</b> видов цветов.</i></blockquote>',
        '',
        f'🪴 <b>Грядок открыто:</b> <b>{g["plot_count"]}/{PLOT_MAX}</b>',
        f'📄 <b>Страница:</b> <b>{page + 1}/{PLOT_PAGES}</b>',
        f'{ESSENCE_ICON} <b>{ESSENCE_NAME}:</b> <b>{format_amount(get_essence(data))}</b>',
    ]
    return "\n".join(lines)


def _plot_button_label(idx: int, plot: dict | None) -> str:
    stage, progress, flower, left = plot_state(plot)
    if stage == "empty":
        return "➕ Пусто"
    if stage == "ready":
        return f"✅ {flower_label(flower)}"
    pct = int(progress * 100)
    return f"{flower['emoji']} {pct}% ({_fmt_time(left)})"


def garden_keyboard(data: dict, page: int = 0):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    g = ensure_garden(data)
    page = max(0, min(PLOT_PAGES - 1, page))
    start = page * PLOTS_PER_PAGE
    end = start + PLOTS_PER_PAGE

    b = InlineKeyboardBuilder()
    for idx in range(start, min(end, PLOT_MAX)):
        if idx < g["plot_count"]:
            plot = g["plots"][idx]
            stage, _, _, _ = plot_state(plot)
            btn_kwargs = {
                "text": _plot_button_label(idx, plot),
                "callback_data": f"garden_plot:{idx}",
            }
            if stage == "ready":
                btn_kwargs["style"] = "success"   # выросло — зелёная
            elif stage == "growing":
                btn_kwargs["style"] = "primary"   # растёт — синяя
            b.row(InlineKeyboardButton(**btn_kwargs))
        elif idx == g["plot_count"]:
            cost = plot_expand_cost(idx + 1)
            b.row(InlineKeyboardButton(
                text=f"Открыть грядку — {format_amount(cost)} {ESSENCE_ICON}",
                icon_custom_emoji_id=EXPAND_PLOT_ICON_EMOJI_ID,
                callback_data="garden_expand",
            ))
        else:
            b.row(InlineKeyboardButton(
                text="Заблокировано",
                icon_custom_emoji_id=LOCKED_ICON_EMOJI_ID,
                callback_data="garden_noop",
            ))

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"garden_page:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"· {page + 1}/{PLOT_PAGES} ·", callback_data="garden_noop"))
    if page < PLOT_PAGES - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"garden_page:{page + 1}"))
    b.row(*nav)

    b.row(
        InlineKeyboardButton(text="🎒 Инвентарь", callback_data="garden_inventory"),
        InlineKeyboardButton(text="🧬 Слияние", callback_data="garden_merge"),
    )
    b.row(InlineKeyboardButton(text="📖 Коллекция", callback_data="garden_collection"))
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"))
    return b.as_markup()


def plot_detail_text(data: dict, plot_idx: int) -> str:
    g = ensure_garden(data)
    plot = g["plots"][plot_idx]
    stage, progress, flower, left = plot_state(plot)

    if stage == "empty":
        return (
            f'🪴 <b>Грядка №{plot_idx + 1}</b>\n'
            f'<blockquote><i>Грядка свободна. Посади семя.</i></blockquote>'
        )
    if stage == "ready":
        return (
            f'🪴 <b>Грядка №{plot_idx + 1}</b>\n'
            f'<blockquote>{flower_label(flower)} · <b>{TIER_NAMES[flower["tier"]]}</b>\n'
            f'<i>{flower["lore"]}</i>\n'
            f'{bonus_line(flower)}\n\n'
            f'✅ <b>Готов к сбору!</b></blockquote>'
        )
    return (
        f'🪴 <b>Грядка №{plot_idx + 1}</b>\n'
        f'<blockquote>{flower_label(flower)} · <b>{TIER_NAMES[flower["tier"]]}</b>\n'
        f'<i>{flower["lore"]}</i>\n'
        f'{bonus_line(flower)}\n\n'
        f'{_progress_bar(progress)} <b>{int(progress * 100)}%</b>\n'
        f'⏳ Осталось: <b>{_fmt_time(left)}</b></blockquote>'
    )


def plot_detail_keyboard(data: dict, plot_idx: int):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    g = ensure_garden(data)
    plot = g["plots"][plot_idx]
    stage, _, flower, left = plot_state(plot)

    b = InlineKeyboardBuilder()
    if stage == "empty":
        b.row(InlineKeyboardButton(text="🌱 Посадить семя", callback_data=f"garden_plantmenu:{plot_idx}"))
    elif stage == "ready":
        b.row(InlineKeyboardButton(text="🌾 Собрать урожай", callback_data=f"garden_harvest:{plot_idx}"))
    else:
        cost = fertilizer_cost(left)
        if flower["bonus"]["type"] == "discount":
            cost = max(30, int(cost * (1 - flower["bonus"]["value"])))
        b.row(InlineKeyboardButton(
            text=f"⚡ Ускорить в 2 раза за {format_amount(cost)} {ESSENCE_ICON}",
            callback_data=f"garden_grow:{plot_idx}",
        ))
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="garden"))
    return b.as_markup()


def _seed_pages(count: int) -> int:
    return max(1, (count + SEEDS_PER_PAGE - 1) // SEEDS_PER_PAGE)


def plant_menu_text(plot_idx: int, page: int = 0) -> str:
    total_pages = _seed_pages(len(FLOWERS_BY_TIER[1]))
    page = max(0, min(total_pages - 1, page))
    return (
        f'🌱 <b>Выбор семени — грядка №{plot_idx + 1}</b>\n'
        f'<blockquote><i>Обычные семена продаются за {ESSENCE_NAME.lower()}. Семена более редких '
        f'цветков появляются в инвентаре только после слияния.</i></blockquote>\n'
        f'📄 Страница: <b>{page + 1}/{total_pages}</b>'
    )


def plant_menu_keyboard(data: dict, plot_idx: int, page: int = 0):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    g = ensure_garden(data)
    tier1 = FLOWERS_BY_TIER[1]
    total_pages = _seed_pages(len(tier1))
    page = max(0, min(total_pages - 1, page))
    start = page * SEEDS_PER_PAGE
    end = start + SEEDS_PER_PAGE

    b = InlineKeyboardBuilder()

    for f in tier1[start:end]:
        b.row(InlineKeyboardButton(
            text=f'{flower_label(f)} — {format_amount(SEED_COST_TIER1)} {ESSENCE_ICON}',
            callback_data=f"garden_plant:{plot_idx}:{f['key']}",
        ))

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"garden_plantmenu:{plot_idx}:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"· {page + 1}/{total_pages} ·", callback_data="garden_noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"garden_plantmenu:{plot_idx}:{page + 1}"))
    b.row(*nav)

    seed_keys = [k for k, cnt in g["inventory"].items() if cnt > 0 and FLOWERS_BY_KEY[k]["tier"] > 1]
    if seed_keys:
        b.row(InlineKeyboardButton(text="🎒 Посадить из инвентаря", callback_data=f"garden_plantinv:{plot_idx}:0"))

    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"garden_plot:{plot_idx}"))
    return b.as_markup()


def plant_inventory_text(data: dict, plot_idx: int, page: int = 0) -> str:
    g = ensure_garden(data)
    seeds = [(k, c) for k, c in g["inventory"].items() if c > 0 and FLOWERS_BY_KEY[k]["tier"] > 1]
    total_pages = _seed_pages(len(seeds)) if seeds else 1
    page = max(0, min(total_pages - 1, page))
    if not seeds:
        body = '<i>В инвентаре пока нет редких семян — получи их через слияние в котле.</i>'
    else:
        body = f'<i>Выбери семя из своего инвентаря, чтобы посадить его на грядку №{plot_idx + 1}.</i>'
    return (
        f'🎒 <b>Посадка из инвентаря — грядка №{plot_idx + 1}</b>\n'
        f'<blockquote>{body}</blockquote>\n'
        f'📄 Страница: <b>{page + 1}/{total_pages}</b>'
    )


def plant_inventory_keyboard(data: dict, plot_idx: int, page: int = 0):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    g = ensure_garden(data)
    seeds = sorted(
        [(k, c) for k, c in g["inventory"].items() if c > 0 and FLOWERS_BY_KEY[k]["tier"] > 1],
        key=lambda kv: (FLOWERS_BY_KEY[kv[0]]["tier"], FLOWERS_BY_KEY[kv[0]]["name"]),
    )
    total_pages = _seed_pages(len(seeds)) if seeds else 1
    page = max(0, min(total_pages - 1, page))
    start = page * SEEDS_PER_PAGE
    end = start + SEEDS_PER_PAGE

    b = InlineKeyboardBuilder()
    for key, cnt in seeds[start:end]:
        f = FLOWERS_BY_KEY[key]
        b.row(InlineKeyboardButton(
            text=f'{flower_label(f)} ×{cnt}',
            callback_data=f"garden_plant:{plot_idx}:{key}",
        ))

    if seeds:
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton(text="◀️", callback_data=f"garden_plantinv:{plot_idx}:{page - 1}"))
        nav.append(InlineKeyboardButton(text=f"· {page + 1}/{total_pages} ·", callback_data="garden_noop"))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton(text="▶️", callback_data=f"garden_plantinv:{plot_idx}:{page + 1}"))
        b.row(*nav)

    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"garden_plantmenu:{plot_idx}:0"))
    return b.as_markup()


def inventory_text(data: dict) -> str:
    g = ensure_garden(data)
    have = {k: c for k, c in g["inventory"].items() if c > 0}
    if not have:
        return (
            '🎒 <b>Инвентарь сада</b>\n'
            '<blockquote><i>Пока пусто. Собери первый урожай!</i></blockquote>'
        )

    lines = ['🎒 <b>Инвентарь сада</b>', '<blockquote>']
    for tier in range(TIER_MIN, TIER_MAX + 1):
        tier_items = [(k, c) for k, c in have.items() if FLOWERS_BY_KEY[k]["tier"] == tier]
        if not tier_items:
            continue
        lines.append(f'\n{TIER_ICON[tier]} <b>{TIER_NAMES[tier]}</b>')
        for k, c in tier_items:
            f = FLOWERS_BY_KEY[k]
            lines.append(f'  {flower_label(f)} — <b>×{c}</b>')
    lines.append('</blockquote>')
    return "\n".join(lines)


def inventory_keyboard(data: dict):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    g = ensure_garden(data)
    b = InlineKeyboardBuilder()
    for tier in range(TIER_MIN, TIER_MAX + 1):
        for f in FLOWERS_BY_TIER[tier]:
            cnt = g["inventory"].get(f["key"], 0)
            if cnt <= 0:
                continue
            b.row(InlineKeyboardButton(
                text=f'{flower_label(f)} ×{cnt}',
                callback_data=f"garden_flower:{f['key']}",
            ))
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="garden"))
    return b.as_markup()


def flower_detail_text(data: dict, flower_key: str) -> str:
    g = ensure_garden(data)
    f = FLOWERS_BY_KEY[flower_key]
    cnt = g["inventory"].get(flower_key, 0)
    tier = f["tier"]

    lines = [
        f'{flower_label(f)}',
        f'<blockquote><i>{f["lore"]}</i>\n\n'
        f'<b>Тир:</b> <b>{TIER_ICON[tier]} {TIER_NAMES[tier]}</b>\n'
        f'{bonus_line(f)}\n'
        f'<b>В инвентаре:</b> <b>×{cnt}</b>\n'
        f'<b>Цена продажи:</b> <b>{format_amount(SELL_PRICE[tier])}</b> {ESSENCE_ICON} за штуку</blockquote>',
    ]
    if tier < TIER_MAX:
        lines.append(
            f'<blockquote><i>🧬 Слияние доступно в меню сада: добавь {MERGE_COUNT} цветка этого тира '
            f'в котёл (можно даже разных), чтобы получить случайный цветок '
            f'тира «{TIER_NAMES[tier + 1]}» — есть шанс «прорыва» сразу на 2 тира выше.</i></blockquote>'
        )
    else:
        lines.append('<blockquote><i>🏆 Это высший тир сада — дальше эволюционировать некуда.</i></blockquote>')
    return "\n".join(lines)


def flower_detail_keyboard(data: dict, flower_key: str):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    g = ensure_garden(data)
    cnt = g["inventory"].get(flower_key, 0)

    b = InlineKeyboardBuilder()
    if cnt >= 1:
        b.row(
            InlineKeyboardButton(text="💰 Продать 1", callback_data=f"garden_sell:{flower_key}:1"),
            InlineKeyboardButton(text="💰 Продать всё", callback_data=f"garden_sell:{flower_key}:all"),
        )
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="garden_inventory"))
    return b.as_markup()


# ── Меню СЛИЯНИЯ (в главном меню сада, не в инвентаре) ──

def merge_menu_text(data: dict) -> str:
    g = ensure_garden(data)
    cart = g["merge_cart"]
    lines = [
        '🧬 <b>Слияние цветков</b>',
        f'<blockquote><i>Выбери тир и добавляй цветки в котёл — одинаковые или '
        f'разные, не важно. Как только наберётся {MERGE_COUNT} шт., слияние '
        f'произойдёт автоматически и подарит случайный цветок следующего тира.</i></blockquote>',
    ]
    if cart["items"]:
        parts = [f'{flower_label(FLOWERS_BY_KEY[k])} ×{c}' for k, c in cart["items"].items()]
        total = sum(cart["items"].values())
        lines.append(
            f'\n🔥 <b>В котле</b> ({total}/{MERGE_COUNT}), тир «{TIER_NAMES[cart["tier"]]}»:\n'
            f'<blockquote>{", ".join(parts)}</blockquote>'
        )
    return "\n".join(lines)


def merge_menu_keyboard(data: dict):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    g = ensure_garden(data)
    b = InlineKeyboardBuilder()
    for tier in range(TIER_MIN, TIER_MAX):
        total = sum(c for k, c in g["inventory"].items() if FLOWERS_BY_KEY[k]["tier"] == tier and c > 0)
        if total <= 0:
            continue
        b.row(InlineKeyboardButton(
            text=f'{TIER_ICON[tier]} {TIER_NAMES[tier]} — {total} шт. в саду',
            callback_data=f"garden_mergetier:{tier}",
        ))
    if g["merge_cart"]["items"]:
        b.row(InlineKeyboardButton(text="🗑 Очистить котёл", callback_data="garden_mergeclear"))
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="garden"))
    return b.as_markup()


def merge_tier_text(data: dict, tier: int) -> str:
    g = ensure_garden(data)
    cart = g["merge_cart"]
    lines = [
        f'{TIER_ICON[tier]} <b>Котёл — тир «{TIER_NAMES[tier]}»</b>',
        f'<blockquote><i>Нажимай на цветок, чтобы бросить его в котёл. '
        f'Нужно {MERGE_COUNT} шт. — не обязательно одинаковых.</i></blockquote>',
    ]
    if cart["items"] and cart.get("tier") == tier:
        total = sum(cart["items"].values())
        lines.append(f'\n🔥 <b>В котле: {total}/{MERGE_COUNT}</b>')
    return "\n".join(lines)


def merge_tier_keyboard(data: dict, tier: int):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    g = ensure_garden(data)
    cart = g["merge_cart"]
    b = InlineKeyboardBuilder()
    for f in FLOWERS_BY_TIER[tier]:
        in_cart = cart["items"].get(f["key"], 0) if cart.get("tier") == tier else 0
        # g["inventory"] уже НЕ включает то, что зарезервировано в котле
        # (merge_cart_add списывает сразу), поэтому avail — это просто
        # текущий остаток в инвентаре, без повторного вычитания in_cart.
        avail = g["inventory"].get(f["key"], 0)
        if avail <= 0 and in_cart <= 0:
            continue
        label = f'{flower_label(f)} · доступно {avail}' + (f' · в котле {in_cart}' if in_cart else '')
        b.row(InlineKeyboardButton(
            text=label,
            callback_data=f"garden_mergeadd:{f['key']}" if avail > 0 else "garden_noop",
        ))
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="garden_merge"))
    return b.as_markup()


# ──────────────────────────────────────────────────────────────
#  КОЛЛЕКЦИЯ — витрина всех 220 видов цветов сада. Неоткрытые виды
#  показываются как "🔒 ???" (ни названия, ни бонуса не видно), а при
#  первом получении вида (сбор урожая ИЛИ результат слияния — см.
#  _register_flower_gain/harvest_plot/_execute_merge) начисляется разовая
#  награда DISCOVERY_REWARD и запись остаётся в коллекции навсегда.
# ──────────────────────────────────────────────────────────────

# Тир 1 в «Коллекции» не участвует — он покупается напрямую за пыльцу и
# весь целиком виден в меню посадки, «открывать» там нечего. Коллекция —
# только про виды, которые могут выпасть случайно при слиянии (тир 2+).
COLLECTION_TIER_MIN = 2
_COLLECTION_FLOWERS = [f for f in FLOWERS if f["tier"] >= COLLECTION_TIER_MIN]


def _collection_pages(tier: int) -> int:
    return max(1, (len(FLOWERS_BY_TIER[tier]) + COLLECTION_PER_PAGE - 1) // COLLECTION_PER_PAGE)


def _collection_sorted(tier: int, discovered: set) -> list:
    """Открытые виды — вперёд списка, закрытые — следом. Внутри каждой
    группы порядок сохраняется исходным (стабильная сортировка), чтобы
    расположение не "прыгало" от открытия к открытию."""
    tier_flowers = FLOWERS_BY_TIER[tier]
    return sorted(tier_flowers, key=lambda f: f["key"] not in discovered)


def collection_menu_text(data: dict) -> str:
    g = ensure_garden(data)
    discovered = set(g["stats"]["discovered"])
    total = len(_COLLECTION_FLOWERS)
    found = sum(1 for f in _COLLECTION_FLOWERS if f["key"] in discovered)
    pct = int(found / total * 100) if total else 0
    lines = [
        '📖 <b>Коллекция цветков</b>',
        f'<blockquote><i>Тир 1 покупается напрямую и весь виден в меню посадки — '
        f'в коллекции его нет. А вот каждый новый вид, который выпадает при '
        f'СЛИЯНИИ (тир 2 и выше), навсегда остаётся здесь, и за первое открытие '
        f'вида даётся разовая награда {ESSENCE_ICON} пыльцой. Неоткрытые виды скрыты — '
        f'их бонус и лор станут видны только после первой поимки.</i></blockquote>',
        '',
        f'🔓 <b>Открыто всего:</b> <b>{found}/{total}</b> ({pct}%)',
    ]
    return "\n".join(lines)


def collection_menu_keyboard(data: dict):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    g = ensure_garden(data)
    discovered = set(g["stats"]["discovered"])
    b = InlineKeyboardBuilder()
    for tier in range(COLLECTION_TIER_MIN, TIER_MAX + 1):
        tier_flowers = FLOWERS_BY_TIER[tier]
        found = sum(1 for f in tier_flowers if f["key"] in discovered)
        total = len(tier_flowers)
        btn_kwargs = {
            "text": f'{TIER_ICON[tier]} {TIER_NAMES[tier]} — {found}/{total}',
            "callback_data": f"garden_colltier:{tier}:0",
        }
        if found == total:
            btn_kwargs["style"] = "success"
        b.row(InlineKeyboardButton(**btn_kwargs))
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="garden"))
    return b.as_markup()


def collection_tier_text(data: dict, tier: int, page: int = 0) -> str:
    g = ensure_garden(data)
    discovered = set(g["stats"]["discovered"])
    tier_flowers = _collection_sorted(tier, discovered)
    found = sum(1 for f in tier_flowers if f["key"] in discovered)
    pages = _collection_pages(tier)
    page = max(0, min(pages - 1, page))

    lines = [
        f'{TIER_ICON[tier]} <b>{TIER_NAMES[tier]}</b> — открыто {found}/{len(tier_flowers)}',
        f'📄 Страница {page + 1}/{pages}',
        '<blockquote>',
    ]
    start = page * COLLECTION_PER_PAGE
    for f in tier_flowers[start:start + COLLECTION_PER_PAGE]:
        if f["key"] in discovered:
            lines.append(f'  {flower_label(f)}')
        else:
            lines.append('  🔒 ??? <i>(не открыто)</i>')
    lines.append('</blockquote>')
    return "\n".join(lines)


def collection_tier_keyboard(data: dict, tier: int, page: int = 0):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    g = ensure_garden(data)
    discovered = set(g["stats"]["discovered"])
    tier_flowers = _collection_sorted(tier, discovered)
    pages = _collection_pages(tier)
    page = max(0, min(pages - 1, page))
    start = page * COLLECTION_PER_PAGE

    b = InlineKeyboardBuilder()
    for f in tier_flowers[start:start + COLLECTION_PER_PAGE]:
        if f["key"] in discovered:
            b.row(InlineKeyboardButton(
                text=flower_label(f),
                style="success",
                callback_data=f"garden_collflower:{f['key']}:{page}",
            ))
        else:
            b.row(InlineKeyboardButton(
                text="???",
                icon_custom_emoji_id=LOCKED_ICON_EMOJI_ID,
                callback_data="garden_noop",
            ))

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"garden_colltier:{tier}:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"· {page + 1}/{pages} ·", callback_data="garden_noop"))
    if page < pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"garden_colltier:{tier}:{page + 1}"))
    b.row(*nav)

    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="garden_collection"))
    return b.as_markup()


def collection_flower_text(data: dict, flower_key: str) -> str:
    f = FLOWERS_BY_KEY[flower_key]
    tier = f["tier"]
    lines = [
        f'{flower_label(f)}',
        f'<blockquote><i>{f["lore"]}</i>\n\n'
        f'<b>Тир:</b> <b>{TIER_ICON[tier]} {TIER_NAMES[tier]}</b>\n'
        f'{bonus_line(f)}</blockquote>',
        '',
        '<i>✅ Этот вид уже открыт в твоей коллекции.</i>',
    ]
    return "\n".join(lines)


def collection_flower_keyboard(data: dict, flower_key: str, page: int = 0):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    f = FLOWERS_BY_KEY[flower_key]
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"garden_colltier:{f['tier']}:{page}"))
    return b.as_markup()
