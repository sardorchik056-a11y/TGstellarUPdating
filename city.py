# city.py — модуль "Арбитражный трейдинг" (география)
# Полностью отдельный модуль: своя БД-логика (в той же базе tgstellar.db),
# свои хендлеры, свои фоновые таски. Никак не пересекается с командами
# /profile, /shop, /inventory, /sell и т.д. из main.py — все команды здесь
# названы по-другому (с префиксом city), чтобы не было конфликтов.

import sqlite3
import random
import time
import asyncio
from datetime import datetime, timedelta, timezone, date

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import DB_PATH  # используем тот же файл БД, что и весь бот
from database import get_user as _db_get_user, update_user as _db_update_user
from database import get_user_by_id_or_username as _db_get_user_by_id_or_username
from database import aio_get_user as _aio_db_get_user
from database import aio_get_user_by_id_or_username as _aio_db_get_user_by_id_or_username
from database import format_amount as _db_format_amount

# Лог начислений/списаний кристаллов гильдии — нужен топу кристаллов
# (leaders_crystals.py), чтобы считать "сколько заработано за сегодня/
# вчера/неделю", а не только текущий баланс. Модуль не импортирует
# city.py обратно, поэтому цикла импорта нет.
from leaders_crystals import log_crystal_event

router = Router(name="city")

# Список админов продублирован здесь, чтобы не тянуть импорт из main.py
# (там уже импортируется city.py — циклический импорт).
CITY_ADMIN_IDS = {8118184388}

# ──────────────────────────────────────────────────────────────────────────
# ОГРАНИЧЕНИЕ ПО УРОВНЮ: город открывается только с CITY_MIN_LEVEL
# ──────────────────────────────────────────────────────────────────────────
CITY_MIN_LEVEL = 15


async def _city_level_gate(handler, event, data):
    """Закрывает весь раздел города игрокам ниже CITY_MIN_LEVEL уровня."""
    user = event.from_user
    if user is None:
        return await handler(event, data)

    if user.id in CITY_ADMIN_IDS:
        return await handler(event, data)

    main_user = await _aio_db_get_user(user.id)
    level = (main_user or {}).get("level", 1)

    if level < CITY_MIN_LEVEL:
        text = (
            f'<tg-emoji emoji-id="5334544901428229844">🌟</tg-emoji> <b><i>Город откроется на {CITY_MIN_LEVEL} уровне!</i></b>\n'
        )
        if isinstance(event, Message):
            await event.reply(text, parse_mode="HTML")
        elif isinstance(event, CallbackQuery):
            await event.answer(
                f'<tg-emoji emoji-id="5334544901428229844">🌟</tg-emoji> Город откроется на {CITY_MIN_LEVEL} уровне!',
                show_alert=True,
            )
        return

    return await handler(event, data)


router.message.middleware(_city_level_gate)
router.callback_query.middleware(_city_level_gate)

# ──────────────────────────────────────────────────────────────────────────
# КОНСТАНТЫ
# ──────────────────────────────────────────────────────────────────────────

CURRENCY_NAME = "кристаллы"
CURRENCY_NAME_SINGULAR = "кристалл"
CURRENCY_EMOJI = "💎"

CITIES = ["Северный", "Южный", "Столица"]

CITY_EMOJI = {
    "Северный": "🧊",
    "Южный": "🌴",
    "Столица": "🏛",
}

ITEMS = {
    "potions": {"name": "Зелья", "emoji": "🧪", "base": 10},
    "scrolls": {"name": "Свитки", "emoji": "📜", "base": 12},
    "food":    {"name": "Еда",    "emoji": "🍖", "base": 8},
    # ── Запретные свитки: контрабандный товар — дороже обычных свитков,
    # но таможня проверяет их особенно тщательно (см. ITEM_CUSTOMS_CHANCE).
    "forbidden_scrolls": {"name": "Запретные свитки", "emoji": "🔮", "base": 30},
    # ── Чёрная икра: скоропортящийся товар — теряет свежесть через
    # CAVIAR_FRESHNESS_SECONDS после покупки (см. get_inventory).
    "caviar": {"name": "Чёрная икра", "emoji": "🐟", "base": 45, "perishable": True},
}

# Модификаторы базовой цены по городам
CITY_MODIFIERS = {
    "Северный": {"potions": 0.7, "scrolls": 1.3, "food": 1.3, "forbidden_scrolls": 1.1, "caviar": 0.8},
    "Южный":    {"potions": 1.3, "scrolls": 0.7, "food": 0.7, "forbidden_scrolls": 0.8, "caviar": 1.3},
    "Столица":  {"potions": 1.2, "scrolls": 1.2, "food": 1.2, "forbidden_scrolls": 1.3, "caviar": 1.1},
}

# ──────────────────────────────────────────────────────────────────────────
# ID КАСТОМНЫХ ЭМОДЗИ ДЛЯ КНОПОК
# Сюда вставить реальные icon_custom_emoji_id вместо None
# ──────────────────────────────────────────────────────────────────────────
BTN_EMOJI = {
    "market": "5278702045883292456",         # 🏪 Рынок
    "bag": "5848184700396376824",             # 🎒 Сумка
    "travel": "5208964438559835776",          # 🧭 Путешествие
    "route": "5361768641828240505",            # 🗺 Маршрут
    "news": "5307747174539338142",              # 🗞 Новости
    "help": "5452069934089641166",              # ❓ Помощь
    "home": "5422765062991389606",              # 🏠 В главное меню
    "cancel_travel": "5907027122446145395",     # ❌ Отменить поездку
    "city_north": "5422721344519299183",        # 🧊 Северный
    "city_south": "5208964438559835776",        # 🌴 Южный
    "city_capital": "5424887227807188349",      # 🏛 Столица
    "balance": "5224257782013769471",           # баланс
    "currency": "5427168083074628963",          # кристаллы
    "customs": "5859243644183124239",           # таможня / гильдия магов
    "buy": "5312361253610475399",               # покупка
    "sell": "5429518319243775957",              # продажа
    "status": "5400362079783770689",            # статус
    "exchange": "5402186569006210455",          # 🔁 Обмен
    "cart": "6334399977833366867",               # 🐎 Повозка
    "warehouse": "5337023862062208549",                            # 📦 Склад — вставить реальный icon_custom_emoji_id
    "defense": "6050643982646513651",           # 🛡 Защита от таможни
    "capsules": "5217620305194800391",          # 🔮 Капсулы усиления
}

# ──────────────────────────────────────────────────────────────────────────
# КАСТОМНЫЕ ЭМОДЗИ СТАТУСОВ (переиспользованы из miner.py — тот же набор
# premium-эмодзи, что и в магазине кирок/длительностей шахты). Используем
# одинаковую логику отображения состояний "заблокировано / куплено /
# активно" везде в боте, чтобы UI был единообразным.
# ──────────────────────────────────────────────────────────────────────────
EMOJI_LOCKED   = "5240241223632954241"   # 🔒 ещё не куплено
EMOJI_OWNED    = "5391032818111363540"   # 📦 куплено, но не активировано / не выбрано
EMOJI_ACTIVE   = "5206607081334906820"   # ✅ выбрано / активно сейчас
EMOJI_BACK_ARR = "6039539366177541657"   # ⬅️ назад
EMOJI_BUY_BTN  = "5199552030615558774"   # 🪙 купить (кнопка с ценой)
EMOJI_CRYSTAL_BUY = "5427168083074628963"  # 💎 купить за кристаллы (капсулы) — тот же id, что и currency
EMOJI_USE_BTN  = "5397916757333654639"   # ✨ использовать / выбрать
EMOJI_PICKAXE  = "5197371802136892976"   # ⛏ капсулы добычи


def _stat_tge(emoji_id: str, fallback: str) -> str:
    """Тег кастомного emoji по «сырому» id (не из BTN_EMOJI), с фолбэком."""
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'

TRAVEL_COST = 50
TRAVEL_MINUTES = 15
TRAVEL_CANCEL_WINDOW = 120  # сек. — в течение скольких секунд после старта можно отменить поездку
CUSTOMS_LIMIT = 200          # лимит единиц товара, выше которого возможна конфискация
CUSTOMS_CHANCE = 0.30        # базовый шанс конфискации (для обычных товаров)
CUSTOMS_FINE = 50

# ── Индивидуальный шанс конфискации по товарам. Если товара нет в словаре —
# используется базовый CUSTOMS_CHANCE. Запретные свитки — контрабанда,
# гильдия магов проверяет её вдвое тщательнее.
ITEM_CUSTOMS_CHANCE = {
    "forbidden_scrolls": 0.50,
}

# ── Свежесть чёрной икры: через столько секунд после покупки товар портится
# и автоматически изымается (протухший товар не хранится и не провозится).
CAVIAR_FRESHNESS_SECONDS = 20 * 60  # 20 минут

# ──────────────────────────────────────────────────────────────────────────
# МАГАЗИН ЗАЩИТЫ ОТ ТАМОЖНИ
# Три вида защиты, снижающие шанс конфискации. Эффекты не складываются
# наивно — фальшивые документы и сопровождение вместе дают отдельное,
# меньшее чем сумма, совместное снижение; охрана добавляется поверх.
# Итоговый шанс конфискации никогда не опускается ниже MIN_CUSTOMS_CHANCE
# (при покупке всех трёх защит шанс падает ровно до этого минимума).
# ──────────────────────────────────────────────────────────────────────────
MIN_CUSTOMS_CHANCE = 0.15    # минимальный шанс конфискации даже с максимальной защитой

FAKE_DOCS_COST = 15_000_000       # фальшивые документы
FAKE_DOCS_REDUCTION = 0.15

ESCORT_COST = 50_000_000          # сопроводительное письмо
ESCORT_REDUCTION = 0.25

FAKE_DOCS_AND_ESCORT_REDUCTION = 0.30   # совместный эффект (вместо наивных 0.15+0.25=0.40)

SECURITY_COST = 8_000_000         # охрана каравана
SECURITY_REDUCTION = 0.10

# ──────────────────────────────────────────────────────────────────────────
# КАПСУЛЫ УСИЛЕНИЯ
# 3 категории по 5 капсул (15 всего). Каждая капсула — постоянный множитель,
# который вступает в силу при активации ("использовании") и держится, пока
# игрок не активирует другую капсулу той же категории (тогда старая
# заменяется — активна всегда максимум ОДНА капсула на категорию,
# использовать сразу несколько капсул одной категории нельзя).
# Множители одинаковы для всех трёх категорий (I→V: 1.15×...2.00×),
# цены растут от 100 млн до 15 млрд кристаллов.
# ──────────────────────────────────────────────────────────────────────────
CAPSULE_ROMAN = ["I", "II", "III", "IV", "V"]
CAPSULE_TIER_MULT = [1.15, 1.35, 1.55, 1.80, 2.00]
CAPSULE_TIER_PRICE = [100_000_000, 500_000_000, 2_000_000_000, 6_000_000_000, 15_000_000_000]

CAPSULE_CATEGORIES = {
    "mining": {
        "title": "Капсулы добычи",
        "emoji": _stat_tge(EMOJI_PICKAXE, "⛏"),
        "noun": "добычи",
        "effect": "увеличивает добычу руды в шахте",
        "flavor": "Алхимический состав ускоряет резонанс кирки с рудной жилой — "
                   "с каждой партией из недр поднимается больше породы.",
    },
    "damage": {
        "title": "Капсулы урона",
        "emoji": "⚔️",
        "noun": "урона",
        "effect": "увеличивает урон в бою",
        "flavor": "Концентрат боевых трав разгоняет кровь и обостряет реакцию — "
                   "удары становятся тяжелее и точнее.",
    },
    "pets": {
        "title": "Капсулы питомцев",
        "emoji": "🐾",
        "noun": "питомцев",
        "effect": "увеличивает силу питомцев",
        "flavor": "Питательная эссенция, выведенная зверинцем гильдии — "
                   "любимец растёт сильнее и выносливее.",
    },
}


def _build_capsules() -> dict:
    capsules = {}
    for category, info in CAPSULE_CATEGORIES.items():
        for i in range(5):
            cid = f"{category}_{i + 1}"
            capsules[cid] = {
                "category": category,
                "tier": i + 1,
                "name": f"Капсула {info['noun']} {CAPSULE_ROMAN[i]}",
                "mult": CAPSULE_TIER_MULT[i],
                "price": CAPSULE_TIER_PRICE[i],
            }
    return capsules


CAPSULES = _build_capsules()

# ── ПОВОЗКА: лимит суммарного количества товара, который можно везти за раз ──
# Уровень 0 — базовая повозка, доступна всем бесплатно. Дальше — платная
# прокачка за кристаллы вплоть до максимума в 1 000 000 единиц товара.
# capacity — новый суммарный лимит (сумма ВСЕХ товаров в сумке одновременно),
# cost — сколько кристаллов стоит апгрейд именно ДО этого уровня (т.е. это
# цена перехода с предыдущего уровня на этот).
CART_LEVELS = [
    {"level": 0, "capacity": 50_000,    "cost": 0,       "name": "Телега"},
    {"level": 1, "capacity": 150_000,   "cost": 8_000,   "name": "Гружёная телега"},
    {"level": 2, "capacity": 300_000,   "cost": 20_000,  "name": "Малый караван"},
    {"level": 3, "capacity": 500_000,   "cost": 45_000,  "name": "Большой караван"},
    {"level": 4, "capacity": 700_000,   "cost": 80_000,  "name": "Купеческий обоз"},
    {"level": 5, "capacity": 1_000_000, "cost": 150_000, "name": "Королевский обоз"},
]
CART_MAX_LEVEL = len(CART_LEVELS) - 1

# ── СКЛАД: лимит ОБЩЕГО количества товара, которое можно ХРАНИТЬ (не путать
# с повозкой — та ограничивает, сколько можно ВЕЗТИ за одну поездку). Это
# отдельная механика хранения: если покупка превысит вместимость склада,
# купить нельзя, даже если места в повозке достаточно.
# Уровень 0 — базовый склад, доступен всем бесплатно. Дальше — платная
# прокачка за кристаллы, всего 10 уровней (9 платных), от 10 000 до
# 10 000 000 кристаллов, вместимость от 10 000 до 10 000 000 товаров.
WAREHOUSE_LEVELS = [
    {"level": 0, "capacity": 10_000,     "cost": 0,          "name": "Сарай"},
    {"level": 1, "capacity": 25_000,     "cost": 10_000,     "name": "Погреб"},
    {"level": 2, "capacity": 60_000,     "cost": 30_000,     "name": "Малый склад"},
    {"level": 3, "capacity": 150_000,    "cost": 80_000,     "name": "Склад"},
    {"level": 4, "capacity": 350_000,    "cost": 200_000,    "name": "Большой склад"},
    {"level": 5, "capacity": 800_000,    "cost": 500_000,    "name": "Пакгауз"},
    {"level": 6, "capacity": 1_800_000,  "cost": 1_200_000,  "name": "Хранилище"},
    {"level": 7, "capacity": 3_500_000,  "cost": 2_800_000,  "name": "Логистический центр"},
    {"level": 8, "capacity": 6_000_000,  "cost": 5_500_000,  "name": "Мега-хаб"},
    {"level": 9, "capacity": 10_000_000, "cost": 10_000_000, "name": "Имперское хранилище"},
]
WAREHOUSE_MAX_LEVEL = len(WAREHOUSE_LEVELS) - 1

# ── Кнопочная покупка через меню склада: набор количеств для быстрого выбора.
WAREHOUSE_BUY_QTY_OPTIONS = [10, 50, 100, 500, 1000, 5000]

NEWS_TRUE_CHANCE = 0.60      # вероятность, что подсказка сбудется
NEWS_LIFETIME_HOURS = 2

START_BALANCE = 500          # стартовый баланс кристаллов
START_CITY = "Столица"

DAILY_CRYSTALS = 100         # сколько кристаллов выдаётся раз в день

# ── ОБМЕН: кристаллы → монеты (только в одну сторону, обратно купить нельзя) ──
EXCHANGE_MIN_RATE = 100        # минимальный курс (монет за 1 кристалл)
EXCHANGE_MAX_RATE = 500        # максимальный курс (монет за 1 кристалл)
EXCHANGE_WINDOW_SECONDS = 600  # окно анализа активности рынка (10 минут)
EXCHANGE_VOLUME_TARGET = 100   # объём покупок в окне, после которого курс максимален
EXCHANGE_JITTER = 15           # случайное колебание курса (±)
EXCHANGE_RECALC_SECONDS = 60   # как часто пересчитывается курс фоновой задачей
EXCHANGE_PER_USER_CAP = 4       # макс. объём ОДНОГО игрока, который учитывается в расчёте курса
                                 # (защита от накрутки курса одним игроком). При EXCHANGE_VOLUME_TARGET=100
                                 # курс достигает максимума только если активно покупают 25+ разных игроков
                                 # (100 / 4 = 25), даже если каждый из них купит сколько угодно товара.

COIN_EMOJI_ID = "5199552030615558774"
COIN_TAG = f'<tg-emoji emoji-id="{COIN_EMOJI_ID}">🪙</tg-emoji>'

ALIAS_TO_ITEM = {
    "зелья": "potions", "зелье": "potions", "potions": "potions", "potion": "potions",
    "свитки": "scrolls", "свиток": "scrolls", "scrolls": "scrolls", "scroll": "scrolls",
    "еда": "food", "food": "food",
    "запретные свитки": "forbidden_scrolls", "запретный свиток": "forbidden_scrolls",
    "запретныесвитки": "forbidden_scrolls", "запретныйсвиток": "forbidden_scrolls",
    "запретный": "forbidden_scrolls", "forbidden_scrolls": "forbidden_scrolls",
    "forbidden": "forbidden_scrolls",
    "черная икра": "caviar", "чёрная икра": "caviar", "чернаяикра": "caviar",
    "чёрнаяикра": "caviar", "икра": "caviar", "caviar": "caviar",
}
ALIAS_TO_CITY = {
    "северный": "Северный", "север": "Северный", "north": "Северный",
    "южный": "Южный", "юг": "Южный", "south": "Южный",
    "столица": "Столица", "capital": "Столица",
}


def _tge(key: str, fallback: str) -> str:
    """Возвращает <tg-emoji> тег с кастомным id, либо обычный эмодзи если id не задан."""
    eid = BTN_EMOJI.get(key)
    if not eid:
        return fallback
    return f'<tg-emoji emoji-id="{eid}">{fallback}</tg-emoji>'


# Кастомные эмодзи для товаров (ключ — item_type из ITEMS). Используются
# только в HTML-сообщениях (message.reply/edit_text) — в алертах
# call.answer(show_alert=True) кастомные эмодзи не отображаются, поэтому
# там нужно использовать ITEMS[item]['emoji'] напрямую, без этой обёртки.
ITEM_EMOJI_ID = {
    "forbidden_scrolls": "5397797168264260168",
    "caviar": "5920188899400879760",
}


def _item_emoji(item_type: str) -> str:
    """Тег кастомного эмодзи для товара, либо обычный эмодзи из ITEMS, если id не задан."""
    fallback = ITEMS[item_type]["emoji"]
    eid = ITEM_EMOJI_ID.get(item_type)
    if not eid:
        return fallback
    return f'<tg-emoji emoji-id="{eid}">{fallback}</tg-emoji>'


CITY_TGE_KEY = {
    "Северный": "city_north",
    "Южный": "city_south",
    "Столица": "city_capital",
}


def _city_emoji_tag(city: str) -> str:
    return _tge(CITY_TGE_KEY.get(city, ""), CITY_EMOJI.get(city, "🏙"))

# ──────────────────────────────────────────────────────────────────────────
# БД
# ──────────────────────────────────────────────────────────────────────────

from contextlib import contextmanager as _contextmanager

def _get_raw_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.row_factory = sqlite3.Row
    return conn


