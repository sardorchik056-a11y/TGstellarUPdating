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

EVENT_TITLE_RU = "Реферальный марафон"
EVENT_TITLE_EN = "Referral Marathon"

# Рабочие emoji-id (переиспользованы из refs.py / miner.py — те же, что
# уже используются в проекте, чтобы стиль совпадал 1-в-1).
_E_FRIENDS = "5332724926216428039"
_E_TIMER   = "5382194935057372936"
_E_COIN    = "5199552030615558774"
_E_STAR    = "5267500801240092311"
_E_LEVEL   = "5375338737028841420"

from miner import EMOJI_BACK  # тот же back-icon, что и во всём проекте


def _tg(eid: str, fb: str = "") -> str:
    return f'<tg-emoji emoji-id="{eid}">{fb}</tg-emoji>'


E_ROCKET  = "🚀"
E_PARTY   = "🎉"
E_FIRE    = "🔥"
E_CHECK   = "✅"
E_ARROW   = "▶️"
E_LOCK    = "⬜"
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
        return "█" * length
    ratio  = max(0.0, min(1.0, value / total))
    filled = int(round(ratio * length))
    filled = min(length, max(0, filled))
    return "█" * filled + "░" * (length - filled)


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
    """Строит красивую шкалу уровней с прогресс-баром на активном уровне."""
    lines: list[str] = []
    prev_threshold = 0
    next_shown = False

    for threshold, mult in EVENT_TIERS:
        if count >= threshold:
            # Уровень уже достигнут
            lines.append(f"{E_CHECK} <b>{threshold}</b> {E_PEOPLE} → <b>x{mult:g}</b>")
        elif not next_shown:
            # Это ближайший недостигнутый уровень — показываем прогресс-бар
            span = threshold - prev_threshold
            done = count - prev_threshold
            bar  = _progress_bar(done, span)
            pct  = int(round(100 * done / span)) if span else 100
            if lang == "en":
                lines.append(
                    f"{E_ARROW} <b>{threshold}</b> {E_PEOPLE} → <b>x{mult:g}</b>\n"
                    f"    [{bar}] {count}/{threshold} ({pct}%)"
                )
            else:
                lines.append(
                    f"{E_ARROW} <b>{threshold}</b> {E_PEOPLE} → <b>x{mult:g}</b>\n"
                    f"    [{bar}] {count}/{threshold} ({pct}%)"
                )
            next_shown = True
        else:
            lines.append(f"{E_LOCK} <b>{threshold}</b> {E_PEOPLE} → <b>x{mult:g}</b>")
        prev_threshold = threshold

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
                f'{E_PARTY} <b>Referral Event</b>\n'
                f'<i>No event is running right now.</i>\n'
                f'Stay tuned — announcements will follow!'
                f'</blockquote>'
            )
        return (
            f'<blockquote>'
            f'{E_PARTY} <b>Реферальный ивент</b>\n'
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
            f'{E_PARTY} <b>{name}</b>\n'
            f'{status_line}\n'
            f'{E_PEOPLE} <b>Total referrals invited:</b> {count}'
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
            f'{E_PARTY} <b>{name}</b>\n'
            f'{status_line}\n'
            f'{E_PEOPLE} <b>Всего приглашено рефералов:</b> {count}'
            f'</blockquote>\n'
        )

    scale_lines = _tier_scale_lines(count, lang)
    scale_title = "Scale of bonuses" if lang == "en" else "Шкала бонусов"
    scale_block = (
        f'<blockquote>'
        f'{E_STARI} <b>{scale_title}:</b>\n'
        + "\n".join(scale_lines) +
        f'</blockquote>\n'
    )

    if active:
        if mult > 1.0:
            if lang == "en":
                boost_block = (
                    f'<blockquote>'
                    f'{E_FIRE} <b>Current mining boost: x{mult:g}</b>\n'
                )
            else:
                boost_block = (
                    f'<blockquote>'
                    f'{E_FIRE} <b>Текущий бонус к добыче: x{mult:g}</b>\n'
                )
        else:
            if lang == "en":
                boost_block = f'<blockquote>{E_ROCKET} <b>No bonus yet — invite friends!</b>\n'
            else:
                boost_block = f'<blockquote>{E_ROCKET} <b>Бонус ещё не активен — приглашай друзей!</b>\n'

        if nxt:
            need = nxt[0] - count
            if lang == "en":
                boost_block += f'<i>{need} more referrals to reach x{nxt[1]:g}</i></blockquote>'
            else:
                boost_block += f'<i>Ещё {need} {_ru_word_refs(need)} до x{nxt[1]:g}</i></blockquote>'
        else:
            if lang == "en":
                boost_block += f'<i>Maximum tier reached — x5.0 unlocked!</i></blockquote>'
            else:
                boost_block += f'<i>Максимальный уровень достигнут — x5.0!</i></blockquote>'
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
#  КЛАВИАТУРА
# ─────────────────────────────────────────

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def ivent_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=("🔄 Refresh" if lang == "en" else "🔄 Обновить"),
        callback_data="ivent_refresh",
    ))
    builder.row(InlineKeyboardButton(
        text=("‹ Back" if lang == "en" else "‹ Назад"),
        callback_data="main_menu",
        icon_custom_emoji_id=EMOJI_BACK,
    ))
    return builder.as_markup()


# ─────────────────────────────────────────
#  ХЕНДЛЕРЫ (регистрируются на общий dp проекта)
# ─────────────────────────────────────────

from aiogram import F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
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
        reply_markup=ivent_keyboard(lang),
        parse_mode="HTML",
    )


@dp.callback_query(F.data == "ivent_refresh")
async def cb_ivent_refresh(call: CallbackQuery):
    lang = _lang_of(call.from_user.id)
    new_text = ivent_text(lang)
    try:
        await call.message.edit_text(
            new_text,
            reply_markup=ivent_keyboard(lang),
            parse_mode="HTML",
        )
    except Exception:
        pass
    await call.answer("✅ Обновлено" if lang == "ru" else "✅ Updated")


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
