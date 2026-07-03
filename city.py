# city.py — модуль "Арбитражный трейдинг" (география)
# Полностью отдельный модуль: своя БД-логика (в той же базе tgstellar.db),
# свои хендлеры, свои фоновые таски. Никак не пересекается с командами
# /profile, /shop, /inventory, /sell и т.д. из main.py — все команды здесь
# названы по-другому (с префиксом city), чтобы не было конфликтов.

import sqlite3
import random
import time
from datetime import datetime, timedelta, timezone, date

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import DB_PATH  # используем тот же файл БД, что и весь бот
from database import get_user as _db_get_user, update_user as _db_update_user
from database import get_user_by_id_or_username as _db_get_user_by_id_or_username

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

    main_user = _db_get_user(user.id)
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
}

# Модификаторы базовой цены по городам
CITY_MODIFIERS = {
    "Северный": {"potions": 0.7, "scrolls": 1.3, "food": 1.3},
    "Южный":    {"potions": 1.3, "scrolls": 0.7, "food": 0.7},
    "Столица":  {"potions": 1.2, "scrolls": 1.2, "food": 1.2},
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
    "cart": "5386676074535597403",               # 🐎 Повозка
}

TRAVEL_COST = 50
TRAVEL_MINUTES = 15
TRAVEL_CANCEL_WINDOW = 120  # сек. — в течение скольких секунд после старта можно отменить поездку
CUSTOMS_LIMIT = 200          # лимит единиц товара, выше которого возможна конфискация
CUSTOMS_CHANCE = 0.30        # шанс конфискации
CUSTOMS_FINE = 50

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

def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS city_inventory (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER NOT NULL,
                item_type TEXT NOT NULL,
                quantity  INTEGER NOT NULL DEFAULT 0,
                UNIQUE(user_id, item_type)
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
    with _conn() as conn:
        rows = conn.execute(
            "SELECT item_type, quantity FROM city_inventory WHERE user_id=?", (user_id,)
        ).fetchall()
    inv = {item: 0 for item in ITEMS}
    for r in rows:
        inv[r["item_type"]] = r["quantity"]
    return inv


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


# ──────────────────────────────────────────────────────────────────────────
# ВСПОМОГАТЕЛЬНОЕ
# ──────────────────────────────────────────────────────────────────────────

def _fmt(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def _crystals(n: int) -> str:
    return f"{_fmt(n)} {_tge('currency', CURRENCY_EMOJI)} {CURRENCY_NAME}"


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


def best_trade_route() -> dict | None:
    """Ищет пару город-товар с максимальной разницей (продать дороже всего минус купить дешевле всего)."""
    prices = get_all_prices()
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
        InlineKeyboardButton(text=" Топ кристаллов", callback_data="crystop_alltime", icon_custom_emoji_id=BTN_EMOJI["currency"]),
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


def city_bag_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=" На рынок", callback_data="city_nav_market", icon_custom_emoji_id=BTN_EMOJI["market"]),
        InlineKeyboardButton(text=" В путь", callback_data="city_nav_travel", icon_custom_emoji_id=BTN_EMOJI["travel"]),
    )
    builder.row(InlineKeyboardButton(text=" Повозка", callback_data="city_nav_cart", icon_custom_emoji_id=BTN_EMOJI["cart"]))
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
        f"  {ITEMS['potions']['emoji']} Зелья — <b><i>{inv['potions']}</i></b> <b><i>шт.</i></b>\n"
        f"  {ITEMS['scrolls']['emoji']} Свитки — <b><i>{inv['scrolls']}</i></b> <b><i>шт.</i></b>\n"
        f"  {ITEMS['food']['emoji']} Еда — <b><i>{inv['food']}</i></b> <b><i>шт.</i></b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🎁 <b><i>Ежедневный бонус +{DAILY_CRYSTALS} {CURRENCY_NAME} получен сегодня ✅ — заходи завтра за новым</i></b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<b><i>Выберите раздел ниже 👇</i></b>"
    )


