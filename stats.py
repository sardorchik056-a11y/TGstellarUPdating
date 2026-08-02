# ============================================================
#  stats.py  —  Статистика бота TGStellar
# ============================================================

import sqlite3
import json
import time
import asyncio
from database import DB_PATH

# ---------- Инициализация ----------

def init_stats_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_stats (
                uid       INTEGER PRIMARY KEY,
                last_seen INTEGER NOT NULL DEFAULT 0,
                joined_ts INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.commit()


# ---------- Трекинг ----------

def _is_onboarded(conn: sqlite3.Connection, uid: int) -> bool:
    """
    Прошёл ли пользователь онбординг (капча → язык).
    Пока не прошёл — это просто голый /start, который может быть накруткой
    (боты, реф-фарм и т.п.), поэтому такие uid не должны попадать в статистику.
    """
    row = conn.execute("SELECT data_json FROM users WHERE uid=?", (uid,)).fetchone()
    if row is None:
        return False
    try:
        return bool(json.loads(row[0]).get("onboarded", True))
    except Exception:
        return True


def track_user(uid: int, joined_ts: int = 0):
    now = int(time.time())
    with sqlite3.connect(DB_PATH) as conn:
        if not _is_onboarded(conn, uid):
            return
        conn.execute("""
            INSERT INTO user_stats (uid, last_seen, joined_ts)
            VALUES (?, ?, ?)
            ON CONFLICT(uid) DO UPDATE SET last_seen = excluded.last_seen
        """, (uid, now, joined_ts or now))
        conn.commit()


# ---------- Асинхронная обёртка (использовать из async-хендлеров!) ----------
# track_user() дёргает sqlite3 синхронно и раньше вызывалась напрямую из
# event loop почти в каждом хендлере mainhelp.py (диск-I/O блокировал всех
# пользователей одновременно). Теперь — только через asyncio.to_thread.

async def aio_track_user(uid: int, joined_ts: int = 0) -> None:
    await asyncio.to_thread(track_user, uid, joined_ts)


# ---------- Очистка накрутки (/clear) ----------
# Раньше track_user() писался в user_stats на КАЖДЫЙ /start, даже если
# пользователь не прошёл капчу/выбор языка (onboarded=False) — отсюда
# расхождение между "статистикой" и реальным числом получателей рассылки
# (rass.py шлёт только тем, у кого onboarded=True). Новые /start такие
# uid'ы больше не создают (см. _is_onboarded выше), но старые записи
# нужно вычистить один раз вручную.

def clear_unregistered() -> int:
    """
    Удаляет из user_stats всех uid, которые так и не прошли онбординг
    (onboarded=False), а также uid, которых вообще нет в таблице users
    (данные потерялись/уже удалены). Возвращает число удалённых записей.
    """
    with sqlite3.connect(DB_PATH) as conn:
        stats_uids = [r[0] for r in conn.execute("SELECT uid FROM user_stats").fetchall()]
        if not stats_uids:
            return 0

        onboarded_map: dict[int, bool] = {}
        for row_uid, data_json in conn.execute("SELECT uid, data_json FROM users").fetchall():
            try:
                onboarded_map[row_uid] = bool(json.loads(data_json).get("onboarded", True))
            except Exception:
                onboarded_map[row_uid] = True

        to_delete = [uid for uid in stats_uids if not onboarded_map.get(uid, False)]

        if to_delete:
            conn.executemany(
                "DELETE FROM user_stats WHERE uid=?",
                [(uid,) for uid in to_delete]
            )
            conn.commit()

    return len(to_delete)


async def aio_clear_unregistered() -> int:
    return await asyncio.to_thread(clear_unregistered)


# ---------- Онлайн ----------

def _count_online(seconds: int) -> int:
    threshold = int(time.time()) - seconds
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM user_stats WHERE last_seen >= ?",
            (threshold,)
        ).fetchone()
    return row[0] if row else 0


# ---------- Новые пользователи ----------

def _count_new(seconds: int) -> int:
    threshold = int(time.time()) - seconds
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM user_stats WHERE joined_ts >= ?",
            (threshold,)
        ).fetchone()
    return row[0] if row else 0


def total_users() -> int:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT COUNT(*) FROM user_stats").fetchone()
    return row[0] if row else 0


# ---------- Текст и клавиатура ----------

_EMOJI_ONLINE = "5906727823355156804"
_EMOJI_USERS  = "5258513401784573443"
_EMOJI_CLOCK  = "5906852613629941703"
_EMOJI_ARROW  = "5332724926216428039"
_EMOJI_NEW    = "5397916757333654639"


def _e(eid: str, fallback: str = "▪️") -> str:
    return f'<tg-emoji emoji-id="{eid}">{fallback}</tg-emoji>'


def stats_text(lang: str = "ru") -> str:
    from lang import t
    o5m  = _count_online(5 * 60)
    o24h = _count_online(24 * 3600)
    o7d  = _count_online(7 * 24 * 3600)
    o30d = _count_online(30 * 24 * 3600)

    n5m  = _count_new(5 * 60)
    n24h = _count_new(24 * 3600)
    n7d  = _count_new(7 * 24 * 3600)
    n30d = _count_new(30 * 24 * 3600)

    total = total_users()

    return (
        f'<blockquote>'
        f'{_e(_EMOJI_ONLINE)} <b>{t(lang, "stats_title_online")}</b>\n\n'
        f'{_e(_EMOJI_CLOCK)} {t(lang, "stats_5min")} — <b>{o5m}</b>\n'
        f'{_e(_EMOJI_CLOCK)} {t(lang, "stats_24h")} — <b>{o24h}</b>\n'
        f'{_e(_EMOJI_CLOCK)} {t(lang, "stats_week")} — <b>{o7d}</b>\n'
        f'{_e(_EMOJI_CLOCK)} {t(lang, "stats_month")} — <b>{o30d}</b>'
        f'</blockquote>\n'
        f'<blockquote>'
        f'{_e(_EMOJI_USERS)} <b>{t(lang, "stats_title_users")}</b>\n\n'
        f'{_e(_EMOJI_ARROW)} {t(lang, "stats_total")} — <b>{total:,}</b>\n'
        f'{_e(_EMOJI_NEW)} {t(lang, "stats_5min")} — <b>{n5m}</b>\n'
        f'{_e(_EMOJI_NEW)} {t(lang, "stats_24h")} — <b>{n24h}</b>\n'
        f'{_e(_EMOJI_NEW)} {t(lang, "stats_week")} — <b>{n7d}</b>\n'
        f'{_e(_EMOJI_NEW)} {t(lang, "stats_month")} — <b>{n30d}</b>'
        f'</blockquote>'
    )


async def aio_stats_text(lang: str = "ru") -> str:
    """Асинхронная обёртка stats_text() — сама stats_text() внутри делает
    несколько синхронных sqlite3-запросов (COUNT'ы), поэтому в event loop
    её вызывать напрямую нельзя, только через to_thread."""
    return await asyncio.to_thread(stats_text, lang)


def stats_keyboard(lang: str = "ru"):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    from miner import EMOJI_BACK
    from lang import t
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=t(lang, "btn_back"),
        callback_data="back_to_menu",
        icon_custom_emoji_id=EMOJI_BACK
    ))
    return builder.as_markup()
