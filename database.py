# ============================================================
#  database.py  —  База данных пользователей TGStellar
#  Хранение: SQLite (файл tgstellar.db)
#  При каждом изменении данных вызывай save_user(uid)
#  Переписан для aiogram 3.x
# ============================================================

import sqlite3
import json
import asyncio
from contextlib import contextmanager
from datetime import date
from miner import init_mine_data, MAX_LEVEL, xp_for_level, COIN

DB_PATH = "tgstellar.db"

# ---------- Сокращённый формат чисел (100K / 1.5M / 2.3B / 1.4Sx итд) ----------

def format_amount(n) -> str:
    """
    Сокращает число до буквенного вида (стандартная короткая шкала,
    единый стиль с miner.py -> _fmt_num):
      999          -> "999"
      1500         -> "1.5K"
      100000       -> "100K"
      2300000      -> "2.3M"
      100000000    -> "100M"
      1500000000   -> "1.5B"
      1_000_000_000_000        -> "1T"
      1_000_000_000_000_000    -> "1Qa"  (quadrillion)
      1_000_000_000_000_000_000-> "1Qi"  (quintillion)
      10**21                   -> "1Sx"  (sextillion)
      10**24                   -> "1Sp"  (septillion)
      10**27                   -> "1Oc"  (octillion)
      10**30                   -> "1No"  (nonillion)
      10**33                   -> "1Dc"  (decillion)
    Если число ещё больше — формат не ломается: продолжаем Dc2, Dc3, ...
    Дробная часть показывается только если она не нулевая (1.5K, но не 1.0K).
    Знак сохраняется (для отрицательных значений, если вдруг понадобится).
    """
    try:
        n = float(n)
    except (TypeError, ValueError):
        return str(n)

    sign = "-" if n < 0 else ""
    n = abs(n)

    if n < 1000:
        # Целые числа без дробной части выводим как int, иначе с одним знаком
        if n == int(n):
            return f"{sign}{int(n)}"
        return f"{sign}{n:.1f}"

    suffixes = ["", "K", "M", "B", "T", "Qa", "Qi", "Sx", "Sp", "Oc", "No", "Dc"]
    idx = 0
    val = n
    while val >= 1000:
        val /= 1000
        idx += 1

    val = int(val * 10) / 10  # округление вниз до 1 знака после запятой

    if idx < len(suffixes):
        suffix = suffixes[idx]
    else:
        # За пределами "Dc" (10^33) продолжаем нумеровать: Dc2, Dc3, ...
        suffix = f"Dc{idx - len(suffixes) + 2}"

    if val == int(val):
        return f"{sign}{int(val)}{suffix}"
    return f"{sign}{val:.1f}{suffix}"


# Короткий алиас, чтобы было удобно импортировать как `fmt`
fmt = format_amount


# ---------- Инициализация таблицы ----------

def _get_conn():
    # timeout=30 -> при занятой БД sqlite сам ждёт до 30 сек вместо
    # мгновенного "database is locked"
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    # WAL: читатели больше не блокируют писателя и наоборот (сильно меньше
    # шансов на "database is locked" при параллельных запросах бота).
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


