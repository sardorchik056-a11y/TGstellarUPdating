# ============================================================
#  cdl.py  —  Система вкладов TGStellar
#  4 типа вкладов: 24ч/48ч/96ч/144ч
#  Логика: открыть вклад → ждать → забрать с процентами
# ============================================================

import sqlite3
import json
import time
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

DB_PATH = "tgstellar.db"

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


# ---------- База данных ----------

def init_cdl_db():
    """Создаёт таблицу вкладов. Вызвать при старте бота."""
    with sqlite3.connect(DB_PATH) as conn:
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
    with sqlite3.connect(DB_PATH) as conn:
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
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM deposits WHERE uid=? AND claimed=0 ORDER BY opens_at, id",
            (uid,)
        ).fetchall()
    return [dict(r) for r in rows]


def _get_ready_deposits(uid: int) -> list[dict]:
    """Вклады, срок которых истёк — можно забрать."""
    now = int(time.time())
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM deposits WHERE uid=? AND claimed=0 AND closes_at<=?",
            (uid, now)
        ).fetchall()
    return [dict(r) for r in rows]


def _claim_deposit(dep_id: int) -> int | None:
    """Отметить вклад как выплаченный. Возвращает payout или None."""
    now = int(time.time())
    with sqlite3.connect(DB_PATH) as conn:
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


def _count_active(uid: int) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM deposits WHERE uid=? AND claimed=0", (uid,)
        ).fetchone()
    return row[0] if row else 0


