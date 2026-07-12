# ============================================================
#  cdl.py  —  Система вкладов TGStellar
#  4 типа вкладов: 24ч/48ч/96ч/144ч
#  Логика: открыть вклад → ждать → забрать с процентами
# ============================================================

import sqlite3
import json
import time
import asyncio
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

DB_PATH = "tgstellar.db"


from contextlib import contextmanager as _contextmanager

def _get_raw_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


@_contextmanager
def _connect():
    """Единая точка создания соединения — те же PRAGMA, что и в database.py,
    чтобы избежать разных таймаутов на одном и том же файле БД.

    ВАЖНО: раньше это была обычная функция, а не контекст-менеджер —
    `with _connect() as conn:` у голого sqlite3.Connection управляет ТОЛЬКО
    транзакцией (commit/rollback), но НЕ закрывает соединение. Ни в одном
    из мест в этом файле close() не вызывался — утечка fd на tgstellar.db.
    Теперь закрытие гарантировано в finally, использование в коде не меняется."""
    conn = _get_raw_conn()
    try:
        with conn:
            yield conn
    finally:
        conn.close()

# ---------- Конфигурация вкладов ----------

DEPOSITS = [
    {
        "key":      "dep_24h",
        "hours":    24,
        "percent":  130,       # итого к выплате (130% = вложил 1000 → получил 1300)
        "profit":   30,        # чистая прибыль %
        "min":      200_000,
        "label":    "Дневной",
        "emoji_id": "5440621591387980068",   # 🌅
        "color":    "🟡",
    },
    {
        "key":      "dep_48h",
        "hours":    48,
        "percent":  160,
        "profit":   60,
        "min":      500_000,
        "label":    "Двухдневный",
        "emoji_id": "5440621591387980068",   # 📈
        "color":    "🟠",
    },
    {
        "key":      "dep_96h",
        "hours":    96,
        "percent":  220,
        "profit":   120,
        "min":      5_000_000,
        "label":    "Недельный",
        "emoji_id": "5440621591387980068",   # 💎
        "color":    "🔵",
    },
    {
        "key":      "dep_144h",
        "hours":    144,
        "percent":  360,
        "profit":   260,
        "min":      50_000_000,
        "label":    "Элитный",
        "emoji_id": "5440621591387980068",   # 👑
        "color":    "🔴",
    },
]

DEPOSITS_BY_KEY = {d["key"]: d for d in DEPOSITS}

# Emoji кнопки «назад»
_BACK_EMOJI = "6039539366177541657"

# ---------- Лимиты вкладов ----------
# dep_24h:  3 раза за 2 недели (14 дней)
# dep_48h:  2 раза за неделю (7 дней)
# dep_96h:  2 раза за месяц (30 дней)
# dep_144h: 2 раза за месяц (30 дней)

DEPOSIT_LIMITS = {
    "dep_24h":  {"max": 3, "window_days": 14},
    "dep_48h":  {"max": 2, "window_days": 7},
    "dep_96h":  {"max": 2, "window_days": 30},
    "dep_144h": {"max": 2, "window_days": 30},
}


def _count_recent(uid: int, dep_key: str) -> int:
    """Сколько вкладов dep_key открыл пользователь за окно лимита."""
    limit = DEPOSIT_LIMITS.get(dep_key)
    if not limit:
        return 0
    since = int(time.time()) - limit["window_days"] * 86400
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM deposits WHERE uid=? AND dep_key=? AND opened_at>=?",
            (uid, dep_key, since)
        ).fetchone()
    return row[0] if row else 0


def check_deposit_limit(uid: int, dep_key: str) -> tuple[bool, int, int]:
    """
    Проверяет можно ли открыть вклад.
    Возвращает (ok, used, max).
    """
    limit = DEPOSIT_LIMITS.get(dep_key)
    if not limit:
        return True, 0, 0
    used = _count_recent(uid, dep_key)
    return used < limit["max"], used, limit["max"]


# ---------- База данных ----------

