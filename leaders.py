# ============================================================
#  leaders.py  —  Лидерборд TGStellar
#  Категории: убийства боссов, баланс, уровень, урон боссу
#  Периоды: сегодня, вчера, неделя, месяц, всё время
#  Переписан для aiogram 3.x
# ============================================================

import sqlite3
import json
import unicodedata
from datetime import datetime, timezone, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

DB_PATH = "tgstellar.db"

# ─────────────────────────────────────────
#  КОНСТАНТЫ
# ─────────────────────────────────────────

TOP_SIZE = 10  # Топ 10 игроков

# Периоды
PERIODS = {
    "today":     "Сегодня",
    "yesterday": "Вчера",
    "week":      "Неделя",
    "month":     "Месяц",
    "alltime":   "Всё время",
}

PERIODS_EN = {
    "today":     "Today",
    "yesterday": "Yesterday",
    "week":      "Week",
    "month":     "Month",
    "alltime":   "All Time",
}

# Категории
CATEGORIES = {
    "kills":   "Убийства боссов",
    "balance": "Баланс",
    "level":   "Уровень",
    "damage":  "Урон боссу",
}

CATEGORIES_EN = {
    "kills":   "Boss Kills",
    "balance": "Balance",
    "level":   "Level",
    "damage":  "Boss Damage",
}

# ─────────────────────────────────────────
#  ЭМОДЗИ
# ─────────────────────────────────────────
_E = {
    "trophy":     "5449683594425410231",
    "crown":      "5325547803936572038",
    "star":       "5427168083074628963",
    "sword":      "5258203794772085854",
    "skull":      "5228962845672096235",
    "coin":       "5199552030615558774",
    "level":      "5341498088408234504",
    "damage":     "5373173798633752502",
    "fire":       "5438571934210082705",
    "back":       "6039539366177541657",
    "calendar":   "5382194935057372936",
    "medal_gold": "5449683594425410231",
    "up":         "5197371802136892976",
    "shield":     "5354905713585975489",
    "kills":      "5228962845672096235",
    "empty":      "5397916757333654639",
}

# Иконки категорий
_CAT_ICONS = {
    "kills":   ("5228962845672096235", "💀"),
    "balance": ("5278467510604160626", "💰"),
    "level":   ("5341498088408234504", "⭐"),
    "damage":  ("5373173798633752502", "💥"),
}

# Иконки периодов
_PERIOD_ICONS = {
    "today":     ("5274055917766202507", "📅"),
    "yesterday": ("5274055917766202507", "📅"),
    "week":      ("5274055917766202507", "📅"),
    "month":     ("5274055917766202507", "📅"),
    "alltime":   ("5274055917766202507", "📅"),
}

# Иконки мест 1-10 (медали + цветные цифры).
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

# Метка "слева-направо" (Left-to-Right Mark, U+200E) — невидимая,
# ставим в начало каждой строки таблицы, чтобы Telegram не пытался
# сам угадывать направление параграфа.
_LRM = "\u200e"

# Изоляторы направления (Left-to-Right Isolate / Pop Directional
# Isolate, U+2066 / U+2069) — оборачиваем ИМЯ игрока в них. Имя —
# единственный кусок строки, который приходит от пользователя и
# не контролируется ботом. Реальная причина "каши" на скрине —
# не обычная RTL-путаница, а то, что один из игроков вписал себе
# в имя символ U+202E (Right-to-Left Override, "троянский" символ,
# которым обычно маскируют exe под txt). Этот символ форсированно
# разворачивает посимвольно ВСЁ, что идёт после него, до конца
# строки, и никакой LRM в начале строки это не остановит — explicit
# override игнорирует базовое направление параграфа. Изоляторы не
# дают такому символу "выйти" за пределы имени и испортить всё
# остальное (тире, иконку, значение), а заодно не ломают вид
# нормальных RTL-имён (арабские/иврит), позволяя им читаться
# корректно внутри своей изоляции.
_LRI = "\u2066"
_PDI = "\u2069"


def _tg(eid: str, fb: str = "") -> str:
    return f'<tg-emoji emoji-id="{eid}">{fb}</tg-emoji>'


