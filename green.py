# ============================================================
#  green.py — «Мистический Сад» 🌺
#  Вся ЛОГИКА и ДАННЫЕ раздела: 40 цветков, посадка, рост во
#  времени, сбор урожая, ЭВОЛЮЦИЯ через СЛИЯНИЕ (3 одинаковых
#  цветка -> случайный цветок следующего тира), продажа, тексты
#  и клавиатуры.
#
#  ХЕНДЛЕРЫ (команды/кнопки) сюда НЕ кладём — они в main.py,
#  ровно как это уже сделано с парой case.py <-> main.py.
#  Здесь используются готовые хелперы из database.py (сохранение
#  пользователя, формат чисел) — mainhelp.py не трогаем.
# ============================================================

import time
import random

from database import format_amount

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

# Стоимость семени тира 1 (единственный тир, который можно купить
# напрямую за монеты — остальные добываются только слиянием)
SEED_COST_TIER1 = 500

# Награда монетами за сбор урожая (диапазон) по тиру
HARVEST_REWARD = {
    1: (200, 400),
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

# Цена продажи одного цветка из инвентаря (без слияния) по тиру
SELL_PRICE = {
    1: 150, 2: 400, 3: 900, 4: 2000,
    5: 4500, 6: 10000, 7: 22000, 8: 50000,
}

# Сколько одинаковых цветков нужно для слияния (эволюции)
MERGE_COUNT = 3
# Шанс "прорыва" — слияние сразу перескакивает через тир
MERGE_SURGE_CHANCE = 0.08

# Грядки
PLOT_BASE = 3
PLOT_MAX = 12


def plot_expand_cost(next_count: int) -> int:
    """Стоимость расширения сада до next_count грядок (next_count-я грядка)."""
    return int(4000 * (1.8 ** (next_count - PLOT_BASE - 1)))


def fertilizer_cost(remaining_seconds: int) -> int:
    """Стоимость мгновенного ускорения роста — 1 монета за ~1.2 сек оставшегося времени, минимум 100."""
    return max(100, int(remaining_seconds * 0.9))


# ──────────────────────────────────────────────────────────────
#  40 ЦВЕТКОВ
# ──────────────────────────────────────────────────────────────
# key, name, tier, emoji, lore (короткая строка атмосферы)

FLOWERS = [
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

FLOWERS_BY_KEY = {f["key"]: f for f in FLOWERS}
FLOWERS_BY_TIER = {tier: [f for f in FLOWERS if f["tier"] == tier] for tier in range(TIER_MIN, TIER_MAX + 1)}

# Ключи всех цветков верхнего тира — нужны для бонуса "Полное цветение"
_TOP_TIER_KEYS = {f["key"] for f in FLOWERS_BY_TIER[TIER_MAX]}
GRAND_BLOOM_BONUS_COINS = 1_000_000
GRAND_BLOOM_BONUS_XP    = 5_000


def flower_label(flower: dict) -> str:
    return f'{flower["emoji"]} {flower["name"]}'


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

    g.setdefault("inventory", {})       # flower_key -> количество собранных/полученных цветков
    g.setdefault("stats", {
        "harvested": 0,
        "merges": 0,
        "surges": 0,
        "tier8_seen": [],   # ключи тир-8 цветков, которые хоть раз были получены
        "grand_bloom": False,
    })
    g["stats"].setdefault("tier8_seen", [])
    g["stats"].setdefault("grand_bloom", False)

    data["garden"] = g
    return g


def plot_state(plot: dict | None, now: int | None = None):
    """Возвращает (stage, progress, flower|None, seconds_left).
    stage: 'empty' | 'growing' | 'ready'"""
    if plot is None:
        return "empty", 0.0, None, 0

    now = now or _now()
    flower = FLOWERS_BY_KEY[plot["key"]]
    total = GROW_SECONDS[flower["tier"]]
    elapsed = now - plot["planted_at"]
    left = max(0, total - elapsed)

    if elapsed >= total:
        return "ready", 1.0, flower, 0
    return "growing", min(1.0, elapsed / total), flower, left


def _progress_bar(progress: float, length: int = 10) -> str:
    filled = int(round(progress * length))
    filled = max(0, min(length, filled))
    return "🟩" * filled + "⬜" * (length - filled)


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
        if data.get("balance", 0) < cost:
            return {"ok": False, "reason": "no_coins", "cost": cost}
        data["balance"] = data.get("balance", 0) - cost
    else:
        have = g["inventory"].get(flower_key, 0)
        if have < 1:
            return {"ok": False, "reason": "no_seed"}
        g["inventory"][flower_key] = have - 1

    g["plots"][plot_idx] = {"key": flower_key, "planted_at": _now()}
    return {"ok": True, "flower": flower}


def _check_grand_bloom(data: dict, g: dict) -> bool:
    """Проверяет и выдаёт единоразовый бонус за то, что все 5 цветков
    тира «Изначальный» когда-либо были получены. Возвращает True, если
    бонус выдан только что."""
    if g["stats"]["grand_bloom"]:
        return False
    if _TOP_TIER_KEYS.issubset(set(g["stats"]["tier8_seen"])):
        g["stats"]["grand_bloom"] = True
        data["balance"] = data.get("balance", 0) + GRAND_BLOOM_BONUS_COINS
        return True
    return False


def _register_flower_gain(g: dict, flower_key: str, count: int = 1):
    g["inventory"][flower_key] = g["inventory"].get(flower_key, 0) + count
    flower = FLOWERS_BY_KEY[flower_key]
    if flower["tier"] == TIER_MAX and flower_key not in g["stats"]["tier8_seen"]:
        g["stats"]["tier8_seen"].append(flower_key)


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
    coins = random.randint(*HARVEST_REWARD[tier])
    xp = XP_REWARD[tier]

    data["balance"] = data.get("balance", 0) + coins
    _register_flower_gain(g, flower["key"])
    g["stats"]["harvested"] += 1
    g["plots"][plot_idx] = None

    grand_bloom = _check_grand_bloom(data, g)

    return {"ok": True, "flower": flower, "coins": coins, "xp": xp, "grand_bloom": grand_bloom}


def instant_grow(data: dict, plot_idx: int) -> dict:
    """Мгновенно завершает рост цветка на грядке за монеты (не бесплатно)."""
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
    if data.get("balance", 0) < cost:
        return {"ok": False, "reason": "no_coins", "cost": cost}

    data["balance"] = data.get("balance", 0) - cost
    plot["planted_at"] = _now() - GROW_SECONDS[flower["tier"]]
    return {"ok": True, "cost": cost, "flower": flower}


def merge_flowers(data: dict, flower_key: str) -> dict:
    """Слияние (эволюция): MERGE_COUNT одинаковых цветков -> 1 случайный
    цветок следующего тира (либо, с небольшим шансом, через тир — «прорыв»)."""
    g = ensure_garden(data)
    flower = FLOWERS_BY_KEY.get(flower_key)
    if not flower:
        return {"ok": False, "reason": "unknown_flower"}

    tier = flower["tier"]
    if tier >= TIER_MAX:
        return {"ok": False, "reason": "max_tier"}

    have = g["inventory"].get(flower_key, 0)
    if have < MERGE_COUNT:
        return {"ok": False, "reason": "not_enough", "need": MERGE_COUNT, "have": have}

    g["inventory"][flower_key] = have - MERGE_COUNT

    surge = tier <= TIER_MAX - 2 and random.random() < MERGE_SURGE_CHANCE
    result_tier = min(TIER_MAX, tier + (2 if surge else 1))
    result = random.choice(FLOWERS_BY_TIER[result_tier])

    _register_flower_gain(g, result["key"])
    g["stats"]["merges"] += 1
    if surge:
        g["stats"]["surges"] += 1

    grand_bloom = _check_grand_bloom(data, g)

    return {"ok": True, "consumed": flower, "result": result, "surge": surge, "grand_bloom": grand_bloom}


def sell_flower(data: dict, flower_key: str, count: int = 1) -> dict:
    g = ensure_garden(data)
    flower = FLOWERS_BY_KEY.get(flower_key)
    if not flower:
        return {"ok": False, "reason": "unknown_flower"}

    have = g["inventory"].get(flower_key, 0)
    if count <= 0 or have < count:
        return {"ok": False, "reason": "not_enough"}

    price = SELL_PRICE[flower["tier"]] * count
    g["inventory"][flower_key] = have - count
    data["balance"] = data.get("balance", 0) + price
    return {"ok": True, "coins": price, "count": count, "flower": flower}


def expand_garden(data: dict) -> dict:
    g = ensure_garden(data)
    if g["plot_count"] >= PLOT_MAX:
        return {"ok": False, "reason": "max_plots"}

    cost = plot_expand_cost(g["plot_count"] + 1)
    if data.get("balance", 0) < cost:
        return {"ok": False, "reason": "no_coins", "cost": cost}

    data["balance"] = data.get("balance", 0) - cost
    g["plot_count"] += 1
    g["plots"].append(None)
    return {"ok": True, "plot_count": g["plot_count"], "cost": cost}


# ──────────────────────────────────────────────────────────────
#  ТЕКСТЫ / КЛАВИАТУРЫ
#  (используются напрямую в хендлерах main.py, как case_status_text
#  и case_keyboard используются из case.py)
# ──────────────────────────────────────────────────────────────

def garden_text(data: dict) -> str:
    g = ensure_garden(data)
    lines = [
        '🌺 <b>МИСТИЧЕСКИЙ САД</b>',
        f'<blockquote>Выращивай цветки, собирай урожай и сливай по {MERGE_COUNT} '
        f'одинаковых, чтобы получить более редкий — от {TIER_ICON[1]} обычного '
        f'до {TIER_ICON[8]} изначального.</blockquote>',
        '',
        f'🪴 Грядок: <b>{g["plot_count"]}/{PLOT_MAX}</b>',
        f'💰 Баланс: <b>{format_amount(data.get("balance", 0))}</b>',
    ]
    return "\n".join(lines)


def _plot_button_label(idx: int, plot: dict | None) -> str:
    stage, progress, flower, left = plot_state(plot)
    if stage == "empty":
        return f"{idx + 1}. ➕ Пусто"
    if stage == "ready":
        return f"{idx + 1}. ✅ {flower_label(flower)}"
    pct = int(progress * 100)
    return f"{idx + 1}. {flower['emoji']} {pct}% ({_fmt_time(left)})"


def garden_keyboard(data: dict):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    g = ensure_garden(data)
    b = InlineKeyboardBuilder()
    for idx, plot in enumerate(g["plots"]):
        b.row(InlineKeyboardButton(
            text=_plot_button_label(idx, plot),
            callback_data=f"garden_plot:{idx}",
        ))
    b.row(
        InlineKeyboardButton(text="🎒 Инвентарь", callback_data="garden_inventory"),
        InlineKeyboardButton(text="➕ Расширить сад", callback_data="garden_expand"),
    )
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"))
    return b.as_markup()


def plot_detail_text(data: dict, plot_idx: int) -> str:
    g = ensure_garden(data)
    plot = g["plots"][plot_idx]
    stage, progress, flower, left = plot_state(plot)

    if stage == "empty":
        return (
            f'🪴 <b>Грядка №{plot_idx + 1}</b>\n'
            f'<blockquote>Грядка свободна. Посади семя.</blockquote>'
        )
    if stage == "ready":
        return (
            f'🪴 <b>Грядка №{plot_idx + 1}</b>\n'
            f'<blockquote>{flower_label(flower)} · {TIER_NAMES[flower["tier"]]}\n'
            f'<i>{flower["lore"]}</i>\n\n'
            f'✅ <b>Готов к сбору!</b></blockquote>'
        )
    return (
        f'🪴 <b>Грядка №{plot_idx + 1}</b>\n'
        f'<blockquote>{flower_label(flower)} · {TIER_NAMES[flower["tier"]]}\n'
        f'<i>{flower["lore"]}</i>\n\n'
        f'{_progress_bar(progress)} {int(progress * 100)}%\n'
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
        b.row(InlineKeyboardButton(
            text=f"⚡ Ускорить за {format_amount(cost)}",
            callback_data=f"garden_grow:{plot_idx}",
        ))
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="garden"))
    return b.as_markup()


def plant_menu_text(plot_idx: int) -> str:
    return (
        f'🌱 <b>Выбор семени — грядка №{plot_idx + 1}</b>\n'
        f'<blockquote>Обычные семена продаются за монеты. Семена более редких '
        f'цветков появляются в инвентаре только после слияния.</blockquote>'
    )


def plant_menu_keyboard(data: dict, plot_idx: int):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    g = ensure_garden(data)
    b = InlineKeyboardBuilder()

    for f in FLOWERS_BY_TIER[1]:
        b.row(InlineKeyboardButton(
            text=f'{flower_label(f)} — {format_amount(SEED_COST_TIER1)}',
            callback_data=f"garden_plant:{plot_idx}:{f['key']}",
        ))

    seed_keys = [k for k, cnt in g["inventory"].items() if cnt > 0 and FLOWERS_BY_KEY[k]["tier"] > 1]
    if seed_keys:
        b.row(InlineKeyboardButton(text="🎒 Посадить из инвентаря", callback_data=f"garden_plantinv:{plot_idx}"))

    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"garden_plot:{plot_idx}"))
    return b.as_markup()