def init_cdl_db():
    """Создаёт таблицу вкладов. Вызвать при старте бота."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS deposits (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                uid        INTEGER NOT NULL,
                dep_key    TEXT    NOT NULL,
                amount     INTEGER NOT NULL,
                payout     INTEGER NOT NULL,
                opened_at  INTEGER NOT NULL,
                closes_at  INTEGER NOT NULL,
                claimed    INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.commit()


def _open_deposit(uid: int, dep_key: str, amount: int) -> int:
    """Открыть вклад. Возвращает id записи."""
    dep = DEPOSITS_BY_KEY[dep_key]
    now = int(time.time())
    closes_at = now + dep["hours"] * 3600
    payout = int(amount * dep["percent"] / 100)
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO deposits (uid, dep_key, amount, payout, opened_at, closes_at, claimed) "
            "VALUES (?,?,?,?,?,?,0)",
            (uid, dep_key, amount, payout, now, closes_at)
        )
        conn.commit()
        return cur.lastrowid


def _get_active_deposits(uid: int) -> list[dict]:
    """Все активные (не выплаченные) вклады пользователя."""
    now = int(time.time())
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM deposits WHERE uid=? AND claimed=0 ORDER BY opened_at, id",
            (uid,)
        ).fetchall()
    return [dict(r) for r in rows]


def _get_ready_deposits(uid: int) -> list[dict]:
    """Вклады, срок которых истёк — можно забрать."""
    now = int(time.time())
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM deposits WHERE uid=? AND claimed=0 AND closes_at<=?",
            (uid, now)
        ).fetchall()
    return [dict(r) for r in rows]


def _claim_deposit(dep_id: int) -> int | None:
    """Отметить вклад как выплаченный. Возвращает payout или None."""
    now = int(time.time())
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM deposits WHERE id=? AND claimed=0 AND closes_at<=?",
            (dep_id, now)
        ).fetchone()
        if not row:
            return None
        conn.execute("UPDATE deposits SET claimed=1 WHERE id=?", (dep_id,))
        conn.commit()
        return row["payout"]


def get_matured_deposits_for_all_users() -> list[dict]:
    """Все вклады всех пользователей, срок которых истёк и не выплачены."""
    now = int(time.time())
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM deposits WHERE claimed=0 AND closes_at<=?",
            (now,)
        ).fetchall()
    return [dict(r) for r in rows]


def _count_active(uid: int) -> int:
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM deposits WHERE uid=? AND claimed=0", (uid,)
        ).fetchone()
    return row[0] if row else 0


def _get_all_active(uid: int) -> list[dict]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM deposits WHERE uid=? AND claimed=0 ORDER BY closes_at ASC",
            (uid,)
        ).fetchall()
    return [dict(r) for r in rows]


# ---------- Async-обёртки ----------
# Все функции выше синхронные (блокирующий sqlite3). Вызов любой из них
# напрямую из async-хэндлера в mainhelp.py или из фонового цикла
# останавливает ВЕСЬ event loop бота на время диск-I/O — то есть зависают
# ВСЕ пользователи одновременно, а не только тот, кто открывает/забирает
# вклад. Именно это было причиной многоминутных зависаний бота.
#
# Использовать ТОЛЬКО эти aio_-обёртки из handle_callback и фоновых циклов
# вместо прямого вызова синхронных функций выше.

async def aio_count_recent(uid: int, dep_key: str) -> int:
    return await asyncio.to_thread(_count_recent, uid, dep_key)


async def aio_check_deposit_limit(uid: int, dep_key: str) -> tuple[bool, int, int]:
    return await asyncio.to_thread(check_deposit_limit, uid, dep_key)


async def aio_open_deposit(uid: int, dep_key: str, amount: int) -> int:
    return await asyncio.to_thread(_open_deposit, uid, dep_key, amount)


async def aio_get_active_deposits(uid: int) -> list[dict]:
    return await asyncio.to_thread(_get_active_deposits, uid)


async def aio_get_ready_deposits(uid: int) -> list[dict]:
    return await asyncio.to_thread(_get_ready_deposits, uid)


async def aio_claim_deposit(dep_id: int) -> int | None:
    return await asyncio.to_thread(_claim_deposit, dep_id)


async def aio_get_matured_deposits_for_all_users() -> list[dict]:
    return await asyncio.to_thread(get_matured_deposits_for_all_users)


async def aio_count_active(uid: int) -> int:
    return await asyncio.to_thread(_count_active, uid)


async def aio_get_all_active(uid: int) -> list[dict]:
    return await asyncio.to_thread(_get_all_active, uid)


# ---------- Вспомогательные функции ----------

def _fmt_time_left(secs: int) -> str:
    if secs <= 0:
        return "готово ✅"
    h = secs // 3600
    m = (secs % 3600) // 60
    if h >= 24:
        d = h // 24
        h2 = h % 24
        return f"{d}д {h2}ч {m}м"
    return f"{h}ч {m}м"


def _fmt_ts(ts: int) -> str:
    import datetime
    dt = datetime.datetime.fromtimestamp(ts)
    return dt.strftime("%d.%m %H:%M")


# ---------- Тексты ----------

def cdl_main_text(d: dict) -> str:
    from database import format_amount
    uid = d["id"]
    bal = d.get("balance", 0)
    active = _get_all_active(uid)
    now = int(time.time())

    if active:
        active_lines = ""
        now_active = [dep for dep in active if dep["closes_at"] > now]
        for dep in now_active:
            dep_cfg = DEPOSITS_BY_KEY.get(dep["dep_key"], {})
            left = dep["closes_at"] - now
            tag = f'{dep_cfg.get("hours", "?")}h | {dep_cfg.get("profit", "?")}%'
            active_lines += (
                f'\n<b>#{dep["id"]} {tag}</b>'
                f' · <b>{format_amount(dep["payout"])}</b>'
                f' · <i>{_fmt_time_left(left)}</i>'
            )
        if active_lines:
            active_block = f'\n\n<blockquote><b>Активные вклады:</b>{active_lines}</blockquote>'
        else:
            active_block = f'\n\n<blockquote><i>Вкладов нет — выбери тариф ниже</i></blockquote>'
    else:
        active_block = f'\n\n<blockquote><i>Вкладов нет — выбери тариф ниже</i></blockquote>'

    return (
        f'<tg-emoji emoji-id="5427168083074628963">💰</tg-emoji> <b>Вклады</b>\n\n'
        f'<blockquote>'
        f'<i>Вложи монеты — забери с прибылью</i>\n'
        f'<b><tg-emoji emoji-id="5278467510604160626">💰</tg-emoji>Баланс:</b> {format_amount(bal)}<tg-emoji emoji-id="5199552030615558774">💰</tg-emoji>'
        f'</blockquote>'
        f'{active_block}'
    )


def cdl_main_keyboard(uid: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    ready = _get_ready_deposits(uid)

    if ready:
        builder.row(InlineKeyboardButton(
            text=f"✅ Забрать вклады ({len(ready)})",
            callback_data="cdl_claim_all",
            icon_custom_emoji_id="5325547803936572038",
            style="success"
        ))

    builder.row(
        InlineKeyboardButton(
            text="24h | 130%",
            callback_data="cdl_info_dep_24h",
            icon_custom_emoji_id="5397916757333654639"
        ),
        InlineKeyboardButton(
            text="48h | 160%",
            callback_data="cdl_info_dep_48h",
            icon_custom_emoji_id="5397916757333654639"
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="96h | 220%",
            callback_data="cdl_info_dep_96h",
            icon_custom_emoji_id="5397916757333654639"
        ),
        InlineKeyboardButton(
            text="144h | 360%",
            callback_data="cdl_info_dep_144h",
            icon_custom_emoji_id="5397916757333654639"
        ),
    )
    builder.row(InlineKeyboardButton(
        text="Назад",
        callback_data="back_to_menu",
        icon_custom_emoji_id=_BACK_EMOJI
    ))
    return builder.as_markup()


def cdl_detail_text(dep_key: str, d: dict) -> str:
    from database import format_amount
    dep = DEPOSITS_BY_KEY[dep_key]
    uid = d["id"]
    bal = d.get("balance", 0)
    can_afford = bal >= dep["min"]

    # Пример расчёта: минимальный вклад
    example_in  = dep["min"]
    example_out = int(example_in * dep["percent"] / 100)
    example_profit = example_out - example_in

    afford_line = (
        f'✅ <b>Можно открыть</b>'
        if can_afford else
        f'❌ <i>Не хватает {format_amount(dep["min"] - bal)}</i>'
    )

    # Лимиты
    lim = DEPOSIT_LIMITS.get(dep_key, {})
    used = _count_recent(uid, dep_key)
    max_uses = lim.get("max", 0)
    win_days = lim.get("window_days", 0)
    win_label = f"{win_days} дн." if win_days != 7 else "неделю"
    if win_days == 14:
        win_label = "2 недели"
    limit_line = (
        f'✅ <i>{used}/{max_uses} за {win_label}</i>'
        if used < max_uses else
        f'🚫 <b>Лимит исчерпан</b> <i>({used}/{max_uses} за {win_label})</i>'
    )

    return (
        f'<tg-emoji emoji-id="{dep["emoji_id"]}">{dep["color"]}</tg-emoji> '
        f'<b>{dep["label"]} вклад</b>\n\n'
        f'<blockquote>'
        f'<tg-emoji emoji-id="5440621591387980068">⏰</tg-emoji> '
        f'<b>Срок:</b> <i>{dep["hours"]}ч · {dep["hours"] // 24} дн.</i>\n'
        f'<tg-emoji emoji-id="5224257782013769471">💸</tg-emoji> '
        f'<b>Прибыль:</b> +{dep["profit"]}%\n'
        f'<tg-emoji emoji-id="5447183459602669338">💰</tg-emoji> '
        f'<b>Минимум:</b> {format_amount(dep["min"])}\n'
        f'<tg-emoji emoji-id="5429651785352501917">🧮</tg-emoji> '
        f'<b>{format_amount(example_in)}</b> → <b>{format_amount(example_out)}</b> <i>(+{format_amount(example_profit)})</i>'
        f'</blockquote>\n'
        f'<blockquote>'
        f'<tg-emoji emoji-id="5278467510604160626">👛</tg-emoji> '
        f'<b>Баланс:</b> {format_amount(bal)} <tg-emoji emoji-id="5199552030615558774">👛</tg-emoji> · {afford_line}\n'
        f'📊 <b>Лимит:</b> {limit_line}'
        f'</blockquote>'
    )


def cdl_detail_keyboard(dep_key: str, can_afford: bool, uid: int = 0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    limit_ok, used, max_uses = check_deposit_limit(uid, dep_key) if uid else (True, 0, 0)
    if not limit_ok:
        builder.row(InlineKeyboardButton(
            text=f"🚫 Лимит исчерпан ({used}/{max_uses})",
            callback_data="cdl_limit_reached",
            icon_custom_emoji_id="5400362079783770689",
            style="danger"
        ))
    elif can_afford:
        builder.row(InlineKeyboardButton(
            text="Открыть вклад",
            callback_data=f"cdl_open_{dep_key}",
            icon_custom_emoji_id="5197288647275071607",
            style="success"
        ))
    else:
        builder.row(InlineKeyboardButton(
            text="Недостаточно монет",
            callback_data="cdl_cant_afford",
            icon_custom_emoji_id="5400362079783770689",
            style="danger"
        ))
    builder.row(InlineKeyboardButton(
        text="Назад",
        callback_data="cdl_main",
        icon_custom_emoji_id=_BACK_EMOJI
    ))
    return builder.as_markup()


def cdl_input_text(dep_key: str, d: dict) -> str:
    from database import format_amount
    dep = DEPOSITS_BY_KEY[dep_key]
    bal = d.get("balance", 0)
    return (
        f'<tg-emoji emoji-id="{dep["emoji_id"]}">{dep["color"]}</tg-emoji> '
        f'<b>{dep["label"]} вклад</b>\n\n'
        f'<blockquote>'
        f'<b><tg-emoji emoji-id="5278467510604160626">👛</tg-emoji>Баланс:</b> {format_amount(bal)}\n'
        f'<b><tg-emoji emoji-id="5447183459602669338">👛</tg-emoji>Минимум:</b> {format_amount(dep["min"])} · <b>+{dep["profit"]}%</b>'
        f'</blockquote>\n\n'
        f'<b><i><tg-emoji emoji-id="5197269100878907942">👛</tg-emoji>Введи сумму ниже:</i></b>'
    )


def cdl_input_keyboard(dep_key: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="Отмена",
        callback_data=f"cdl_info_{dep_key}",
        icon_custom_emoji_id=_BACK_EMOJI
    ))
    return builder.as_markup()


def cdl_confirm_text(dep_key: str, amount: int) -> str:
    from database import format_amount
    dep = DEPOSITS_BY_KEY[dep_key]
    payout = int(amount * dep["percent"] / 100)
    profit = payout - amount
    return (
        f'<tg-emoji emoji-id="{dep["emoji_id"]}">{dep["color"]}</tg-emoji> '
        f'<b>Подтверди вклад</b>\n\n'
        f'<blockquote>'
        f'<b>{format_amount(amount)}</b> → <b>{format_amount(payout)}</b> <i>(+{format_amount(profit)})</i>\n'
        f'<i>{dep["label"]} · {dep["hours"]}ч · +{dep["profit"]}%</i>'
        f'</blockquote>'
    )


def cdl_confirm_keyboard(dep_key: str, amount: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Открыть",
            callback_data=f"cdl_confirm_{dep_key}_{amount}",
            icon_custom_emoji_id="5449683594425410231",
            style="success"
        ),
        InlineKeyboardButton(
            text=" Отмена",
            callback_data=f"cdl_info_{dep_key}",
            icon_custom_emoji_id="5447183459602669338",
            style="danger"
        ),
    )
    return builder.as_markup()


def cdl_opened_text(dep_key: str, amount: int) -> str:
    from database import format_amount
    dep = DEPOSITS_BY_KEY[dep_key]
    payout = int(amount * dep["percent"] / 100)
    closes_ts = int(time.time()) + dep["hours"] * 3600
    return (
        f'<tg-emoji emoji-id="{dep["emoji_id"]}">{dep["color"]}</tg-emoji> '
        f'<b>Вклад открыт!</b>\n\n'
        f'<blockquote>'
        f'<b>{format_amount(amount)}</b> → <b>{format_amount(payout)}</b>\n'
        f'<i>Забрать {_fmt_ts(closes_ts)}</i>'
        f'</blockquote>'
    )


def cdl_claim_text(total_payout: int, total_profit: int, count: int) -> str:
    from database import format_amount
    return (
        f'<tg-emoji emoji-id="5440621591387980068">💰</tg-emoji> '
        f'<b>Получено!</b>\n\n'
        f'<blockquote>'
        f'<b>{format_amount(total_payout)}</b> · <i>+{format_amount(total_profit)} прибыли</i> · {count} вкл.'
        f'</blockquote>'
    )