def _fmt(n) -> str:
    """
    Сокращённый формат чисел: 1500 -> "1.5к", 100000 -> "100к",
    2300000 -> "2.3м" и т.д. Единый стиль во всём боте.
    """
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


# ─────────────────────────────────────────
#  ИНИЦИАЛИЗАЦИЯ ТАБЛИЦЫ СТАТИСТИКИ
# ─────────────────────────────────────────

def init_leaders_db():
    """Создаёт таблицу stats если не существует. Вызвать при старте."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS boss_stats (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                uid        INTEGER NOT NULL,
                username   TEXT    NOT NULL DEFAULT 'Аноним',
                first_name TEXT    NOT NULL DEFAULT '',
                boss_key   TEXT    NOT NULL,
                damage     INTEGER NOT NULL DEFAULT 0,
                killed     INTEGER NOT NULL DEFAULT 0,
                ts         INTEGER NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_bs_uid ON boss_stats(uid)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_bs_ts  ON boss_stats(ts)")
        conn.commit()


def record_boss_hit(uid: int, username: str, first_name: str,
                    boss_key: str, damage: int, killed: bool):
    """
    Записывает удар по боссу в таблицу boss_stats.
    Вызывать из hunt.py после каждого успешного удара.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO boss_stats (uid, username, first_name, boss_key, damage, killed, ts) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (uid, username or "Аноним", first_name or "", boss_key,
             damage, 1 if killed else 0, _now_ts())
        )
        conn.commit()


# ─────────────────────────────────────────
#  ВЫЧИСЛЕНИЕ ГРАНИЦ ПЕРИОДА
# ─────────────────────────────────────────

def _period_bounds(period: str) -> tuple[int, int]:
    """Возвращает (ts_from, ts_to) для периода. ts_to=0 → без верхней границы."""
    now   = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if period == "today":
        return int(today.timestamp()), 0

    if period == "yesterday":
        yd = today - timedelta(days=1)
        return int(yd.timestamp()), int(today.timestamp())

    if period == "week":
        week_start = today - timedelta(days=today.weekday())
        return int(week_start.timestamp()), 0

    if period == "month":
        month_start = today.replace(day=1)
        return int(month_start.timestamp()), 0

    # alltime
    return 0, 0


# ─────────────────────────────────────────
#  ЗАПРОСЫ ЛИДЕРОВ
# ─────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _leaders_kills(period: str) -> list[dict]:
    ts_from, ts_to = _period_bounds(period)
    where = "WHERE killed=1"
    params: list = []
    if ts_from:
        where += " AND ts>=?"; params.append(ts_from)
    if ts_to:
        where += " AND ts<?";  params.append(ts_to)

    sql = f"""
        SELECT uid, first_name, username,
               SUM(killed) AS value
        FROM boss_stats
        {where}
        GROUP BY uid
        ORDER BY value DESC
        LIMIT {TOP_SIZE}
    """
    with _get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def _leaders_damage(period: str) -> list[dict]:
    ts_from, ts_to = _period_bounds(period)
    where = "WHERE 1=1"
    params: list = []
    if ts_from:
        where += " AND ts>=?"; params.append(ts_from)
    if ts_to:
        where += " AND ts<?";  params.append(ts_to)

    sql = f"""
        SELECT uid, first_name, username,
               SUM(damage) AS value
        FROM boss_stats
        {where}
        GROUP BY uid
        ORDER BY value DESC
        LIMIT {TOP_SIZE}
    """
    with _get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def _leaders_balance(period: str) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute("SELECT data_json FROM users").fetchall()

    users_all = [json.loads(r["data_json"]) for r in rows]
    ranked = sorted(users_all, key=lambda u: u.get("balance", 0), reverse=True)[:TOP_SIZE]
    return [
        {
            "uid":        u["id"],
            "first_name": u.get("first_name", "") or u.get("username", "Аноним"),
            "username":   u.get("username", ""),
            "value":      u.get("balance", 0),
        }
        for u in ranked
    ]


