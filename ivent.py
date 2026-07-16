# ============================================================
#  ivent.py  —  Глобальный реферальный ивент TGStellar
#  ------------------------------------------------------------
#  Идея: пока идёт ивент, ВСЕ игроки суммарно приглашают рефералов.
#  Чем больше суммарно приглашено рефералов за время ивента —
#  тем выше глобальный множитель скорости/объёма ВСЕЙ добычи
#  (шахта, питомцы, город и т.д.) — бонус общий для всех игроков
#  одновременно, а не персональный.
#
#  Шкала бонусов (накопительная, суммарно по всем игрокам):
#     25   рефералов  → x1.3
#     75   рефералов  → x1.5
#     150  рефералов  → x2.0
#     500  рефералов  → x3.0
#     1000 рефералов  → x5.0
#
#  Ивент длится 30 дней с момента запуска (/startevent), после
#  чего множитель автоматически возвращается к x1.0.
#
#  Считаются только ПОДТВЕРЖДЁННЫЕ рефералы (прошедшие капчу,
#  refs.rewarded=1), зарегистрированные ПОСЛЕ старта ивента —
#  это стимулирует именно новых приглашённых за время акции,
#  а не рефералов, набранных когда-то раньше.
#
#  ИНТЕГРАЦИЯ (как применить множитель к добыче):
#  В месте, где считается итоговая добыча (например miner.py,
#  функция продажи руды / начисления дохода), нужно домножить
#  итоговую сумму на множитель ивента:
#
#      from ivent import aio_get_event_multiplier
#      mult = await aio_get_event_multiplier()
#      final_amount = int(base_amount * mult)
#
#  Больше никаких правок в существующих файлах не требуется —
#  ivent.py самодостаточен и работает поверх той же БД (refs).
# ============================================================

import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = "tgstellar.db"

# ─────────────────────────────────────────
#  ПАРАМЕТРЫ ИВЕНТА
# ─────────────────────────────────────────

EVENT_DURATION_DAYS = 30
EVENT_DURATION_SEC  = EVENT_DURATION_DAYS * 24 * 60 * 60

# (порог суммарных рефералов, множитель добычи)
EVENT_TIERS: list[tuple[int, float]] = [
    (25,   1.3),
    (75,   1.5),
    (150,  2.0),
    (500,  3.0),
    (1000, 5.0),
]

EVENT_TITLE_RU = "Глобальный реферальный марафон"
EVENT_TITLE_EN = "Global Referral Marathon"

# Рабочие emoji-id (переиспользованы из refs.py / miner.py — те же, что
# уже используются в проекте, чтобы стиль совпадал 1-в-1).
_E_FRIENDS = "5332724926216428039"
_E_TIMER   = "5382194935057372936"
_E_COIN    = "5199552030615558774"
_E_STAR    = "5267500801240092311"
_E_LEVEL   = "5375338737028841420"



def _tg(eid: str, fb: str = "") -> str:
    return f'<tg-emoji emoji-id="{eid}">{fb}</tg-emoji>'


E_ROCKET  = _tg("5195033767969839232", "🔒")
E_PARTY   = _tg("5461151367559141950", "🔒")
E_FIRE    = "🔥"
E_GLOBE   = _tg("5303479226882603449", "🔒")
E_CHECK   = "✅"
E_LOCKED  = _tg("5296369303661067030", "🔒")
E_TARGET  = _tg("5310278924616356636", "🎯")
E_CLOCK   = _tg(_E_TIMER, "⏳")
E_PEOPLE  = _tg(_E_FRIENDS, "👥")
E_COINI   = _tg(_E_COIN, "🪙")
E_STARI   = _tg(_E_STAR, "⭐")

# ─────────────────────── инициализация БД ────────────────────


