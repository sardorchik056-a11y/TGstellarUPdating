# city.py — модуль "Арбитражный трейдинг" (география)
# Полностью отдельный модуль: своя БД-логика (в той же базе tgstellar.db),
# свои хендлеры, свои фоновые таски. Никак не пересекается с командами
# /profile, /shop, /inventory, /sell и т.д. из main.py — все команды здесь
# названы по-другому (с префиксом city), чтобы не было конфликтов.

import sqlite3
import random
import time
from datetime import datetime, timedelta, timezone

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import DB_PATH  # используем тот же файл БД, что и весь бот

router = Router(name="city")

# ──────────────────────────────────────────────────────────────────────────
# КОНСТАНТЫ
# ──────────────────────────────────────────────────────────────────────────

CURRENCY_NAME = "кристаллы"
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
}

TRAVEL_COST = 50
TRAVEL_MINUTES = 15
TRAVEL_CANCEL_WINDOW = 120  # сек. — в течение скольких секунд после старта можно отменить поездку
CUSTOMS_LIMIT = 200          # лимит единиц товара, выше которого возможна конфискация
CUSTOMS_CHANCE = 0.30        # шанс конфискации
CUSTOMS_FINE = 50

NEWS_TRUE_CHANCE = 0.60      # вероятность, что подсказка сбудется
NEWS_LIFETIME_HOURS = 2

START_BALANCE = 1000
START_CITY = "Столица"

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
                balance        INTEGER NOT NULL DEFAULT 1000,
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
    with _conn() as conn:
        row = conn.execute("SELECT * FROM city_users WHERE user_id=?", (user_id,)).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO city_users (user_id, username, balance, city, status, travel_end_time) "
                "VALUES (?,?,?,?,?,NULL)",
                (user_id, username or "", START_BALANCE, START_CITY, "free"),
            )
            for item in ITEMS:
                conn.execute(
                    "INSERT OR IGNORE INTO city_inventory (user_id, item_type, quantity) VALUES (?,?,0)",
                    (user_id, item),
                )
            conn.commit()
            row = conn.execute("SELECT * FROM city_users WHERE user_id=?", (user_id,)).fetchone()
    return dict(row)


def update_city_user(user_id: int, **fields):
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields)
    vals = list(fields.values()) + [user_id]
    with _conn() as conn:
        conn.execute(f"UPDATE city_users SET {sets} WHERE user_id=?", vals)
        conn.commit()


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
    with _conn() as conn:
        conn.execute(
            "INSERT INTO city_inventory (user_id, item_type, quantity) VALUES (?,?,?) "
            "ON CONFLICT(user_id, item_type) DO UPDATE SET quantity=excluded.quantity",
            (user_id, item_type, max(0, qty)),
        )
        conn.commit()


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
        InlineKeyboardButton(text=" Новости", callback_data="city_nav_news", icon_custom_emoji_id=BTN_EMOJI["news"]),
        InlineKeyboardButton(text=" Помощь", callback_data="city_nav_help", icon_custom_emoji_id=BTN_EMOJI["help"]),
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


CITY_BTN_EMOJI_KEY = {
    "Северный": "city_north",
    "Южный": "city_south",
    "Столица": "city_capital",
}