def _market_text() -> str:
    prices = get_all_prices()
    lines = [
        f"{_tge('market', '🏪')} <b><i>ТОРГОВЫЕ РЯДЫ</i></b>",
        "<b><i>Актуальные цены по всем городам</i></b> ✨",
        "━━━━━━━━━━━━━━━━━━━━\n",
    ]
    for city in CITIES:
        lines.append(f"{_city_emoji_tag(city)} <b><i>{city}</i></b>")
        for item, info in ITEMS.items():
            p = prices[city][item]
            lines.append(f"   {info['emoji']} <b><i>{info['name']}</i></b> — <b><i>{p}</i></b> {_tge('currency', CURRENCY_EMOJI)}")
        lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"{0} <b><i>Купить —</i></b> <code>/citybuy товар количество</code>".format(_tge("buy", "🛒")))
    lines.append(f"{0} <b><i>Продать —</i></b> <code>/citysell товар количество</code>".format(_tge("sell", "💰")))
    return "\n".join(lines)


def _cart_bar(carried: int, capacity: int, length: int = 12) -> str:
    ratio = 0 if capacity <= 0 else min(1.0, carried / capacity)
    filled = round(ratio * length)
    return "▰" * filled + "▱" * (length - filled)


def _bag_text(inv: dict, u: dict | None = None) -> str:
    total_items = sum(inv.values())
    capacity = get_cart_capacity(u) if u else CART_LEVELS[0]["capacity"]
    bar = _cart_bar(total_items, capacity)
    pct = 0 if capacity <= 0 else min(100, round(total_items / capacity * 100))
    return (
        f"{_tge('bag', '🎒')} <b><i>ИНВЕНТАРЬ ТОРГОВЦА</i></b>\n"
        "<b><i>Что лежит у вас на складе</i></b> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{ITEMS['potions']['emoji']} Зелья: <b><i>{inv['potions']}</i></b> <b><i>шт.</i></b>\n"
        f"{ITEMS['scrolls']['emoji']} Свитки: <b><i>{inv['scrolls']}</i></b> <b><i>шт.</i></b>\n"
        f"{ITEMS['food']['emoji']} Еда: <b><i>{inv['food']}</i></b> <b><i>шт.</i></b>\n\n"
        f"🐎 <b><i>Повозка:</i></b> <b><i>{_fmt(total_items)} / {_fmt(capacity)}</i></b> <b><i>({pct}%)</i></b>\n"
        f"{bar}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ <b><i>Провоз свыше {CUSTOMS_LIMIT} ед. одного товара рискует конфискацией на таможне.</i></b>\n"
        f"📝 <b><i>Прокачать повозку:</i></b> <code>/citycart</code>"
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


def _news_text() -> str:
    news = get_active_news()
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


def _route_text() -> str:
    best = best_trade_route()
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
        f"{info['emoji']} Товар: <b><i>{info['name']}</i></b>\n\n"
        f"{_tge('buy', '🛒')} Купить в {_city_emoji_tag(best['buy_city'])} <b><i>{best['buy_city']}</i></b> — <b><i>{best['buy_price']}</i></b> {_tge('currency', CURRENCY_EMOJI)}\n"
        f"{_tge('sell', '💰')} Продать в {_city_emoji_tag(best['sell_city'])} <b><i>{best['sell_city']}</i></b> — <b><i>{best['sell_price']}</i></b> {_tge('currency', CURRENCY_EMOJI)}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f'<tg-emoji emoji-id="5397916757333654639">🌟</tg-emoji> Прибыль с единицы: <b><i>+{best['profit']}</i></b> {_tge('currency', CURRENCY_EMOJI)} <b><i>(≈{margin_pct}%)</i></b>'
    )


