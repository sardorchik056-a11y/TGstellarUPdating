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
from aiogram.types import Message
from aiogram.filters import Command

from database import DB_PATH  # используем тот же файл БД, что и весь бот

router = Router(name="city")

# ──────────────────────────────────────────────────────────────────────────
# КОНСТАНТЫ
# ──────────────────────────────────────────────────────────────────────────

CITIES = ["Северный", "Южный", "Столица"]

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

TRAVEL_COST = 50
TRAVEL_MINUTES = 15
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
                travel_end_time INTEGER
            )
        """)
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


def _is_traveling(u: dict) -> bool:
    if u["status"] != "traveling":
        return False
    end = u["travel_end_time"]
    if end is None:
        return False
    return int(time.time()) < end


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
# ХЕНДЛЕРЫ КОМАНД
# (намеренно с другими именами, чтобы не конфликтовать с /profile, /shop,
#  /inventory, /sell и т.д. из main.py)
# ──────────────────────────────────────────────────────────────────────────

@router.message(Command("city", "трейдер", "trader"))
async def cmd_city_profile(message: Message):
    u = get_city_user(message.from_user.id, message.from_user.username or "")
    inv = get_inventory(u["user_id"])

    status_line = "🟢 Свободен"
    if _is_traveling(u):
        left = u["travel_end_time"] - int(time.time())
        status_line = f"🚶 В пути ещё {max(0, left // 60)} мин {max(0, left % 60)} сек"

    text = (
        "🧙‍♂️ <b>Профиль торговца</b>\n\n"
        f"💰 Баланс: <b>{_fmt(u['balance'])}</b> монет\n"
        f"🏙 Город: <b>{u['city']}</b>\n"
        f"📦 Статус: {status_line}\n\n"
        "<b>Инвентарь:</b>\n"
        f"{ITEMS['potions']['emoji']} Зелья: {inv['potions']}\n"
        f"{ITEMS['scrolls']['emoji']} Свитки: {inv['scrolls']}\n"
        f"{ITEMS['food']['emoji']} Еда: {inv['food']}\n"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("citymarket", "рынок", "market"))
async def cmd_city_shop(message: Message):
    prices = get_all_prices()
    lines = ["🏪 <b>Цены по городам</b>\n"]
    for city in CITIES:
        lines.append(f"<b>{city}</b>")
        for item, info in ITEMS.items():
            p = prices[city][item]
            lines.append(f"  {info['emoji']} {info['name']}: {p} монет")
        lines.append("")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("citybuy", "купить"))
async def cmd_city_buy(message: Message):
    args = (message.text or "").split()[1:]
    if len(args) != 2:
        await message.answer("Использование: <code>/citybuy [товар] [количество]</code>", parse_mode="HTML")
        return

    u = get_city_user(message.from_user.id, message.from_user.username or "")
    if _is_traveling(u):
        await message.answer("🚶 Вы в пути — торговля недоступна.")
        return

    item = _parse_item(args[0])
    if not item:
        await message.answer("Неизвестный товар. Доступно: зелья, свитки, еда.")
        return

    try:
        qty = int(args[1])
    except ValueError:
        await message.answer("Количество должно быть числом.")
        return
    if qty <= 0:
        await message.answer("Количество должно быть положительным.")
        return

    price = get_price(u["city"], item)
    total = price * qty
    if total > u["balance"]:
        await message.answer(f"💸 Недостаточно монет. Нужно {_fmt(total)}, у вас {_fmt(u['balance'])}.")
        return

    inv = get_inventory(u["user_id"])
    set_inventory_qty(u["user_id"], item, inv[item] + qty)
    update_city_user(u["user_id"], balance=u["balance"] - total)
    register_trade(u["city"], item, "buy")

    await message.answer(
        f"✅ Куплено {qty} × {ITEMS[item]['name']} за {_fmt(total)} монет "
        f"({price} за шт.) в городе {u['city']}."
    )


@router.message(Command("citysell", "продать"))
async def cmd_city_sell(message: Message):
    args = (message.text or "").split()[1:]
    if len(args) != 2:
        await message.answer("Использование: <code>/citysell [товар] [количество]</code>", parse_mode="HTML")
        return

    u = get_city_user(message.from_user.id, message.from_user.username or "")
    if _is_traveling(u):
        await message.answer("🚶 Вы в пути — торговля недоступна.")
        return

    item = _parse_item(args[0])
    if not item:
        await message.answer("Неизвестный товар. Доступно: зелья, свитки, еда.")
        return

    try:
        qty = int(args[1])
    except ValueError:
        await message.answer("Количество должно быть числом.")
        return
    if qty <= 0:
        await message.answer("Количество должно быть положительным.")
        return

    inv = get_inventory(u["user_id"])
    if qty > inv[item]:
        await message.answer(f"📦 У вас только {inv[item]} единиц этого товара.")
        return

    price = get_price(u["city"], item)
    total = price * qty
    set_inventory_qty(u["user_id"], item, inv[item] - qty)
    update_city_user(u["user_id"], balance=u["balance"] + total)
    register_trade(u["city"], item, "sell")

    await message.answer(
        f"✅ Продано {qty} × {ITEMS[item]['name']} за {_fmt(total)} монет "
        f"({price} за шт.) в городе {u['city']}."
    )


@router.message(Command("citytravel", "путешествие", "ехать"))
async def cmd_city_travel(message: Message):
    args = (message.text or "").split()[1:]
    if len(args) != 1:
        await message.answer("Использование: <code>/citytravel [город]</code>\nГорода: Северный, Южный, Столица", parse_mode="HTML")
        return

    u = get_city_user(message.from_user.id, message.from_user.username or "")
    if _is_traveling(u):
        await message.answer("🚶 Вы уже в пути.")
        return

    dest = _parse_city(args[0])
    if not dest:
        await message.answer("Неизвестный город. Доступно: Северный, Южный, Столица.")
        return
    if dest == u["city"]:
        await message.answer("Вы уже в этом городе.")
        return
    if u["balance"] < TRAVEL_COST:
        await message.answer(f"💸 Недостаточно монет на дорогу. Нужно {TRAVEL_COST}.")
        return

    # Таможня: проверка провоза товара > лимита
    inv = get_inventory(u["user_id"])
    confiscated = []
    fine_total = 0
    for item, qty in inv.items():
        if qty > CUSTOMS_LIMIT and random.random() < CUSTOMS_CHANCE:
            set_inventory_qty(u["user_id"], item, 0)
            confiscated.append(ITEMS[item]["name"])
            fine_total += CUSTOMS_FINE

    new_balance = u["balance"] - TRAVEL_COST - fine_total
    if new_balance < 0:
        new_balance = 0  # штраф не должен увести в минус с учётом дороги

    end_time = int(time.time()) + TRAVEL_MINUTES * 60
    update_city_user(
        u["user_id"],
        balance=new_balance,
        status="traveling",
        travel_end_time=end_time,
        city=dest,  # город фиксируем сразу — назначение применится после прибытия по статусу
    )

    text = f"🚶 Вы отправились в город <b>{dest}</b>. Прибытие через {TRAVEL_MINUTES} минут."
    if confiscated:
        text += (
            "\n\n🧙‍♂️ Гильдия магов конфисковала ваш товар "
            f"({', '.join(confiscated)})! Вы заплатили штраф {fine_total} монет."
        )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("citybag", "сумка", "bag"))
async def cmd_city_inventory(message: Message):
    u = get_city_user(message.from_user.id, message.from_user.username or "")
    inv = get_inventory(u["user_id"])
    lines = ["🎒 <b>Ваш инвентарь</b>\n"]
    for item, info in ITEMS.items():
        lines.append(f"{info['emoji']} {info['name']}: {inv[item]}")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("citynews", "новости"))
async def cmd_city_news(message: Message):
    news = get_active_news()
    if not news:
        await message.answer("🗞 Пока новостей нет. Загляните позже.")
        return
    lines = ["🗞 <b>Слухи с торговых путей</b>\n"]
    for n in news:
        lines.append(f"• {n['news_text']}")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("cityroute", "маршрут", "route"))
async def cmd_city_trade_route(message: Message):
    best = best_trade_route()
    if not best:
        await message.answer("Сейчас нет выгодных маршрутов.")
        return
    info = ITEMS[best["item"]]
    text = (
        "📈 <b>Самый выгодный маршрут</b>\n\n"
        f"{info['emoji']} Товар: <b>{info['name']}</b>\n"
        f"🛒 Купить в: <b>{best['buy_city']}</b> по {best['buy_price']} монет\n"
        f"💰 Продать в: <b>{best['sell_city']}</b> по {best['sell_price']} монет\n"
        f"📊 Прибыль с единицы: <b>{best['profit']}</b> монет"
    )
    await message.answer(text, parse_mode="HTML")


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
                        "UPDATE city_users SET status='free', travel_end_time=NULL WHERE user_id=?",
                        (r["user_id"],),
                    )
                conn.commit()

            for r in rows:
                try:
                    await bot.send_message(
                        r["user_id"],
                        f"🧙 Вы прибыли в {r['city']}! Торговля доступна.",
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