def _leaders_level(period: str) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute("SELECT data_json FROM users").fetchall()

    users_all = [json.loads(r["data_json"]) for r in rows]
    ranked = sorted(users_all, key=lambda u: (u.get("level", 1), u.get("xp", 0)), reverse=True)[:TOP_SIZE]
    return [
        {
            "uid":        u["id"],
            "first_name": u.get("first_name", "") or u.get("username", "Аноним"),
            "username":   u.get("username", ""),
            "value":      u.get("level", 1),
            "xp":         u.get("xp", 0),
        }
        for u in ranked
    ]


def get_leaders(category: str, period: str) -> list[dict]:
    if category == "kills":
        return _leaders_kills(period)
    if category == "damage":
        return _leaders_damage(period)
    if category == "balance":
        return _leaders_balance(period)
    if category == "level":
        return _leaders_level(period)
    return []


# ─────────────────────────────────────────
#  РАНГ ПОЛЬЗОВАТЕЛЯ
# ─────────────────────────────────────────

def get_user_rank(uid: int, category: str, period: str) -> int | None:
    leaders = get_leaders(category, period)
    for i, row in enumerate(leaders):
        if row["uid"] == uid:
            return i + 1
    return None


# ─────────────────────────────────────────
#  ФОРМАТИРОВАНИЕ ТЕКСТА
# ─────────────────────────────────────────

def _strip_invisible(text: str) -> str:
    """
    Убирает из строки все непечатаемые control/format-символы (категории
    Unicode 'Cc' и 'Cf') — туда попадают любые bidi-метки/оверрайды
    (LRM, RLM, LRE/RLE, LRO/RLO, LRI/RLI/FSI/PDI), zero-width символы
    и обычные control-символы типа \\n или \\t внутри имени. Это общая
    защита от "троянских" имён, а не патч под один конкретный символ.
    """
    return "".join(ch for ch in text if unicodedata.category(ch) not in ("Cc", "Cf"))


def _display_name(row: dict) -> str:
    fname = _strip_invisible((row.get("first_name") or "")).strip()
    uname = _strip_invisible((row.get("username")   or "")).strip()
    if fname:
        return fname
    if uname:
        return f"@{uname}"
    return "@none"


def _value_str(category: str, row: dict, lang: str = "ru") -> str:
    val = row.get("value", 0)
    if category == "kills":
        return f'{_fmt(val)} {"kills" if lang == "en" else "убийств"}'
    if category == "damage":
        return f'{_fmt(val)} {"dmg" if lang == "en" else "урона"}'
    if category == "balance":
        return f'{_fmt(val)}'
    if category == "level":
        return f'{"Lv." if lang == "en" else "Ур."} {val}'
    return str(val)


def _value_icon(category: str) -> str:
    eid, fb = _CAT_ICONS[category]
    return _tg(eid, fb)


