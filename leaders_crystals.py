# ============================================================
#  leaders_crystals.py  —  Топ по кристаллам (Гильдия торговцев)
#  Периоды: всё время, сегодня, вчера, неделя
#  Стиль полностью синхронизирован с leaders.py
#  Отдельный модуль: НЕ импортирует city.py (наоборот — city.py
#  импортирует отсюда log_crystal_event), поэтому циклов импорта нет.
# ============================================================

import sqlite3
import unicodedata
from datetime import datetime, timezone, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import DB_PATH  # тот же файл БД, что и у всего бота

router = Router(name="leaders_crystals")

# ─────────────────────────────────────────
#  КОНСТАНТЫ
# ─────────────────────────────────────────

TOP_SIZE = 10  # Топ 10 игроков

CURRENCY_NAME = "кристаллы"
CURRENCY_NAME_SINGULAR = "кристалл"

# Периоды — ровно те, что нужны: всё время / сегодня / вчера / неделя
PERIODS = {
    "alltime":   "Всё время",
    "today":     "Сегодня",
    "yesterday": "Вчера",
    "week":      "Неделя",
}

_E = {
    "crystal":  "5427168083074628963",
    "back":     "6039539366177541657",
    "calendar": "5274055917766202507",
    "shield":   "5354905713585975489",
    "empty":    "5397916757333654639",
}

_PERIOD_ICONS = {
    "alltime":   ("5274055917766202507", "📅"),
    "today":     ("5274055917766202507", "📅"),
    "yesterday": ("5274055917766202507", "📅"),
    "week":      ("5274055917766202507", "📅"),
}

# Иконки мест 1-10 (те же id, что в leaders.py — для единого визуального стиля)
_PLACE_EMOJI = {
    1:  "5440539497383087970",
    2:  "5447203607294265305",
    3:  "5453902265922376865",
    4:  "5382054253403577563",
    5:  "5391197405553107640",
    6:  "5390966190283694453",
    7:  "5382132232829804982",
    8:  "5391038994274329680",
    9:  "5391234698754138414",
    10: "5393480373944459905",
}

_LRM = "\u200e"
_LRI = "\u2066"
_PDI = "\u2069"


def _tg(eid: str, fb: str = "") -> str:
    return f'<tg-emoji emoji-id="{eid}">{fb}</tg-emoji>'


def _fmt(n) -> str:
    """1500 -> '1.5к', 100000 -> '100к', 2300000 -> '2.3м' — как в leaders.py."""
    try:
        n = float(n)
    except (TypeError, ValueError):
        return str(n)

    sign = "-" if n < 0 else ""
    n = abs(n)

    if n < 1000:
        if n == int(n):
            return f"{sign}{int(n)}"
        return f"{sign}{n:.1f}"

    for div, suffix in [
        (1_000_000_000_000, "трлн"),
        (1_000_000_000,     "млрд"),
        (1_000_000,         "м"),
        (1_000,             "к"),
    ]:
        if n >= div:
            val = n / div
            val = int(val * 10) / 10
            if val == int(val):
                return f"{sign}{int(val)}{suffix}"
            return f"{sign}{val:.1f}{suffix}"

    return f"{sign}{int(n)}"


def _now_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ─────────────────────────────────────────
#  ИНИЦИАЛИЗАЦИЯ / ЛОГ СОБЫТИЙ
# ─────────────────────────────────────────