def _exchange_text(u: dict) -> str:
    rate = get_exchange_rate()
    balance = u["balance"]
    potential = balance * rate
    volume = get_recent_buy_volume()
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
        f"{_tge('news', '🗞')} <code>/citynews</code> — <b><i>слухи и прогнозы цен на 2 часа вперёд</i></b>\n"
        f"{_tge('route', '🗺')} <code>/cityroute</code> — <b><i>самый выгодный маршрут прямо сейчас</i></b>\n"
        f"{_tge('exchange', '🔁')} <code>/cityexchange количество</code> — <b><i>обменять кристаллы на монеты</i></b>\n"
        f"{_tge('help', '❓')} <code>/cityhelp</code> — <b><i>эта справка</i></b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<b><i>📦 Товары</i></b>\n"
        f"  {ITEMS['potions']['emoji']} Зелья — <b><i>дёшевы на Севере, дороги на Юге</i></b>\n"
        f"  {ITEMS['scrolls']['emoji']} Свитки — <b><i>дёшевы на Юге, дороги на Севере</i></b>\n"
        f"  {ITEMS['food']['emoji']} Еда — <b><i>дешевле на Юге, дороже на Севере</i></b>\n"
        f"  {_tge('city_capital', '🏛')} Столица — <b><i>всё дорого, но цены стабильнее</i></b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"<b><i>{_tge('travel', '🧭')} Путешествия</i></b>\n"
        f"  • Стоимость дороги: <b><i>{TRAVEL_COST}</i></b> {_tge('currency', CURRENCY_EMOJI)}\n"
        f"  • Время в пути: <b><i>{TRAVEL_MINUTES}</i></b> минут\n"
        "  • <b><i>Во время пути торговля недоступна</i></b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"<b><i>{_tge('customs', '🧙‍♂️')} Таможня (Гильдия магов)</i></b>\n"
        f"  • <b><i>Провоз свыше</i></b> <b><i>{CUSTOMS_LIMIT}</i></b> <b><i>ед. одного товара рискует конфискацией</i></b>\n"
        f"  • Шанс конфискации: <b><i>{int(CUSTOMS_CHANCE * 100)}%</i></b>, штраф <b><i>{CUSTOMS_FINE}</i></b> {_tge('currency', CURRENCY_EMOJI)}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"<b><i>{_tge('cart', '🐎')} Повозка (лимит перевозки)</i></b>\n"
        f"  • <b><i>Базовый лимит:</i></b> <b><i>{_fmt(CART_LEVELS[0]['capacity'])}</i></b> <b><i>ед. товара за раз</i></b>\n"
        f"  • <b><i>Максимум после прокачки:</i></b> <b><i>{_fmt(CART_LEVELS[CART_MAX_LEVEL]['capacity'])}</i></b> <b><i>ед.</i></b>\n"
        f"  • <b><i>Прокачивается за кристаллы, всего {CART_MAX_LEVEL} платных уровней</i></b>\n\n"
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
    main_user = _db_get_user(user.id)
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
    u = get_city_user(message.from_user.id, message.from_user.username or "")
    inv = get_inventory(u["user_id"])
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
        _market_text(),
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

    found = _db_get_user_by_id_or_username(target_raw)
    if not found:
        await message.reply(
            f"❌ Пользователь <code>{target_raw}</code> не найден в базе.",
            parse_mode="HTML",
        )
        return

    new_balance = add_crystals_to_user(found["id"], amount, found.get("username", "") or "")

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
    if len(args) != 2:
        await message.reply(
            "📝 Использование: <code>/citybuy [товар] [количество]</code>\n"
            "<b><i>Например: /citybuy зелья 10</i></b>",
            parse_mode="HTML",
        )
        return

    u = get_city_user(message.from_user.id, message.from_user.username or "")
    if _is_traveling(u):
        await message.reply("🚶 Вы в пути — торговля недоступна до прибытия.")
        return

    item = _parse_item(args[0])
    if not item:
        await message.reply("❌ Неизвестный товар. Доступно: зелья, свитки, еда.")
        return

    try:
        qty = int(args[1])
    except ValueError:
        await message.reply("❌ Количество должно быть числом.")
        return
    if qty <= 0:
        await message.reply("❌ Количество должно быть положительным.")
        return

    capacity = get_cart_capacity(u)
    inv_before = get_inventory(u["user_id"])
    carried = total_inventory_qty(inv_before)
    if carried + qty > capacity:
        free_space = max(0, capacity - carried)
        await message.reply(
            f"🐎 <b><i>Повозка не выдержит столько груза!</i></b>\n"
            f"📦 Лимит повозки: <b><i>{_fmt(capacity)}</i></b> <b><i>ед.</i></b>\n"
            f"📦 Уже везёте: <b><i>{_fmt(carried)}</i></b> <b><i>ед.</i></b>\n"
            f"📦 Свободно места: <b><i>{_fmt(free_space)}</i></b> <b><i>ед.</i></b>\n\n"
            f"<b><i>Прокачайте повозку командой</i></b> <code>/citycart</code> <b><i>, чтобы возить больше груза за раз.</i></b>",
            parse_mode="HTML",
        )
        return

    price = get_price(u["city"], item)
    total = price * qty
    if total > u["balance"]:
        await message.reply(
            f"💸 Недостаточно {CURRENCY_NAME}. Нужно {_crystals(total)}, у вас {_crystals(u['balance'])}.",
            parse_mode="HTML",
        )
        return

    if not try_spend_balance(u["user_id"], total):
        await message.reply(
            f"💸 Недостаточно {CURRENCY_NAME} для этой покупки.",
            parse_mode="HTML",
        )
        return
    if not try_adjust_inventory(u["user_id"], item, qty):
        add_balance(u["user_id"], total)  # откатываем списание, если товар не начислился
        await message.reply(
            "❌ Не удалось начислить товар. Средства возвращены на баланс.",
            parse_mode="HTML",
        )
        return
    register_trade(u["city"], item, "buy")
    log_trade_qty(u["user_id"], qty, "buy")

    await message.reply(
        "✅ <b><i>СДЕЛКА СОВЕРШЕНА</i></b>\n"
        "<b><i>Покупка прошла успешно</i></b> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{ITEMS[item]['emoji']} Куплено: <b><i>{qty} × {ITEMS[item]['name']}</i></b>\n"
        f"💵 Цена за шт.: <b><i>{price}</i></b> {_tge('currency', CURRENCY_EMOJI)}\n"
        f"{_tge('currency', CURRENCY_EMOJI)} Списано: <b><i>{_fmt(total)}</i></b> <b><i>{CURRENCY_NAME}</i></b>\n"
        f"📍 Город: <b><i>{u['city']}</i></b>",
        parse_mode="HTML",
        reply_markup=city_back_keyboard(),
    )