def plant_inventory_keyboard(data: dict, plot_idx: int):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    g = ensure_garden(data)
    b = InlineKeyboardBuilder()
    for key, cnt in sorted(g["inventory"].items(), key=lambda kv: FLOWERS_BY_KEY[kv[0]]["tier"]):
        if cnt <= 0 or FLOWERS_BY_KEY[key]["tier"] == 1:
            continue
        f = FLOWERS_BY_KEY[key]
        b.row(InlineKeyboardButton(
            text=f'{flower_label(f)} ×{cnt}',
            callback_data=f"garden_plant:{plot_idx}:{key}",
        ))
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"garden_plantmenu:{plot_idx}"))
    return b.as_markup()


def inventory_text(data: dict) -> str:
    g = ensure_garden(data)
    have = {k: c for k, c in g["inventory"].items() if c > 0}
    if not have:
        return (
            '🎒 <b>Инвентарь сада</b>\n'
            '<blockquote>Пока пусто. Собери первый урожай!</blockquote>'
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
        f'Тир: <b>{TIER_ICON[tier]} {TIER_NAMES[tier]}</b>\n'
        f'В инвентаре: <b>×{cnt}</b>\n'
        f'Цена продажи: <b>{format_amount(SELL_PRICE[tier])}</b> за штуку</blockquote>',
    ]
    if tier < TIER_MAX:
        lines.append(
            f'<blockquote>🧬 Слей {MERGE_COUNT} шт., чтобы получить случайный цветок '
            f'тира «{TIER_NAMES[tier + 1]}» (есть небольшой шанс «прорыва» сразу на 2 тира выше).</blockquote>'
        )
    else:
        lines.append('<blockquote>🏆 Это высший тир сада — дальше эволюционировать некуда.</blockquote>')
    return "\n".join(lines)


def flower_detail_keyboard(data: dict, flower_key: str):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    g = ensure_garden(data)
    f = FLOWERS_BY_KEY[flower_key]
    cnt = g["inventory"].get(flower_key, 0)

    b = InlineKeyboardBuilder()
    if f["tier"] < TIER_MAX and cnt >= MERGE_COUNT:
        b.row(InlineKeyboardButton(text=f"🧬 Слить ({MERGE_COUNT} шт.)", callback_data=f"garden_merge:{flower_key}"))
    if cnt >= 1:
        b.row(
            InlineKeyboardButton(text="💰 Продать 1", callback_data=f"garden_sell:{flower_key}:1"),
            InlineKeyboardButton(text="💰 Продать всё", callback_data=f"garden_sell:{flower_key}:all"),
        )
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="garden_inventory"))
    return b.as_markup()