@_contextmanager
def _conn():
    # timeout=30 + busy_timeout — согласовано с database.py, чтобы это
    # соединение вело себя предсказуемо на общем файле БД (раньше был
    # дефолтный таймаут sqlite3 — 5 сек — что давало более частые
    # "database is locked" при конкуренции с остальными модулями).
    #
    # ВАЖНО: раньше это была обычная функция, а не контекст-менеджер —
    # `with _conn() as conn:` у голого sqlite3.Connection управляет ТОЛЬКО
    # транзакцией (commit/rollback), но НЕ закрывает соединение. Ни в одном
    # из ~27 мест в этом файле close() не вызывался — при активных фоновых
    # циклах города (city_prices_loop и т.д.) это постепенно копило
    # открытые fd на tgstellar.db. Теперь закрытие гарантировано в finally,
    # использование в коде не меняется.
    conn = _get_raw_conn()
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_city_db():
    """Создаёт все таблицы модуля. Вызвать один раз при старте бота."""
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS city_users (
                user_id        INTEGER PRIMARY KEY,
                username       TEXT,
                balance        INTEGER NOT NULL DEFAULT 50,
                city           TEXT NOT NULL DEFAULT 'Столица',
                status         TEXT NOT NULL DEFAULT 'free',
                travel_end_time INTEGER,
                travel_from    TEXT
            )
        """)
        # Миграция для уже существующих баз — добавляем колонку travel_from,
        # если её ещё нет (нужна, чтобы знать, куда вернуть игрока при отмене поездки).
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(city_users)").fetchall()]
        if "travel_from" not in cols:
            conn.execute("ALTER TABLE city_users ADD COLUMN travel_from TEXT")
        if "last_daily" not in cols:
            conn.execute("ALTER TABLE city_users ADD COLUMN last_daily TEXT")
        if "cart_level" not in cols:
            conn.execute("ALTER TABLE city_users ADD COLUMN cart_level INTEGER NOT NULL DEFAULT 0")
        if "warehouse_level" not in cols:
            conn.execute("ALTER TABLE city_users ADD COLUMN warehouse_level INTEGER NOT NULL DEFAULT 0")
        # Магазин защиты от таможни — три независимых флага защиты.
        if "has_fake_docs" not in cols:
            conn.execute("ALTER TABLE city_users ADD COLUMN has_fake_docs INTEGER NOT NULL DEFAULT 0")
        if "has_escort" not in cols:
            conn.execute("ALTER TABLE city_users ADD COLUMN has_escort INTEGER NOT NULL DEFAULT 0")
        if "has_security" not in cols:
            conn.execute("ALTER TABLE city_users ADD COLUMN has_security INTEGER NOT NULL DEFAULT 0")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS city_inventory (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER NOT NULL,
                item_type TEXT NOT NULL,
                quantity  INTEGER NOT NULL DEFAULT 0,
                UNIQUE(user_id, item_type)
            )
        """)
        # ── Склад — ОТДЕЛЬНОЕ хранилище от сумки/повозки (city_inventory).
        # Товар не "продаётся"/"покупается" при перекладке — он физически
        # переезжает между двумя таблицами (см. try_deposit_to_warehouse /
        # try_withdraw_from_warehouse). Лимит склада (get_warehouse_capacity)
        # теперь считается от суммы именно этой таблицы, а не от сумки.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS city_warehouse (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER NOT NULL,
                item_type TEXT NOT NULL,
                quantity  INTEGER NOT NULL DEFAULT 0,
                UNIQUE(user_id, item_type)
            )
        """)
        # Миграция: колонка для отслеживания свежести скоропортящихся товаров
        # (используется чёрной икрой) — timestamp последней "свежей" покупки.
        inv_cols = [r["name"] for r in conn.execute("PRAGMA table_info(city_inventory)").fetchall()]
        if "acquired_at" not in inv_cols:
            conn.execute("ALTER TABLE city_inventory ADD COLUMN acquired_at INTEGER")
        # ── Капсулы усиления: купленный, но ещё не использованный запас ──
        conn.execute("""
            CREATE TABLE IF NOT EXISTS city_capsules_owned (
                user_id    INTEGER NOT NULL,
                capsule_id TEXT NOT NULL,
                quantity   INTEGER NOT NULL DEFAULT 0,
                UNIQUE(user_id, capsule_id)
            )
        """)
        # ── Капсулы усиления: активная (использованная) капсула по категориям —
        # ровно одна запись на пару (user_id, category), т.е. максимум одна
        # активная капсула на категорию одновременно.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS city_capsules_active (
                user_id      INTEGER NOT NULL,
                category     TEXT NOT NULL,
                capsule_id   TEXT NOT NULL,
                activated_at INTEGER NOT NULL,
                UNIQUE(user_id, category)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS city_prices (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                city          TEXT NOT NULL,
                item_type     TEXT NOT NULL,
                price         INTEGER NOT NULL,
                buy_count     INTEGER NOT NULL DEFAULT 0,
                sell_count    INTEGER NOT NULL DEFAULT 0,
                last_updated  INTEGER,
                UNIQUE(city, item_type)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS city_trade_news (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                news_text         TEXT NOT NULL,
                city              TEXT NOT NULL,
                item_type         TEXT NOT NULL,
                predicted_change  TEXT NOT NULL,
                will_come_true    INTEGER NOT NULL,
                created_at        INTEGER NOT NULL,
                expires_at        INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS city_trade_log (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                ts        INTEGER NOT NULL,
                action    TEXT NOT NULL,
                qty       INTEGER NOT NULL,
                user_id   INTEGER
            )
        """)
        # Миграция: добавляем user_id, если таблица создана старой версией кода —
        # без него нельзя отличить покупки одного игрока от покупок многих игроков.
        log_cols = [r["name"] for r in conn.execute("PRAGMA table_info(city_trade_log)").fetchall()]
        if "user_id" not in log_cols:
            conn.execute("ALTER TABLE city_trade_log ADD COLUMN user_id INTEGER")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS city_meta (
                key   TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()

    # первичная генерация цен, если их ещё нет
    with _conn() as conn:
        for city in CITIES:
            for item in ITEMS:
                row = conn.execute(
                    "SELECT id FROM city_prices WHERE city=? AND item_type=?",
                    (city, item),
                ).fetchone()
                if not row:
                    price = _roll_price(city, item)
                    conn.execute(
                        "INSERT INTO city_prices (city, item_type, price, last_updated) "
                        "VALUES (?,?,?,?)",
                        (city, item, price, int(time.time())),
                    )
        conn.commit()


def _roll_price(city: str, item: str) -> int:
    base = ITEMS[item]["base"]
    mod = CITY_MODIFIERS[city][item]
    rand_coef = random.uniform(0.8, 1.2)
    return max(1, round(base * mod * rand_coef))


# ---------- пользователи ----------

def get_city_user(user_id: int, username: str = "") -> dict:
    today = date.today().isoformat()
    with _conn() as conn:
        row = conn.execute("SELECT * FROM city_users WHERE user_id=?", (user_id,)).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO city_users (user_id, username, balance, city, status, travel_end_time, last_daily) "
                "VALUES (?,?,?,?,?,NULL,?)",
                (user_id, username or "", START_BALANCE, START_CITY, "free", today),
            )
            for item in ITEMS:
                conn.execute(
                    "INSERT OR IGNORE INTO city_inventory (user_id, item_type, quantity) VALUES (?,?,0)",
                    (user_id, item),
                )
            conn.commit()
            row = conn.execute("SELECT * FROM city_users WHERE user_id=?", (user_id,)).fetchone()
            return dict(row)

    u = dict(row)
    # ── Ежедневный бонус кристаллов (атомарно и идемпотентно — раз в день) ──
    # Условие на last_daily проверяется прямо в WHERE, поэтому даже если два
    # запроса от одного игрока придут одновременно, бонус начислится один раз.
    if u.get("last_daily") != today:
        with _conn() as conn:
            cur = conn.execute(
                "UPDATE city_users SET balance = balance + ?, last_daily=? "
                "WHERE user_id=? AND (last_daily IS NULL OR last_daily<>?)",
                (DAILY_CRYSTALS, today, user_id, today),
            )
            conn.commit()
            if cur.rowcount:
                row = conn.execute("SELECT * FROM city_users WHERE user_id=?", (user_id,)).fetchone()
                u = dict(row)
                log_crystal_event(user_id, DAILY_CRYSTALS)
    return u


def update_city_user(user_id: int, **fields):
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields)
    vals = list(fields.values()) + [user_id]
    with _conn() as conn:
        conn.execute(f"UPDATE city_users SET {sets} WHERE user_id=?", vals)
        conn.commit()


def claim_travel_slot(user_id: int, dest: str, origin_city: str, end_time: int) -> bool:
    """Атомарно переводит игрока в статус 'traveling' ОДНИМ запросом с условием
    status='free' в WHERE. Это единственная точка входа в поездку — вызывается
    ДО списания денег и ДО броска таможни, поэтому повторный/параллельный клик
    (двойной тап, ретрай апдейта от Telegram) не может пройти дальше одного раза
    и, как следствие, не может дать два независимых броска конфискации на один
    и тот же товар. True — слот успешно захвачен этим вызовом."""
    with _conn() as conn:
        cur = conn.execute(
            "UPDATE city_users SET status='traveling', travel_end_time=?, "
            "city=?, travel_from=? WHERE user_id=? AND status='free'",
            (end_time, dest, origin_city, user_id),
        )
        conn.commit()
        return cur.rowcount > 0


def release_travel_slot(user_id: int, origin_city: str):
    """Откатывает claim_travel_slot, если после захвата слота выяснилось, что
    поездку продолжить нельзя (например, не хватило денег на дорогу)."""
    with _conn() as conn:
        conn.execute(
            "UPDATE city_users SET status='free', travel_end_time=NULL, "
            "travel_from=NULL, city=? WHERE user_id=?",
            (origin_city, user_id),
        )
        conn.commit()


def add_crystals_to_all(amount: int) -> int:
    """Начисляет всем существующим пользователям города указанное количество
    кристаллов. Возвращает количество затронутых пользователей."""
    with _conn() as conn:
        ids = [r["user_id"] for r in conn.execute("SELECT user_id FROM city_users").fetchall()]
        cur = conn.execute("UPDATE city_users SET balance = balance + ?", (amount,))
        conn.commit()
    for uid in ids:
        log_crystal_event(uid, amount)
    return cur.rowcount


def add_crystals_to_user(user_id: int, amount: int, username: str = "") -> int:
    """Начисляет кристаллы одному пользователю города (по user_id).
    Если у игрока ещё нет записи в городе — создаёт её.
    Возвращает новый баланс."""
    get_city_user(user_id, username)  # гарантируем, что запись существует
    with _conn() as conn:
        conn.execute(
            "UPDATE city_users SET balance = balance + ? WHERE user_id=?",
            (amount, user_id),
        )
        conn.commit()
        row = conn.execute("SELECT balance FROM city_users WHERE user_id=?", (user_id,)).fetchone()
    log_crystal_event(user_id, amount)
    return row["balance"] if row else 0


def get_inventory(user_id: int) -> dict:
    _spoil_expired_perishables(user_id)
    with _conn() as conn:
        rows = conn.execute(
            "SELECT item_type, quantity FROM city_inventory WHERE user_id=?", (user_id,)
        ).fetchall()
    inv = {item: 0 for item in ITEMS}
    for r in rows:
        inv[r["item_type"]] = r["quantity"]
    return inv


def _spoil_expired_perishables(user_id: int):
    """Проверяет скоропортящиеся товары (сейчас — только чёрная икра) и
    обнуляет их, если с момента покупки прошло больше CAVIAR_FRESHNESS_SECONDS.
    Вызывается лениво из get_inventory, поэтому испорченный товар исчезает
    сам собой при любом обращении к инвентарю (покупка, продажа, поездка,
    просмотр сумки/склада) — отдельный фоновый цикл не нужен."""
    now = int(time.time())
    perishable_items = [k for k, v in ITEMS.items() if v.get("perishable")]
    if not perishable_items:
        return
    with _conn() as conn:
        placeholders = ",".join("?" * len(perishable_items))
        rows = conn.execute(
            f"SELECT item_type, quantity, acquired_at FROM city_inventory "
            f"WHERE user_id=? AND item_type IN ({placeholders}) AND quantity>0",
            (user_id, *perishable_items),
        ).fetchall()
        for r in rows:
            if r["acquired_at"] and now - r["acquired_at"] > CAVIAR_FRESHNESS_SECONDS:
                conn.execute(
                    "UPDATE city_inventory SET quantity=0 "
                    "WHERE user_id=? AND item_type=? AND quantity=?",
                    (user_id, r["item_type"], r["quantity"]),
                )
        conn.commit()


def refresh_item_freshness(user_id: int, item_type: str):
    """Обновляет таймер свежести товара (вызывается при каждой покупке
    скоропортящегося товара — новая партия считается свежей целиком)."""
    with _conn() as conn:
        conn.execute(
            "UPDATE city_inventory SET acquired_at=? WHERE user_id=? AND item_type=?",
            (int(time.time()), user_id, item_type),
        )
        conn.commit()


def get_item_freshness_left(user_id: int, item_type: str) -> int | None:
    """Секунд до порчи товара, или None если товар не портится, отсутствует
    в инвентаре, либо уже испорчен/списан."""
    if not ITEMS.get(item_type, {}).get("perishable"):
        return None
    _spoil_expired_perishables(user_id)
    with _conn() as conn:
        row = conn.execute(
            "SELECT quantity, acquired_at FROM city_inventory WHERE user_id=? AND item_type=?",
            (user_id, item_type),
        ).fetchone()
    if not row or row["quantity"] <= 0 or not row["acquired_at"]:
        return None
    left = CAVIAR_FRESHNESS_SECONDS - (int(time.time()) - row["acquired_at"])
    return max(0, left)


def set_inventory_qty(user_id: int, item_type: str, qty: int):
    """Жёстко выставляет количество товара. ВНИМАНИЕ: не атомарна относительно
    параллельных изменений — для покупки/продажи использовать try_adjust_inventory."""
    with _conn() as conn:
        conn.execute(
            "INSERT INTO city_inventory (user_id, item_type, quantity) VALUES (?,?,?) "
            "ON CONFLICT(user_id, item_type) DO UPDATE SET quantity=excluded.quantity",
            (user_id, item_type, max(0, qty)),
        )
        conn.commit()


# ---------- атомарные операции с балансом и инвентарём ----------
# Все изменения баланса/количества товара идут через эти функции:
# проверка и запись делаются ОДНИМ SQL-запросом с условием в WHERE,
# поэтому два параллельных запроса (двойной тап, повтор доставки апдейта
# от Telegram, рестарт во время обработки и т.п.) не могут списать/начислить
# дважды или увести значение в минус.

def try_spend_balance(user_id: int, amount: int) -> bool:
    """Атомарно списывает `amount` кристаллов, если их хватает. True — списано."""
    if amount <= 0:
        return True
    with _conn() as conn:
        cur = conn.execute(
            "UPDATE city_users SET balance = balance - ? WHERE user_id=? AND balance>=?",
            (amount, user_id, amount),
        )
        conn.commit()
        ok = cur.rowcount > 0
        if ok:
            log_crystal_event(user_id, -amount)
        return ok


def add_balance(user_id: int, amount: int):
    """Атомарно прибавляет (или, если amount<0, списывает без проверки) кристаллы.
    Используется для зачислений и для отката ранее списанной суммы."""
    if amount == 0:
        return
    with _conn() as conn:
        conn.execute(
            "UPDATE city_users SET balance = balance + ? WHERE user_id=?",
            (amount, user_id),
        )
        conn.commit()
    log_crystal_event(user_id, amount)


def spend_up_to(user_id: int, amount: int):
    """Атомарно списывает `amount`, но не уводит баланс в минус — если средств
    не хватает, баланс просто зануляется. Используется для штрафов таможни."""
    if amount <= 0:
        return
    with _conn() as conn:
        row = conn.execute("SELECT balance FROM city_users WHERE user_id=?", (user_id,)).fetchone()
        before = row["balance"] if row else 0
        conn.execute(
            "UPDATE city_users SET balance = CASE WHEN balance>=? THEN balance-? ELSE 0 END "
            "WHERE user_id=?",
            (amount, amount, user_id),
        )
        conn.commit()
    actually_taken = min(amount, before)
    if actually_taken:
        log_crystal_event(user_id, -actually_taken)


def try_adjust_inventory(user_id: int, item_type: str, delta: int) -> bool:
    """Атомарно меняет количество товара на delta (может быть отрицательным).
    Не даёт уйти в минус. Если строки инвентаря ещё нет (например, у старого
    аккаунта, зарегистрированного до появления этого товара) — создаёт её
    перед изменением, иначе UPDATE молча не найдёт строку и ничего не
    изменит, даже если деньги уже списаны. True — изменение применено."""
    if delta == 0:
        return True
    with _conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO city_inventory (user_id, item_type, quantity) VALUES (?,?,0)",
            (user_id, item_type),
        )
        cur = conn.execute(
            "UPDATE city_inventory SET quantity = quantity + ? "
            "WHERE user_id=? AND item_type=? AND quantity + ? >= 0",
            (delta, user_id, item_type, delta),
        )
        conn.commit()
        return cur.rowcount > 0


# ---------- покупка/продажа на рынке — ОДНА транзакция на сделку ----------
# В отличие от try_spend_balance + try_adjust_inventory по отдельности
# (каждый — своё соединение, свой commit, с компенсацией отката вручную,
# если второй шаг не удался), здесь баланс и инвентарь меняются на ОДНОМ
# соединении и коммитятся ОДНИМ commit. Это закрывает не только гонки
# (двойной тап, повтор апдейта от Telegram), но и падение самого процесса
# (kill, OOM, обрыв контейнера) ровно между списанием денег и начислением
# товара — в отличие от компенсации, здесь такого промежутка физически нет:
# до commit изменения не видны и не сохранены, при сбое SQLite/WAL откатывает
# оба изменения сразу, при успехе — оба применяются сразу.

def try_buy_item(user_id: int, item_type: str, qty: int, total_cost: int) -> bool:
    """Атомарно: списывает total_cost кристаллов И начисляет qty товара —
    либо применяются оба изменения, либо ни одного. True — сделка прошла."""
    if qty <= 0:
        return False
    if total_cost < 0:
        return False
    with _conn() as conn:
        cur = conn.execute(
            "UPDATE city_users SET balance = balance - ? WHERE user_id=? AND balance>=?",
            (total_cost, user_id, total_cost),
        )
        if cur.rowcount == 0:
            return False  # средств не хватило — ничего не менялось, коммитить нечего
        conn.execute(
            "INSERT OR IGNORE INTO city_inventory (user_id, item_type, quantity) VALUES (?,?,0)",
            (user_id, item_type),
        )
        conn.execute(
            "UPDATE city_inventory SET quantity = quantity + ? WHERE user_id=? AND item_type=?",
            (qty, user_id, item_type),
        )
        conn.commit()
    if total_cost:
        log_crystal_event(user_id, -total_cost)
    return True


def try_sell_item(user_id: int, item_type: str, qty: int, total_gain: int) -> bool:
    """Атомарно: списывает qty товара И начисляет total_gain кристаллов —
    либо применяются оба изменения, либо ни одного. True — сделка прошла."""
    if qty <= 0:
        return False
    with _conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO city_inventory (user_id, item_type, quantity) VALUES (?,?,0)",
            (user_id, item_type),
        )
        cur = conn.execute(
            "UPDATE city_inventory SET quantity = quantity - ? "
            "WHERE user_id=? AND item_type=? AND quantity>=?",
            (qty, user_id, item_type, qty),
        )
        if cur.rowcount == 0:
            return False  # товара не хватило — INSERT OR IGNORE выше безвреден, коммитить больше нечего
        conn.execute(
            "UPDATE city_users SET balance = balance + ? WHERE user_id=?",
            (total_gain, user_id),
        )
        conn.commit()
    if total_gain:
        log_crystal_event(user_id, total_gain)
    return True


def force_confiscate_inventory(user_id: int, item_type: str) -> int:
    """Атомарно обнуляет товар (конфискация на таможне).
    Возвращает количество, которое реально было изъято (0, если и так пусто)."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT quantity FROM city_inventory WHERE user_id=? AND item_type=?",
            (user_id, item_type),
        ).fetchone()
        qty = row["quantity"] if row else 0
        if qty > 0:
            cur = conn.execute(
                "UPDATE city_inventory SET quantity=0 "
                "WHERE user_id=? AND item_type=? AND quantity=?",
                (user_id, item_type, qty),
            )
            conn.commit()
            return qty if cur.rowcount else 0
        return 0


# ---------- склад — отдельное хранилище (city_warehouse) ----------
# В отличие от сумки/повозки (city_inventory), товар на складе не участвует
# в таможенных проверках и не тратится при поездках — он просто лежит,
# пока игрок не заберёт его обратно кнопкой «Забрать со склада». Деньги
# нигде не участвуют: это перекладка одного и того же товара между двумя
# хранилищами, а не покупка/продажа.

def get_warehouse_stock(user_id: int) -> dict:
    """Содержимое СКЛАДА (не сумки!) — отдельная таблица city_warehouse."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT item_type, quantity FROM city_warehouse WHERE user_id=?", (user_id,)
        ).fetchall()
    stock = {item: 0 for item in ITEMS}
    for r in rows:
        stock[r["item_type"]] = r["quantity"]
    return stock


def try_deposit_to_warehouse(user_id: int, item_type: str, qty: int) -> bool:
    """Атомарно: списывает qty товара из сумки (city_inventory) И начисляет
    qty на склад (city_warehouse) — либо применяются оба изменения, либо ни
    одного. True — в сумке было достаточно товара и перемещение прошло.
    Лимит склада проверяется вызывающей стороной ДО вызова (как и лимит
    повозки при покупке) — здесь только атомарность самой перекладки."""
    if qty <= 0:
        return False
    with _conn() as conn:
        cur = conn.execute(
            "UPDATE city_inventory SET quantity = quantity - ? "
            "WHERE user_id=? AND item_type=? AND quantity>=?",
            (qty, user_id, item_type, qty),
        )
        if cur.rowcount == 0:
            return False  # в сумке не хватило товара — ничего не менялось
        conn.execute(
            "INSERT OR IGNORE INTO city_warehouse (user_id, item_type, quantity) VALUES (?,?,0)",
            (user_id, item_type),
        )
        conn.execute(
            "UPDATE city_warehouse SET quantity = quantity + ? WHERE user_id=? AND item_type=?",
            (qty, user_id, item_type),
        )
        conn.commit()
    return True