def init_event_db():
    with _conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS ivent_state (
                id       INTEGER PRIMARY KEY CHECK (id = 1),
                start_ts INTEGER NOT NULL,
                active   INTEGER NOT NULL DEFAULT 1,
                name_ru  TEXT,
                name_en  TEXT
            );
        """)
        c.commit()


def _get_conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA busy_timeout=30000")
    return c


@contextmanager
def _conn():
    c = _get_conn()
    try:
        with c:
            yield c
    finally:
        c.close()


# ─────────────────────────────────────────
#  УПРАВЛЕНИЕ ИВЕНТОМ
# ─────────────────────────────────────────


def start_event(name_ru: str = EVENT_TITLE_RU, name_en: str = EVENT_TITLE_EN) -> dict:
    """Запускает новый ивент прямо сейчас (перезаписывает предыдущий)."""
    now = int(time.time())
    with _conn() as c:
        c.execute("""
            INSERT INTO ivent_state (id, start_ts, active, name_ru, name_en)
            VALUES (1, ?, 1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                start_ts = excluded.start_ts,
                active   = 1,
                name_ru  = excluded.name_ru,
                name_en  = excluded.name_en
        """, (now, name_ru, name_en))
        c.commit()
    return get_event_state()


def stop_event() -> None:
    """Досрочно останавливает текущий ивент вручную."""
    with _conn() as c:
        c.execute("UPDATE ivent_state SET active = 0 WHERE id = 1")
        c.commit()


def get_event_state() -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM ivent_state WHERE id = 1").fetchone()
    return dict(row) if row else None


def get_event_end_ts(state: dict | None = None) -> int | None:
    state = state or get_event_state()
    if not state:
        return None
    return state["start_ts"] + EVENT_DURATION_SEC


def is_event_active(state: dict | None = None) -> bool:
    """Ивент считается активным, если он запущен вручную (active=1)
    И с момента старта не прошло больше EVENT_DURATION_DAYS дней."""
    state = state or get_event_state()
    if not state or not state["active"]:
        return False
    now = int(time.time())
    return now < get_event_end_ts(state)


def get_seconds_left(state: dict | None = None) -> int:
    state = state or get_event_state()
    if not state:
        return 0
    end_ts = get_event_end_ts(state)
    return max(0, end_ts - int(time.time()))


# ─────────────────────────────────────────
#  ПОДСЧЁТ РЕФЕРАЛОВ И МНОЖИТЕЛЬ
# ─────────────────────────────────────────


def get_event_referral_count(state: dict | None = None) -> int:
    """
    Суммарное число ПОДТВЕРЖДЁННЫХ рефералов (refs.rewarded=1),
    приглашённых ВСЕМИ игроками ПОСЛЕ старта текущего ивента.
    Если ивент не запускался — 0.
    """
    state = state or get_event_state()
    if not state:
        return 0
    with _conn() as c:
        row = c.execute(
            "SELECT COUNT(*) AS cnt FROM refs WHERE rewarded = 1 AND joined_ts >= ?",
            (state["start_ts"],),
        ).fetchone()
    return row["cnt"] if row else 0


def get_tier_for_count(count: int) -> tuple[int, float] | None:
    """Возвращает (порог, множитель) последнего достигнутого уровня, либо None."""
    reached = None
    for threshold, mult in EVENT_TIERS:
        if count >= threshold:
            reached = (threshold, mult)
    return reached


def get_next_tier(count: int) -> tuple[int, float] | None:
    """Возвращает (порог, множитель) следующего ещё не достигнутого уровня."""
    for threshold, mult in EVENT_TIERS:
        if count < threshold:
            return threshold, mult
    return None


def get_current_multiplier() -> float:
    """
    ГЛАВНАЯ ФУНКЦИЯ ДЛЯ ИНТЕГРАЦИИ.
    Возвращает текущий множитель добычи (x1.0, если ивент неактивен
    или порог 25 ещё не достигнут).
    """
    state = get_event_state()
    if not is_event_active(state):
        return 1.0
    count = get_event_referral_count(state)
    tier = get_tier_for_count(count)
    return tier[1] if tier else 1.0


# ─────────────────────────────────────────
#  ВИЗУАЛ: ПРОГРЕСС-БАР И ШКАЛА
# ─────────────────────────────────────────


def _progress_bar(value: int, total: int, length: int = 12) -> str:
    if total <= 0:
        return "■" * length
    ratio  = max(0.0, min(1.0, value / total))
    filled = int(round(ratio * length))
    filled = min(length, max(0, filled))
    return "■" * filled + "□" * (length - filled)


def _fmt_timedelta(seconds: int) -> str:
    seconds = max(0, int(seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days > 0:
        return f"{days} дн. {hours} ч."
    if hours > 0:
        return f"{hours} ч. {minutes} мин."
    return f"{minutes} мин."


def _fmt_timedelta_en(seconds: int) -> str:
    seconds = max(0, int(seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days > 0:
        return f"{days}d {hours}h"
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def _tier_scale_lines(count: int, lang: str = "ru") -> list[str]:
    """
    Строит шкалу-«лестницу» уровней сверху вниз (от максимального x5.0
    до первого x1.3). У каждого уровня:
      ✅ — уровень уже открыт для всех игроков
      🎯 — ближайшая цель (единственная), под ней прогресс-бар со счётом
      🔒 — уровень пока заблокирован
    Рамка из "┌│├└" визуально собирает всё в единую лестницу.
    """
    tiers_desc = list(reversed(EVENT_TIERS))  # от 1000 к 25

    # Ближайшая недостигнутая цель — САМЫЙ МАЛЕНЬКИЙ порог, который ещё
    # не пройден (а не первый по счёту сверху при обходе по убыванию).
    next_tier = get_next_tier(count)  # (threshold, mult) либо None

    # Порог уровня, стоящего чуть НИЖЕ next_tier — нужен, чтобы прогресс-бар
    # считался "от" него, а не от нуля.
    lower_of = {}
    prev = 0
    for threshold, _ in EVENT_TIERS:
        lower_of[threshold] = prev
        prev = threshold

    lines: list[str] = []
    for idx, (threshold, mult) in enumerate(tiers_desc):
        is_last = idx == len(tiers_desc) - 1
        branch  = "└" if is_last else "├"

        if count >= threshold:
            lines.append(f"{branch}{E_CHECK} <b>x{mult:g}</b>  —  {E_PEOPLE} {threshold}+")
        elif next_tier is not None and threshold == next_tier[0]:
            lower = lower_of[threshold]
            span  = threshold - lower
            done  = max(0, count - lower)
            bar   = _progress_bar(done, span, length=11)
            pct   = int(round(100 * done / span)) if span else 100
            lines.append(f"{branch}{E_TARGET} <b>x{mult:g}</b>  —  {E_PEOPLE} {count}/{threshold}")
            lines.append(f"│    [{bar}] {pct}%")
        else:
            lines.append(f"{branch}{E_LOCKED} <b>x{mult:g}</b>  —  {E_PEOPLE} {threshold}+")

    if lines:
        lines[0] = f"┌{lines[0][1:]}"
    return lines


# ─────────────────────────────────────────
#  ТЕКСТ ДЛЯ ПОЛЬЗОВАТЕЛЯ
# ─────────────────────────────────────────


def ivent_text(lang: str = "ru") -> str:
    state = get_event_state()

    if not state:
        if lang == "en":
            return (
                f'<blockquote>'
                f'{E_GLOBE} <b>Global Referral Marathon</b>\n'
                f'<i>No event is running right now.</i>\n'
                f'Stay tuned — announcements will follow!'
                f'</blockquote>'
            )
        return (
            f'<blockquote>'
            f'{E_GLOBE} <b>Глобальный реферальный марафон</b>\n'
            f'<i>Сейчас ивент не запущен.</i>\n'
            f'Следи за анонсами — скоро стартуем!'
            f'</blockquote>'
        )

    active   = is_event_active(state)
    count    = get_event_referral_count(state)
    mult     = get_current_multiplier()
    tier     = get_tier_for_count(count)
    nxt      = get_next_tier(count)
    name     = state["name_en"] if lang == "en" and state.get("name_en") else state["name_ru"]
    name     = name or (EVENT_TITLE_EN if lang == "en" else EVENT_TITLE_RU)

    if lang == "en":
        status_line = (
            f"{E_CLOCK} <b>Time left:</b> {_fmt_timedelta_en(get_seconds_left(state))}"
            if active else
            f"{E_CLOCK} <b>Event has ended</b>"
        )
        header = (
            f'<blockquote>'
            f'{E_GLOBE} <b>{name}</b>\n'
            f'<i>One shared goal for the ENTIRE community — every referral '
            f'from every player adds to the SAME counter below.</i>\n'
            f'{status_line}'
            f'</blockquote>\n'
            f'<blockquote>'
            f'{E_PEOPLE} <b>GLOBAL counter (all players combined):</b>\n'
            f'<b>{count}</b> {"referrals" if lang == "en" else "рефералов"}'
            f'</blockquote>\n'
        )
    else:
        status_line = (
            f"{E_CLOCK} <b>Осталось времени:</b> {_fmt_timedelta(get_seconds_left(state))}"
            if active else
            f"{E_CLOCK} <b>Ивент завершён</b>"
        )
        header = (
            f'<blockquote>'
            f'{E_GLOBE} <b>{name}</b>\n'
            f'<i>Общая цель для ВСЕХ игроков сразу — каждый реферал '
            f'от любого игрока пополняет ОДИН общий счётчик ниже.</i>\n'
            f'{status_line}'
            f'</blockquote>\n'
            f'<blockquote>'
            f'{E_PEOPLE} <b>ОБЩИЙ счётчик (сумма по всем игрокам):</b>\n'
            f'<b>{count}</b> рефералов'
            f'</blockquote>\n'
        )

    scale_lines = _tier_scale_lines(count, lang)
    scale_title = "Bonus ladder (shared for everyone)" if lang == "en" else "Лестница бонусов (общая для всех)"
    scale_block = (
        f'<blockquote>'
        f'{E_STARI} <b>{scale_title}</b>\n'
        + "\n".join(scale_lines) +
        f'</blockquote>\n'
    )

    if active:
        if mult > 1.0:
            if lang == "en":
                boost_block = (
                    f'<blockquote>'
                    f'{E_FIRE} <b>Boost live for EVERYONE right now: x{mult:g}</b>\n'
                )
            else:
                boost_block = (
                    f'<blockquote>'
                    f'{E_FIRE} <b>Бонус уже действует у ВСЕХ игроков: x{mult:g}</b>\n'
                )
        else:
            if lang == "en":
                boost_block = f'<blockquote>{E_ROCKET} <b>No bonus yet — invite friends to unlock it for everyone!</b>\n'
            else:
                boost_block = f'<blockquote>{E_ROCKET} <b>Бонус ещё не открыт — приглашай друзей, чтобы включить его для всех!</b>\n'

        if nxt:
            need = nxt[0] - count
            if lang == "en":
                boost_block += f'<i>{need} more referrals (from anyone!) to unlock x{nxt[1]:g}</i></blockquote>'
            else:
                boost_block += f'<i>Ещё {need} {_ru_word_refs(need)} (от кого угодно!) до x{nxt[1]:g}</i></blockquote>'
        else:
            if lang == "en":
                boost_block += f'<i>Maximum tier reached — x5.0 unlocked for everyone!</i></blockquote>'
            else:
                boost_block += f'<i>Максимальный уровень открыт — x5.0 у всех игроков!</i></blockquote>'
    else:
        if lang == "en":
            boost_block = (
                f'<blockquote>{E_COINI} <b>Final boost reached: x{mult:g}</b>\n'
                f'<i>The event is over, mining speed is back to normal.</i></blockquote>'
            )
        else:
            boost_block = (
                f'<blockquote>{E_COINI} <b>Финальный достигнутый бонус: x{mult:g}</b>\n'
                f'<i>Ивент завершён, скорость добычи вернулась к обычной.</i></blockquote>'
            )

    return header + scale_block + boost_block


def _ru_word_refs(n: int) -> str:
    """Склонение слова 'реферал' под число."""
    n_abs = abs(n) % 100
    n1 = n_abs % 10
    if 11 <= n_abs <= 14:
        return "рефералов"
    if n1 == 1:
        return "реферал"
    if 2 <= n1 <= 4:
        return "реферала"
    return "рефералов"


# ─────────────────────────────────────────
#  ХЕНДЛЕРЫ (регистрируются на общий dp проекта)
# ─────────────────────────────────────────

from aiogram.filters import Command
from aiogram.types import Message
from mainhelp import dp, bot, ADMIN_IDS


def _lang_of(uid: int) -> str:
    """Пытается определить язык пользователя через database.py,
    если это не удалось — используется 'ru' по умолчанию."""
    try:
        from database import get_user
        u = get_user(uid) or {}
        return u.get("lang", "ru")
    except Exception:
        return "ru"


@dp.message(Command("event", "ивент", "событие"))
async def cmd_event(message: Message):
    lang = _lang_of(message.from_user.id)
    await message.answer(
        ivent_text(lang),
        parse_mode="HTML",
    )


@dp.message(Command("startevent"))
async def cmd_startevent(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    state = get_event_state()
    if state and is_event_active(state):
        left = _fmt_timedelta(get_seconds_left(state))
        await message.answer(f"⚠️ Ивент уже запущен. Осталось: {left}")
        return
    start_event()
    await message.answer(
        f"{E_PARTY} <b>Ивент запущен!</b>\n"
        f"Длительность: {EVENT_DURATION_DAYS} дней.\n"
        f"Шкала бонусов: 25→x1.3, 75→x1.5, 150→x2.0, 500→x3.0, 1000→x5.0",
        parse_mode="HTML",
    )


@dp.message(Command("stopevent"))
async def cmd_stopevent(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    stop_event()
    await message.answer("🛑 Ивент остановлен вручную.")


@dp.message(Command("eventstats"))
async def cmd_eventstats(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    state = get_event_state()
    if not state:
        await message.answer("Ивент ещё ни разу не запускался.")
        return
    count = get_event_referral_count(state)
    mult  = get_current_multiplier()
    active = is_event_active(state)
    start_str = datetime.fromtimestamp(state["start_ts"], tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    await message.answer(
        f"📊 <b>Статистика ивента</b>\n"
        f"Старт: {start_str}\n"
        f"Активен: {'да' if active else 'нет'}\n"
        f"Рефералов за ивент: {count}\n"
        f"Текущий множитель: x{mult:g}",
        parse_mode="HTML",
    )


# ─────────────────────────────────────────
#  ASYNC-ОБЁРТКИ (для вызова из miner.py и др. async-кода)
# ─────────────────────────────────────────
import asyncio as _asyncio


async def aio_get_current_multiplier() -> float:
    return await _asyncio.to_thread(get_current_multiplier)


# Синоним для читаемости в интеграциях (miner.py и т.д.)
aio_get_event_multiplier = aio_get_current_multiplier


async def aio_is_event_active() -> bool:
    return await _asyncio.to_thread(is_event_active)


async def aio_get_event_referral_count() -> int:
    return await _asyncio.to_thread(get_event_referral_count)


async def aio_ivent_text(lang: str = "ru") -> str:
    return await _asyncio.to_thread(ivent_text, lang)


# ─────────────────────────────────────────
#  ИНИЦИАЛИЗАЦИЯ ТАБЛИЦЫ ПРИ ИМПОРТЕ
# ─────────────────────────────────────────
init_event_db()