@router.message(Command("citysell", "продать"))
async def cmd_city_sell(message: Message):
    args = (message.text or "").split()[1:]
    if len(args) != 2:
        await message.reply(
            "📝 Использование: <code>/citysell [товар] [количество]</code>\n"
            "<b><i>Например: /citysell свитки 5</i></b>",
            parse_mode="HTML",
        )
        return

    u = get_city_user(message.from_user.id, message.from_user.username or "")
    if _is_traveling(u):
        await message.reply("🚶 Вы в пути — торговля недоступна до прибытия.")
        return

    item = _parse_item(args[0])
    if not item:
        await message.reply("❌ Неизвестный товар. Доступно: зелья, свитки, еда.")
        return

    try:
        qty = int(args[1])
    except ValueError:
        await message.reply("❌ Количество должно быть числом.")
        return
    if qty <= 0:
        await message.reply("❌ Количество должно быть положительным.")
        return

    inv = get_inventory(u["user_id"])
    if qty > inv[item]:
        await message.reply(f"📦 У вас только <b><i>{inv[item]}</i></b> единиц этого товара.", parse_mode="HTML")
        return

    if not try_adjust_inventory(u["user_id"], item, -qty):
        await message.reply(f"📦 У вас недостаточно этого товара.", parse_mode="HTML")
        return

    price = get_price(u["city"], item)
    total = price * qty
    add_balance(u["user_id"], total)
    register_trade(u["city"], item, "sell")
    log_trade_qty(u["user_id"], qty, "sell")

    await message.reply(
        "✅ <b><i>СДЕЛКА СОВЕРШЕНА</i></b>\n"
        "<b><i>Продажа прошла успешно</i></b> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{ITEMS[item]['emoji']} Продано: <b><i>{qty} × {ITEMS[item]['name']}</i></b>\n"
        f"💵 Цена за шт.: <b><i>{price}</i></b> {_tge('currency', CURRENCY_EMOJI)}\n"
        f"{_tge('currency', CURRENCY_EMOJI)} Получено: <b><i>{_fmt(total)}</i></b> <b><i>{CURRENCY_NAME}</i></b>\n"
        f"📍 Город: <b><i>{u['city']}</i></b>",
        parse_mode="HTML",
        reply_markup=city_back_keyboard(),
    )