def try_withdraw_from_warehouse(user_id: int, item_type: str, qty: int) -> bool:
    """Атомарно: списывает qty товара со склада (city_warehouse) И
    начисляет qty в сумку (city_inventory) — либо применяются оба
    изменения, либо ни одного. True — на складе было достаточно товара.
    Сумка ничем не ограничена (лимит повозки проверяется только при
    отправлении в поездку), поэтому здесь дополнительных лимитов нет."""
    if qty <= 0:
        return False
    with _conn() as conn:
        cur = conn.execute(
            "UPDATE city_warehouse SET quantity = quantity - ? "
            "WHERE user_id=? AND item_type=? AND quantity>=?",
            (qty, user_id, item_type, qty),
        )
        if cur.rowcount == 0:
            return False  # на складе не хватило товара — ничего не менялось
        conn.execute(
            "INSERT OR IGNORE INTO city_inventory (user_id, item_type, quantity) VALUES (?,?,0)",
            (user_id, item_type),
        )
        conn.execute(
            "UPDATE city_inventory SET quantity = quantity + ? WHERE user_id=? AND item_type=?",
            (qty, user_id, item_type),
        )
        conn.commit()
    return True


# ---------- магазин защиты от таможни ----------

def get_customs_reduction(u: dict) -> float:
    """Суммарное снижение шанса конфискации от купленных защит.
    Фальшивые документы + сопровождение вместе дают фиксированные 30%
    (не наивную сумму 15%+25%=40%); охрана добавляет ещё 10% поверх."""
    has_docs = bool(u.get("has_fake_docs"))
    has_escort = bool(u.get("has_escort"))
    has_security = bool(u.get("has_security"))

    if has_docs and has_escort:
        reduction = FAKE_DOCS_AND_ESCORT_REDUCTION
    elif has_docs:
        reduction = FAKE_DOCS_REDUCTION
    elif has_escort:
        reduction = ESCORT_REDUCTION
    else:
        reduction = 0.0

    if has_security:
        reduction += SECURITY_REDUCTION

    return reduction


def get_customs_chance(item_type: str, u: dict) -> float:
    """Итоговый шанс конфискации для конкретного товара с учётом купленной
    защиты. Никогда не опускается ниже MIN_CUSTOMS_CHANCE."""
    base = ITEM_CUSTOMS_CHANCE.get(item_type, CUSTOMS_CHANCE)
    reduction = get_customs_reduction(u)
    return max(MIN_CUSTOMS_CHANCE, base - reduction)


def try_buy_protection(user_id: int, kind: str) -> tuple[bool, str]:
    """Покупает один из видов защиты ('fake_docs' | 'escort' | 'security').
    Атомарно: списывает кристаллы, только если хватает средств и защита
    ещё не куплена. Возвращает (успех, текст-сообщение)."""
    cost_map = {
        "fake_docs": (FAKE_DOCS_COST, "has_fake_docs"),
        "escort": (ESCORT_COST, "has_escort"),
        "security": (SECURITY_COST, "has_security"),
    }
    if kind not in cost_map:
        return False, "❌ Неизвестный вид защиты."
    cost, column = cost_map[kind]

    with _conn() as conn:
        row = conn.execute(f"SELECT {column}, balance FROM city_users WHERE user_id=?", (user_id,)).fetchone()
        if row is None:
            return False, "❌ Профиль не найден."
        if row[column]:
            return False, "✅ У вас уже куплена эта защита."
        if row["balance"] < cost:
            return False, f"💸 Недостаточно {CURRENCY_NAME}. Нужно {_crystals_plain(cost)}, у вас {_crystals_plain(row['balance'])}."
        cur = conn.execute(
            f"UPDATE city_users SET balance = balance - ?, {column} = 1 "
            f"WHERE user_id=? AND {column}=0 AND balance>=?",
            (cost, user_id, cost),
        )
        conn.commit()
        if cur.rowcount == 0:
            return False, "❌ Не удалось совершить покупку. Попробуйте ещё раз."
    log_crystal_event(user_id, -cost)
    return True, "✅ Защита успешно приобретена."


# ---------- капсулы усиления ----------

def get_capsules_owned(user_id: int) -> dict:
    """{capsule_id: количество на складе (ещё не использовано)}."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT capsule_id, quantity FROM city_capsules_owned WHERE user_id=? AND quantity>0",
            (user_id,),
        ).fetchall()
    return {r["capsule_id"]: r["quantity"] for r in rows}


def get_active_capsules(user_id: int) -> dict:
    """{category: capsule_id} — активная (используемая) капсула по каждой категории."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT category, capsule_id FROM city_capsules_active WHERE user_id=?", (user_id,)
        ).fetchall()
    return {r["category"]: r["capsule_id"] for r in rows}


def get_capsule_multiplier(user_id: int, category: str) -> float:
    """Текущий множитель для категории (1.0, если нет активной капсулы).
    Это единственная точка интеграции, которую нужно вызывать из основной
    игровой логики (добыча в шахте / урон в бою / сила питомцев), чтобы
    учесть эффект капсул."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT capsule_id FROM city_capsules_active WHERE user_id=? AND category=?",
            (user_id, category),
        ).fetchone()
    if not row:
        return 1.0
    return CAPSULES.get(row["capsule_id"], {}).get("mult", 1.0)


def try_buy_capsule(user_id: int, capsule_id: str) -> tuple[bool, str]:
    """Покупает одну капсулу — пополняет склад, НЕ активирует автоматически."""
    cap = CAPSULES.get(capsule_id)
    if not cap:
        return False, "❌ Неизвестная капсула."
    cost = cap["price"]
    with _conn() as conn:
        row = conn.execute("SELECT balance FROM city_users WHERE user_id=?", (user_id,)).fetchone()
        if row is None:
            return False, "❌ Профиль не найден."
        if row["balance"] < cost:
            return False, f"💸 Недостаточно {CURRENCY_NAME}. Нужно {_crystals_plain(cost)}, у вас {_crystals_plain(row['balance'])}."
        cur = conn.execute(
            "UPDATE city_users SET balance = balance - ? WHERE user_id=? AND balance>=?",
            (cost, user_id, cost),
        )
        if cur.rowcount == 0:
            return False, "❌ Не удалось совершить покупку. Попробуйте ещё раз."
        conn.execute(
            "INSERT INTO city_capsules_owned (user_id, capsule_id, quantity) VALUES (?,?,1) "
            "ON CONFLICT(user_id, capsule_id) DO UPDATE SET quantity = quantity + 1",
            (user_id, capsule_id),
        )
        conn.commit()
    log_crystal_event(user_id, -cost)
    return True, f"✅ Куплена «{cap['name']}»."


def try_use_capsule(user_id: int, capsule_id: str) -> tuple[bool, str]:
    """Активирует капсулу со склада. Списывает 1 шт. со склада и делает её
    активной в своей категории — если в этой категории уже была активна
    другая капсула, она заменяется (использовать сразу несколько капсул
    одной категории нельзя, активна всегда только одна)."""
    cap = CAPSULES.get(capsule_id)
    if not cap:
        return False, "❌ Неизвестная капсула."
    category = cap["category"]
    with _conn() as conn:
        row = conn.execute(
            "SELECT quantity FROM city_capsules_owned WHERE user_id=? AND capsule_id=?",
            (user_id, capsule_id),
        ).fetchone()
        if not row or row["quantity"] <= 0:
            return False, "❌ У вас нет этой капсулы на складе — сначала купите её."
        cur = conn.execute(
            "UPDATE city_capsules_owned SET quantity = quantity - 1 "
            "WHERE user_id=? AND capsule_id=? AND quantity>0",
            (user_id, capsule_id),
        )
        if cur.rowcount == 0:
            return False, "❌ У вас нет этой капсулы на складе — сначала купите её."
        conn.execute(
            "INSERT INTO city_capsules_active (user_id, category, capsule_id, activated_at) "
            "VALUES (?,?,?,?) "
            "ON CONFLICT(user_id, category) DO UPDATE SET capsule_id=excluded.capsule_id, "
            "activated_at=excluded.activated_at",
            (user_id, category, capsule_id, int(time.time())),
        )
        conn.commit()
    return True, f"✅ Активирована «{cap['name']}» (×{cap['mult']:g})."


# ---------- повозка (лимит перевозки) ----------

def get_cart_level(u: dict) -> int:
    lvl = u.get("cart_level", 0) or 0
    return max(0, min(lvl, CART_MAX_LEVEL))


def get_cart_capacity(u: dict) -> int:
    """Суммарный лимит товара (всех видов вместе), который можно везти за раз."""
    return CART_LEVELS[get_cart_level(u)]["capacity"]


def get_cart_next_tier(u: dict) -> dict | None:
    """Следующий уровень повозки, или None если уже максимум."""
    lvl = get_cart_level(u)
    if lvl >= CART_MAX_LEVEL:
        return None
    return CART_LEVELS[lvl + 1]


def try_upgrade_cart(user_id: int) -> tuple[bool, str, dict | None]:
    """Атомарно прокачивает повозку на следующий уровень за кристаллы.
    Возвращает (успех, текст_ошибки_или_пусто, данные_нового_уровня_или_None)."""
    u = get_city_user(user_id)
    nxt = get_cart_next_tier(u)
    if nxt is None:
        return False, "🐎 Повозка уже прокачана до максимума.", None

    if not try_spend_balance(user_id, nxt["cost"]):
        return False, f"💸 Недостаточно {CURRENCY_NAME} для прокачки повозки.", None

    with _conn() as conn:
        cur = conn.execute(
            "UPDATE city_users SET cart_level = ? WHERE user_id=? AND cart_level=?",
            (nxt["level"], user_id, get_cart_level(u)),
        )
        conn.commit()
        if cur.rowcount == 0:
            # кто-то параллельно уже прокачал повозку — возвращаем кристаллы
            add_balance(user_id, nxt["cost"])
            return False, "⚠️ Повозка уже была прокачана. Средства возвращены.", None

    return True, "", nxt


def total_inventory_qty(inv: dict) -> int:
    return sum(inv.values())


# ---------- склад (лимит хранения) ----------
# Отдельная механика от повозки: повозка ограничивает, сколько товара можно
# ВЕЗТИ за одну поездку; склад ограничивает, сколько товара можно ХРАНИТЬ
# вообще (используется при проверке лимита на покупку в cmd_city_buy).

def get_warehouse_level(u: dict) -> int:
    lvl = u.get("warehouse_level", 0) or 0
    return max(0, min(lvl, WAREHOUSE_MAX_LEVEL))


def get_warehouse_capacity(u: dict) -> int:
    """Суммарный лимит товара (всех видов вместе), который можно хранить."""
    return WAREHOUSE_LEVELS[get_warehouse_level(u)]["capacity"]


def get_warehouse_next_tier(u: dict) -> dict | None:
    """Следующий уровень склада, или None если уже максимум."""
    lvl = get_warehouse_level(u)
    if lvl >= WAREHOUSE_MAX_LEVEL:
        return None
    return WAREHOUSE_LEVELS[lvl + 1]


def try_upgrade_warehouse(user_id: int) -> tuple[bool, str, dict | None]:
    """Атомарно прокачивает склад на следующий уровень за кристаллы.
    Возвращает (успех, текст_ошибки_или_пусто, данные_нового_уровня_или_None)."""
    u = get_city_user(user_id)
    nxt = get_warehouse_next_tier(u)
    if nxt is None:
        return False, "📦 Склад уже прокачан до максимума.", None

    if not try_spend_balance(user_id, nxt["cost"]):
        return False, f"💸 Недостаточно {CURRENCY_NAME} для прокачки склада.", None

    with _conn() as conn:
        cur = conn.execute(
            "UPDATE city_users SET warehouse_level = ? WHERE user_id=? AND warehouse_level=?",
            (nxt["level"], user_id, get_warehouse_level(u)),
        )
        conn.commit()
        if cur.rowcount == 0:
            # кто-то параллельно уже прокачал склад — возвращаем кристаллы
            add_balance(user_id, nxt["cost"])
            return False, "⚠️ Склад уже был прокачан. Средства возвращены.", None

    return True, "", nxt


# ---------- цены ----------

def get_price(city: str, item: str) -> int:
    with _conn() as conn:
        row = conn.execute(
            "SELECT price FROM city_prices WHERE city=? AND item_type=?", (city, item)
        ).fetchone()
    return row["price"] if row else _roll_price(city, item)


def get_all_prices() -> dict:
    """{city: {item: price}}"""
    with _conn() as conn:
        rows = conn.execute("SELECT city, item_type, price FROM city_prices").fetchall()
    out = {c: {} for c in CITIES}
    for r in rows:
        out[r["city"]][r["item_type"]] = r["price"]
    return out


def register_trade(city: str, item: str, action: str):
    """action: 'buy' или 'sell' — учитываем для динамики цены."""
    col = "buy_count" if action == "buy" else "sell_count"
    with _conn() as conn:
        conn.execute(
            f"UPDATE city_prices SET {col} = {col} + 1 WHERE city=? AND item_type=?",
            (city, item),
        )
        conn.commit()


def update_all_prices():
    """Запускается раз в час: рандомное колебание ±20% + влияние спроса/предложения,
    затем сброс счётчиков покупок/продаж."""
    now = int(time.time())
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM city_prices").fetchall()
        for r in rows:
            city, item = r["city"], r["item_type"]
            new_price = _roll_price(city, item)

            buy_count = r["buy_count"]
            sell_count = r["sell_count"]
            demand_mod = 1.0 + 0.05 * (buy_count // 10) - 0.05 * (sell_count // 10)
            new_price = max(1, round(new_price * demand_mod))

            conn.execute(
                "UPDATE city_prices SET price=?, buy_count=0, sell_count=0, last_updated=? "
                "WHERE city=? AND item_type=?",
                (new_price, now, city, item),
            )
        conn.commit()


# ---------- обмен (кристаллы → монеты) ----------

def log_trade_qty(uid: int, qty: int, action: str):
    """Пишет реальный объём сделки (в штуках товара) для расчёта курса обмена.
    Учитываются именно покупки на рынке гильдии — чем активнее скупают товар,
    тем выгоднее становится курс обмена кристаллов на монеты. user_id нужен,
    чтобы при расчёте курса нельзя было накрутить его в одиночку (см.
    get_recent_buy_volume)."""
    with _conn() as conn:
        conn.execute(
            "INSERT INTO city_trade_log (ts, action, qty, user_id) VALUES (?,?,?,?)",
            (int(time.time()), action, qty, uid),
        )
        conn.commit()


def get_recent_buy_volume(window: int = EXCHANGE_WINDOW_SECONDS) -> int:
    """Сколько единиц товара куплено за последние `window` секунд — но с защитой
    от накрутки одним игроком: вклад каждого отдельного user_id ограничен
    EXCHANGE_PER_USER_CAP, после чего вклады суммируются. Так курс действительно
    растёт за счёт совокупной активности МНОГИХ игроков, а не закупок одного."""
    since = int(time.time()) - window
    with _conn() as conn:
        rows = conn.execute(
            "SELECT user_id, COALESCE(SUM(qty), 0) AS total FROM city_trade_log "
            "WHERE action='buy' AND ts>=? GROUP BY user_id",
            (since,),
        ).fetchall()
    total = 0
    for r in rows:
        total += min(r["total"] or 0, EXCHANGE_PER_USER_CAP)
    return total


def _compute_exchange_rate() -> int:
    """Курс зависит от активности скупки на рынке: чем больше товаров куплено
    за последние 10 минут, тем выше курс (ближе к максимуму). Плюс лёгкое
    случайное колебание, чтобы курс «играл» даже при ровном спросе."""
    volume = get_recent_buy_volume()
    ratio = min(1.0, volume / EXCHANGE_VOLUME_TARGET)
    base = EXCHANGE_MIN_RATE + (EXCHANGE_MAX_RATE - EXCHANGE_MIN_RATE) * ratio
    jitter = random.randint(-EXCHANGE_JITTER, EXCHANGE_JITTER)
    rate = int(base + jitter)
    return max(EXCHANGE_MIN_RATE, min(EXCHANGE_MAX_RATE, rate))


def _set_exchange_rate(rate: int):
    now = int(time.time())
    with _conn() as conn:
        conn.execute(
            "INSERT INTO city_meta (key, value) VALUES ('exchange_rate', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (str(rate),),
        )
        conn.execute(
            "INSERT INTO city_meta (key, value) VALUES ('exchange_rate_ts', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (str(now),),
        )
        conn.commit()


def get_exchange_rate() -> int:
    """Текущий курс обмена (монет за 1 кристалл). Пересчитывается фоновой
    задачей раз в минуту; если значения ещё нет — считает на лету."""
    with _conn() as conn:
        row = conn.execute("SELECT value FROM city_meta WHERE key='exchange_rate'").fetchone()
    if row is None:
        rate = _compute_exchange_rate()
        _set_exchange_rate(rate)
        return rate
    return int(row["value"])


def refresh_exchange_rate() -> int:
    """Принудительно пересчитывает и сохраняет курс (вызывается фоновой задачей)."""
    rate = _compute_exchange_rate()
    _set_exchange_rate(rate)
    return rate


def exchange_crystals_for_coins(uid: int, qty: int) -> tuple[bool, str, int, int]:
    """Обменивает `qty` кристаллов гильдии на монеты основного бота.
    Возвращает (успех, текст_ошибки_или_пусто, начисленные_монеты, курс).
    Купить кристаллы за монеты нельзя — обмен работает только в эту сторону.

    Списание кристаллов выполняется ОДНИМ атомарным UPDATE с проверкой баланса
    в WHERE — это закрывает гонку, при которой два почти одновременных вызова
    (двойной тап, повторная доставка апдейта от Telegram) могли увидеть один и
    тот же баланс и оба пройти проверку, получив монеты дважды за одни и те же
    кристаллы. Монеты начисляются только ПОСЛЕ успешного списания; если
    начисление в основном боте не удалось — кристаллы возвращаются обратно."""
    main_user = _db_get_user(uid)
    if main_user is None:
        return False, "❌ Сначала запусти основного бота командой /start.", 0, 0

    if not try_spend_balance(uid, qty):
        return False, f"💸 Недостаточно {CURRENCY_NAME} для обмена.", 0, 0

    rate = get_exchange_rate()
    coins = qty * rate
    try:
        new_main_balance = main_user.get("balance", 0) + coins
        _db_update_user(uid, {"balance": new_main_balance})
    except Exception:
        add_balance(uid, qty)  # откатываем списание кристаллов
        return False, "❌ Не удалось начислить монеты, попробуйте ещё раз.", 0, 0
    return True, "", coins, rate


# ---------- новости ----------

def generate_news() -> dict:
    city = random.choice(CITIES)
    item = random.choice(list(ITEMS.keys()))
    direction = random.choice(["up", "down"])
    will_come_true = random.random() < NEWS_TRUE_CHANCE

    item_name = ITEMS[item]["name"].lower()
    flavor_up = [
        f"Странник сообщает, что в городе {city} начались перебои с {item_name} — цена скоро вырастет",
        f"Купцы из {city} жалуются на дефицит {item_name} — ожидается рост цены",
        f"Гильдия торговцев {city} подтверждает спрос на {item_name} — цена пойдёт вверх",
    ]
    flavor_down = [
        f"Странник сообщает, что в городе {city} нашли богатый склад {item_name} — цена скоро упадёт",
        f"В {city} обнаружен новый караван с {item_name} — стоит ждать снижения цены",
        f"Слухи о переизбытке {item_name} в {city} — цена может просесть",
    ]
    text = random.choice(flavor_up if direction == "up" else flavor_down)
    text += " (прогноз на 2 часа)"

    now = int(time.time())
    expires = now + NEWS_LIFETIME_HOURS * 3600

    with _conn() as conn:
        conn.execute(
            "INSERT INTO city_trade_news (news_text, city, item_type, predicted_change, "
            "will_come_true, created_at, expires_at) VALUES (?,?,?,?,?,?,?)",
            (text, city, item, direction, int(will_come_true), now, expires),
        )
        conn.commit()

    return {
        "text": text, "city": city, "item": item,
        "direction": direction, "will_come_true": will_come_true, "expires_at": expires,
    }


def apply_due_news():
    """Применяет прогнозы, у которых подошло время (раз в минуту дёргать из фонового таска)."""
    now = int(time.time())
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM city_trade_news WHERE expires_at<=? AND expires_at>?",
            (now, now - 120),  # окно в 2 минуты, чтобы не применить дважды при сбоях
        ).fetchall()
        for r in rows:
            if not r["will_come_true"]:
                continue
            city, item, direction = r["city"], r["item_type"], r["predicted_change"]
            row = conn.execute(
                "SELECT price FROM city_prices WHERE city=? AND item_type=?", (city, item)
            ).fetchone()
            if not row:
                continue
            price = row["price"]
            new_price = round(price * (1.15 if direction == "up" else 0.85))
            new_price = max(1, new_price)
            conn.execute(
                "UPDATE city_prices SET price=? WHERE city=? AND item_type=?",
                (new_price, city, item),
            )
        conn.commit()


def get_active_news(limit: int = 5) -> list:
    now = int(time.time())
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM city_trade_news WHERE expires_at>? ORDER BY created_at DESC LIMIT ?",
            (now, limit),
        ).fetchall()
    return [dict(r) for r in rows]


# ---------- Async-обёртки ----------
# Все функции выше — синхронный sqlite3. Вызов любой из них напрямую из
# async-хэндлера (cmd_city_*/cb_city_*) или фонового цикла блокирует ВЕСЬ
# event loop бота на время диск-I/O — то есть зависают ВСЕ пользователи
# бота одновременно, а не только те, кто сейчас в разделе "Город".
#
# Использовать эти aio_-обёртки из любого async-кода вместо прямого
# вызова синхронных версий выше.

async def aio_get_city_user(user_id: int, username: str = "") -> dict:
    return await asyncio.to_thread(get_city_user, user_id, username)


async def aio_update_city_user(user_id: int, **fields):
    return await asyncio.to_thread(lambda: update_city_user(user_id, **fields))


async def aio_claim_travel_slot(user_id: int, dest: str, origin_city: str, end_time: int) -> bool:
    return await asyncio.to_thread(claim_travel_slot, user_id, dest, origin_city, end_time)


async def aio_release_travel_slot(user_id: int, origin_city: str):
    return await asyncio.to_thread(release_travel_slot, user_id, origin_city)


async def aio_add_crystals_to_all(amount: int) -> int:
    return await asyncio.to_thread(add_crystals_to_all, amount)


async def aio_add_crystals_to_user(user_id: int, amount: int, username: str = "") -> int:
    return await asyncio.to_thread(add_crystals_to_user, user_id, amount, username)


async def aio_get_inventory(user_id: int) -> dict:
    return await asyncio.to_thread(get_inventory, user_id)


async def aio_set_inventory_qty(user_id: int, item_type: str, qty: int):
    return await asyncio.to_thread(set_inventory_qty, user_id, item_type, qty)


async def aio_try_spend_balance(user_id: int, amount: int) -> bool:
    return await asyncio.to_thread(try_spend_balance, user_id, amount)


async def aio_add_balance(user_id: int, amount: int):
    return await asyncio.to_thread(add_balance, user_id, amount)


async def aio_spend_up_to(user_id: int, amount: int):
    return await asyncio.to_thread(spend_up_to, user_id, amount)


async def aio_try_adjust_inventory(user_id: int, item_type: str, delta: int) -> bool:
    return await asyncio.to_thread(try_adjust_inventory, user_id, item_type, delta)


async def aio_try_buy_item(user_id: int, item_type: str, qty: int, total_cost: int) -> bool:
    return await asyncio.to_thread(try_buy_item, user_id, item_type, qty, total_cost)


async def aio_try_sell_item(user_id: int, item_type: str, qty: int, total_gain: int) -> bool:
    return await asyncio.to_thread(try_sell_item, user_id, item_type, qty, total_gain)


async def aio_force_confiscate_inventory(user_id: int, item_type: str) -> int:
    return await asyncio.to_thread(force_confiscate_inventory, user_id, item_type)


async def aio_get_warehouse_stock(user_id: int) -> dict:
    return await asyncio.to_thread(get_warehouse_stock, user_id)


async def aio_try_deposit_to_warehouse(user_id: int, item_type: str, qty: int) -> bool:
    return await asyncio.to_thread(try_deposit_to_warehouse, user_id, item_type, qty)


async def aio_try_withdraw_from_warehouse(user_id: int, item_type: str, qty: int) -> bool:
    return await asyncio.to_thread(try_withdraw_from_warehouse, user_id, item_type, qty)


async def aio_refresh_item_freshness(user_id: int, item_type: str):
    return await asyncio.to_thread(refresh_item_freshness, user_id, item_type)


async def aio_get_item_freshness_left(user_id: int, item_type: str) -> int | None:
    return await asyncio.to_thread(get_item_freshness_left, user_id, item_type)


async def aio_try_buy_protection(user_id: int, kind: str) -> tuple[bool, str]:
    return await asyncio.to_thread(try_buy_protection, user_id, kind)


async def aio_get_capsules_owned(user_id: int) -> dict:
    return await asyncio.to_thread(get_capsules_owned, user_id)


async def aio_get_active_capsules(user_id: int) -> dict:
    return await asyncio.to_thread(get_active_capsules, user_id)


async def aio_get_capsule_multiplier(user_id: int, category: str) -> float:
    return await asyncio.to_thread(get_capsule_multiplier, user_id, category)


async def aio_try_buy_capsule(user_id: int, capsule_id: str) -> tuple[bool, str]:
    return await asyncio.to_thread(try_buy_capsule, user_id, capsule_id)


async def aio_try_use_capsule(user_id: int, capsule_id: str) -> tuple[bool, str]:
    return await asyncio.to_thread(try_use_capsule, user_id, capsule_id)


async def aio_try_upgrade_cart(user_id: int) -> tuple[bool, str, dict | None]:
    return await asyncio.to_thread(try_upgrade_cart, user_id)


async def aio_try_upgrade_warehouse(user_id: int) -> tuple[bool, str, dict | None]:
    return await asyncio.to_thread(try_upgrade_warehouse, user_id)


async def aio_get_price(city: str, item: str) -> int:
    return await asyncio.to_thread(get_price, city, item)


async def aio_get_all_prices() -> dict:
    return await asyncio.to_thread(get_all_prices)


async def aio_register_trade(city: str, item: str, action: str):
    return await asyncio.to_thread(register_trade, city, item, action)


async def aio_update_all_prices():
    return await asyncio.to_thread(update_all_prices)


async def aio_log_trade_qty(uid: int, qty: int, action: str):
    return await asyncio.to_thread(log_trade_qty, uid, qty, action)


async def aio_get_recent_buy_volume(window: int = EXCHANGE_WINDOW_SECONDS) -> int:
    return await asyncio.to_thread(get_recent_buy_volume, window)


async def aio_get_exchange_rate() -> int:
    return await asyncio.to_thread(get_exchange_rate)


async def aio_refresh_exchange_rate() -> int:
    return await asyncio.to_thread(refresh_exchange_rate)


async def aio_exchange_crystals_for_coins(uid: int, qty: int) -> tuple[bool, str, int, int]:
    return await asyncio.to_thread(exchange_crystals_for_coins, uid, qty)


async def aio_generate_news() -> dict:
    return await asyncio.to_thread(generate_news)


async def aio_apply_due_news():
    return await asyncio.to_thread(apply_due_news)


async def aio_get_active_news(limit: int = 5) -> list:
    return await asyncio.to_thread(get_active_news, limit)


# ──────────────────────────────────────────────────────────────────────────
# ВСПОМОГАТЕЛЬНОЕ
# ──────────────────────────────────────────────────────────────────────────

def _fmt(n: int) -> str:
    """Сокращает число так же, как format_amount в database.py
    (единая шкала и округление во всём боте): 1500->1.5K, 2.3M, 1.5B, итд."""
    return _db_format_amount(n)


def _crystals(n: int) -> str:
    return f"{_fmt(n)} {_tge('currency', CURRENCY_EMOJI)} {CURRENCY_NAME}"


def _crystals_plain(n: int) -> str:
    """Как _crystals(), но без кастомного тега эмодзи — для алертов
    (call.answer(show_alert=True)), которые не поддерживают HTML/кастомные эмодзи."""
    return f"{_fmt(n)} {CURRENCY_EMOJI} {CURRENCY_NAME}"


def _is_traveling(u: dict) -> bool:
    if u["status"] != "traveling":
        return False
    end = u["travel_end_time"]
    if end is None:
        return False
    return int(time.time()) < end


def _travel_elapsed(u: dict) -> int:
    """Сколько секунд прошло с момента начала текущей поездки."""
    end = u["travel_end_time"]
    if end is None:
        return 0
    start = end - TRAVEL_MINUTES * 60
    return max(0, int(time.time()) - start)


def _can_cancel_travel(u: dict) -> bool:
    return _is_traveling(u) and _travel_elapsed(u) < TRAVEL_CANCEL_WINDOW


def _parse_item(raw: str):
    return ALIAS_TO_ITEM.get(raw.strip().lower())


def _parse_city(raw: str):
    return ALIAS_TO_CITY.get(raw.strip().lower())


async def best_trade_route() -> dict | None:
    """Ищет пару город-товар с максимальной разницей (продать дороже всего минус купить дешевле всего)."""
    prices = await aio_get_all_prices()
    best = None
    for item in ITEMS:
        cheapest_city = min(CITIES, key=lambda c: prices[c][item])
        priciest_city = max(CITIES, key=lambda c: prices[c][item])
        if cheapest_city == priciest_city:
            continue
        profit = prices[priciest_city][item] - prices[cheapest_city][item]
        if best is None or profit > best["profit"]:
            best = {
                "item": item,
                "buy_city": cheapest_city,
                "buy_price": prices[cheapest_city][item],
                "sell_city": priciest_city,
                "sell_price": prices[priciest_city][item],
                "profit": profit,
            }
    return best


# ──────────────────────────────────────────────────────────────────────────
# ИНЛАЙН-КЛАВИАТУРЫ
# Каждый раздел — отдельный экран со своими кнопками действий и кнопкой
# «Назад», которая возвращает в главное меню (профиль).
# ──────────────────────────────────────────────────────────────────────────

def city_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню — показывается на экране профиля."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=" Рынок", callback_data="city_nav_market", icon_custom_emoji_id=BTN_EMOJI["market"]),
        InlineKeyboardButton(text=" Сумка", callback_data="city_nav_bag", icon_custom_emoji_id=BTN_EMOJI["bag"]),
    )
    builder.row(
        InlineKeyboardButton(text=" Путешествие", callback_data="city_nav_travel", icon_custom_emoji_id=BTN_EMOJI["travel"]),
        InlineKeyboardButton(text=" Маршрут", callback_data="city_nav_route", icon_custom_emoji_id=BTN_EMOJI["route"]),
    )
    builder.row(
        InlineKeyboardButton(text=" Обмен", callback_data="city_nav_exchange", icon_custom_emoji_id=BTN_EMOJI["exchange"]),
        InlineKeyboardButton(text=" Новости", callback_data="city_nav_news", icon_custom_emoji_id=BTN_EMOJI["news"]),
    )
    builder.row(
        InlineKeyboardButton(text=" Повозка", callback_data="city_nav_cart", icon_custom_emoji_id=BTN_EMOJI["cart"]),
        InlineKeyboardButton(text=" Помощь", callback_data="city_nav_help", icon_custom_emoji_id=BTN_EMOJI["help"]),
    )
    builder.row(
        InlineKeyboardButton(text=" Склад", callback_data="city_nav_warehouse", icon_custom_emoji_id=BTN_EMOJI["warehouse"]),
        InlineKeyboardButton(text=" Топ кристаллов", callback_data="crystop_alltime", icon_custom_emoji_id=BTN_EMOJI["currency"]),
    )
    builder.row(
        InlineKeyboardButton(text=" Защита от таможни", callback_data="city_nav_defense", icon_custom_emoji_id=BTN_EMOJI["defense"]),
        InlineKeyboardButton(text=" Капсулы", callback_data="city_nav_capsules", icon_custom_emoji_id=BTN_EMOJI.get("capsules")),
    )
    return builder.as_markup()


def city_back_keyboard() -> InlineKeyboardMarkup:
    """Простой возврат в главное меню — используется на «итоговых» экранах
    (результат покупки/продажи/путешествия)."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=" В главное меню", callback_data="city_nav_profile", icon_custom_emoji_id=BTN_EMOJI["home"]))
    return builder.as_markup()