@contextmanager
def _conn_ctx():
    """
    Правильный контекстный менеджер для соединения.
    В отличие от голого `with _get_conn() as conn:` (который у sqlite3.Connection
    управляет ТОЛЬКО транзакцией — commit/rollback — но НЕ закрывает соединение),
    здесь соединение гарантированно закрывается в finally. Именно отсутствие
    close() было причиной утечки: десятки открытых fd на tgstellar.db и,
    как следствие, "database is locked" при старте второго процесса.
    """
    conn = _get_conn()
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db():
    """Создаёт таблицу если не существует. Вызвать при старте бота."""
    with _conn_ctx() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                uid       INTEGER PRIMARY KEY,
                data_json TEXT    NOT NULL,
                username  TEXT
            )
        """)
        # Таблица для дедупликации платежей Stars (сохраняется между перезапусками)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_charges (
                charge_id TEXT PRIMARY KEY,
                uid       INTEGER NOT NULL,
                payload   TEXT,
                ts        INTEGER NOT NULL
            )
        """)

        # ── Миграция: если таблица users уже существует со старой схемой
        # (без колонки username) — добавляем колонку и переносим значения
        # из JSON, чтобы поиск по нику больше не требовал полного скана.
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        if "username" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN username TEXT")
            rows = conn.execute("SELECT uid, data_json FROM users").fetchall()
            for row in rows:
                try:
                    uname = json.loads(row["data_json"]).get("username")
                except Exception:
                    uname = None
                conn.execute("UPDATE users SET username=? WHERE uid=?", (uname, row["uid"]))

        # Индекс для быстрого регистронезависимого поиска по нику
        # (раньше get_user_by_username делал SELECT * FROM users и линейно
        # перебирал в Python — при росте базы это одна из причин тормозов).
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username COLLATE NOCASE)"
        )
        conn.commit()


def is_charge_processed(charge_id: str) -> bool:
    """Проверяет, был ли этот charge_id уже обработан."""
    with _conn_ctx() as conn:
        row = conn.execute(
            "SELECT 1 FROM processed_charges WHERE charge_id=?", (charge_id,)
        ).fetchone()
    return row is not None


def mark_charge_processed(charge_id: str, uid: int, payload: str = ""):
    """Записывает charge_id как обработанный. Вызывать ДО выдачи товара."""
    import time as _time
    with _conn_ctx() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO processed_charges (charge_id, uid, payload, ts) VALUES (?,?,?,?)",
            (charge_id, uid, payload, int(_time.time()))
        )
        conn.commit()


# ---------- Сохранение / загрузка ----------

def _load_raw(uid: int) -> dict | None:
    with _conn_ctx() as conn:
        row = conn.execute("SELECT data_json FROM users WHERE uid=?", (uid,)).fetchone()
    if row:
        return json.loads(row["data_json"])
    return None


def save_user(uid: int, data: dict):
    """Сохранить данные пользователя в БД."""
    username = data.get("username")
    with _conn_ctx() as conn:
        conn.execute(
            "INSERT INTO users (uid, data_json, username) VALUES (?,?,?) "
            "ON CONFLICT(uid) DO UPDATE SET data_json=excluded.data_json, username=excluded.username",
            (uid, json.dumps(data, ensure_ascii=False), username)
        )
        conn.commit()


# ---------- Получить / создать пользователя ----------

def get_or_create_user(user) -> dict:
    uid  = user.id
    data = _load_raw(uid)

    if data is None:
        # Новый пользователь — должен пройти онбординг: капча → язык → меню
        data = {
            "id":         uid,
            "username":   user.username or "Аноним",
            "first_name": user.first_name or "",
            "joined":     date.today().isoformat(),
            "balance":    0,
            "level":      1,
            "xp":         0,
            "xp_max":     xp_for_level(1),
            "boosters_inventory": [],
            "active_booster":     None,
            "onboarded":  False,
            **init_mine_data(),
        }
        save_user(uid, data)
    else:
        # Миграция: добавляем поля если отсутствуют
        changed = False

        # ── Обновляем username и first_name при каждом визите ──
        # Без этого поиск по @username не работает после смены ника
        new_username   = user.username or "Аноним"
        new_first_name = user.first_name or ""
        if data.get("username") != new_username:
            data["username"] = new_username
            changed = True
        if data.get("first_name") != new_first_name:
            data["first_name"] = new_first_name
            changed = True

        defaults = {
            "owned_pickaxes":      ["wood_1"],
            "mine_duration_key":   "5min",
            "owned_durations":     ["5min"],
            "mine_start":          None,
            "mine_campaigns_done": 0,
            "mine_collected":      False,
            "xp_max":              xp_for_level(data.get("level", 1)),
            "boosters_inventory":  [],
            "active_booster":      None,
            # Уже существующие пользователи онбординг не проходят повторно
            "onboarded":           True,
        }
        for key, val in defaults.items():
            if key not in data:
                data[key] = val
                changed = True
        # Убедиться что ores содержит все руды
        from miner import ORES
        if "ores" not in data:
            data["ores"] = {o["key"]: 0 for o in ORES}
            changed = True
        else:
            for o in ORES:
                if o["key"] not in data["ores"]:
                    data["ores"][o["key"]] = 0
                    changed = True
        if changed:
            save_user(uid, data)

    return data