def city_travel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for city in CITIES:
        builder.row(InlineKeyboardButton(
            text=f"{CITY_EMOJI[city]} {city}",
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
    status_line = "🟢 <b>Свободен</b> <i>— можно торговать прямо сейчас</i>"
    if _is_traveling(u):
        left = u["travel_end_time"] - int(time.time())
        m, s = max(0, left // 60), max(0, left % 60)
        status_line = f"🚶 <b>В пути</b> <i>— прибытие через {m} мин {s} сек</i>"

    return (
        "🧙‍♂️ <b>ГИЛЬДИЯ ТОРГОВЦЕВ</b>\n"
        "<i>Личный кабинет искателя прибыли</i> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{CURRENCY_EMOJI} Баланс: <b>{_fmt(u['balance'])}</b> <i>{CURRENCY_NAME}</i>\n"
        f"{CITY_EMOJI.get(u['city'], '🏙')} Город: <b>{u['city']}</b>\n"
        f"📡 Статус: {status_line}\n\n"
        "📦 <b>Склад</b>\n"
        f"  {ITEMS['potions']['emoji']} Зелья — <b>{inv['potions']}</b> <i>шт.</i>\n"
        f"  {ITEMS['scrolls']['emoji']} Свитки — <b>{inv['scrolls']}</b> <i>шт.</i>\n"
        f"  {ITEMS['food']['emoji']} Еда — <b>{inv['food']}</b> <i>шт.</i>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Выберите раздел ниже 👇</i>"
    )


def _market_text() -> str:
    prices = get_all_prices()
    lines = [
        "🏪 <b>ТОРГОВЫЕ РЯДЫ</b>",
        "<i>Актуальные цены по всем городам</i> ✨",
        "━━━━━━━━━━━━━━━━━━━━\n",
    ]
    for city in CITIES:
        lines.append(f"{CITY_EMOJI[city]} <b>{city}</b>")
        for item, info in ITEMS.items():
            p = prices[city][item]
            lines.append(f"   {info['emoji']} <i>{info['name']}</i> — <b>{p}</b> {CURRENCY_EMOJI}")
        lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"🛒 <i>Купить —</i> <code>/citybuy товар количество</code>")
    lines.append(f"💰 <i>Продать —</i> <code>/citysell товар количество</code>")
    return "\n".join(lines)


def _bag_text(inv: dict) -> str:
    total_items = sum(inv.values())
    return (
        "🎒 <b>ИНВЕНТАРЬ ТОРГОВЦА</b>\n"
        "<i>Что лежит у вас на складе</i> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{ITEMS['potions']['emoji']} Зелья: <b>{inv['potions']}</b> <i>шт.</i>\n"
        f"{ITEMS['scrolls']['emoji']} Свитки: <b>{inv['scrolls']}</b> <i>шт.</i>\n"
        f"{ITEMS['food']['emoji']} Еда: <b>{inv['food']}</b> <i>шт.</i>\n\n"
        f"📦 Всего товаров: <b>{total_items}</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ <i>Провоз свыше {CUSTOMS_LIMIT} ед. одного товара рискует конфискацией на таможне.</i>"
    )


def _news_text() -> str:
    news = get_active_news()
    if not news:
        return (
            "🗞 <b>ТОРГОВЫЕ СЛУХИ</b>\n"
            "<i>Прогнозы рынка на ближайшие часы</i> ✨\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "<i>Пока тихо... странники ещё не принесли новостей.\n"
            "Загляните чуть позже.</i>"
        )
    lines = [
        "🗞 <b>ТОРГОВЫЕ СЛУХИ</b>",
        "<i>Прогнозы рынка на ближайшие часы</i> ✨",
        "━━━━━━━━━━━━━━━━━━━━\n",
    ]
    for n in news:
        published = datetime.fromtimestamp(n["created_at"]).strftime("%H:%M")
        lines.append(
            f"🔮 <i>{n['news_text']}</i>\n"
            f"🕒 <i>опубликовано в {published}</i>"
        )
    return "\n\n".join(lines)


def _route_text() -> str:
    best = best_trade_route()
    if not best:
        return (
            "📈 <b>ЛУЧШИЙ ТОРГОВЫЙ МАРШРУТ</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "<i>Сейчас нет выгодных маршрутов — цены во всех городах примерно равны.</i>"
        )
    info = ITEMS[best["item"]]
    margin_pct = round(best["profit"] / max(1, best["buy_price"]) * 100)
    return (
        "📈 <b>ЛУЧШИЙ ТОРГОВЫЙ МАРШРУТ</b>\n"
        "<i>Подсказка гильдии — где заработать прямо сейчас</i> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{info['emoji']} Товар: <b>{info['name']}</b>\n\n"
        f"🛒 Купить в {CITY_EMOJI[best['buy_city']]} <b>{best['buy_city']}</b> — <b>{best['buy_price']}</b> {CURRENCY_EMOJI}\n"
        f"💰 Продать в {CITY_EMOJI[best['sell_city']]} <b>{best['sell_city']}</b> — <b>{best['sell_price']}</b> {CURRENCY_EMOJI}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 Прибыль с единицы: <b>+{best['profit']}</b> {CURRENCY_EMOJI} <i>(≈{margin_pct}%)</i>"
    )


def _help_text() -> str:
    return (
        "❓ <b>СПРАВКА ПО ТРЕЙДИНГУ</b>\n"
        "<i>Арбитражная торговля между городами</i> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>📋 Команды</b>\n"
        "👤 <code>/city</code> — <i>профиль торговца: баланс, город, статус, склад</i>\n"
        "🏪 <code>/citymarket</code> — <i>цены на товары во всех городах</i>\n"
        "🛒 <code>/citybuy товар количество</code> — <i>купить товар</i>\n"
        "💰 <code>/citysell товар количество</code> — <i>продать товар</i>\n"
        "🧭 <code>/citytravel город</code> — <i>отправиться в другой город</i>\n"
        "❌ <code>/citycancel</code> — <i>отменить поездку (только в первые 2 минуты)</i>\n"
        "🎒 <code>/citybag</code> — <i>инвентарь</i>\n"
        "🗞 <code>/citynews</code> — <i>слухи и прогнозы цен на 2 часа вперёд</i>\n"
        "🗺 <code>/cityroute</code> — <i>самый выгодный маршрут прямо сейчас</i>\n"
        "❓ <code>/help</code> — <i>эта справка</i>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<b>📦 Товары</b>\n"
        f"  {ITEMS['potions']['emoji']} Зелья — <i>дёшевы на Севере, дороги на Юге</i>\n"
        f"  {ITEMS['scrolls']['emoji']} Свитки — <i>дёшевы на Юге, дороги на Севере</i>\n"
        f"  {ITEMS['food']['emoji']} Еда — <i>дешевле на Юге, дороже на Севере</i>\n"
        "  🏛 Столица — <i>всё дорого, но цены стабильнее</i>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<b>🧭 Путешествия</b>\n"
        f"  • Стоимость дороги: <b>{TRAVEL_COST}</b> {CURRENCY_EMOJI}\n"
        f"  • Время в пути: <b>{TRAVEL_MINUTES}</b> минут\n"
        "  • <i>Во время пути торговля недоступна</i>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<b>🧙‍♂️ Таможня (Гильдия магов)</b>\n"
        f"  • <i>Провоз свыше</i> <b>{CUSTOMS_LIMIT}</b> <i>ед. одного товара рискует конфискацией</i>\n"
        f"  • Шанс конфискации: <b>{int(CUSTOMS_CHANCE * 100)}%</b>, штраф <b>{CUSTOMS_FINE}</b> {CURRENCY_EMOJI}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<b>💹 Динамика цен</b>\n"
        "  • <i>Цены обновляются каждый час (±20% случайно)</i>\n"
        "  • <i>Массовая скупка повышает цену, массовая продажа — снижает</i>\n\n"
        "<i>Удачной торговли, искатель прибыли!</i> 💎"
    )


# ──────────────────────────────────────────────────────────────────────────
# ХЕНДЛЕРЫ КОМАНД
# (намеренно с другими именами, чтобы не конфликтовать с /profile, /shop,
#  /inventory, /sell и т.д. из main.py)
# ──────────────────────────────────────────────────────────────────────────

@router.message(Command("city", "трейдер", "trader"))
async def cmd_city_profile(message: Message):
    u = get_city_user(message.from_user.id, message.from_user.username or "")
    inv = get_inventory(u["user_id"])
    await message.answer(
        _profile_text(u, inv),
        parse_mode="HTML",
        reply_markup=city_main_menu_keyboard(),
    )


@router.message(Command("citymarket", "рынок", "market"))
async def cmd_city_shop(message: Message):
    await message.answer(
        _market_text(),
        parse_mode="HTML",
        reply_markup=city_market_keyboard(),
    )


@router.message(Command("citybuy", "купить"))
async def cmd_city_buy(message: Message):
    args = (message.text or "").split()[1:]
    if len(args) != 2:
        await message.answer(
            "📝 Использование: <code>/citybuy [товар] [количество]</code>\n"
            "<i>Например: /citybuy зелья 10</i>",
            parse_mode="HTML",
        )
        return

    u = get_city_user(message.from_user.id, message.from_user.username or "")
    if _is_traveling(u):
        await message.answer("🚶 Вы в пути — торговля недоступна до прибытия.")
        return

    item = _parse_item(args[0])
    if not item:
        await message.answer("❌ Неизвестный товар. Доступно: зелья, свитки, еда.")
        return

    try:
        qty = int(args[1])
    except ValueError:
        await message.answer("❌ Количество должно быть числом.")
        return
    if qty <= 0:
        await message.answer("❌ Количество должно быть положительным.")
        return

    price = get_price(u["city"], item)
    total = price * qty
    if total > u["balance"]:
        await message.answer(
            f"💸 Недостаточно {CURRENCY_NAME}. Нужно {_crystals(total)}, у вас {_crystals(u['balance'])}."
        )
        return

    inv = get_inventory(u["user_id"])
    set_inventory_qty(u["user_id"], item, inv[item] + qty)
    update_city_user(u["user_id"], balance=u["balance"] - total)
    register_trade(u["city"], item, "buy")

    await message.answer(
        "✅ <b>СДЕЛКА СОВЕРШЕНА</b>\n"
        "<i>Покупка прошла успешно</i> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{ITEMS[item]['emoji']} Куплено: <b>{qty} × {ITEMS[item]['name']}</b>\n"
        f"💵 Цена за шт.: <b>{price}</b> {CURRENCY_EMOJI}\n"
        f"{CURRENCY_EMOJI} Списано: <b>{_fmt(total)}</b> <i>{CURRENCY_NAME}</i>\n"
        f"📍 Город: <b>{u['city']}</b>",
        parse_mode="HTML",
        reply_markup=city_back_keyboard(),
    )


@router.message(Command("citysell", "продать"))
async def cmd_city_sell(message: Message):
    args = (message.text or "").split()[1:]
    if len(args) != 2:
        await message.answer(
            "📝 Использование: <code>/citysell [товар] [количество]</code>\n"
            "<i>Например: /citysell свитки 5</i>",
            parse_mode="HTML",
        )
        return

    u = get_city_user(message.from_user.id, message.from_user.username or "")
    if _is_traveling(u):
        await message.answer("🚶 Вы в пути — торговля недоступна до прибытия.")
        return

    item = _parse_item(args[0])
    if not item:
        await message.answer("❌ Неизвестный товар. Доступно: зелья, свитки, еда.")
        return

    try:
        qty = int(args[1])
    except ValueError:
        await message.answer("❌ Количество должно быть числом.")
        return
    if qty <= 0:
        await message.answer("❌ Количество должно быть положительным.")
        return

    inv = get_inventory(u["user_id"])
    if qty > inv[item]:
        await message.answer(f"📦 У вас только <b>{inv[item]}</b> единиц этого товара.", parse_mode="HTML")
        return

    price = get_price(u["city"], item)
    total = price * qty
    set_inventory_qty(u["user_id"], item, inv[item] - qty)
    update_city_user(u["user_id"], balance=u["balance"] + total)
    register_trade(u["city"], item, "sell")

    await message.answer(
        "✅ <b>СДЕЛКА СОВЕРШЕНА</b>\n"
        "<i>Продажа прошла успешно</i> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{ITEMS[item]['emoji']} Продано: <b>{qty} × {ITEMS[item]['name']}</b>\n"
        f"💵 Цена за шт.: <b>{price}</b> {CURRENCY_EMOJI}\n"
        f"{CURRENCY_EMOJI} Получено: <b>{_fmt(total)}</b> <i>{CURRENCY_NAME}</i>\n"
        f"📍 Город: <b>{u['city']}</b>",
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
    if u["balance"] < TRAVEL_COST:
        return False, f"💸 Недостаточно {CURRENCY_NAME} на дорогу. Нужно {_crystals(TRAVEL_COST)}."

    origin_city = u["city"]

    inv = get_inventory(u["user_id"])
    confiscated = []
    fine_total = 0
    for item, qty in inv.items():
        if qty > CUSTOMS_LIMIT and random.random() < CUSTOMS_CHANCE:
            set_inventory_qty(u["user_id"], item, 0)
            confiscated.append(ITEMS[item]["name"])
            fine_total += CUSTOMS_FINE

    new_balance = max(0, u["balance"] - TRAVEL_COST - fine_total)
    end_time = int(time.time()) + TRAVEL_MINUTES * 60
    update_city_user(
        u["user_id"],
        balance=new_balance,
        status="traveling",
        travel_end_time=end_time,
        city=dest,
        travel_from=origin_city,
    )

    cancel_min = TRAVEL_CANCEL_WINDOW // 60
    text = (
        "🧭 <b>В ПУТЬ!</b>\n"
        "<i>Караван покидает город</i> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Направление: {CITY_EMOJI.get(dest, '🏙')} <b>{dest}</b>\n"
        f"⏳ Прибытие через <b>{TRAVEL_MINUTES}</b> <i>минут</i>\n"
        f"{CURRENCY_EMOJI} Дорога стоила: <b>{TRAVEL_COST}</b> <i>{CURRENCY_NAME}</i>\n\n"
        f"<i>Передумали? В первые {cancel_min} минуты поездку можно отменить "
        f"(плата за дорогу не возвращается).</i>"
    )
    if confiscated:
        text += (
            "\n\n━━━━━━━━━━━━━━━━━━━━\n"
            f"🧙‍♂️ <b>Гильдия магов конфисковала ваш товар!</b>\n"
            f"<i>Изъято: {', '.join(confiscated)}</i>\n"
            f"💸 Штраф: <b>{fine_total}</b> {CURRENCY_EMOJI} <i>{CURRENCY_NAME}</i>"
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
        "❌ <b>ПОЕЗДКА ОТМЕНЕНА</b>\n"
        "<i>Вы вернулись назад</i> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{CITY_EMOJI.get(origin, '🏙')} Вы снова в городе <b>{origin}</b>\n"
        f"<i>Плата за дорогу не возвращается.</i>"
    )
    return True, text


def _traveling_status_text(u: dict) -> str:
    left = u["travel_end_time"] - int(time.time())
    m, s = max(0, left // 60), max(0, left % 60)
    text = (
        "🚶 <b>ВЫ В ПУТИ</b>\n"
        f"<i>Прибытие через {m} мин {s} сек</i> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Направление: {CITY_EMOJI.get(u['city'], '🏙')} <b>{u['city']}</b>"
    )
    if _can_cancel_travel(u):
        left_cancel = TRAVEL_CANCEL_WINDOW - _travel_elapsed(u)
        text += f"\n\n<i>Поездку ещё можно отменить — осталось {left_cancel} сек.</i>"
    return text


@router.message(Command("citytravel", "путешествие", "ехать"))
async def cmd_city_travel(message: Message):
    u = get_city_user(message.from_user.id, message.from_user.username or "")
    if _is_traveling(u):
        await message.answer(
            _traveling_status_text(u),
            parse_mode="HTML",
            reply_markup=city_travel_active_keyboard(_can_cancel_travel(u)),
        )
        return

    args = (message.text or "").split()[1:]
    if len(args) != 1:
        await message.answer(
            "🧭 <b>КУДА ОТПРАВЛЯЕМСЯ?</b>\n<i>Выберите пункт назначения</i> ✨\n━━━━━━━━━━━━━━━━━━━━",
            parse_mode="HTML",
            reply_markup=city_travel_keyboard(),
        )
        return

    dest = _parse_city(args[0])
    if not dest:
        await message.answer("❌ Неизвестный город. Доступно: Северный, Южный, Столица.")
        return

    ok, text = await _do_travel(message.from_user.id, message.from_user.username or "", dest)
    await message.answer(
        text, parse_mode="HTML",
        reply_markup=city_travel_active_keyboard(True) if ok else None,
    )


@router.message(Command("citycancel", "отмена", "cancel"))
async def cmd_city_cancel_travel(message: Message):
    ok, text = await _do_cancel_travel(message.from_user.id, message.from_user.username or "")
    await message.answer(text, parse_mode="HTML", reply_markup=city_back_keyboard())


@router.message(Command("citybag", "сумка", "bag"))
async def cmd_city_inventory(message: Message):
    u = get_city_user(message.from_user.id, message.from_user.username or "")
    inv = get_inventory(u["user_id"])
    await message.answer(
        _bag_text(inv),
        parse_mode="HTML",
        reply_markup=city_bag_keyboard(),
    )


@router.message(Command("citynews", "новости"))
async def cmd_city_news(message: Message):
    await message.answer(
        _news_text(),
        parse_mode="HTML",
        reply_markup=city_news_keyboard(),
    )


@router.message(Command("cityroute", "маршрут", "route"))
async def cmd_city_trade_route(message: Message):
    await message.answer(
        _route_text(),
        parse_mode="HTML",
        reply_markup=city_route_keyboard(),
    )


@router.message(Command("help", "помощь", "cityhelp"))
async def cmd_city_help(message: Message):
    await message.answer(
        _help_text(),
        parse_mode="HTML",
        reply_markup=city_help_keyboard(),
    )


# ──────────────────────────────────────────────────────────────────────────
# ОБРАБОТКА КНОПОК НАВИГАЦИИ (callback_query)
# ──────────────────────────────────────────────────────────────────────────

from aiogram.types import CallbackQuery  # noqa: E402


@router.callback_query(F.data == "city_nav_profile")
async def cb_city_profile(call: CallbackQuery):
    u = get_city_user(call.from_user.id, call.from_user.username or "")
    inv = get_inventory(u["user_id"])
    await call.message.edit_text(
        _profile_text(u, inv), parse_mode="HTML", reply_markup=city_main_menu_keyboard()
    )
    await call.answer()


@router.callback_query(F.data == "city_nav_market")
async def cb_city_market(call: CallbackQuery):
    await call.message.edit_text(
        _market_text(), parse_mode="HTML", reply_markup=city_market_keyboard()
    )
    await call.answer()


@router.callback_query(F.data == "city_nav_bag")
async def cb_city_bag(call: CallbackQuery):
    inv = get_inventory(call.from_user.id)
    await call.message.edit_text(
        _bag_text(inv), parse_mode="HTML", reply_markup=city_bag_keyboard()
    )
    await call.answer()


@router.callback_query(F.data == "city_nav_news")
async def cb_city_news(call: CallbackQuery):
    await call.message.edit_text(
        _news_text(), parse_mode="HTML", reply_markup=city_news_keyboard()
    )
    await call.answer()


@router.callback_query(F.data == "city_nav_route")
async def cb_city_route(call: CallbackQuery):
    await call.message.edit_text(
        _route_text(), parse_mode="HTML", reply_markup=city_route_keyboard()
    )
    await call.answer()


@router.callback_query(F.data == "city_nav_help")
async def cb_city_help(call: CallbackQuery):
    await call.message.edit_text(
        _help_text(), parse_mode="HTML", reply_markup=city_help_keyboard()
    )
    await call.answer()


@router.callback_query(F.data == "city_nav_travel")
async def cb_city_travel_menu(call: CallbackQuery):
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
        "🧭 <b>КУДА ОТПРАВЛЯЕМСЯ?</b>\n<i>Выберите пункт назначения</i> ✨\n━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML",
        reply_markup=city_travel_keyboard(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("city_go_"))
async def cb_city_go(call: CallbackQuery):
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
                        "🧙 <b>ВЫ ПРИБЫЛИ!</b>\n"
                        f"<i>Добро пожаловать в {r['city']}</i> ✨\n\n"
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