def city_market_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=" Сумка", callback_data="city_nav_bag", icon_custom_emoji_id=BTN_EMOJI["bag"]),
        InlineKeyboardButton(text=" Маршрут", callback_data="city_nav_route", icon_custom_emoji_id=BTN_EMOJI["route"]),
    )
    builder.row(InlineKeyboardButton(text=" В главное меню", callback_data="city_nav_profile", icon_custom_emoji_id=BTN_EMOJI["home"]))
    return builder.as_markup()


def city_defense_keyboard(u: dict) -> InlineKeyboardMarkup:
    """Клавиатура магазина защиты — кнопка на каждый вид защиты, если он
    ещё не куплен; уже купленные виды кнопкой не показываются. Иконка и
    цвет кнопки зависят от того, хватает ли баланса (как в мастерской
    шахты: success — можно купить, danger — не хватает кристаллов)."""
    balance = u.get("balance", 0)
    builder = InlineKeyboardBuilder()
    if not u.get("has_fake_docs"):
        builder.row(InlineKeyboardButton(
            text=f"Фальшивые документы — {_fmt(FAKE_DOCS_COST)}",
            callback_data="city_buy_defense_fake_docs",
            icon_custom_emoji_id=EMOJI_BUY_BTN,
            style="success" if balance >= FAKE_DOCS_COST else "danger",
        ))
    if not u.get("has_escort"):
        builder.row(InlineKeyboardButton(
            text=f"Сопроводительное письмо — {_fmt(ESCORT_COST)}",
            callback_data="city_buy_defense_escort",
            icon_custom_emoji_id=EMOJI_BUY_BTN,
            style="success" if balance >= ESCORT_COST else "danger",
        ))
    if not u.get("has_security"):
        builder.row(InlineKeyboardButton(
            text=f"Охрана каравана — {_fmt(SECURITY_COST)}",
            callback_data="city_buy_defense_security",
            icon_custom_emoji_id=EMOJI_BUY_BTN,
            style="success" if balance >= SECURITY_COST else "danger",
        ))
    builder.row(InlineKeyboardButton(text=" В главное меню", callback_data="city_nav_profile", icon_custom_emoji_id=BTN_EMOJI["home"]))
    return builder.as_markup()


def city_capsules_menu_keyboard(active: dict | None = None) -> InlineKeyboardMarkup:
    """Главное окно капсул — по кнопке на каждую из 3 категорий.
    active: {category: capsule_id или None} — если в категории есть
    активная капсула, кнопка подсвечивается иконкой ✅, иначе — 🔒."""
    active = active or {}
    builder = InlineKeyboardBuilder()
    for category, info in CAPSULE_CATEGORIES.items():
        has_active = bool(active.get(category))
        icon = EMOJI_ACTIVE if has_active else EMOJI_LOCKED
        style = "success" if has_active else None
        builder.row(InlineKeyboardButton(
            text=info["title"],
            callback_data=f"city_capsule_cat_{category}",
            icon_custom_emoji_id=icon,
            **({"style": style} if style else {}),
        ))
    builder.row(InlineKeyboardButton(text=" В главное меню", callback_data="city_nav_profile", icon_custom_emoji_id=BTN_EMOJI["home"]))
    return builder.as_markup()


def city_capsule_category_keyboard(category: str, owned: dict | None = None, active_id: str | None = None) -> InlineKeyboardMarkup:
    """Окно категории — отдельная кнопка на каждую из 5 капсул этой категории.
    Иконка кнопки отражает статус (как в мастерской шахты):
    ✅ активна / 📦 куплена, но не активна / 🔒 ещё не куплена."""
    owned = owned or {}
    builder = InlineKeyboardBuilder()
    for i in range(1, 6):
        cid = f"{category}_{i}"
        cap = CAPSULES[cid]
        if cid == active_id:
            icon, style = EMOJI_ACTIVE, "success"
        elif owned.get(cid, 0) > 0:
            icon, style = EMOJI_OWNED, "success"
        else:
            icon, style = EMOJI_LOCKED, None
        builder.row(InlineKeyboardButton(
            text=f"{CAPSULE_ROMAN[i - 1]} — ×{cap['mult']:g} — {_fmt(cap['price'])}",
            callback_data=f"city_capsule_view_{cid}",
            icon_custom_emoji_id=icon,
            **({"style": style} if style else {}),
        ))
    builder.row(InlineKeyboardButton(text=" К капсулам", callback_data="city_nav_capsules", icon_custom_emoji_id=EMOJI_BACK_ARR))
    return builder.as_markup()


def city_capsule_detail_keyboard(capsule_id: str, owned: int, is_active: bool = False, balance: int = 0) -> InlineKeyboardMarkup:
    """Отдельное окно одной капсулы — информация + кнопка «Купить», и
    «Использовать», если капсула уже куплена и лежит на складе.
    owned — количество этой капсулы на складе (передаётся вызывающей
    стороной, которая уже получила его асинхронным запросом к БД)."""
    cap = CAPSULES[capsule_id]
    builder = InlineKeyboardBuilder()
    if is_active:
        builder.row(InlineKeyboardButton(text="Уже активна", callback_data="noop", icon_custom_emoji_id=EMOJI_ACTIVE))
    else:
        can_afford = balance >= cap["price"]
        builder.row(InlineKeyboardButton(
            text=f"{_fmt(cap['price'])} ",
            callback_data=f"city_capsule_buy_{capsule_id}",
            icon_custom_emoji_id=EMOJI_CRYSTAL_BUY,
            style="success" if can_afford else "danger",
        ))
    if owned > 0 and not is_active:
        builder.row(InlineKeyboardButton(
            text=f"Использовать ({owned} на складе)",
            callback_data=f"city_capsule_use_{capsule_id}",
            icon_custom_emoji_id=EMOJI_USE_BTN,
            style="success",
        ))
    builder.row(InlineKeyboardButton(text=" К категории", callback_data=f"city_capsule_cat_{cap['category']}", icon_custom_emoji_id=EMOJI_BACK_ARR))
    return builder.as_markup()


def city_bag_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=" На рынок", callback_data="city_nav_market", icon_custom_emoji_id=BTN_EMOJI["market"]),
        InlineKeyboardButton(text=" В путь", callback_data="city_nav_travel", icon_custom_emoji_id=BTN_EMOJI["travel"]),
    )
    builder.row(
        InlineKeyboardButton(text=" Повозка", callback_data="city_nav_cart", icon_custom_emoji_id=BTN_EMOJI["cart"]),
        InlineKeyboardButton(text=" Склад", callback_data="city_nav_warehouse", icon_custom_emoji_id=BTN_EMOJI["warehouse"]),
    )
    builder.row(InlineKeyboardButton(text=" В главное меню", callback_data="city_nav_profile", icon_custom_emoji_id=BTN_EMOJI["home"]))
    return builder.as_markup()


def city_cart_keyboard(can_upgrade: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if can_upgrade:
        builder.row(InlineKeyboardButton(text=" Прокачать повозку", callback_data="city_cart_upgrade", icon_custom_emoji_id=BTN_EMOJI["cart"]))
    builder.row(
        InlineKeyboardButton(text=" Сумка", callback_data="city_nav_bag", icon_custom_emoji_id=BTN_EMOJI["bag"]),
        InlineKeyboardButton(text=" На рынок", callback_data="city_nav_market", icon_custom_emoji_id=BTN_EMOJI["market"]),
    )
    builder.row(InlineKeyboardButton(text=" В главное меню", callback_data="city_nav_profile", icon_custom_emoji_id=BTN_EMOJI["home"]))
    return builder.as_markup()


def city_warehouse_keyboard(can_upgrade: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=" Положить в склад", callback_data="city_wh_buy", icon_custom_emoji_id=BTN_EMOJI["buy"]),
        InlineKeyboardButton(text=" Забрать со склада", callback_data="city_wh_sell", icon_custom_emoji_id=BTN_EMOJI["bag"]),
    )
    if can_upgrade:
        builder.row(InlineKeyboardButton(text=" Прокачать склад", callback_data="city_warehouse_upgrade", icon_custom_emoji_id=BTN_EMOJI["warehouse"]))
    builder.row(
        InlineKeyboardButton(text=" Сумка", callback_data="city_nav_bag", icon_custom_emoji_id=BTN_EMOJI["bag"]),
        InlineKeyboardButton(text=" На рынок", callback_data="city_nav_market", icon_custom_emoji_id=BTN_EMOJI["market"]),
    )
    builder.row(InlineKeyboardButton(text=" В главное меню", callback_data="city_nav_profile", icon_custom_emoji_id=BTN_EMOJI["home"]))
    return builder.as_markup()


def city_warehouse_item_keyboard(inv: dict) -> InlineKeyboardMarkup:
    """Выбор товара для перекладки ИЗ СУМКИ НА СКЛАД (кнопка «Положить в склад»).
    Показывает только товары, которых в сумке больше 0 штук — inv здесь
    инвентарь сумки/повозки (city_inventory), НЕ склада."""
    builder = InlineKeyboardBuilder()
    for item, info in ITEMS.items():
        if inv.get(item, 0) <= 0:
            continue
        eid = ITEM_EMOJI_ID.get(item)
        kwargs = {"icon_custom_emoji_id": eid} if eid else {}
        builder.row(InlineKeyboardButton(
            text=(f"{info['emoji']} {info['name']}" if not eid else info["name"]) + f" ({_fmt(inv[item])})",
            callback_data=f"city_wh_buy_item_{item}",
            **kwargs,
        ))
    if not any(inv.get(item, 0) > 0 for item in ITEMS):
        builder.row(InlineKeyboardButton(text=" В сумке пусто", callback_data="noop"))
    builder.row(InlineKeyboardButton(text=" К складу", callback_data="city_nav_warehouse", icon_custom_emoji_id=EMOJI_BACK_ARR))
    return builder.as_markup()


def city_warehouse_sell_item_keyboard(inv: dict) -> InlineKeyboardMarkup:
    """Выбор товара для перекладки СО СКЛАДА В СУМКУ (кнопка «Забрать со склада»).
    Показывает только товары, которых на складе больше 0 штук — inv здесь
    содержимое СКЛАДА (city_warehouse), НЕ сумки."""
    builder = InlineKeyboardBuilder()
    for item, info in ITEMS.items():
        if inv.get(item, 0) <= 0:
            continue
        eid = ITEM_EMOJI_ID.get(item)
        kwargs = {"icon_custom_emoji_id": eid} if eid else {}
        builder.row(InlineKeyboardButton(
            text=(f"{info['emoji']} {info['name']}" if not eid else info["name"]) + f" ({_fmt(inv[item])})",
            callback_data=f"city_wh_sell_item_{item}",
            **kwargs,
        ))
    if not any(inv.get(item, 0) > 0 for item in ITEMS):
        builder.row(InlineKeyboardButton(text=" Склад пуст", callback_data="noop"))
    builder.row(InlineKeyboardButton(text=" К складу", callback_data="city_nav_warehouse", icon_custom_emoji_id=EMOJI_BACK_ARR))
    return builder.as_markup()