def transfer_coins(sender_uid: int, recipient_uid: int, amount: int,
                    daily_limit: int | None = None, gift_window: int = 86400,
                    now_ts: int | None = None) -> dict:
    """
    Полностью атомарный перевод монет между двумя игроками — одна
    SQLite-транзакция (BEGIN IMMEDIATE) на оба блока данных сразу.

    Раньше /gift брал два asyncio.Lock (по одному на каждого игрока), но это
    защищает только от других хендлеров, которые ТОЖЕ берут этот же лок.
    Майнер/хант/дуэли/шоп и т.д. лока не брали и просто перезаписывали весь
    JSON-блоб пользователя (save_user), из-за чего параллельное действие
    другого хендлера могло затереть уже сохранённый перевод устаревшей
    копией баланса — отсюда "случайный" остаток вместо ожидаемого.

    Здесь читаем и пишем ОБА блока внутри одной транзакции с write-локом
    БД на всё время операции — это исключает гонку в принципе, независимо
    от того, берут ли остальные хендлеры asyncio.Lock или нет.

    Возвращает dict:
      {"ok": True,  "sender_balance": int, "recipient_balance": int}
      {"ok": False, "reason": "no_sender" | "no_recipient" |
                     "insufficient" | "limit", "sender_balance": int,
                     "daily_limit": int, "received_today": int, "remaining": int}
    """
    import time as _time
    if now_ts is None:
        now_ts = int(_time.time())

    conn = _get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")

        srow = conn.execute("SELECT data_json FROM users WHERE uid=?", (sender_uid,)).fetchone()
        if srow is None:
            conn.rollback()
            return {"ok": False, "reason": "no_sender"}

        rrow = conn.execute("SELECT data_json FROM users WHERE uid=?", (recipient_uid,)).fetchone()
        if rrow is None:
            conn.rollback()
            return {"ok": False, "reason": "no_recipient"}

        sender = json.loads(srow["data_json"])
        recipient = json.loads(rrow["data_json"])

        sender_balance = sender.get("balance", 0)
        if sender_balance < amount:
            conn.rollback()
            return {"ok": False, "reason": "insufficient", "sender_balance": sender_balance}

        if daily_limit is not None:
            window_start = recipient.get("gift_window_start", 0)
            if now_ts - window_start >= gift_window:
                recipient["gift_window_start"] = now_ts
                recipient["gift_received_today"] = 0

            received_today = recipient.get("gift_received_today", 0)
            if received_today + amount > daily_limit:
                conn.rollback()
                remaining = max(daily_limit - received_today, 0)
                return {"ok": False, "reason": "limit", "daily_limit": daily_limit,
                        "received_today": received_today, "remaining": remaining}

            recipient["gift_received_today"] = received_today + amount

        sender["balance"] = sender_balance - amount
        recipient["balance"] = recipient.get("balance", 0) + amount

        conn.execute(
            "UPDATE users SET data_json=? WHERE uid=?",
            (json.dumps(sender, ensure_ascii=False), sender_uid)
        )
        conn.execute(
            "UPDATE users SET data_json=? WHERE uid=?",
            (json.dumps(recipient, ensure_ascii=False), recipient_uid)
        )
        conn.commit()

        return {
            "ok": True,
            "sender_balance": sender["balance"],
            "recipient_balance": recipient["balance"],
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def change_balance(uid: int, delta: int, min_balance: int = 0) -> int | None:
    """
    Атомарно меняет data['balance'] на delta прямо на уровне SQLite-транзакции
    (BEGIN IMMEDIATE держит write-лок базы на всё время чтение->изменение->запись),
    поэтому НИКАКОЙ другой параллельный save_user() (майнер/хант/дуэли/шоп и т.д.)
    не может "перетереть" это изменение своей устаревшей копией блоба — именно
    из-за этой race condition перевод монет мог давать неверный остаток.

    Возвращает новый баланс, либо None если:
      - юзер не найден
      - итоговый баланс < min_balance (изменение НЕ применяется, откат)

    ВАЖНО: используй эту функцию (а не data["balance"] = ...; save_user(...))
    везде, где меняется баланс — /gift, покупки, награды, майнинг и т.д.
    """
    conn = _get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT data_json FROM users WHERE uid=?", (uid,)).fetchone()
        if row is None:
            conn.rollback()
            return None

        data = json.loads(row["data_json"])
        new_balance = data.get("balance", 0) + delta

        if new_balance < min_balance:
            conn.rollback()
            return None

        data["balance"] = new_balance
        conn.execute(
            "UPDATE users SET data_json=? WHERE uid=?",
            (json.dumps(data, ensure_ascii=False), uid)
        )
        conn.commit()
        return new_balance
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_user(uid: int) -> dict | None:
    return _load_raw(uid)


def get_user_by_username(username: str) -> dict | None:
    """
    Поиск пользователя по username (без @, регистронезависимо).
    Использует индекс idx_users_username — быстрый поиск по одной строке,
    без загрузки и разбора всей таблицы в память (раньше именно это было
    одной из причин тормозов при росте базы игроков).
    """
    with _conn_ctx() as conn:
        row = conn.execute(
            "SELECT data_json FROM users WHERE username = ? COLLATE NOCASE",
            (username,)
        ).fetchone()
    if row:
        return json.loads(row["data_json"])
    return None


def get_user_by_id_or_username(target_raw: str) -> dict | None:
    """
    Универсальный поиск: если target_raw — число → ищем по uid,
    иначе → ищем по username (без @).
    Используй везде вместо get_all_users() + линейного поиска.
    """
    target_raw = target_raw.lstrip("@")
    if target_raw.lstrip("-").isdigit():
        return get_user(int(target_raw))
    return get_user_by_username(target_raw)


def update_user(uid: int, fields: dict):
    data = _load_raw(uid)
    if data:
        data.update(fields)
        save_user(uid, data)


def get_all_users() -> list[dict]:
    with _conn_ctx() as conn:
        rows = conn.execute("SELECT data_json FROM users").fetchall()
    return [json.loads(r["data_json"]) for r in rows]


# ---------- Async-обёртки ----------
# sqlite3 в этом модуле синхронный (блокирующий). Вызов любой из функций
# выше напрямую из async-хэндлера или фонового цикла останавливает ВЕСЬ
# event loop бота на время выполнения запроса — то есть в этот момент
# зависают ВСЕ пользователи одновременно, а не только тот, кто вызвал
# операцию. Особенно критично для "тяжёлых" функций (get_all_users,
# любой полный скан) и для фоновых циклов, которые дёргаются каждые
# несколько секунд/минут.
#
# Эти обёртки выполняют исходную функцию в отдельном потоке
# (asyncio.to_thread), чтобы event loop продолжал обрабатывать остальных
# пользователей, пока идёт работа с БД. Использовать их из любого async
# кода вместо прямого вызова синхронных функций выше.

async def aio_get_user(uid: int) -> dict | None:
    return await asyncio.to_thread(get_user, uid)


async def aio_get_or_create_user(user) -> dict:
    return await asyncio.to_thread(get_or_create_user, user)


async def aio_save_user(uid: int, data: dict) -> None:
    await asyncio.to_thread(save_user, uid, data)


async def aio_update_user(uid: int, fields: dict) -> None:
    await asyncio.to_thread(update_user, uid, fields)


async def aio_get_user_by_username(username: str) -> dict | None:
    return await asyncio.to_thread(get_user_by_username, username)


async def aio_get_user_by_id_or_username(target_raw: str) -> dict | None:
    return await asyncio.to_thread(get_user_by_id_or_username, target_raw)


async def aio_get_all_users() -> list[dict]:
    return await asyncio.to_thread(get_all_users)


# ---------- Вспомогательные функции профиля ----------

def days_on_project(joined_str: str) -> int:
    return (date.today() - date.fromisoformat(joined_str)).days


def level_to_rank(level: int, lang: str = "ru") -> str:
    from lang import t
    if level < 5:   return t(lang, "rank_novice")
    if level < 10:  return t(lang, "rank_skilled")
    if level < 20:  return t(lang, "rank_pro")
    if level < 35:  return t(lang, "rank_master")
    if level < 50:  return t(lang, "rank_expert")
    if level < 75:  return t(lang, "rank_elite")
    return t(lang, "rank_legend")


def status_from_level(level: int) -> str:
    # Оставлено для обратной совместимости, но в профиле теперь используется
    # реальный статус из status.py (get_active_status)
    return "Standart"


def xp_bar(xp: int, xp_max: int, length: int = 10) -> str:
    """
    10 ячеек × 10% каждая. Внутри ячейки:
      < 25%  → пустая       5992142065603974345
      25–49% → четверть     5992256170000127661
      50–74% → половина     5992488673759729434
      ≥ 75%  → полная       5992459287593489418
    """
    _E_EMPTY   = "5992142065603974345"
    _E_QUARTER = "5992256170000127661"
    _E_HALF    = "5992488673759729434"
    _E_FULL    = "5992459287593489418"

    percent = (xp / xp_max * 100) if xp_max > 0 else 100.0
    percent = max(0.0, min(percent, 100.0))

    cells = []
    for i in range(length):
        cell_start = i * (100 / length)
        cell_fill  = percent - cell_start
        cell_pct   = max(0.0, min(cell_fill, (100 / length))) / (100 / length) * 100

        if cell_pct >= 75:
            eid = _E_FULL
        elif cell_pct >= 50:
            eid = _E_HALF
        elif cell_pct >= 25:
            eid = _E_QUARTER
        else:
            eid = _E_EMPTY

        cells.append(f'<tg-emoji emoji-id="{eid}">⬜</tg-emoji>')

    return "".join(cells)


# ---------- Текст профиля ----------

def profile_text(d: dict) -> str:
    from lang import t, get_lang
    lang   = get_lang(d)
    uid    = d["id"]
    name   = d["first_name"] or d["username"]
    anon   = t(lang, "profile_anon")
    uname  = f"@{d['username']}" if d["username"] != anon and d["username"] != "Аноним" else "—"
    days   = days_on_project(d["joined"])
    level  = d["level"]
    xp     = d["xp"]
    xp_max = d["xp_max"]

    if level >= MAX_LEVEL:
        lvl_line = f"<b>{MAX_LEVEL} (MAX)</b> ✨"
        bar_str  = xp_bar(xp_max, xp_max)
        xp_str   = "<b>MAX</b>"
    else:
        lvl_line = f"<b>{level}</b>"
        bar_str  = xp_bar(xp, xp_max)
        xp_str   = f"<b>{format_amount(xp)}/{format_amount(xp_max)}</b>"

    # Активный статус (VIP / Premium / Standart)
    from status import get_active_status, get_status_ends_at, _fmt_time_left as _st_fmt, _now_ts as _st_now
    _active_status = get_active_status(d)
    _status_ends   = get_status_ends_at(d)
    if _active_status == "premium":
        _sleft       = _st_fmt(_status_ends - _st_now())
        status_badge = f'<tg-emoji emoji-id="5427168083074628963">⭐</tg-emoji> <b>Premium</b> · <b>{_sleft}</b>'
    elif _active_status == "vip":
        _sleft       = _st_fmt(_status_ends - _st_now())
        status_badge = f'<tg-emoji emoji-id="5325547803936572038">👑</tg-emoji> <b>VIP</b> · <b>{_sleft}</b>'
    else:
        status_badge = f'<tg-emoji emoji-id="5397916757333654639">🎟</tg-emoji> <b>Standart</b>'

    # Ускорители
    from shop import get_active_booster_info, get_active_xp_booster_info, get_active_enh_booster_info, _multiplier_label, _DUR_LABELS, _fmt_time_left, _now_ts
    active     = get_active_booster_info(d)
    xp_active  = get_active_xp_booster_info(d)
    enh_active = get_active_enh_booster_info(d)

    booster_lines = ""

    if active:
        mult = _multiplier_label(active["multiplier"])
        dur  = _DUR_LABELS[active["dur_key"]]
        left = _fmt_time_left(active["ends_at"] - _now_ts())
        booster_lines += f'\n<tg-emoji emoji-id="5438571934210082705">⚡</tg-emoji> {t(lang, "boost_pickaxe")}: {mult} {t(lang, "boost_on")} {dur} — <tg-emoji emoji-id="5382194935057372936">⏱</tg-emoji> {left}'
    if xp_active:
        mult = _multiplier_label(xp_active["multiplier"])
        dur  = _DUR_LABELS[xp_active["dur_key"]]
        left = _fmt_time_left(xp_active["ends_at"] - _now_ts())
        booster_lines += f'\n<tg-emoji emoji-id="5224607267797606837">🔮</tg-emoji> {t(lang, "boost_xp")}: ×{mult} {t(lang, "boost_on")} {dur} — <tg-emoji emoji-id="5382194935057372936">⏱</tg-emoji> {left}'
    if enh_active:
        mult = _multiplier_label(enh_active["multiplier"])
        dur  = _DUR_LABELS[enh_active["dur_key"]]
        left = _fmt_time_left(enh_active["ends_at"] - _now_ts())
        booster_lines += f'\n<tg-emoji emoji-id="5256047523620995497">⚡</tg-emoji> {t(lang, "boost_enhancer")}: ×{mult} {t(lang, "boost_on")} {dur} — <tg-emoji emoji-id="5382194935057372936">⏱</tg-emoji> {left}'

    booster_block = (
        f'\n\n<blockquote><tg-emoji emoji-id="5258203794772085854">⚡</tg-emoji> <b>{t(lang, "boost_active")}</b>{booster_lines}</blockquote>'
        if booster_lines else ""
    )

    return (
        f'<blockquote>'
        f'<tg-emoji emoji-id="5906581476639513176">🎟</tg-emoji> <b>{name}</b>\n'
        f'<tg-emoji emoji-id="5282843764451195532">🎟</tg-emoji> <b><code>{uid}</code></b>\n'
        f'<tg-emoji emoji-id="5323442290708985472">🎟</tg-emoji> <b>{uname}</b>\n'
        f'</blockquote>'
        f'<blockquote>'
        f'<tg-emoji emoji-id="5415655814079723871">🎟</tg-emoji> <b>{t(lang, "profile_rank")} — {level_to_rank(level, lang)}</b>\n'
        f'<tg-emoji emoji-id="5438496463044752972">🎟</tg-emoji> <b>{t(lang, "profile_status")} — {status_badge}</b>\n'
        f'<tg-emoji emoji-id="5274055917766202507">🎟</tg-emoji> <b>{t(lang, "profile_days")} — {days}</b>\n'
        f'</blockquote>'
        f'<blockquote>'
        f'<tg-emoji emoji-id="5375338737028841420">🎟</tg-emoji> <b>{t(lang, "profile_level")} —</b> {lvl_line}\n'
        f'<tg-emoji emoji-id="5341498088408234504">🎟</tg-emoji> <b>{t(lang, "profile_xp")} —</b> {xp_str}\n'
        f'{bar_str}'
        f'</blockquote>'
        f'{booster_block}\n'
        f'<blockquote><tg-emoji emoji-id="5278467510604160626">🎟</tg-emoji> <b>{t(lang, "profile_balance")} — {format_amount(d["balance"])}</b>{COIN}</blockquote>'
    )