def leaders_text(category: str, period: str, viewer_uid: int | None = None, lang: str = "ru") -> str:
    leaders = get_leaders(category, period)

    _PERIODS    = PERIODS_EN    if lang == "en" else PERIODS
    _CATEGORIES = CATEGORIES_EN if lang == "en" else CATEGORIES

    cat_name    = _CATEGORIES[category]
    period_name = _PERIODS[period]
    p_eid, p_fb = _PERIOD_ICONS[period]
    c_eid, c_fb = _CAT_ICONS[category]

    # ── Заголовок ──
    if lang == "en":
        lines = [
            f'<blockquote>'
            f'{_tg(c_eid, c_fb)} <b>Leaderboard · {cat_name}</b>\n'
            f'{_tg(p_eid, p_fb)} <b>Period: {period_name}</b>'
            f'</blockquote>\n'
        ]
    else:
        lines = [
            f'<blockquote>'
            f'{_tg(c_eid, c_fb)} <b>Лидеры · {cat_name}</b>\n'
            f'{_tg(p_eid, p_fb)} <b>Период: {period_name}</b>'
            f'</blockquote>\n'
        ]

    if not leaders:
        if lang == "en":
            lines.append(
                f'<blockquote>'
                f'{_tg(_E["empty"], "🎟")} <b>No stats yet.</b>\n'
                f'<i>Be the first — attack the bosses!</i>'
                f'</blockquote>'
            )
        else:
            lines.append(
                f'<blockquote>'
                f'{_tg(_E["empty"], "🎟")} <b>Статистики пока нет.</b>\n'
                f'<i>Будь первым — атакуй боссов!</i>'
                f'</blockquote>'
            )
        return "\n".join(lines)

    # ── Таблица ──
    table_lines: list[str] = []
    for i, row in enumerate(leaders):
        place = i + 1
        name  = _display_name(row)
        val   = _value_str(category, row, lang)
        is_me = (viewer_uid is not None and row.get("uid") == viewer_uid)

        if place in _PLACE_EMOJI:
            place_str = _tg(_PLACE_EMOJI[place], "🏅")
        else:
            place_str = f"<b>{place}.</b>"

        name_str = f"<b>{name}</b>" if is_me else name
        val_str  = f"<b>{val}</b>"  if is_me else val
        me_mark  = " ←" if is_me else ""

        table_lines.append(f'{_LRM}{place_str} {name_str} — {_value_icon(category)} {val_str}{me_mark}')

    lines.append("<blockquote>" + "\n".join(table_lines) + "</blockquote>")

    # ── Позиция зрителя ──
    if viewer_uid is not None:
        rank = get_user_rank(viewer_uid, category, period)
        if rank is None:
            if lang == "en":
                lines.append(
                    f'\n<blockquote>'
                    f'{_tg(_E["shield"], "🛡")} <b>You are not in the top {TOP_SIZE}</b>\n'
                    f'<i>Keep going — you\'ll make the list!</i>'
                    f'</blockquote>'
                )
            else:
                lines.append(
                    f'\n<blockquote>'
                    f'{_tg(_E["shield"], "🛡")} <b>Тебя нет в топ-{TOP_SIZE}</b>\n'
                    f'<i>Продолжай — и ты попадёшь в список!</i>'
                    f'</blockquote>'
                )

    return "\n".join(lines)


# ─────────────────────────────────────────
#  КЛАВИАТУРЫ
# ─────────────────────────────────────────

def leaders_keyboard(category: str, period: str, lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    _CATEGORIES = CATEGORIES_EN if lang == "en" else CATEGORIES
    _PERIODS    = PERIODS_EN    if lang == "en" else PERIODS

    # ── Строка категорий ──
    cat_buttons: list[InlineKeyboardButton] = []
    _SHORT_RU = {"kills": "Убийства", "balance": "Баланс", "level": "Уровень", "damage": "Урон"}
    _SHORT_EN = {"kills": "Kills",    "balance": "Balance", "level": "Level",   "damage": "Damage"}
    _SHORT = _SHORT_EN if lang == "en" else _SHORT_RU

    for key in CATEGORIES:
        eid, fb = _CAT_ICONS[key]
        short    = _SHORT[key]
        btn_text = f"· {short} ·" if key == category else short
        cat_buttons.append(InlineKeyboardButton(
            text=btn_text,
            callback_data=f"leaders_{key}_{period}",
            icon_custom_emoji_id=eid,
        ))

    builder.row(*cat_buttons[:2])
    builder.row(*cat_buttons[2:])

    # ── Строка периодов ──
    period_buttons: list[InlineKeyboardButton] = []
    for key in PERIODS:
        eid, fb  = _PERIOD_ICONS[key]
        label    = _PERIODS[key]
        btn_text = f"· {label} ·" if key == period else label
        period_buttons.append(InlineKeyboardButton(
            text=btn_text,
            callback_data=f"leaders_{category}_{key}",
            icon_custom_emoji_id=eid,
        ))

    builder.row(*period_buttons[:3])
    builder.row(*period_buttons[3:])

    # ── Назад ──
    builder.row(InlineKeyboardButton(
        text="Back" if lang == "en" else "Назад",
        callback_data="back_to_menu",
        icon_custom_emoji_id=_E["back"],
    ))

    return builder.as_markup()


# ─────────────────────────────────────────
#  ТОЧКА ВХОДА
# ─────────────────────────────────────────

DEFAULT_CATEGORY = "kills"
DEFAULT_PERIOD   = "alltime"


def leaders_main_text(viewer_uid: int | None = None, lang: str = "ru") -> str:
    return leaders_text(DEFAULT_CATEGORY, DEFAULT_PERIOD, viewer_uid, lang)


def leaders_main_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    return leaders_keyboard(DEFAULT_CATEGORY, DEFAULT_PERIOD, lang)