async def _do_travel(user_id: int, username: str, dest: str):
    """Общая логика путешествия. Возвращает (ok, text)."""
    u = get_city_user(user_id, username)
    if _is_traveling(u):
        return False, "🚶 Вы уже в пути."
    if dest == u["city"]:
        return False, "📍 Вы уже находитесь в этом городе."

    if not try_spend_balance(u["user_id"], TRAVEL_COST):
        return False, f"💸 Недостаточно {CURRENCY_NAME} на дорогу. Нужно {_crystals(TRAVEL_COST)}."

    origin_city = u["city"]

    inv = get_inventory(u["user_id"])
    confiscated = []
    fine_total = 0
    for item, qty in inv.items():
        if qty > CUSTOMS_LIMIT and random.random() < CUSTOMS_CHANCE:
            taken = force_confiscate_inventory(u["user_id"], item)
            if taken > 0:
                confiscated.append(ITEMS[item]["name"])
                fine_total += CUSTOMS_FINE

    if fine_total:
        spend_up_to(u["user_id"], fine_total)  # не уводит баланс в минус

    end_time = int(time.time()) + TRAVEL_MINUTES * 60
    update_city_user(
        u["user_id"],
        status="traveling",
        travel_end_time=end_time,
        city=dest,
        travel_from=origin_city,
    )

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
    u = get_city_user(user_id, username)
    if not _is_traveling(u):
        return False, "📍 Вы сейчас никуда не едете."
    if not _can_cancel_travel(u):
        return False, "⏳ Время на отмену уже истекло — поездку можно только завершить."

    origin = u["travel_from"] or u["city"]
    update_city_user(
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
    u = get_city_user(message.from_user.id, message.from_user.username or "")
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


@router.message(Command("citybag", "сумка", "bag"))
async def cmd_city_inventory(message: Message):
    u = get_city_user(message.from_user.id, message.from_user.username or "")
    inv = get_inventory(u["user_id"])
    await message.reply(
        _bag_text(inv, u),
        parse_mode="HTML",
        reply_markup=city_bag_keyboard(),
    )


@router.message(Command("citycart", "повозка", "cart"))
async def cmd_city_cart(message: Message):
    u = get_city_user(message.from_user.id, message.from_user.username or "")
    inv = get_inventory(u["user_id"])
    await message.reply(
        _cart_text(u, inv),
        parse_mode="HTML",
        reply_markup=city_cart_keyboard(get_cart_next_tier(u) is not None),
    )


@router.message(Command("citycartup", "прокачатьповозку", "cartup"))
async def cmd_city_cart_upgrade(message: Message):
    ok, err, nxt = try_upgrade_cart(message.from_user.id)
    if not ok:
        await message.reply(err, parse_mode="HTML", reply_markup=city_back_keyboard())
        return

    u = get_city_user(message.from_user.id, message.from_user.username or "")
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


@router.message(Command("citynews", "новости"))
async def cmd_city_news(message: Message):
    await message.reply(
        _news_text(),
        parse_mode="HTML",
        reply_markup=city_news_keyboard(),
    )


@router.message(Command("cityroute", "маршрут", "route"))
async def cmd_city_trade_route(message: Message):
    await message.reply(
        _route_text(),
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
    u = get_city_user(message.from_user.id, message.from_user.username or "")
    args = (message.text or "").split()[1:]

    if not args:
        await message.reply(
            _exchange_text(u),
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

    ok, err, coins, rate = exchange_crystals_for_coins(message.from_user.id, qty)
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
    u = get_city_user(call.from_user.id, call.from_user.username or "")
    inv = get_inventory(u["user_id"])
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
        _market_text(), parse_mode="HTML", reply_markup=city_market_keyboard()
    )
    await call.answer()


@router.callback_query(F.data == "city_nav_bag")
async def cb_city_bag(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    u = get_city_user(call.from_user.id, call.from_user.username or "")
    inv = get_inventory(call.from_user.id)
    await call.message.edit_text(
        _bag_text(inv, u), parse_mode="HTML", reply_markup=city_bag_keyboard()
    )
    await call.answer()


@router.callback_query(F.data == "city_nav_cart")
async def cb_city_cart(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    u = get_city_user(call.from_user.id, call.from_user.username or "")
    inv = get_inventory(u["user_id"])
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
    ok, err, nxt = try_upgrade_cart(call.from_user.id)
    if not ok:
        await call.answer(err, show_alert=True)
        return

    u = get_city_user(call.from_user.id, call.from_user.username or "")
    inv = get_inventory(u["user_id"])
    await call.message.edit_text(
        _cart_text(u, inv),
        parse_mode="HTML",
        reply_markup=city_cart_keyboard(get_cart_next_tier(u) is not None),
    )
    await call.answer(f"✅ Повозка прокачана до «{nxt['name']}»!", show_alert=True)


@router.callback_query(F.data == "city_nav_news")
async def cb_city_news(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    await call.message.edit_text(
        _news_text(), parse_mode="HTML", reply_markup=city_news_keyboard()
    )
    await call.answer()


@router.callback_query(F.data == "city_nav_exchange")
async def cb_city_exchange(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    u = get_city_user(call.from_user.id, call.from_user.username or "")
    await call.message.edit_text(
        _exchange_text(u), parse_mode="HTML", reply_markup=city_exchange_keyboard()
    )
    await call.answer()


@router.callback_query(F.data == "city_nav_route")
async def cb_city_route(call: CallbackQuery):
    if not _city_check_owner(call):
        await _city_deny(call)
        return
    await call.message.edit_text(
        _route_text(), parse_mode="HTML", reply_markup=city_route_keyboard()
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
    u = get_city_user(call.from_user.id, call.from_user.username or "")
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
            update_all_prices()
        except Exception as e:
            print(f"[city_prices_loop] {e}")


async def city_travel_loop(bot):
    """Проверяет каждую минуту, не истекло ли путешествие, и уведомляет игрока."""
    import asyncio
    while True:
        await asyncio.sleep(60)
        try:
            now = int(time.time())
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
            apply_due_news()
            now = time.time()
            if now - last_news_time >= NEWS_LIFETIME_HOURS * 3600:
                generate_news()
                last_news_time = now
        except Exception as e:
            print(f"[city_news_loop] {e}")


async def city_exchange_loop():
    """Раз в минуту пересчитывает курс обмена кристаллов на монеты —
    курс растёт вместе с активностью закупок на рынке гильдии."""
    import asyncio
    while True:
        try:
            refresh_exchange_rate()
        except Exception as e:
            print(f"[city_exchange_loop] {e}")
        await asyncio.sleep(EXCHANGE_RECALC_SECONDS)