def _get_all_active(uid: int) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM deposits WHERE uid=? AND claimed=0 ORDER BY closes_at ASC",
            (uid,)
        ).fetchall()
    return [dict(r) for r in rows]


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

    # Строки активных вкладов
    if active:
        active_lines = ""
        for dep in active:
            dep_cfg = DEPOSITS_BY_KEY.get(dep["dep_key"], {})
            left = max(0, dep["closes_at"] - now)
            ready = left == 0
            status = "<b>Готов!</b> ✅" if ready else f"<i>{_fmt_time_left(left)}</i>"
            active_lines += (
                f'\n<tg-emoji emoji-id="{dep_cfg.get("emoji_id", "")}">'
                f'{dep_cfg.get("color", "⚪")}</tg-emoji>'
                f' <b>{dep_cfg.get("label", dep["dep_key"])}</b>'
                f' · {format_amount(dep["amount"])} → <b>{format_amount(dep["payout"])}</b>'
                f' · {status}'
            )
        active_block = (
            f'\n\n<blockquote>'
            f'<tg-emoji emoji-id="6030776052345737530">📋</tg-emoji> '
            f'<b>Активные вклады:</b>'
            f'{active_lines}'
            f'</blockquote>'
        )
    else:
        active_block = (
            f'\n\n<blockquote>'
            f'<tg-emoji emoji-id="6030776052345737530">📋</tg-emoji> '
            f'<b>Активных вкладов нет</b>\n'
            f'<i>Выбери тариф ниже и открой первый вклад</i>'
            f'</blockquote>'
        )

    return (
        f'<tg-emoji emoji-id="5397916757333654639">💰</tg-emoji> <b>Вклады</b>\n\n'
        f'<blockquote>'
        f'Вложи монеты на срок и забери с прибылью — '
        f'чем дольше вклад, тем выше доходность.\n\n'
        f'<tg-emoji emoji-id="5438496463044752972">📌</tg-emoji> '
        f'<b>Баланс:</b> <b>{format_amount(bal)}</b> монет'
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
    bal = d.get("balance", 0)
    can_afford = bal >= dep["min"]

    # Пример расчёта: минимальный вклад
    example_in  = dep["min"]
    example_out = int(example_in * dep["percent"] / 100)
    example_profit = example_out - example_in

    afford_line = (
        f'<tg-emoji emoji-id="5325547803936572038">✅</tg-emoji> '
        f'<b>Монет достаточно — можно открывать</b>'
        if can_afford else
        f'<tg-emoji emoji-id="5325547803936572038">❌</tg-emoji> '
        f'<b>Не хватает</b> <i>{format_amount(dep["min"] - bal)} монет</i>'
    )

    return (
        f'<tg-emoji emoji-id="{dep["emoji_id"]}">{dep["color"]}</tg-emoji> '
        f'<b>{dep["label"]} вклад</b>\n\n'
        f'<blockquote>'
        f'<tg-emoji emoji-id="5440621591387980068">⏰</tg-emoji> '
        f'<b>Срок:</b> {dep["hours"]}ч <i>({dep["hours"] // 24} дн.)</i>\n'
        f'<tg-emoji emoji-id="5231200819986047254">📊</tg-emoji> '
        f'<b>Выплата:</b> {dep["percent"]}% от вклада\n'
        f'<tg-emoji emoji-id="5427168083074628963">💸</tg-emoji> '
        f'<b>Прибыль:</b> +{dep["profit"]}%\n'
        f'<tg-emoji emoji-id="5397916757333654639">💰</tg-emoji> '
        f'<b>Минимум:</b> {format_amount(dep["min"])}'
        f'</blockquote>\n'
        f'<blockquote>'
        f'<tg-emoji emoji-id="5303214794336125778">🧮</tg-emoji> '
        f'<b>Пример:</b> вложить <b>{format_amount(example_in)}</b> → '
        f'получить <b>{format_amount(example_out)}</b> '
        f'<i>(+{format_amount(example_profit)})</i>'
        f'</blockquote>\n'
        f'<blockquote>'
        f'<tg-emoji emoji-id="5278467510604160626">👛</tg-emoji> '
        f'<b>Баланс:</b> {format_amount(bal)}\n'
        f'{afford_line}'
        f'</blockquote>'
    )


def cdl_detail_keyboard(dep_key: str, can_afford: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if can_afford:
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
        f'<tg-emoji emoji-id="5197269100878907942">📌</tg-emoji> '
        f'<b>Минимум:</b> {format_amount(dep["min"])}\n'
        f'<tg-emoji emoji-id="5429518319243775957">💳</tg-emoji> '
        f'<b>Баланс:</b> {format_amount(bal)}\n'
        f'<tg-emoji emoji-id="5201691993775818138">💸</tg-emoji> '
        f'<b>Доходность:</b> <b>+{dep["profit"]}%</b> за {dep["hours"]}ч'
        f'</blockquote>\n'
        f'<i>Введи сумму — например <code>{format_amount(dep["min"])}</code></i>'
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
        f'<b>Подтверждение вклада</b>\n\n'
        f'<blockquote>'
        f'<tg-emoji emoji-id="5199552030615558774">💰</tg-emoji> '
        f'<b>Сумма:</b> {format_amount(amount)}\n'
        f'<tg-emoji emoji-id="5231200819986047254">📊</tg-emoji> '
        f'<b>Тариф:</b> {dep["label"]} · <b>{dep["percent"]}%</b>\n'
        f'<tg-emoji emoji-id="5440621591387980068">⏰</tg-emoji> '
        f'<b>Срок:</b> {dep["hours"]}ч\n'
        f'<tg-emoji emoji-id="5244837092042750681">📈</tg-emoji> '
        f'<b>Получишь:</b> <b>{format_amount(payout)}</b> '
        f'<i>(+{format_amount(profit)})</i>'
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
        f'<b>{dep["label"]} вклад открыт!</b>\n\n'
        f'<blockquote>'
        f'<tg-emoji emoji-id="5222079954421818267">💰</tg-emoji> '
        f'<b>Вложено:</b> {format_amount(amount)}\n'
        f'<tg-emoji emoji-id="5251203410396458957">🎯</tg-emoji> '
        f'<b>Выплата:</b> <b>{format_amount(payout)}</b>\n'
        f'<tg-emoji emoji-id="5440621591387980068">⏰</tg-emoji> '
        f'<b>Готов:</b> <i>{_fmt_ts(closes_ts)}</i>'
        f'</blockquote>'
    )


def cdl_claim_text(total_payout: int, total_profit: int, count: int) -> str:
    from database import format_amount
    return (
        f'<tg-emoji emoji-id="5440621591387980068">💰</tg-emoji> '
        f'<b>Вклады получены!</b>\n\n'
        f'<blockquote>'
        f'<tg-emoji emoji-id="5397916757333654639">📦</tg-emoji> '
        f'<b>Выплачено вкладов:</b> {count}\n'
        f'<tg-emoji emoji-id="5427168083074628963">💳</tg-emoji> '
        f'<b>Получено:</b> <b>{format_amount(total_payout)}</b>\n'
        f'<tg-emoji emoji-id="5438496463044752972">📈</tg-emoji> '
        f'<b>Прибыль:</b> <i>+{format_amount(total_profit)}</i>'
        f'</blockquote>'
    )