def city_warehouse_sell_qty_keyboard(item: str, max_qty: int) -> InlineKeyboardMarkup:
    """Быстрый выбор количества для перекладки со склада в сумку. Показывает
    только варианты, не превышающие max_qty (сколько реально лежит на
    складе), плюс кнопку «Максимум»."""
    builder = InlineKeyboardBuilder()
    row = []
    for qty in WAREHOUSE_BUY_QTY_OPTIONS:
        if qty > max_qty:
            continue
        row.append(InlineKeyboardButton(text=_fmt(qty), callback_data=f"city_wh_sell_qty_{item}_{qty}"))
        if len(row) == 3:
            builder.row(*row)
            row = []
    if row:
        builder.row(*row)
    if max_qty > 0:
        builder.row(InlineKeyboardButton(
            text=f"Максимум ({_fmt(max_qty)})",
            callback_data=f"city_wh_sell_qty_{item}_{max_qty}",
            icon_custom_emoji_id=BTN_EMOJI["bag"],
        ))
    builder.row(InlineKeyboardButton(text=" К товарам", callback_data="city_wh_sell"))
    return builder.as_markup()


def city_warehouse_qty_keyboard(item: str, max_qty: int) -> InlineKeyboardMarkup:
    """Быстрый выбор количества для перекладки из сумки на склад. Показывает
    только варианты, которые реально можно переложить (не превышают
    max_qty — уже посчитанный вызывающей стороной минимум из «сколько есть
    в сумке» и «сколько влезет на склад»), плюс кнопку «Максимум», если
    максимум больше нуля."""
    builder = InlineKeyboardBuilder()
    row = []
    for qty in WAREHOUSE_BUY_QTY_OPTIONS:
        if qty > max_qty:
            continue
        row.append(InlineKeyboardButton(text=_fmt(qty), callback_data=f"city_wh_buy_qty_{item}_{qty}"))
        if len(row) == 3:
            builder.row(*row)
            row = []
    if row:
        builder.row(*row)
    if max_qty > 0:
        builder.row(InlineKeyboardButton(
            text=f"Максимум ({_fmt(max_qty)})",
            callback_data=f"city_wh_buy_qty_{item}_{max_qty}",
            icon_custom_emoji_id=BTN_EMOJI["buy"],
        ))
    builder.row(InlineKeyboardButton(text=" К товарам", callback_data="city_wh_buy"))
    return builder.as_markup()


def city_news_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=" В главное меню", callback_data="city_nav_profile", icon_custom_emoji_id=BTN_EMOJI["home"]))
    return builder.as_markup()


def city_route_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=" Рынок", callback_data="city_nav_market", icon_custom_emoji_id=BTN_EMOJI["market"]),
        InlineKeyboardButton(text=" В путь", callback_data="city_nav_travel", icon_custom_emoji_id=BTN_EMOJI["travel"]),
    )
    builder.row(InlineKeyboardButton(text=" В главное меню", callback_data="city_nav_profile", icon_custom_emoji_id=BTN_EMOJI["home"]))
    return builder.as_markup()


def city_help_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=" В главное меню", callback_data="city_nav_profile", icon_custom_emoji_id=BTN_EMOJI["home"]))
    return builder.as_markup()


def city_exchange_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=" Рынок", callback_data="city_nav_market", icon_custom_emoji_id=BTN_EMOJI["market"]),
        InlineKeyboardButton(text=" Сумка", callback_data="city_nav_bag", icon_custom_emoji_id=BTN_EMOJI["bag"]),
    )
    builder.row(InlineKeyboardButton(text=" В главное меню", callback_data="city_nav_profile", icon_custom_emoji_id=BTN_EMOJI["home"]))
    return builder.as_markup()


CITY_BTN_EMOJI_KEY = {
    "Северный": "city_north",
    "Южный": "city_south",
    "Столица": "city_capital",
}


def city_travel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for city in CITIES:
        builder.row(InlineKeyboardButton(
            text=f"{city}",
            callback_data=f"city_go_{city}",
            icon_custom_emoji_id=BTN_EMOJI[CITY_BTN_EMOJI_KEY[city]],
        ))
    builder.row(InlineKeyboardButton(text=" В главное меню", callback_data="city_nav_profile", icon_custom_emoji_id=BTN_EMOJI["home"]))
    return builder.as_markup()


def city_travel_active_keyboard(can_cancel: bool) -> InlineKeyboardMarkup:
    """Показывается сразу после старта поездки. Пока не истекло окно отмены —
    предлагает кнопку отмены."""
    builder = InlineKeyboardBuilder()
    if can_cancel:
        builder.row(InlineKeyboardButton(text=" Отменить поездку", callback_data="city_cancel_travel", icon_custom_emoji_id=BTN_EMOJI["cancel_travel"]))
    builder.row(InlineKeyboardButton(text=" В главное меню", callback_data="city_nav_profile", icon_custom_emoji_id=BTN_EMOJI["home"]))
    return builder.as_markup()


# ──────────────────────────────────────────────────────────────────────────
# ТЕКСТЫ ЭКРАНОВ
# ──────────────────────────────────────────────────────────────────────────

def _profile_text(u: dict, inv: dict) -> str:
    status_line = "🟢 <b><i>Свободен</i></b> <b><i>— можно торговать прямо сейчас</i></b>"
    if _is_traveling(u):
        left = u["travel_end_time"] - int(time.time())
        m, s = max(0, left // 60), max(0, left % 60)
        status_line = f"🚶 <b><i>В пути</i></b> <b><i>— прибытие через {m} мин {s} сек</i></b>"

    return (
        f"{_tge('customs', '🧙‍♂️')} <b><i>ГИЛЬДИЯ ТОРГОВЦЕВ</i></b>\n"
        "<b><i>Личный кабинет искателя прибыли</i></b> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{_tge('balance', CURRENCY_EMOJI)} Баланс: <b><i>{_fmt(u['balance'])}</i></b> <b><i>{CURRENCY_NAME}</i></b>\n"
        f"{_city_emoji_tag(u['city'])} Город: <b><i>{u['city']}</i></b>\n"
        f"{_tge('status', '📡')} Статус: {status_line}\n\n"
        "📦 <b><i>Склад</i></b>\n"
        + "".join(
            f"  {_item_emoji(item)} {info['name']} — <b><i>{inv.get(item, 0)}</i></b> <b><i>шт.</i></b>\n"
            for item, info in ITEMS.items()
        )
        + "\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🎁 <b><i>Ежедневный бонус +{DAILY_CRYSTALS} {CURRENCY_NAME} получен сегодня ✅ — заходи завтра за новым</i></b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<b><i>Выберите раздел ниже 👇</i></b>"
    )


async def _market_text() -> str:
    prices = await aio_get_all_prices()
    lines = [
        f"{_tge('market', '🏪')} <b><i>ТОРГОВЫЕ РЯДЫ</i></b>",
        "<b><i>Актуальные цены по всем городам</i></b> ✨",
        "━━━━━━━━━━━━━━━━━━━━\n",
    ]
    for city in CITIES:
        lines.append(f"{_city_emoji_tag(city)} <b><i>{city}</i></b>")
        for item, info in ITEMS.items():
            p = prices[city][item]
            lines.append(f"   {_item_emoji(item)} <b><i>{info['name']}</i></b> — <b><i>{p}</i></b> {_tge('currency', CURRENCY_EMOJI)}")
        lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"{0} <b><i>Купить —</i></b> <code>/citybuy товар количество</code>".format(_tge("buy", "🛒")))
    lines.append(f"{0} <b><i>Продать —</i></b> <code>/citysell товар количество</code>".format(_tge("sell", "💰")))
    return "\n".join(lines)


def _defense_text(u: dict) -> str:
    has_docs = bool(u.get("has_fake_docs"))
    has_escort = bool(u.get("has_escort"))
    has_security = bool(u.get("has_security"))

    def _status(owned: bool) -> str:
        icon, label = (EMOJI_ACTIVE, "куплено") if owned else (EMOJI_LOCKED, "не куплено")
        return f"{_stat_tge(icon, '✅' if owned else '🔒')} <b><i>{label}</i></b>"

    base_chance = int(CUSTOMS_CHANCE * 100)
    forbidden_chance = int(ITEM_CUSTOMS_CHANCE.get("forbidden_scrolls", CUSTOMS_CHANCE) * 100)
    effective_normal = int(round(get_customs_chance("potions", u) * 100))
    effective_forbidden = int(round(get_customs_chance("forbidden_scrolls", u) * 100))

    return (
        f"{_tge('defense', '🛡')} <b><i>ЗАЩИТА ОТ ТАМОЖНИ</i></b>\n"
        "<b><i>Снижайте риск конфискации товара</i></b> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<blockquote>📄 <b><i>Фальшивые документы</i></b> — <b><i>{_fmt(FAKE_DOCS_COST)}</i></b> {_tge('currency', CURRENCY_EMOJI)}\n"
        f"<i>Снижает шанс конфискации на <b>{int(FAKE_DOCS_REDUCTION * 100)}%</b></i>\n"
        f"{_status(has_docs)}</blockquote>\n\n"
        f"<blockquote>✉️ <b><i>Сопроводительное письмо</i></b> — <b><i>{_fmt(ESCORT_COST)}</i></b> {_tge('currency', CURRENCY_EMOJI)}\n"
        f"<i>Снижает шанс конфискации на <b>{int(ESCORT_REDUCTION * 100)}%</b>, вместе с документами — <b>{int(FAKE_DOCS_AND_ESCORT_REDUCTION * 100)}%</b></i>\n"
        f"{_status(has_escort)}</blockquote>\n\n"
        f"<blockquote>💂 <b><i>Охрана каравана</i></b> — <b><i>{_fmt(SECURITY_COST)}</i></b> {_tge('currency', CURRENCY_EMOJI)}\n"
        f"<i>Снижает шанс конфискации ещё на <b>{int(SECURITY_REDUCTION * 100)}%</b></i>\n"
        f"{_status(has_security)}</blockquote>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{_tge('status', '📊')} <i><b>Базовый шанс конфискации:</b></i> обычный товар — <b><i>{base_chance}%</i></b>, "
        f"запретные свитки — <b><i>{forbidden_chance}%</i></b>\n"
        f"{_tge('status', '📊')} <i><b>Ваш текущий шанс:</b></i> обычный товар — <b><i>{effective_normal}%</i></b>, "
        f"запретные свитки — <b><i>{effective_forbidden}%</i></b>\n"
        f"🏆 <b><i>При покупке всех трёх защит шанс падает до минимума —</i></b> <b><i>{int(MIN_CUSTOMS_CHANCE * 100)}%</i></b>"
    )


def _capsules_menu_text(active: dict) -> str:
    """active: {category: capsule_id или None} — активные капсулы игрока."""
    lines = [
        f"{_tge('capsules', '🔮')} <b><i>КАПСУЛЫ УСИЛЕНИЯ</i></b>\n"
        "<b><i>Алхимия гильдии для тех, кто не привык ждать</i></b> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
    ]
    for category, info in CAPSULE_CATEGORIES.items():
        cid = active.get(category)
        if cid:
            cap = CAPSULES[cid]
            status = f"{_stat_tge(EMOJI_ACTIVE, '✅')} <b><i>активна «{cap['name']}» (×{cap['mult']:g})</i></b>"
        else:
            status = f"{_stat_tge(EMOJI_LOCKED, '🔒')} <b><i>нет активной капсулы</i></b>"
        lines.append(
            f"<blockquote>{info['emoji']} <b><i>{info['title']}</i></b> — <i>{info['effect']}</i>\n"
            f"{status}</blockquote>"
        )
    lines.append(
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<b><i>В каждой категории 5 капсул — от I до V, множитель растёт "
        "от ×1.15 до ×2.00. Активной в категории может быть только "
        "ОДНА капсула: новая всегда заменяет предыдущую, использовать "
        "несколько капсул одной категории разом нельзя.</i></b>\n\n"
        "<b><i>Выберите категорию ниже 👇</i></b>"
    )
    return "\n\n".join(lines)


def _capsule_category_text(category: str, owned: dict, active_id: str | None) -> str:
    info = CAPSULE_CATEGORIES[category]
    lines = [
        f"{info['emoji']} <b><i>{info['title'].upper()}</i></b>\n"
        f"<i>{info['flavor']}</i>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
    ]
    for i in range(1, 6):
        cid = f"{category}_{i}"
        cap = CAPSULES[cid]
        have = owned.get(cid, 0)
        if cid == active_id:
            status = f"{_stat_tge(EMOJI_ACTIVE, '✅')} <b><i>активна</i></b>"
        elif have > 0:
            status = f"{_stat_tge(EMOJI_OWNED, '📦')} <b><i>на складе: {have} шт.</i></b>"
        else:
            status = f"{_stat_tge(EMOJI_LOCKED, '🔒')} <b><i>ещё не куплена</i></b>"
        lines.append(
            f"<blockquote><b><i>{CAPSULE_ROMAN[i - 1]}. {cap['name']}</i></b>\n"
            f"{_tge('currency', CURRENCY_EMOJI)} <i><b>×{cap['mult']:g}</b></i> к {info['noun']} "
            f"— <i><b>{_fmt(cap['price'])}</b></i> {_tge('currency', CURRENCY_EMOJI)}\n"
            f"{status}</blockquote>"
        )
    lines.append("━━━━━━━━━━━━━━━━━━━━\n<b><i>Выберите капсулу, чтобы посмотреть подробности и купить</i></b> 👇")
    return "\n\n".join(lines)


def _capsule_detail_text(capsule_id: str, owned: int, is_active: bool) -> str:
    cap = CAPSULES[capsule_id]
    info = CAPSULE_CATEGORIES[cap["category"]]
    if is_active:
        status = f"{_stat_tge(EMOJI_ACTIVE, '✅')} <b><i>сейчас активна</i></b>"
    elif owned > 0:
        status = f"{_stat_tge(EMOJI_OWNED, '📦')} <b><i>лежит на складе, не активирована</i></b>"
    else:
        status = f"{_stat_tge(EMOJI_LOCKED, '🔒')} <b><i>не куплена</i></b>"
    return (
        f"{info['emoji']} <b><i>{cap['name'].upper()}</i></b>\n"
        f"<i>{info['flavor']}</i>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<blockquote>{_tge('capsules', '📈')} <i><b>Эффект:</b></i> {info['effect']} — множитель <b><i>×{cap['mult']:g}</i></b>\n"
        f"{_tge('currency', CURRENCY_EMOJI)} <i><b>Цена:</b></i> <b><i>{_fmt(cap['price'])}</i></b> {_tge('currency', CURRENCY_EMOJI)}\n"
        f"{_stat_tge(EMOJI_OWNED, '📦')} <i><b>На складе:</b></i> <b><i>{owned}</i></b> шт.\n"
        f"{_tge('status', '📡')} <i><b>Статус:</b></i> {status}</blockquote>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ <b><i>Активной в этой категории может быть только одна капсула — "
        "использование новой заменит текущую.</i></b>"
    )


def _cart_bar(carried: int, capacity: int, length: int = 12) -> str:
    ratio = 0 if capacity <= 0 else min(1.0, carried / capacity)
    filled = round(ratio * length)
    return "▰" * filled + "▱" * (length - filled)


def _bag_text(inv: dict, u: dict | None = None, freshness: dict | None = None) -> str:
    """freshness: {item_type: seconds_left} для скоропортящихся товаров, которые
    сейчас лежат в инвентаре (передаётся вызывающей стороной, т.к. это отдельный
    async-запрос к БД)."""
    freshness = freshness or {}
    total_items = sum(inv.values())
    capacity = get_cart_capacity(u) if u else CART_LEVELS[0]["capacity"]
    bar = _cart_bar(total_items, capacity)
    pct = 0 if capacity <= 0 else min(100, round(total_items / capacity * 100))

    goods_lines = []
    for item, info in ITEMS.items():
        line = f"{_item_emoji(item)} {info['name']}: <b><i>{inv.get(item, 0)}</i></b> <b><i>шт.</i></b>"
        if info.get("perishable") and inv.get(item, 0) > 0:
            left = freshness.get(item)
            if left is not None:
                m, s = left // 60, left % 60
                line += f" — ⏳ <b><i>свежесть {m} мин {s} сек</i></b>"
        goods_lines.append(line)
    goods_block = "\n".join(goods_lines)

    return (
        f"{_tge('bag', '🎒')} <b><i>ИНВЕНТАРЬ ТОРГОВЦА</i></b>\n"
        "<b><i>Что лежит у вас в сумке (готово к перевозке)</i></b> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{goods_block}\n\n"
        f"🐎 <b><i>Повозка:</i></b> <b><i>{_fmt(total_items)} / {_fmt(capacity)}</i></b> <b><i>({pct}%)</i></b>\n"
        f"{bar}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ <b><i>Провоз свыше {CUSTOMS_LIMIT} ед. одного товара рискует конфискацией на таможне.</i></b>\n"
        f"⚠️ <b><i>Запретные свитки проверяют вдвое строже — шанс конфискации {int(ITEM_CUSTOMS_CHANCE.get('forbidden_scrolls', CUSTOMS_CHANCE) * 100)}%.</i></b>\n"
        f"⏳ <b><i>Чёрная икра портится через {CAVIAR_FRESHNESS_SECONDS // 60} мин. после покупки — на складе не портится.</i></b>\n"
        f"📝 <b><i>Прокачать повозку:</i></b> <code>/citycart</code>\n"
        f"📝 <b><i>Спрятать товар от таможни на складе:</i></b> <code>/citywarehouse</code>\n"
        f"📝 <b><i>Снизить риск конфискации:</i></b> <code>/citydefense</code>"
    )


def _cart_text(u: dict, inv: dict) -> str:
    lvl = get_cart_level(u)
    cur_tier = CART_LEVELS[lvl]
    capacity = cur_tier["capacity"]
    carried = total_inventory_qty(inv)
    bar = _cart_bar(carried, capacity)
    pct = 0 if capacity <= 0 else min(100, round(carried / capacity * 100))
    nxt = get_cart_next_tier(u)

    lines = [
        "🐎 <b><i>ПОВОЗКА</i></b>",
        "<b><i>Сколько товара можно везти с собой за раз</i></b> ✨",
        "━━━━━━━━━━━━━━━━━━━━\n",
        f"🚚 Текущая повозка: <b><i>{cur_tier['name']}</i></b> <b><i>(уровень {lvl})</i></b>\n",
        f"📦 Загружено: <b><i>{_fmt(carried)} / {_fmt(capacity)}</i></b> <b><i>({pct}%)</i></b>\n"
        f"{bar}\n",
        "<i>Лимит проверяется только при отправлении в другой город — если товара больше, чем везёт повозка, в путь не отправиться.</i>\n",
    ]

    if nxt is None:
        lines.append(
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🏆 <b><i>Повозка прокачана до максимума — 1 000 000 ед. товара за раз!</i></b>"
        )
    else:
        lines.append(
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"⬆️ <b><i>Следующий уровень:</i></b> <b><i>{nxt['name']}</i></b>\n"
            f"📦 Новый лимит: <b><i>{_fmt(nxt['capacity'])}</i></b> <b><i>ед.</i></b>\n"
            f"{_tge('currency', CURRENCY_EMOJI)} Цена прокачки: <b><i>{_fmt(nxt['cost'])}</i></b> <b><i>{CURRENCY_NAME}</i></b>\n\n"
            f"{_tge('balance', CURRENCY_EMOJI)} Ваш баланс: <b><i>{_fmt(u['balance'])}</i></b> <b><i>{CURRENCY_NAME}</i></b>\n\n"
            "📝 <b><i>Прокачать:</i></b> <code>/citycartup</code>"
        )

    lines.append(
        "\n━━━━━━━━━━━━━━━━━━━━\n"
        "<b><i>Все уровни повозки</i></b>\n" +
        "\n".join(
            f"  {'✅' if t['level'] <= lvl else '🔒'} <b><i>{t['name']}</i></b> — "
            f"<b><i>{_fmt(t['capacity'])} ед.</i></b>"
            + (f" <b><i>({_fmt(t['cost'])} {CURRENCY_NAME_SINGULAR})</i></b>" if t['cost'] else " <b><i>(база, бесплатно)</i></b>")
            for t in CART_LEVELS
        )
    )
    return "\n".join(lines)