def init_crystal_leaders_db():
    """Создаёт таблицу событий баланса кристаллов, если её ещё нет.
    Вызвать при старте бота (можно рядом с init_city_db)."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS city_crystal_events (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                uid     INTEGER NOT NULL,
                delta   INTEGER NOT NULL,
                ts      INTEGER NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cce_uid ON city_crystal_events(uid)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cce_ts  ON city_crystal_events(ts)")
        conn.commit()


def log_crystal_event(uid: int, delta: int):
    """Пишет изменение баланса кристаллов (+/-). Вызывается из city.py
    в каждой функции, которая двигает баланс: покупка, продажа, дорога,
    штраф таможни, ежедневный бонус, обмен, апгрейд повозки, админ-начисления.
    Нулевые дельты не пишем — они бесполезны для топа и просто раздувают таблицу."""
    if not delta:
        return
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO city_crystal_events (uid, delta, ts) VALUES (?, ?, ?)",
            (uid, delta, _now_ts()),
        )
        conn.commit()


# ─────────────────────────────────────────
#  ГРАНИЦЫ ПЕРИОДА
# ─────────────────────────────────────────

def _period_bounds(period: str) -> tuple[int, int]:
    """(ts_from, ts_to). ts_to=0 → без верхней границы."""
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if period == "today":
        return int(today.timestamp()), 0

    if period == "yesterday":
        yd = today - timedelta(days=1)
        return int(yd.timestamp()), int(today.timestamp())

    if period == "week":
        week_start = today - timedelta(days=today.weekday())
        return int(week_start.timestamp()), 0

    # alltime
    return 0, 0


# ─────────────────────────────────────────
#  ИМЕНА ИГРОКОВ
# ─────────────────────────────────────────

def _strip_invisible(text: str) -> str:
    """Убирает control/format-символы (bidi-оверрайды, zero-width и т.п.) —
    защита от "троянских" имён с символами разворота направления текста."""
    return "".join(ch for ch in text if unicodedata.category(ch) not in ("Cc", "Cf"))


def _lookup_names(uids: list) -> dict:
    """uid -> (first_name, username). Сначала пробуем основную таблицу users
    (там обычно есть first_name), затем добираем то, чего не хватает, из
    city_users.username. Если игрока нигде нет — просто "Аноним"."""
    names = {}
    if not uids:
        return names

    placeholders = ",".join("?" for _ in uids)
    with _get_conn() as conn:
        try:
            rows = conn.execute(
                f"SELECT id, data_json FROM users WHERE id IN ({placeholders})", uids
            ).fetchall()
            import json
            for r in rows:
                try:
                    d = json.loads(r["data_json"])
                    names[r["id"]] = (d.get("first_name", ""), d.get("username", ""))
                except Exception:
                    pass
        except sqlite3.OperationalError:
            pass  # таблицы users в другом формате/нет — не критично

        try:
            rows = conn.execute(
                f"SELECT user_id, username FROM city_users WHERE user_id IN ({placeholders})", uids
            ).fetchall()
            for r in rows:
                if r["user_id"] not in names:
                    names[r["user_id"]] = ("", r["username"] or "")
        except sqlite3.OperationalError:
            pass

    return names


def _display_name(uid: int, names: dict) -> str:
    fname, uname = names.get(uid, ("", ""))
    fname = _strip_invisible(fname or "").strip()
    uname = _strip_invisible(uname or "").strip()
    if fname:
        return fname
    if uname:
        return f"@{uname}"
    return "@none"


# ─────────────────────────────────────────
#  ЗАПРОСЫ ЛИДЕРОВ
# ─────────────────────────────────────────

def get_crystal_leaders(period: str) -> list[dict]:
    """
    alltime  → топ по ТЕКУЩЕМУ балансу кристаллов (кто богаче всех прямо сейчас).
    today / yesterday / week → топ по ЧИСТОМУ приросту кристаллов за период
    (сумма всех +/- событий баланса за окно времени) — то есть "кто больше
    всех заработал" за сегодня/вчера/неделю, а не просто у кого больше денег.
    """
    if period == "alltime":
        with _get_conn() as conn:
            rows = conn.execute(
                "SELECT user_id AS uid, balance AS value FROM city_users "
                "WHERE balance > 0 ORDER BY balance DESC LIMIT ?",
                (TOP_SIZE,),
            ).fetchall()
        ranked = [dict(r) for r in rows]
    else:
        ts_from, ts_to = _period_bounds(period)
        where = "WHERE 1=1"
        params: list = []
        if ts_from:
            where += " AND ts>=?"; params.append(ts_from)
        if ts_to:
            where += " AND ts<?";  params.append(ts_to)

        sql = f"""
            SELECT uid, SUM(delta) AS value
            FROM city_crystal_events
            {where}
            GROUP BY uid
            HAVING value > 0
            ORDER BY value DESC
            LIMIT {TOP_SIZE}
        """
        with _get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        ranked = [dict(r) for r in rows]

    uids = [r["uid"] for r in ranked]
    names = _lookup_names(uids)
    for r in ranked:
        fname, uname = names.get(r["uid"], ("", ""))
        r["first_name"] = fname
        r["username"] = uname
    return ranked


def get_user_crystal_rank(uid: int, period: str) -> int | None:
    leaders = get_crystal_leaders(period)
    for i, row in enumerate(leaders):
        if row["uid"] == uid:
            return i + 1
    return None


# ─────────────────────────────────────────
#  ФОРМАТИРОВАНИЕ ТЕКСТА
# ─────────────────────────────────────────

def crystal_leaders_text(period: str, viewer_uid: int | None = None) -> str:
    leaders = get_crystal_leaders(period)
    period_name = PERIODS[period]
    p_eid, p_fb = _PERIOD_ICONS[period]

    is_snapshot = period == "alltime"
    subtitle = "Богатейшие торговцы" if is_snapshot else "Больше всех заработали за период"

    lines = [
        f'<blockquote>'
        f'{_tg(_E["crystal"], "💎")} <b>Топ по кристаллам</b>\n'
        f'{_tg(p_eid, p_fb)} <b>Период: {period_name}</b>\n'
        f'<i>{subtitle}</i>'
        f'</blockquote>\n'
    ]

    if not leaders:
        lines.append(
            f'<blockquote>'
            f'{_tg(_E["empty"], "🎟")} <b>Статистики пока нет.</b>\n'
            f'<i>Торгуй в Гильдии — и попадёшь в топ!</i>'
            f'</blockquote>'
        )
        return "\n".join(lines)

    table_lines: list[str] = []
    for i, row in enumerate(leaders):
        place = i + 1
        name = _display_name(row["uid"], {row["uid"]: (row.get("first_name", ""), row.get("username", ""))})
        val = f'{_fmt(row["value"])} 💎'
        is_me = (viewer_uid is not None and row["uid"] == viewer_uid)

        if place in _PLACE_EMOJI:
            place_str = _tg(_PLACE_EMOJI[place], "🏅")
        else:
            place_str = f"<b>{place}.</b>"

        name_str = f"<b>{name}</b>" if is_me else name
        val_str = f"<b>{val}</b>" if is_me else val
        me_mark = " ←" if is_me else ""

        table_lines.append(
            f'{_LRM}{place_str} {_LRI}{name_str}{_PDI} — {val_str}{me_mark}'
        )

    lines.append("<blockquote>" + "\n".join(table_lines) + "</blockquote>")

    if viewer_uid is not None:
        rank = get_user_crystal_rank(viewer_uid, period)
        if rank is None:
            lines.append(
                f'\n<blockquote>'
                f'{_tg(_E["shield"], "🛡")} <b>Тебя нет в топ-{TOP_SIZE}</b>\n'
                f'<i>Торгуй и копи кристаллы — и ты попадёшь в список!</i>'
                f'</blockquote>'
            )

    return "\n".join(lines)


# ─────────────────────────────────────────
#  КЛАВИАТУРА
# ─────────────────────────────────────────

def crystal_leaders_keyboard(period: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    period_buttons: list[InlineKeyboardButton] = []
    for key in PERIODS:
        eid, fb = _PERIOD_ICONS[key]
        label = PERIODS[key]
        btn_text = f"· {label} ·" if key == period else label
        period_buttons.append(InlineKeyboardButton(
            text=btn_text,
            callback_data=f"crystop_{key}",
            icon_custom_emoji_id=eid,
        ))

    builder.row(*period_buttons[:2])
    builder.row(*period_buttons[2:])

    builder.row(InlineKeyboardButton(
        text="Назад",
        callback_data="back_to_menu",
        icon_custom_emoji_id=_E["back"],
    ))

    return builder.as_markup()


# ─────────────────────────────────────────
#  ТОЧКА ВХОДА
# ─────────────────────────────────────────

DEFAULT_PERIOD = "alltime"


def crystal_leaders_main_text(viewer_uid: int | None = None) -> str:
    return crystal_leaders_text(DEFAULT_PERIOD, viewer_uid)


def crystal_leaders_main_keyboard() -> InlineKeyboardMarkup:
    return crystal_leaders_keyboard(DEFAULT_PERIOD)


# ─────────────────────────────────────────
#  ХЕНДЛЕРЫ
# ─────────────────────────────────────────

@router.message(Command("citytop", "топкристаллов", "crystaltop"))
async def cmd_crystal_leaders(message: Message):
    uid = message.from_user.id
    await message.reply(
        crystal_leaders_main_text(viewer_uid=uid),
        parse_mode="HTML",
        reply_markup=crystal_leaders_main_keyboard(),
    )


@router.callback_query(F.data.startswith("crystop_"))
async def cb_crystal_leaders(call: CallbackQuery):
    period = call.data.replace("crystop_", "", 1)
    if period not in PERIODS:
        await call.answer("Неизвестный период", show_alert=True)
        return
    uid = call.from_user.id
    await call.message.edit_text(
        crystal_leaders_text(period, viewer_uid=uid),
        parse_mode="HTML",
        reply_markup=crystal_leaders_keyboard(period),
    )
    await call.answer()