def _warehouse_text(u: dict, inv: dict) -> str:
    """inv — содержимое СКЛАДА (city_warehouse), а не сумки."""
    lvl = get_warehouse_level(u)
    cur_tier = WAREHOUSE_LEVELS[lvl]
    capacity = cur_tier["capacity"]
    stored = total_inventory_qty(inv)
    bar = _cart_bar(stored, capacity)
    pct = 0 if capacity <= 0 else min(100, round(stored / capacity * 100))
    nxt = get_warehouse_next_tier(u)

    goods_lines = [
        f"  {_item_emoji(item)} {info['name']}: <b><i>{inv.get(item, 0)}</i></b> <b><i>шт.</i></b>"
        for item, info in ITEMS.items() if inv.get(item, 0) > 0
    ]
    goods_block = "\n".join(goods_lines) if goods_lines else "  <i>На складе пока пусто</i>"

    lines = [
        "📦 <b><i>СКЛАД</i></b>",
        "<b><i>Отдельное хранилище — товар лежит здесь, а не в сумке</i></b> ✨",
        "━━━━━━━━━━━━━━━━━━━━\n",
        f"🏬 Текущий склад: <b><i>{cur_tier['name']}</i></b> <b><i>(уровень {lvl})</i></b>\n",
        f"{goods_block}\n",
        f"📦 Хранится: <b><i>{_fmt(stored)} / {_fmt(capacity)}</i></b> <b><i>({pct}%)</i></b>\n"
        f"{bar}\n",
        "<i>Товар на складе не портится, не рискует конфискацией на таможне и не занимает место в повозке. "
        "Заберите его обратно кнопкой «Забрать со склада», когда понадобится для торговли или поездки.</i>\n",
    ]

    if nxt is None:
        lines.append(
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🏆 <b><i>Склад прокачан до максимума — {_fmt(WAREHOUSE_LEVELS[WAREHOUSE_MAX_LEVEL]['capacity'])} ед. товара!</i></b>"
        )
    else:
        lines.append(
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"⬆️ <b><i>Следующий уровень:</i></b> <b><i>{nxt['name']}</i></b>\n"
            f"📦 Новый лимит: <b><i>{_fmt(nxt['capacity'])}</i></b> <b><i>ед.</i></b>\n"
            f"{_tge('currency', CURRENCY_EMOJI)} Цена прокачки: <b><i>{_fmt(nxt['cost'])}</i></b> <b><i>{CURRENCY_NAME}</i></b>\n\n"
            f"{_tge('balance', CURRENCY_EMOJI)} Ваш баланс: <b><i>{_fmt(u['balance'])}</i></b> <b><i>{CURRENCY_NAME}</i></b>\n\n"
            "📝 <b><i>Прокачать:</i></b> <code>/citywarehouseup</code>"
        )

    lines.append(
        "\n━━━━━━━━━━━━━━━━━━━━\n"
        "<b><i>Все уровни склада</i></b>\n" +
        "\n".join(
            f"  {'✅' if t['level'] <= lvl else '🔒'} <b><i>{t['name']}</i></b> — "
            f"<b><i>{_fmt(t['capacity'])} ед.</i></b>"
            + (f" <b><i>({_fmt(t['cost'])} {CURRENCY_NAME_SINGULAR})</i></b>" if t['cost'] else " <b><i>(база, бесплатно)</i></b>")
            for t in WAREHOUSE_LEVELS
        )
    )
    return "\n".join(lines)


async def _news_text() -> str:
    news = await aio_get_active_news()
    if not news:
        return (
            f"{_tge('news', '🗞')} <b><i>ТОРГОВЫЕ СЛУХИ</i></b>\n"
            "<b><i>Прогнозы рынка на ближайшие часы</i></b> ✨\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b><i>Пока тихо... странники ещё не принесли новостей.\n"
            "Загляните чуть позже.</i></b>"
        )
    lines = [
        f"{_tge('news', '🗞')} <b><i>ТОРГОВЫЕ СЛУХИ</i></b>",
        "<b><i>Прогнозы рынка на ближайшие часы</i></b> ✨",
        "━━━━━━━━━━━━━━━━━━━━\n",
    ]
    for n in news:
        published = datetime.fromtimestamp(n["created_at"]).strftime("%H:%M")
        lines.append(
            f'<tg-emoji emoji-id="5337313450232140345">🌟</tg-emoji> <b><i>{n['news_text']}</i></b>\n'
            f"🕒 <b><i>опубликовано в {published}</i></b>"
        )
    return "\n\n".join(lines)


async def _route_text() -> str:
    best = await best_trade_route()
    if not best:
        return (
            '<tg-emoji emoji-id="5422439311196834318">🌟</tg-emoji> <b><i>ЛУЧШИЙ ТОРГОВЫЙ МАРШРУТ</i></b>\n'
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b><i>Сейчас нет выгодных маршрутов — цены во всех городах примерно равны.</i></b>"
        )
    info = ITEMS[best["item"]]
    margin_pct = round(best["profit"] / max(1, best["buy_price"]) * 100)
    return (
        f'<tg-emoji emoji-id="5422439311196834318">🌟</tg-emoji> <b><i>ЛУЧШИЙ ТОРГОВЫЙ МАРШРУТ</i></b>\n'
        "<b><i>Подсказка гильдии — где заработать прямо сейчас</i></b> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{_item_emoji(best['item'])} Товар: <b><i>{info['name']}</i></b>\n\n"
        f"{_tge('buy', '🛒')} Купить в {_city_emoji_tag(best['buy_city'])} <b><i>{best['buy_city']}</i></b> — <b><i>{best['buy_price']}</i></b> {_tge('currency', CURRENCY_EMOJI)}\n"
        f"{_tge('sell', '💰')} Продать в {_city_emoji_tag(best['sell_city'])} <b><i>{best['sell_city']}</i></b> — <b><i>{best['sell_price']}</i></b> {_tge('currency', CURRENCY_EMOJI)}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f'<tg-emoji emoji-id="5397916757333654639">🌟</tg-emoji> Прибыль с единицы: <b><i>+{best['profit']}</i></b> {_tge('currency', CURRENCY_EMOJI)} <b><i>(≈{margin_pct}%)</i></b>'
    )


async def _exchange_text(u: dict) -> str:
    rate = await aio_get_exchange_rate()
    balance = u["balance"]
    potential = balance * rate
    volume = await aio_get_recent_buy_volume()
    activity_pct = min(100, round(volume / EXCHANGE_VOLUME_TARGET * 100))

    if rate >= EXCHANGE_MAX_RATE - EXCHANGE_JITTER:
        mood = "🔥 <b><i>Ажиотаж на рынке — курс почти на максимуме!</i></b>"
    elif rate <= EXCHANGE_MIN_RATE + EXCHANGE_JITTER:
        mood = "😴 <b><i>Рынок спокоен — курс у нижней границы.</i></b>"
    else:
        mood = "📈 <b><i>Рынок понемногу разогревается.</i></b>"

    return (
        f"{_tge('exchange', '🔁')} <b><i>ОБМЕННЫЙ ПУНКТ ГИЛЬДИИ</i></b>\n"
        "<b><i>Кристаллы можно обменять на монеты основного бота</i></b> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{_tge('currency', CURRENCY_EMOJI)} Текущий курс: <b><i>1 {CURRENCY_NAME_SINGULAR}</i></b> = <b><i>{rate}</i></b> {COIN_TAG}\n"
        f"📊 Активность рынка: <b><i>{activity_pct}%</i></b> <b><i>(закупки за 10 мин)</i></b>\n"
        f"{mood}\n\n"
        f"{_tge('balance', CURRENCY_EMOJI)} Твой баланс: <b><i>{_fmt(balance)}</i></b> {CURRENCY_NAME}\n"
        f"💵 Можно получить: <b><i>≈{_fmt(potential)}</i></b> {COIN_TAG} <b><i>(если обменять всё)</i></b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 <b><i>Команда:</i></b> <code>/cityexchange количество</code>\n"
        f"<b><i>Например:</i></b> <code>/cityexchange 20</code> <b><i>или</i></b> <code>/cityexchange все</code>\n\n"
        f"⚠️ <b><i>Курс колеблется от</i></b> <b><i>{EXCHANGE_MIN_RATE}</i></b> <b><i>до</i></b> <b><i>{EXCHANGE_MAX_RATE}</i></b> {COIN_TAG} "
        f"<b><i>и зависит от объёма закупок на рынке гильдии. Купить кристаллы за монеты нельзя — обмен работает только в одну сторону.</i></b>"
    )


def _help_text() -> str:
    return (
        f"{_tge('help', '❓')} <b><i>СПРАВКА ПО ТРЕЙДИНГУ</i></b>\n"
        "<b><i>Арбитражная торговля между городами</i></b> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b><i>📋 Команды</i></b>\n"
        '<tg-emoji emoji-id="5906581476639513176">🌟</tg-emoji> <code>/city</code> — <b><i>профиль торговца: баланс, город, статус, склад</i></b>\n'
        f"{_tge('market', '🏪')} <code>/citymarket</code> — <b><i>цены на товары во всех городах</i></b>\n"
        f"{_tge('buy', '🛒')} <code>/citybuy товар количество</code> — <b><i>купить товар</i></b>\n"
        f"{_tge('sell', '💰')} <code>/citysell товар количество</code> — <b><i>продать товар</i></b>\n"
        f"{_tge('travel', '🧭')} <code>/citytravel город</code> — <b><i>отправиться в другой город</i></b>\n"
        f"{_tge('cancel_travel', '❌')} <code>/citycancel</code> — <b><i>отменить поездку (только в первые 2 минуты)</i></b>\n"
        f"{_tge('bag', '🎒')} <code>/citybag</code> — <b><i>инвентарь</i></b>\n"
        f"{_tge('cart', '🐎')} <code>/citycart</code> — <b><i>статус повозки и прокачка</i></b>\n"
        f"{_tge('cart', '🐎')} <code>/citycartup</code> — <b><i>прокачать повозку на след. уровень</i></b>\n"
        f"{_tge('warehouse', '📦')} <code>/citywarehouse</code> — <b><i>статус склада и прокачка</i></b>\n"
        f"{_tge('warehouse', '📦')} <code>/citywarehouseup</code> — <b><i>прокачать склад на след. уровень</i></b>\n"
        f"{_tge('news', '🗞')} <code>/citynews</code> — <b><i>слухи и прогнозы цен на 2 часа вперёд</i></b>\n"
        f"{_tge('route', '🗺')} <code>/cityroute</code> — <b><i>самый выгодный маршрут прямо сейчас</i></b>\n"
        f"{_tge('exchange', '🔁')} <code>/cityexchange количество</code> — <b><i>обменять кристаллы на монеты</i></b>\n"
        f"{_tge('defense', '🛡')} <code>/citydefense</code> — <b><i>магазин защиты от таможни</i></b>\n"
        f"💊 <code>/citycapsules</code> — <b><i>капсулы усиления (добыча/урон/питомцы)</i></b>\n"
        f"{_tge('help', '❓')} <code>/cityhelp</code> — <b><i>эта справка</i></b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<b><i>📦 Товары</i></b>\n"
        f"  {_item_emoji('potions')} Зелья — <b><i>дёшевы на Севере, дороги на Юге</i></b>\n"
        f"  {_item_emoji('scrolls')} Свитки — <b><i>дёшевы на Юге, дороги на Севере</i></b>\n"
        f"  {_item_emoji('food')} Еда — <b><i>дешевле на Юге, дороже на Севере</i></b>\n"
        f"  {_item_emoji('forbidden_scrolls')} Запретные свитки — <b><i>дорогая контрабанда, шанс конфискации {int(ITEM_CUSTOMS_CHANCE['forbidden_scrolls'] * 100)}% вместо {int(CUSTOMS_CHANCE * 100)}%</i></b>\n"
        f"  {_item_emoji('caviar')} Чёрная икра — <b><i>портится через {CAVIAR_FRESHNESS_SECONDS // 60} минут после покупки — не затягивайте с продажей</i></b>\n"
        f"  {_tge('city_capital', '🏛')} Столица — <b><i>всё дорого, но цены стабильнее</i></b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"<b><i>{_tge('travel', '🧭')} Путешествия</i></b>\n"
        f"  • Стоимость дороги: <b><i>{TRAVEL_COST}</i></b> {_tge('currency', CURRENCY_EMOJI)}\n"
        f"  • Время в пути: <b><i>{TRAVEL_MINUTES}</i></b> минут\n"
        "  • <b><i>Во время пути торговля недоступна</i></b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"<b><i>{_tge('customs', '🧙‍♂️')} Таможня (Гильдия магов)</i></b>\n"
        f"  • <b><i>Провоз свыше</i></b> <b><i>{CUSTOMS_LIMIT}</i></b> <b><i>ед. одного товара рискует конфискацией</i></b>\n"
        f"  • Шанс конфискации: <b><i>{int(CUSTOMS_CHANCE * 100)}%</i></b> (обычный товар), "
        f"<b><i>{int(ITEM_CUSTOMS_CHANCE['forbidden_scrolls'] * 100)}%</i></b> (запретные свитки), "
        f"штраф <b><i>{CUSTOMS_FINE}</i></b> {_tge('currency', CURRENCY_EMOJI)}\n"
        f"  • <b><i>{_tge('defense', '🛡')} Магазин защиты</i></b> (<code>/citydefense</code>) снижает риск: "
        f"фальшивые документы −{int(FAKE_DOCS_REDUCTION * 100)}%, сопроводительное письмо −{int(ESCORT_REDUCTION * 100)}% "
        f"(вместе −{int(FAKE_DOCS_AND_ESCORT_REDUCTION * 100)}%), охрана −{int(SECURITY_REDUCTION * 100)}%\n"
        f"  • <b><i>Все три защиты вместе снижают шанс конфискации до минимума —</i></b> <b><i>{int(MIN_CUSTOMS_CHANCE * 100)}%</i></b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"<b><i>{_tge('cart', '🐎')} Повозка (лимит перевозки)</i></b>\n"
        f"  • <b><i>Проверяется только при отправлении в другой город — сколько товара у вас на руках, столько и повезёте</i></b>\n"
        f"  • <b><i>Если товара больше лимита повозки — в путь не отправиться, пока не продадите излишек или не прокачаете повозку</i></b>\n"
        f"  • <b><i>Базовый лимит:</i></b> <b><i>{_fmt(CART_LEVELS[0]['capacity'])}</i></b> <b><i>ед. товара за раз</i></b>\n"
        f"  • <b><i>Максимум после прокачки:</i></b> <b><i>{_fmt(CART_LEVELS[CART_MAX_LEVEL]['capacity'])}</i></b> <b><i>ед.</i></b>\n"
        f"  • <b><i>Прокачивается за кристаллы, всего {CART_MAX_LEVEL} платных уровней</i></b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"<b><i>{_tge('warehouse', '📦')} Склад (лимит хранения)</i></b>\n"
        f"  • <b><i>Проверяется при покупке — сколько товара вы вообще можете хранить, независимо от повозки</i></b>\n"
        f"  • <b><i>Кнопка «Положить в склад» в меню склада — покупка прямо через кнопки, без команд</i></b>\n"
        f"  • <b><i>Базовый лимит:</i></b> <b><i>{_fmt(WAREHOUSE_LEVELS[0]['capacity'])}</i></b> <b><i>ед. товара</i></b>\n"
        f"  • <b><i>Максимум после прокачки:</i></b> <b><i>{_fmt(WAREHOUSE_LEVELS[WAREHOUSE_MAX_LEVEL]['capacity'])}</i></b> <b><i>ед.</i></b>\n"
        f"  • <b><i>Прокачивается за кристаллы, всего {WAREHOUSE_MAX_LEVEL} платных уровней</i></b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        '<b><i><tg-emoji emoji-id="5231200819986047254">🌟</tg-emoji> Динамика цен</i></b>\n'
        "  • <b><i>Цены обновляются каждый час (±20% случайно)</i></b>\n"
        "  • <b><i>Массовая скупка повышает цену, массовая продажа — снижает</i></b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"<b><i>{_tge('exchange', '🔁')} Обменный пункт</i></b>\n"
        f"  • Курс: <b><i>{EXCHANGE_MIN_RATE}–{EXCHANGE_MAX_RATE}</i></b> {COIN_TAG} <b><i>за 1 {CURRENCY_NAME_SINGULAR}</i></b>\n"
        "  • <b><i>Курс растёт, если на рынке гильдии активно скупают товары</i></b>\n"
        "  • <b><i>Обмен работает только в одну сторону — купить кристаллы за монеты нельзя</i></b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"<b><i>🎁 Ежедневный бонус</i></b>\n"
        f"  • <b><i>Каждый день — бесплатно</i></b> <b><i>+{DAILY_CRYSTALS}</i></b> {_tge('currency', CURRENCY_EMOJI)}\n\n"
        f"<b><i>Удачной торговли, искатель прибыли!</i></b> {_tge('currency', CURRENCY_EMOJI)}"
    )


# ──────────────────────────────────────────────────────────────────────────
# ХЕНДЛЕРЫ КОМАНД
# (намеренно с другими именами, чтобы не конфликтовать с /profile, /shop,
#  /inventory, /sell и т.д. из main.py)
# ──────────────────────────────────────────────────────────────────────────

async def _city_level_ok(message: Message) -> bool:
    """Проверка уровня для точек входа, которые могут вызываться напрямую
    из main.py (в обход city_router и его outer_middleware).
    Возвращает True если можно продолжать, иначе сама отвечает отказом."""
    user = message.from_user
    if user is None:
        return True
    if user.id in CITY_ADMIN_IDS:
        return True
    main_user = await _aio_db_get_user(user.id)
    level = (main_user or {}).get("level", 1)
    if level < CITY_MIN_LEVEL:
        await message.reply(
            f'<tg-emoji emoji-id="5334544901428229844">🌟</tg-emoji> <b><i>Город откроется на {CITY_MIN_LEVEL} уровне!</i></b>\n',
            parse_mode="HTML",
        )
        return False
    return True


@router.message(Command("city", "трейдер", "trader", "торг", "торговля", "город"))
async def cmd_city_profile(message: Message):
    if not await _city_level_ok(message):
        return
    u = await aio_get_city_user(message.from_user.id, message.from_user.username or "")
    inv = await aio_get_inventory(u["user_id"])
    await message.reply(
        _profile_text(u, inv),
        parse_mode="HTML",
        reply_markup=city_main_menu_keyboard(),
    )


@router.message(F.text.regexp(
    r"^(?:торг|торговля|город)(?:\s|$)",
    flags=__import__("re").IGNORECASE
))
async def cmd_city_profile_noslash(message: Message):
    """Текстовые алиасы раздела города без слеша."""
    await cmd_city_profile(message)


@router.message(Command("citymarket", "рынок", "market"))
async def cmd_city_shop(message: Message):
    if not await _city_level_ok(message):
        return
    await message.reply(
        await _market_text(),
        parse_mode="HTML",
        reply_markup=city_market_keyboard(),
    )


@router.message(F.text.regexp(
    r"^рынок(?:\s|$)",
    flags=__import__("re").IGNORECASE
))
async def cmd_city_shop_noslash(message: Message):
    """Текстовый алиас рынка без слеша."""
    await cmd_city_shop(message)


@router.message(Command("citydefense", "защита"))
async def cmd_city_defense(message: Message):
    if not await _city_level_ok(message):
        return
    u = await aio_get_city_user(message.from_user.id, message.from_user.username or "")
    await message.reply(
        _defense_text(u),
        parse_mode="HTML",
        reply_markup=city_defense_keyboard(u),
    )


@router.message(F.text.regexp(
    r"^защита(?:\s|$)",
    flags=__import__("re").IGNORECASE
))
async def cmd_city_defense_noslash(message: Message):
    """Текстовый алиас магазина защиты без слеша."""
    await cmd_city_defense(message)


@router.message(Command("citycapsules", "капсулы"))
async def cmd_city_capsules(message: Message):
    if not await _city_level_ok(message):
        return
    u = await aio_get_city_user(message.from_user.id, message.from_user.username or "")
    active = await aio_get_active_capsules(u["user_id"])
    await message.reply(
        _capsules_menu_text(active),
        parse_mode="HTML",
        reply_markup=city_capsules_menu_keyboard(active),
    )


@router.message(F.text.regexp(
    r"^капсулы(?:\s|$)",
    flags=__import__("re").IGNORECASE
))
async def cmd_city_capsules_noslash(message: Message):
    """Текстовый алиас магазина капсул без слеша."""
    await cmd_city_capsules(message)


def _parse_crystal_amount(s: str) -> int | None:
    """
    Парсит число с суффиксами: 100м → 100000000, 1.5к → 1500, 2млрд → 2000000000.
    Поддерживает: к/k, м/m/mil, млрд/b/bil, трлн/t/tri.
    Возвращает int или None если не распознано.
    (Дубль парсера из main.py — чтобы не тянуть циклический импорт.)
    """
    s = s.strip().lower().replace(" ", "").replace("_", "")
    _SUFFIXES = [
        (("трлн", "tri", "t"), 1_000_000_000_000),
        (("млрд", " млд", "bil", "b"), 1_000_000_000),
        (("mil", "м", "m"), 1_000_000),
        (("к", "k"), 1_000),
    ]
    for aliases, multiplier in _SUFFIXES:
        for alias in aliases:
            if s.endswith(alias):
                num_str = s[:-len(alias)]
                if not num_str:
                    return None
                try:
                    return int(float(num_str) * multiplier)
                except ValueError:
                    return None
    try:
        return int(s)
    except ValueError:
        return None


@router.message(Command("addcrystal"))
async def cmd_city_addcrystal(message: Message):
    """Админ-команда: /addcrystal username|id сумма — начислить кристаллы одному игроку."""
    if message.from_user.id not in CITY_ADMIN_IDS:
        return  # тихо игнорируем

    parts = (message.text or "").strip().split(maxsplit=2)
    if len(parts) != 3:
        await message.reply(
            "❌ Неверный формат.\nИспользование: <code>/addcrystal username|id сумма</code>\n"
            "<b><i>Например: /addcrystal @ivan 500 или /addcrystal 123456789 1к</i></b>",
            parse_mode="HTML",
        )
        return

    target_raw = parts[1].lstrip("@")
    amount = _parse_crystal_amount(parts[2])
    if amount is None or amount == 0:
        await message.reply("❌ Не удалось распознать сумму.", parse_mode="HTML")
        return

    found = await _aio_db_get_user_by_id_or_username(target_raw)
    if not found:
        await message.reply(
            f"❌ Пользователь <code>{target_raw}</code> не найден в базе.",
            parse_mode="HTML",
        )
        return

    new_balance = await aio_add_crystals_to_user(found["id"], amount, found.get("username", "") or "")

    import html as _html
    name = _html.escape(str(found.get("first_name") or found.get("username") or found["id"]))
    sign = "+" if amount > 0 else ""
    await message.reply(
        f"{CURRENCY_EMOJI} <b><i>Кристаллы начислены!</i></b>\n\n"
        f"👤 Игрок: <b><i>{name}</i></b> (<code>{found['id']}</code>)\n"
        f"Начислено: <b><i>{sign}{amount}</i></b>\n"
        f"Новый баланс: <b><i>{new_balance}</i></b> {CURRENCY_EMOJI}",
        parse_mode="HTML",
    )


@router.message(Command("citybuy", "купить"))
async def cmd_city_buy(message: Message):
    args = (message.text or "").split()[1:]
    if len(args) < 2:
        await message.reply(
            "📝 Использование: <code>/citybuy [товар] [количество]</code>\n"
            "<b><i>Например: /citybuy зелья 10 или /citybuy черная икра 5</i></b>",
            parse_mode="HTML",
        )
        return

    # Последний токен — количество, всё до него — название товара
    # (нужно для товаров из двух слов: "запретные свитки", "черная икра").
    qty_raw, item_raw = args[-1], " ".join(args[:-1])

    u = await aio_get_city_user(message.from_user.id, message.from_user.username or "")
    if _is_traveling(u):
        await message.reply("🚶 Вы в пути — торговля недоступна до прибытия.")
        return

    item = _parse_item(item_raw)
    if not item:
        await message.reply("❌ Неизвестный товар. Доступно: зелья, свитки, еда, запретные свитки, черная икра.")
        return

    try:
        qty = int(qty_raw)
    except ValueError:
        await message.reply("❌ Количество должно быть числом.")
        return
    if qty <= 0:
        await message.reply("❌ Количество должно быть положительным.")
        return

    # ── Лимит повозки проверяется только при отправлении в другой город
    # (см. _do_travel), а не здесь при покупке: сумка сама по себе ничем
    # не ограничена, лишний товар можно унести на склад (/citywarehouse).

    price = await aio_get_price(u["city"], item)
    total = price * qty
    if total > u["balance"]:
        await message.reply(
            f"💸 Недостаточно {CURRENCY_NAME}. Нужно {_crystals(total)}, у вас {_crystals(u['balance'])}.",
            parse_mode="HTML",
        )
        return

    if not await aio_try_buy_item(u["user_id"], item, qty, total):
        await message.reply(
            f"💸 Недостаточно {CURRENCY_NAME} для этой покупки.",
            parse_mode="HTML",
        )
        return
    await aio_register_trade(u["city"], item, "buy")
    await aio_log_trade_qty(u["user_id"], qty, "buy")

    perishable_note = ""
    if ITEMS[item].get("perishable"):
        # Каждая новая покупка обновляет таймер свежести для всего товара на руках.
        await aio_refresh_item_freshness(u["user_id"], item)
        fresh_min = CAVIAR_FRESHNESS_SECONDS // 60
        perishable_note = f"\n⏳ <b><i>Свежесть: {fresh_min} мин. — успейте продать или довезти!</i></b>"

    await message.reply(
        "✅ <b><i>СДЕЛКА СОВЕРШЕНА</i></b>\n"
        "<b><i>Покупка прошла успешно</i></b> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{_item_emoji(item)} Куплено: <b><i>{qty} × {ITEMS[item]['name']}</i></b>\n"
        f"💵 Цена за шт.: <b><i>{price}</i></b> {_tge('currency', CURRENCY_EMOJI)}\n"
        f"{_tge('currency', CURRENCY_EMOJI)} Списано: <b><i>{_fmt(total)}</i></b> <b><i>{CURRENCY_NAME}</i></b>\n"
        f"📍 Город: <b><i>{u['city']}</i></b>"
        f"{perishable_note}",
        parse_mode="HTML",
        reply_markup=city_back_keyboard(),
    )


@router.message(Command("citysell", "продать"))
async def cmd_city_sell(message: Message):
    args = (message.text or "").split()[1:]
    if len(args) < 2:
        await message.reply(
            "📝 Использование: <code>/citysell [товар] [количество]</code>\n"
            "<b><i>Например: /citysell свитки 5 или /citysell черная икра 3</i></b>",
            parse_mode="HTML",
        )
        return

    qty_raw, item_raw = args[-1], " ".join(args[:-1])

    u = await aio_get_city_user(message.from_user.id, message.from_user.username or "")
    if _is_traveling(u):
        await message.reply("🚶 Вы в пути — торговля недоступна до прибытия.")
        return

    item = _parse_item(item_raw)
    if not item:
        await message.reply("❌ Неизвестный товар. Доступно: зелья, свитки, еда, запретные свитки, черная икра.")
        return

    try:
        qty = int(qty_raw)
    except ValueError:
        await message.reply("❌ Количество должно быть числом.")
        return
    if qty <= 0:
        await message.reply("❌ Количество должно быть положительным.")
        return

    inv = await aio_get_inventory(u["user_id"])
    if qty > inv[item]:
        await message.reply(f"📦 У вас только <b><i>{inv[item]}</i></b> единиц этого товара.", parse_mode="HTML")
        return

    # ── Цену фиксируем ДО списания товара, чтобы игрок получал деньги
    # по той цене, что видел на момент продажи (а не по цене, которая
    # могла смениться фоновой задачей city_prices_loop в этот же момент).
    price = await aio_get_price(u["city"], item)
    total = price * qty

    if not await aio_try_sell_item(u["user_id"], item, qty, total):
        await message.reply(f"📦 У вас недостаточно этого товара.", parse_mode="HTML")
        return

    await aio_register_trade(u["city"], item, "sell")
    await aio_log_trade_qty(u["user_id"], qty, "sell")

    await message.reply(
        "✅ <b><i>СДЕЛКА СОВЕРШЕНА</i></b>\n"
        "<b><i>Продажа прошла успешно</i></b> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{_item_emoji(item)} Продано: <b><i>{qty} × {ITEMS[item]['name']}</i></b>\n"
        f"💵 Цена за шт.: <b><i>{price}</i></b> {_tge('currency', CURRENCY_EMOJI)}\n"
        f"{_tge('currency', CURRENCY_EMOJI)} Получено: <b><i>{_fmt(total)}</i></b> <b><i>{CURRENCY_NAME}</i></b>\n"
        f"📍 Город: <b><i>{u['city']}</i></b>",
        parse_mode="HTML",
        reply_markup=city_back_keyboard(),
    )


async def _do_travel(user_id: int, username: str, dest: str):
    """Общая логика путешествия. Возвращает (ok, text)."""
    u = await aio_get_city_user(user_id, username)
    if _is_traveling(u):
        return False, "🚶 Вы уже в пути."
    if dest == u["city"]:
        return False, "📍 Вы уже находитесь в этом городе."

    # ── Лимит ПОВОЗКИ проверяется именно здесь — перед отправлением, а не
    # при покупке товара (см. cmd_city_buy). Повозка ограничивает, сколько
    # товара можно физически ВЗЯТЬ в конкретную поездку; сумка сама по себе
    # ничем не ограничена — лишний товар можно унести на отдельный склад
    # (/citywarehouse), который в поездках вообще не участвует. Если товара
    # на руках больше, чем влезает в повозку — в путь отправиться нельзя,
    # пока часть не продана, не убрана на склад, или повозка не прокачана.
    cart_capacity = get_cart_capacity(u)
    inv_now = await aio_get_inventory(u["user_id"])
    carried = total_inventory_qty(inv_now)
    if carried > cart_capacity:
        overflow = carried - cart_capacity
        return False, (
            f"🐎 <b><i>Повозка не выдержит столько груза!</i></b>\n"
            f"📦 Везёте: <b><i>{_fmt(carried)}</i></b> <b><i>ед.</i></b>\n"
            f"📦 Лимит повозки: <b><i>{_fmt(cart_capacity)}</i></b> <b><i>ед.</i></b>\n"
            f"📦 Лишнего: <b><i>{_fmt(overflow)}</i></b> <b><i>ед.</i></b>\n\n"
            f"<b><i>Продайте часть товара (</i></b><code>/citysell</code><b><i>), уберите на склад (</i></b><code>/citywarehouse</code><b><i>) "
            f"или прокачайте повозку (</i></b><code>/citycartup</code><b><i>), чтобы отправиться в путь.</i></b>"
        )


    origin_city = u["city"]
    end_time = int(time.time()) + TRAVEL_MINUTES * 60

    # ── Атомарный "замок" на поездку ────────────────────────────────────
    # Захватываем статус 'traveling' ОДНИМ запросом (status='free' в WHERE)
    # ДО списания денег и ДО броска таможни. Если между чтением статуса
    # выше и этим запросом кто-то параллельно (двойной тап по кнопке,
    # повтор апдейта от Telegram) уже запустил поездку — claim провалится,
    # и мы просто вежливо откажем, вместо того чтобы прокрутить кубик
    # конфискации второй раз на тот же груз.
    if not await aio_claim_travel_slot(user_id, dest, origin_city, end_time):
        return False, "🚶 Вы уже в пути."

    if not await aio_try_spend_balance(u["user_id"], TRAVEL_COST):
        await aio_release_travel_slot(user_id, origin_city)  # снимаем замок, поездка не состоялась
        return False, f"💸 Недостаточно {CURRENCY_NAME} на дорогу. Нужно {_crystals(TRAVEL_COST)}."

    inv = await aio_get_inventory(u["user_id"])  # заодно спишет протухшую икру
    confiscated = []
    fine_total = 0
    for item, qty in inv.items():
        if qty > CUSTOMS_LIMIT and random.random() < get_customs_chance(item, u):
            taken = await aio_force_confiscate_inventory(u["user_id"], item)
            if taken > 0:
                confiscated.append(ITEMS[item]["name"])
                fine_total += CUSTOMS_FINE

    if fine_total:
        await aio_spend_up_to(u["user_id"], fine_total)  # не уводит баланс в минус

    cancel_min = TRAVEL_CANCEL_WINDOW // 60
    text = (
        f"{_tge('travel', '🧭')} <b><i>В ПУТЬ!</i></b>\n"
        "<b><i>Караван покидает город</i></b> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Направление: {_city_emoji_tag(dest)} <b><i>{dest}</i></b>\n"
        f"⏳ Прибытие через <b><i>{TRAVEL_MINUTES}</i></b> <b><i>минут</i></b>\n"
        f"{_tge('currency', CURRENCY_EMOJI)} Дорога стоила: <b><i>{TRAVEL_COST}</i></b> <b><i>{CURRENCY_NAME}</i></b>\n\n"
        f"<b><i>Передумали? В первые {cancel_min} минуты поездку можно отменить "
        f"(плата за дорогу не возвращается).</i></b>"
    )
    if confiscated:
        text += (
            "\n\n━━━━━━━━━━━━━━━━━━━━\n"
            f"{_tge('customs', '🧙‍♂️')} <b><i>Гильдия магов конфисковала ваш товар!</i></b>\n"
            f"<b><i>Изъято: {', '.join(confiscated)}</i></b>\n"
            f"💸 Штраф: <b><i>{fine_total}</i></b> {_tge('currency', CURRENCY_EMOJI)} <b><i>{CURRENCY_NAME}</i></b>"
        )
    return True, text


async def _do_cancel_travel(user_id: int, username: str):
    """Отменяет текущую поездку, если прошло меньше TRAVEL_CANCEL_WINDOW секунд.
    Деньги за дорогу НЕ возвращаются."""
    u = await aio_get_city_user(user_id, username)
    if not _is_traveling(u):
        return False, "📍 Вы сейчас никуда не едете."
    if not _can_cancel_travel(u):
        return False, "⏳ Время на отмену уже истекло — поездку можно только завершить."

    origin = u["travel_from"] or u["city"]
    await aio_update_city_user(
        u["user_id"],
        status="free",
        travel_end_time=None,
        travel_from=None,
        city=origin,
    )
    text = (
        f"{_tge('cancel_travel', '❌')} <b><i>ПОЕЗДКА ОТМЕНЕНА</i></b>\n"
        "<b><i>Вы вернулись назад</i></b> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{_city_emoji_tag(origin)} Вы снова в городе <b><i>{origin}</i></b>\n"
        f"<b><i>Плата за дорогу не возвращается.</i></b>"
    )
    return True, text


def _traveling_status_text(u: dict) -> str:
    left = u["travel_end_time"] - int(time.time())
    m, s = max(0, left // 60), max(0, left % 60)
    text = (
        "🚶 <b><i>ВЫ В ПУТИ</i></b>\n"
        f"<b><i>Прибытие через {m} мин {s} сек</i></b> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Направление: {_city_emoji_tag(u['city'])} <b><i>{u['city']}</i></b>"
    )
    if _can_cancel_travel(u):
        left_cancel = TRAVEL_CANCEL_WINDOW - _travel_elapsed(u)
        text += f"\n\n<b><i>Поездку ещё можно отменить — осталось {left_cancel} сек.</i></b>"
    return text


@router.message(Command("citytravel", "путешествие", "ехать"))
async def cmd_city_travel(message: Message):
    u = await aio_get_city_user(message.from_user.id, message.from_user.username or "")
    if _is_traveling(u):
        await message.reply(
            _traveling_status_text(u),
            parse_mode="HTML",
            reply_markup=city_travel_active_keyboard(_can_cancel_travel(u)),
        )
        return

    args = (message.text or "").split()[1:]
    if len(args) != 1:
        await message.reply(
            f"{_tge('travel', '🧭')} <b><i>КУДА ОТПРАВЛЯЕМСЯ?</i></b>\n<b><i>Выберите пункт назначения</i></b> ✨\n━━━━━━━━━━━━━━━━━━━━",
            parse_mode="HTML",
            reply_markup=city_travel_keyboard(),
        )
        return

    dest = _parse_city(args[0])
    if not dest:
        await message.reply("❌ Неизвестный город. Доступно: Северный, Южный, Столица.")
        return

    ok, text = await _do_travel(message.from_user.id, message.from_user.username or "", dest)
    await message.reply(
        text, parse_mode="HTML",
        reply_markup=city_travel_active_keyboard(True) if ok else None,
    )


@router.message(Command("citycancel", "отмена", "cancel"))
async def cmd_city_cancel_travel(message: Message):
    ok, text = await _do_cancel_travel(message.from_user.id, message.from_user.username or "")
    await message.reply(text, parse_mode="HTML", reply_markup=city_back_keyboard())


async def _get_perishables_freshness(user_id: int) -> dict:
    """Собирает {item_type: секунд_до_порчи} по всем скоропортящимся товарам."""
    result = {}
    for item, info in ITEMS.items():
        if info.get("perishable"):
            left = await aio_get_item_freshness_left(user_id, item)
            if left is not None:
                result[item] = left
    return result


@router.message(Command("citybag", "сумка", "bag"))
async def cmd_city_inventory(message: Message):
    u = await aio_get_city_user(message.from_user.id, message.from_user.username or "")
    inv = await aio_get_inventory(u["user_id"])
    freshness = await _get_perishables_freshness(u["user_id"])
    await message.reply(
        _bag_text(inv, u, freshness),
        parse_mode="HTML",
        reply_markup=city_bag_keyboard(),
    )


@router.message(Command("citycart", "повозка", "cart"))
async def cmd_city_cart(message: Message):
    u = await aio_get_city_user(message.from_user.id, message.from_user.username or "")
    inv = await aio_get_inventory(u["user_id"])
    await message.reply(
        _cart_text(u, inv),
        parse_mode="HTML",
        reply_markup=city_cart_keyboard(get_cart_next_tier(u) is not None),
    )


@router.message(Command("citycartup", "прокачатьповозку", "cartup"))
async def cmd_city_cart_upgrade(message: Message):
    ok, err, nxt = await aio_try_upgrade_cart(message.from_user.id)
    if not ok:
        await message.reply(err, parse_mode="HTML", reply_markup=city_back_keyboard())
        return

    u = await aio_get_city_user(message.from_user.id, message.from_user.username or "")
    await message.reply(
        "✅ <b><i>ПОВОЗКА ПРОКАЧАНА!</i></b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🐎 Новая повозка: <b><i>{nxt['name']}</i></b>\n"
        f"📦 Новый лимит перевозки: <b><i>{_fmt(nxt['capacity'])}</i></b> <b><i>ед.</i></b>\n"
        f"{_tge('currency', CURRENCY_EMOJI)} Списано: <b><i>{_fmt(nxt['cost'])}</i></b> <b><i>{CURRENCY_NAME}</i></b>\n"
        f"{_tge('balance', CURRENCY_EMOJI)} Остаток: <b><i>{_fmt(u['balance'])}</i></b> <b><i>{CURRENCY_NAME}</i></b>",
        parse_mode="HTML",
        reply_markup=city_back_keyboard(),
    )


@router.message(Command("citywarehouse", "склад", "warehouse"))
async def cmd_city_warehouse(message: Message):
    u = await aio_get_city_user(message.from_user.id, message.from_user.username or "")
    wh = await aio_get_warehouse_stock(u["user_id"])
    await message.reply(
        _warehouse_text(u, wh),
        parse_mode="HTML",
        reply_markup=city_warehouse_keyboard(get_warehouse_next_tier(u) is not None),
    )


@router.message(Command("citywarehouseup", "прокачатьсклад", "warehouseup"))
async def cmd_city_warehouse_upgrade(message: Message):
    ok, err, nxt = await aio_try_upgrade_warehouse(message.from_user.id)
    if not ok:
        await message.reply(err, parse_mode="HTML", reply_markup=city_back_keyboard())
        return

    u = await aio_get_city_user(message.from_user.id, message.from_user.username or "")
    await message.reply(
        "✅ <b><i>СКЛАД ПРОКАЧАН!</i></b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Новый склад: <b><i>{nxt['name']}</i></b>\n"
        f"📦 Новый лимит хранения: <b><i>{_fmt(nxt['capacity'])}</i></b> <b><i>ед.</i></b>\n"
        f"{_tge('currency', CURRENCY_EMOJI)} Списано: <b><i>{_fmt(nxt['cost'])}</i></b> <b><i>{CURRENCY_NAME}</i></b>\n"
        f"{_tge('balance', CURRENCY_EMOJI)} Остаток: <b><i>{_fmt(u['balance'])}</i></b> <b><i>{CURRENCY_NAME}</i></b>",
        parse_mode="HTML",
        reply_markup=city_back_keyboard(),
    )


@router.message(Command("citynews", "новости"))
async def cmd_city_news(message: Message):
    await message.reply(
        await _news_text(),
        parse_mode="HTML",
        reply_markup=city_news_keyboard(),
    )


@router.message(Command("cityroute", "маршрут", "route"))
async def cmd_city_trade_route(message: Message):
    await message.reply(
        await _route_text(),
        parse_mode="HTML",
        reply_markup=city_route_keyboard(),
    )


@router.message(Command("помощь", "cityhelp"))
async def cmd_city_help(message: Message):
    await message.reply(
        _help_text(),
        parse_mode="HTML",
        reply_markup=city_help_keyboard(),
    )


@router.message(Command("cityexchange", "обмен", "exchange"))
async def cmd_city_exchange(message: Message):
    u = await aio_get_city_user(message.from_user.id, message.from_user.username or "")
    args = (message.text or "").split()[1:]

    if not args:
        await message.reply(
            await _exchange_text(u),
            parse_mode="HTML",
            reply_markup=city_exchange_keyboard(),
        )
        return

    raw = args[0].strip().lower()
    if raw in ("все", "всё", "all"):
        qty = u["balance"]
    else:
        try:
            qty = int(raw)
        except ValueError:
            await message.reply(
                f"📝 Использование: <code>/cityexchange [количество]</code>\n"
                f"<b><i>Например: /cityexchange 20 или /cityexchange все</i></b>",
                parse_mode="HTML",
            )
            return

    if qty <= 0:
        await message.reply("❌ Количество должно быть положительным.")
        return

    ok, err, coins, rate = await aio_exchange_crystals_for_coins(message.from_user.id, qty)
    if not ok:
        await message.reply(err, parse_mode="HTML")
        return

    await message.reply(
        f"{_tge('exchange', '🔁')} <b><i>ОБМЕН СОВЕРШЁН</i></b>\n"
        "<b><i>Кристаллы зачислены в монеты основного бота</i></b> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{_tge('currency', CURRENCY_EMOJI)} Обменяно: <b><i>{_fmt(qty)}</i></b> {CURRENCY_NAME}\n"
        f"📈 Курс: <b><i>{rate}</i></b> {COIN_TAG} <b><i>за 1 {CURRENCY_NAME_SINGULAR}</i></b>\n"
        f"{COIN_TAG} Получено: <b><i>{_fmt(coins)}</i></b> монет",
        parse_mode="HTML",
        reply_markup=city_back_keyboard(),
    )


# ──────────────────────────────────────────────────────────────────────────
# ОБРАБОТКА КНОПОК НАВИГАЦИИ (callback_query)
# ──────────────────────────────────────────────────────────────────────────

from aiogram.types import CallbackQuery  # noqa: E402


def _city_check_owner(call: CallbackQuery) -> bool:
    """Проверяет, что кнопку нажимает тот же пользователь, который вызвал
    команду города (сообщение бота было отправлено через .reply()).
    Возвращает True, если можно продолжать обработку."""
    owner_msg = call.message.reply_to_message
    if owner_msg and owner_msg.from_user:
        if call.from_user.id != owner_msg.from_user.id:
            return False
    return True


async def _city_deny(call: CallbackQuery):
    await call.answer("❌ Это не ваша кнопка!", show_alert=True)


@router.callback_query(F.data == "city_nav_profile")
async def cb_city_profile(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    u = await aio_get_city_user(call.from_user.id, call.from_user.username or "")
    inv = await aio_get_inventory(u["user_id"])
    await call.message.edit_text(
        _profile_text(u, inv), parse_mode="HTML", reply_markup=city_main_menu_keyboard()
    )
    await call.answer()


@router.callback_query(F.data == "city_nav_market")
async def cb_city_market(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    await call.message.edit_text(
        await _market_text(), parse_mode="HTML", reply_markup=city_market_keyboard()
    )
    await call.answer()


@router.callback_query(F.data == "city_nav_bag")
async def cb_city_bag(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    u = await aio_get_city_user(call.from_user.id, call.from_user.username or "")
    inv = await aio_get_inventory(call.from_user.id)
    freshness = await _get_perishables_freshness(call.from_user.id)
    await call.message.edit_text(
        _bag_text(inv, u, freshness), parse_mode="HTML", reply_markup=city_bag_keyboard()
    )
    await call.answer()


@router.callback_query(F.data == "city_nav_cart")
async def cb_city_cart(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    u = await aio_get_city_user(call.from_user.id, call.from_user.username or "")
    inv = await aio_get_inventory(u["user_id"])
    await call.message.edit_text(
        _cart_text(u, inv),
        parse_mode="HTML",
        reply_markup=city_cart_keyboard(get_cart_next_tier(u) is not None),
    )
    await call.answer()


@router.callback_query(F.data == "city_cart_upgrade")
async def cb_city_cart_upgrade(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    ok, err, nxt = await aio_try_upgrade_cart(call.from_user.id)
    if not ok:
        await call.answer(err, show_alert=True)
        return

    u = await aio_get_city_user(call.from_user.id, call.from_user.username or "")
    inv = await aio_get_inventory(u["user_id"])
    await call.message.edit_text(
        _cart_text(u, inv),
        parse_mode="HTML",
        reply_markup=city_cart_keyboard(get_cart_next_tier(u) is not None),
    )
    await call.answer(f"✅ Повозка прокачана до «{nxt['name']}»!", show_alert=True)


@router.callback_query(F.data == "city_nav_warehouse")
async def cb_city_warehouse(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    u = await aio_get_city_user(call.from_user.id, call.from_user.username or "")
    wh = await aio_get_warehouse_stock(u["user_id"])
    await call.message.edit_text(
        _warehouse_text(u, wh),
        parse_mode="HTML",
        reply_markup=city_warehouse_keyboard(get_warehouse_next_tier(u) is not None),
    )
    await call.answer()


@router.callback_query(F.data == "city_warehouse_upgrade")
async def cb_city_warehouse_upgrade(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    ok, err, nxt = await aio_try_upgrade_warehouse(call.from_user.id)
    if not ok:
        await call.answer(err, show_alert=True)
        return

    u = await aio_get_city_user(call.from_user.id, call.from_user.username or "")
    wh = await aio_get_warehouse_stock(u["user_id"])
    await call.message.edit_text(
        _warehouse_text(u, wh),
        parse_mode="HTML",
        reply_markup=city_warehouse_keyboard(get_warehouse_next_tier(u) is not None),
    )
    await call.answer(f"✅ Склад прокачан до «{nxt['name']}»!", show_alert=True)


@router.callback_query(F.data == "city_wh_buy")
async def cb_city_wh_buy_menu(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    u = await aio_get_city_user(call.from_user.id, call.from_user.username or "")
    inv = await aio_get_inventory(u["user_id"])
    await call.message.edit_text(
        f"{_tge('warehouse', '📦')} <b><i>ПОЛОЖИТЬ В СКЛАД</i></b>\n"
        "<b><i>Выберите товар из сумки, чтобы убрать на склад</i></b> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML",
        reply_markup=city_warehouse_item_keyboard(inv),
    )
    await call.answer()


@router.callback_query(F.data.startswith("city_wh_buy_item_"))
async def cb_city_wh_buy_item(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    item = call.data.replace("city_wh_buy_item_", "", 1)
    if item not in ITEMS:
        await call.answer("❌ Неизвестный товар.", show_alert=True)
        return

    u = await aio_get_city_user(call.from_user.id, call.from_user.username or "")

    inv = await aio_get_inventory(u["user_id"])
    have = inv.get(item, 0)
    if have <= 0:
        await call.answer("🎒 У вас нет этого товара в сумке.", show_alert=True)
        return

    wh = await aio_get_warehouse_stock(u["user_id"])
    wh_capacity = get_warehouse_capacity(u)
    free_space = max(0, wh_capacity - total_inventory_qty(wh))
    max_qty = max(0, min(have, free_space))

    text = (
        f"{_item_emoji(item)} <b><i>{ITEMS[item]['name'].upper()}</i></b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎒 В сумке: <b><i>{_fmt(have)}</i></b> <b><i>ед.</i></b>\n"
        f"📦 Свободно на складе: <b><i>{_fmt(free_space)}</i></b> <b><i>ед.</i></b>\n\n"
        "<b><i>Сколько убрать на склад?</i></b>"
    )
    if max_qty <= 0:
        text += "\n\n❌ <b><i>Сейчас нельзя переложить ни одной единицы — на складе нет места.</i></b>"

    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=city_warehouse_qty_keyboard(item, max_qty),
    )
    await call.answer()


@router.callback_query(F.data.startswith("city_wh_buy_qty_"))
async def cb_city_wh_buy_qty(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    payload = call.data.replace("city_wh_buy_qty_", "", 1)
    # Количество — всегда последний токен; товар может содержать "_"
    # (forbidden_scrolls), поэтому режем с конца строки.
    item, _, qty_raw = payload.rpartition("_")
    if item not in ITEMS:
        await call.answer("❌ Неизвестный товар.", show_alert=True)
        return
    try:
        qty = int(qty_raw)
    except ValueError:
        await call.answer("❌ Некорректное количество.", show_alert=True)
        return
    if qty <= 0:
        await call.answer("❌ Нечего перекладывать.", show_alert=True)
        return

    u = await aio_get_city_user(call.from_user.id, call.from_user.username or "")

    # ── Перепроверяем лимит склада перед перекладкой — экран с кнопками мог
    # быть открыт какое-то время назад, за это время склад мог заполниться
    # другой перекладкой. Сама перекладка всё равно атомарна
    # (try_deposit_to_warehouse), но лучше сразу дать понятную ошибку, чем
    # молча обрезать qty.
    wh = await aio_get_warehouse_stock(u["user_id"])
    stored = total_inventory_qty(wh)
    wh_capacity = get_warehouse_capacity(u)
    if stored + qty > wh_capacity:
        await call.answer(
            f"📦 Склад переполнен — свободно только {_fmt(max(0, wh_capacity - stored))} ед.",
            show_alert=True,
        )
        return

    if not await aio_try_deposit_to_warehouse(u["user_id"], item, qty):
        await call.answer("🎒 В сумке не хватает этого товара.", show_alert=True)
        return

    u2 = await aio_get_city_user(call.from_user.id, call.from_user.username or "")
    wh2 = await aio_get_warehouse_stock(u["user_id"])
    await call.message.edit_text(
        _warehouse_text(u2, wh2),
        parse_mode="HTML",
        reply_markup=city_warehouse_keyboard(get_warehouse_next_tier(u2) is not None),
    )
    await call.answer(
        f"✅ Убрано на склад: {qty} × {ITEMS[item]['name']}!",
        show_alert=True,
    )


@router.callback_query(F.data == "city_wh_sell")
async def cb_city_wh_sell_menu(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    u = await aio_get_city_user(call.from_user.id, call.from_user.username or "")
    wh = await aio_get_warehouse_stock(u["user_id"])
    await call.message.edit_text(
        f"{_tge('warehouse', '📦')} <b><i>ЗАБРАТЬ СО СКЛАДА</i></b>\n"
        "<b><i>Выберите товар, чтобы вернуть его в сумку</i></b> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML",
        reply_markup=city_warehouse_sell_item_keyboard(wh),
    )
    await call.answer()


@router.callback_query(F.data.startswith("city_wh_sell_item_"))
async def cb_city_wh_sell_item(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    item = call.data.replace("city_wh_sell_item_", "", 1)
    if item not in ITEMS:
        await call.answer("❌ Неизвестный товар.", show_alert=True)
        return

    u = await aio_get_city_user(call.from_user.id, call.from_user.username or "")

    wh = await aio_get_warehouse_stock(u["user_id"])
    owned = wh.get(item, 0)
    if owned <= 0:
        await call.answer("📦 У вас нет этого товара на складе.", show_alert=True)
        return

    text = (
        f"{_item_emoji(item)} <b><i>{ITEMS[item]['name'].upper()}</i></b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 На складе: <b><i>{_fmt(owned)}</i></b> <b><i>ед.</i></b>\n\n"
        "<b><i>Сколько забрать в сумку?</i></b>"
    )

    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=city_warehouse_sell_qty_keyboard(item, owned),
    )
    await call.answer()


@router.callback_query(F.data.startswith("city_wh_sell_qty_"))
async def cb_city_wh_sell_qty(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    payload = call.data.replace("city_wh_sell_qty_", "", 1)
    # Количество — всегда последний токен; товар может содержать "_"
    # (forbidden_scrolls), поэтому режем с конца строки.
    item, _, qty_raw = payload.rpartition("_")
    if item not in ITEMS:
        await call.answer("❌ Неизвестный товар.", show_alert=True)
        return
    try:
        qty = int(qty_raw)
    except ValueError:
        await call.answer("❌ Некорректное количество.", show_alert=True)
        return
    if qty <= 0:
        await call.answer("❌ Нечего забирать.", show_alert=True)
        return

    u = await aio_get_city_user(call.from_user.id, call.from_user.username or "")

    # ── Перепроверяем остаток перед перекладкой — экран с кнопками мог быть
    # открыт какое-то время назад, за это время товар мог закончиться
    # (например, забран по другому каналу). Сама перекладка всё равно
    # атомарна (try_withdraw_from_warehouse), но лучше сразу дать понятную
    # ошибку, чем молча обрезать qty.
    wh = await aio_get_warehouse_stock(u["user_id"])
    if qty > wh.get(item, 0):
        await call.answer(
            f"📦 На складе только {_fmt(wh.get(item, 0))} ед. этого товара.",
            show_alert=True,
        )
        return

    if not await aio_try_withdraw_from_warehouse(u["user_id"], item, qty):
        await call.answer("📦 На складе недостаточно этого товара.", show_alert=True)
        return

    if ITEMS[item].get("perishable"):
        # Товар не портился, пока лежал на складе — при возврате в сумку
        # таймер свежести стартует заново, как при новой покупке.
        await aio_refresh_item_freshness(u["user_id"], item)

    u2 = await aio_get_city_user(call.from_user.id, call.from_user.username or "")
    wh2 = await aio_get_warehouse_stock(u["user_id"])
    await call.message.edit_text(
        _warehouse_text(u2, wh2),
        parse_mode="HTML",
        reply_markup=city_warehouse_keyboard(get_warehouse_next_tier(u2) is not None),
    )
    await call.answer(
        f"✅ Забрано со склада: {qty} × {ITEMS[item]['name']}!",
        show_alert=True,
    )


@router.callback_query(F.data == "city_nav_defense")
async def cb_city_defense(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    u = await aio_get_city_user(call.from_user.id, call.from_user.username or "")
    await call.message.edit_text(
        _defense_text(u), parse_mode="HTML", reply_markup=city_defense_keyboard(u)
    )
    await call.answer()


@router.callback_query(F.data.in_({
    "city_buy_defense_fake_docs", "city_buy_defense_escort", "city_buy_defense_security",
}))
async def cb_city_buy_defense(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    kind = call.data.removeprefix("city_buy_defense_")
    ok, msg = await aio_try_buy_protection(call.from_user.id, kind)
    if not ok:
        await call.answer(msg, show_alert=True)
        return

    u = await aio_get_city_user(call.from_user.id, call.from_user.username or "")
    await call.message.edit_text(
        _defense_text(u), parse_mode="HTML", reply_markup=city_defense_keyboard(u)
    )
    await call.answer(msg, show_alert=True)


@router.callback_query(F.data == "city_nav_capsules")
async def cb_city_capsules(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    active = await aio_get_active_capsules(call.from_user.id)
    await call.message.edit_text(
        _capsules_menu_text(active), parse_mode="HTML", reply_markup=city_capsules_menu_keyboard(active)
    )
    await call.answer()


@router.callback_query(F.data.startswith("city_capsule_cat_"))
async def cb_city_capsule_category(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    category = call.data.removeprefix("city_capsule_cat_")
    if category not in CAPSULE_CATEGORIES:
        await call.answer("❌ Неизвестная категория.", show_alert=True)
        return
    owned = await aio_get_capsules_owned(call.from_user.id)
    active = await aio_get_active_capsules(call.from_user.id)
    await call.message.edit_text(
        _capsule_category_text(category, owned, active.get(category)),
        parse_mode="HTML",
        reply_markup=city_capsule_category_keyboard(category, owned, active.get(category)),
    )
    await call.answer()


@router.callback_query(F.data.startswith("city_capsule_view_"))
async def cb_city_capsule_view(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    capsule_id = call.data.removeprefix("city_capsule_view_")
    if capsule_id not in CAPSULES:
        await call.answer("❌ Неизвестная капсула.", show_alert=True)
        return
    cap = CAPSULES[capsule_id]
    u = await aio_get_city_user(call.from_user.id, call.from_user.username or "")
    owned = (await aio_get_capsules_owned(call.from_user.id)).get(capsule_id, 0)
    active = await aio_get_active_capsules(call.from_user.id)
    is_active = active.get(cap["category"]) == capsule_id
    await call.message.edit_text(
        _capsule_detail_text(capsule_id, owned, is_active),
        parse_mode="HTML",
        reply_markup=city_capsule_detail_keyboard(capsule_id, owned, is_active, u["balance"]),
    )
    await call.answer()


@router.callback_query(F.data.startswith("city_capsule_buy_"))
async def cb_city_capsule_buy(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    capsule_id = call.data.removeprefix("city_capsule_buy_")
    if capsule_id not in CAPSULES:
        await call.answer("❌ Неизвестная капсула.", show_alert=True)
        return
    ok, msg = await aio_try_buy_capsule(call.from_user.id, capsule_id)
    if not ok:
        await call.answer(msg, show_alert=True)
        return

    cap = CAPSULES[capsule_id]
    u = await aio_get_city_user(call.from_user.id, call.from_user.username or "")
    owned = (await aio_get_capsules_owned(call.from_user.id)).get(capsule_id, 0)
    active = await aio_get_active_capsules(call.from_user.id)
    is_active = active.get(cap["category"]) == capsule_id
    await call.message.edit_text(
        _capsule_detail_text(capsule_id, owned, is_active),
        parse_mode="HTML",
        reply_markup=city_capsule_detail_keyboard(capsule_id, owned, is_active, u["balance"]),
    )
    await call.answer(msg, show_alert=True)


@router.callback_query(F.data.startswith("city_capsule_use_"))
async def cb_city_capsule_use(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    capsule_id = call.data.removeprefix("city_capsule_use_")
    if capsule_id not in CAPSULES:
        await call.answer("❌ Неизвестная капсула.", show_alert=True)
        return
    ok, msg = await aio_try_use_capsule(call.from_user.id, capsule_id)
    if not ok:
        await call.answer(msg, show_alert=True)
        return

    cap = CAPSULES[capsule_id]
    u = await aio_get_city_user(call.from_user.id, call.from_user.username or "")
    owned = (await aio_get_capsules_owned(call.from_user.id)).get(capsule_id, 0)
    await call.message.edit_text(
        _capsule_detail_text(capsule_id, owned, True),
        parse_mode="HTML",
        reply_markup=city_capsule_detail_keyboard(capsule_id, owned, True, u["balance"]),
    )
    await call.answer(msg, show_alert=True)


@router.callback_query(F.data == "city_nav_news")
async def cb_city_news(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    await call.message.edit_text(
        await _news_text(), parse_mode="HTML", reply_markup=city_news_keyboard()
    )
    await call.answer()


@router.callback_query(F.data == "city_nav_exchange")
async def cb_city_exchange(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    u = await aio_get_city_user(call.from_user.id, call.from_user.username or "")
    await call.message.edit_text(
        await _exchange_text(u), parse_mode="HTML", reply_markup=city_exchange_keyboard()
    )
    await call.answer()


@router.callback_query(F.data == "city_nav_route")
async def cb_city_route(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    await call.message.edit_text(
        await _route_text(), parse_mode="HTML", reply_markup=city_route_keyboard()
    )
    await call.answer()


@router.callback_query(F.data == "city_nav_help")
async def cb_city_help(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    await call.message.edit_text(
        _help_text(), parse_mode="HTML", reply_markup=city_help_keyboard()
    )
    await call.answer()


@router.callback_query(F.data == "city_nav_travel")
async def cb_city_travel_menu(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    u = await aio_get_city_user(call.from_user.id, call.from_user.username or "")
    if _is_traveling(u):
        await call.message.edit_text(
            _traveling_status_text(u),
            parse_mode="HTML",
            reply_markup=city_travel_active_keyboard(_can_cancel_travel(u)),
        )
        await call.answer()
        return

    await call.message.edit_text(
        f"{_tge('travel', '🧭')} <b><i>КУДА ОТПРАВЛЯЕМСЯ?</i></b>\n<b><i>Выберите пункт назначения</i></b> ✨\n━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML",
        reply_markup=city_travel_keyboard(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("city_go_"))
async def cb_city_go(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    dest = call.data.replace("city_go_", "", 1)
    if dest not in CITIES:
        await call.answer("Неизвестный город", show_alert=True)
        return
    ok, text = await _do_travel(call.from_user.id, call.from_user.username or "", dest)
    await call.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=city_travel_active_keyboard(True) if ok else city_travel_keyboard(),
    )
    await call.answer()


@router.callback_query(F.data == "city_cancel_travel")
async def cb_city_cancel_travel(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    ok, text = await _do_cancel_travel(call.from_user.id, call.from_user.username or "")
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=city_back_keyboard())
    await call.answer()


# ──────────────────────────────────────────────────────────────────────────
# ФОНОВЫЕ ЗАДАЧИ
# Запускать из main.py: asyncio.create_task(city_prices_loop())  и т.д.
# ──────────────────────────────────────────────────────────────────────────

async def city_prices_loop():
    """Обновляет цены каждый час (на часовой границе)."""
    import asyncio
    while True:
        now = datetime.now(timezone.utc)
        next_hour = (now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
        await asyncio.sleep(max(1, (next_hour - now).total_seconds()))
        try:
            await aio_update_all_prices()
        except Exception as e:
            print(f"[city_prices_loop] {e}")


def _city_travel_finish_sync(now: int) -> list:
    """Синхронная часть: находит и завершает истёкшие путешествия.
    Вызывается ТОЛЬКО через asyncio.to_thread (см. city_travel_loop) —
    иначе диск-I/O блокирует event loop для всех пользователей бота."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT user_id, city, travel_end_time FROM city_users "
            "WHERE status='traveling' AND travel_end_time<=?",
            (now,),
        ).fetchall()
        for r in rows:
            conn.execute(
                "UPDATE city_users SET status='free', travel_end_time=NULL, travel_from=NULL WHERE user_id=?",
                (r["user_id"],),
            )
        conn.commit()
        return [dict(r) for r in rows]


async def city_travel_loop(bot):
    """Проверяет каждую минуту, не истекло ли путешествие, и уведомляет игрока."""
    import asyncio
    while True:
        await asyncio.sleep(60)
        try:
            now = int(time.time())
            rows = await asyncio.to_thread(_city_travel_finish_sync, now)

            for r in rows:
                try:
                    await bot.send_message(
                        r["user_id"],
                        f"{_tge('travel', '🧙')} <b><i>ВЫ ПРИБЫЛИ!</i></b>\n"
                        f"<b><i>Добро пожаловать в {r['city']}</i></b> ✨\n\n"
                        "Торговля снова доступна.",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
        except Exception as e:
            print(f"[city_travel_loop] {e}")


async def city_news_loop():
    """Каждые 2 часа генерирует новость, каждую минуту применяет истёкшие прогнозы."""
    import asyncio
    last_news_time = 0
    while True:
        await asyncio.sleep(60)
        try:
            await aio_apply_due_news()
            now = time.time()
            if now - last_news_time >= NEWS_LIFETIME_HOURS * 3600:
                await aio_generate_news()
                last_news_time = now
        except Exception as e:
            print(f"[city_news_loop] {e}")


async def city_exchange_loop():
    """Раз в минуту пересчитывает курс обмена кристаллов на монеты —
    курс растёт вместе с активностью закупок на рынке гильдии."""
    import asyncio
    while True:
        try:
            await aio_refresh_exchange_rate()
        except Exception as e:
            print(f"[city_exchange_loop] {e}")
        await asyncio.sleep(EXCHANGE_RECALC_SECONDS)
